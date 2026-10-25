import copy
import hashlib
import json
from pathlib import Path

import pytest

from worldlab.audit import AuditError, audit_ledger
from worldlab.common import write_json
from worldlab.costs import CostLedger, PRICE_BOOK
from worldlab.reports import build_html_report, main, reconciled_report


@pytest.fixture
def experiment(tmp_path):
    ledger = CostLedger(tmp_path / "costs.jsonl", "0.10")
    call = ledger.reserve("gpt-6-luna", 1000, 1024, {"seed": 7, "branch": "candidate"})
    response = {"id": "resp_fixture", "model": "gpt-6-luna", "service_tier": "default", "usage": {
        "input_tokens": 1000, "output_tokens": 200, "input_tokens_details": {"cached_tokens": 200, "cache_write_tokens": 100},
        "output_tokens_details": {"reasoning_tokens": 100}}}
    ledger.received(call, "gpt-6-luna", response, 20)
    metric = {"step": 2, "signal_sharers": 3, "external_reposts": 0}
    report = {"status": "completed", "mode": "real-openai", "cost": ledger.summary(),
              "candidate": {"model": "gpt-6-luna"}, "experiments": [{"seed": 7, "checkpoint_id": "a" * 32,
                  "initial_world_sha256": "b" * 64, "branches": {
                      "baseline": {"status": "completed", "trajectory": [metric], "estimated_cost_usd": "0"},
                      "candidate": {"status": "completed", "trajectory": [metric], "estimated_cost_usd": "0"}}}]}
    write_json(tmp_path / "report.json", report)
    return tmp_path, ledger, call


def rewrite_events(path, transform):
    events = [json.loads(line) for line in path.read_text().splitlines()]
    path.write_text("".join(json.dumps(event) + "\n" for event in transform(events)))


def test_audit_recovers_durable_response_after_crash_and_uses_recorded_rates(experiment, monkeypatch):
    directory, ledger, call = experiment
    journal = directory / "costs.jsonl"
    rewrite_events(journal, lambda events: [e for e in events if e["event"] != "charged"])
    before = journal.read_bytes()
    changed = copy.deepcopy(PRICE_BOOK["models"])
    changed["gpt-6-luna"]["output"] = "999"
    monkeypatch.setitem(PRICE_BOOK, "models", changed)
    result = audit_ledger(journal)
    assert result["recovered_receipts"] == 1
    assert result["summary"]["estimated_cost_usd"] == "0.0001845000"
    assert result["summary"]["unresolved_calls"] == 0
    assert journal.read_bytes() == before


def test_audit_does_not_turn_pending_or_truncated_usage_into_free_calls(experiment):
    directory, ledger, call = experiment
    journal = directory / "costs.jsonl"
    rewrite_events(journal, lambda events: events[:2])
    result = audit_ledger(journal)
    assert result["summary"]["unresolved_calls"] == 1
    assert result["summary"]["accounting"] == "incomplete_usage"
    assert result["summary"]["unresolved_reserved_usd"] != "0.0000000000"
    report, audit = reconciled_report(directory)
    assert report["status"] == "needs_reconciliation"
    assert report["experiments"][0]["branches"]["candidate"]["unresolved_calls"] == 1
    with journal.open("a") as stream:
        stream.write('{"event":"response","call_id":')
    result = audit_ledger(journal)
    assert result["journal_truncated"] is True
    assert result["summary"]["accounting"] == "incomplete_journal"


@pytest.mark.parametrize("damage", ["price", "duplicate", "malformed"])
def test_complete_but_contradictory_journals_fail_closed(experiment, damage):
    directory, ledger, call = experiment
    path = directory / "costs.jsonl"
    if damage == "price":
        def tamper(events):
            events[-1]["estimated_cost_usd"] = "0"
            return events
        rewrite_events(path, tamper)
    elif damage == "duplicate":
        rewrite_events(path, lambda events: events + [events[-1]])
    else:
        with path.open("a") as stream:
            stream.write("not-json\n")
    with pytest.raises(AuditError):
        audit_ledger(path)
    assert main([str(directory), "--check"]) == 2


def test_report_reconciles_costs_and_escapes_untrusted_posts_and_reasons(experiment):
    directory, ledger, call = experiment
    payload = '</summary><script>alert("unsafe")</script>'
    event = {"event": "decision", "decision_id": "decision1", "seed": 7, "branch": "candidate", "step": 2,
             "action": {"kind": "post", "content": payload}, "reason": payload,
             "observation": {"view": "agent-v1", "feed": [{"content": payload}]}}
    (directory / "decisions.jsonl").write_text(json.dumps(event) + "\n")
    source, report, audit = build_html_report(directory)
    assert "<script>" not in source
    assert "&lt;script&gt;" in source
    assert "application unconfirmed" in source
    assert report["experiments"][0]["estimated_model_cost_usd"] == "0.0001845000"
    assert "Original signal sharers" in source


def test_read_only_audit_preserves_all_source_files_and_can_write_derivative_html(experiment):
    directory, ledger, call = experiment
    originals = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()}
    assert main([str(directory), "--check"]) == 0
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()} == originals
    assert main([str(directory)]) == 0
    assert (directory / "report.html").is_file()
    assert (directory / "audit.json").is_file()
    for name, digest in originals.items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest


def test_journal_symlink_is_not_read(experiment, tmp_path):
    directory, ledger, call = experiment
    (directory / "outside.jsonl").symlink_to(directory / "costs.jsonl")
    with pytest.raises(AuditError, match="symbolic"):
        audit_ledger(directory / "outside.jsonl")
