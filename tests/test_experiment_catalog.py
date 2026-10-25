import json
import os
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from worldlab import experiment_catalog as catalog
from worldlab.common import write_json
from worldlab.costs import CostLedger


def test_catalog_lists_local_reports_and_does_not_read_linked_or_escaped_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "DATA", tmp_path)
    directory = tmp_path / "experiments" / "example-run"
    directory.mkdir(parents=True)
    ledger = CostLedger(directory / "costs.jsonl", "0.10")
    write_json(directory / "report.json", {"status": "completed", "mode": "offline-baseline-self-check",
        "cost": ledger.summary(), "experiments": [{"seed": 7, "checkpoint_id": "a" * 32, "initial_world_sha256": "b" * 64,
        "branches": {name: {"status": "completed", "trajectory": [{"step": 0, "signal_sharers": 1, "external_reposts": 0}], "estimated_cost_usd": "0"} for name in ("baseline", "candidate")}}]})
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "experiments" / "linked").symlink_to(outside, target_is_directory=True)
    app = FastAPI()
    app.include_router(catalog.router)
    with TestClient(app) as client:
        items = client.get("/lab/experiments").json()
        assert len(items) == 1 and items[0]["id"] == "example-run"
        assert items[0]["estimated_cost_usd"] == "0.0000000000"
        response = client.get("/lab/experiments/example-run/report")
        assert response.status_code == 200
        assert "default-src 'none'" in response.headers["content-security-policy"]
        assert "Offline baseline self-check" in response.text
        assert '/lab/experiments/example-run/report.json?download=1' in response.text
        attachment = client.get("/lab/experiments/example-run/report.json?download=1")
        assert attachment.status_code == 200 and 'attachment' in attachment.headers['content-disposition']
        assert attachment.json()["cost"]["completed_calls"] == 0
        assert client.get("/lab/experiments/example-run/report.json").json()["cost"]["completed_calls"] == 0
        assert client.get("/lab/experiments/linked/report").status_code == 404
        assert client.get("/lab/experiments/%2E%2E/report").status_code == 404
        # A receipt written after the saved summary must not appear as a free run.
        ledger.reserve("gpt-6-luna", 1000, 1024, {"seed": 7, "branch": "candidate"})
        stamp = (directory / "report.json").stat().st_mtime_ns + 1_000_000
        os.utime(directory / "costs.jsonl", ns=(stamp, stamp))
        item = client.get("/lab/experiments").json()[0]
        assert item["status"] == "needs_audit" and item["estimated_cost_usd"] is None
        assert client.get("/lab/experiments/example-run/report.json").json()["status"] == "needs_reconciliation"


def test_empty_catalog_is_usable_and_bad_report_does_not_break_listing(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "DATA", tmp_path)
    assert catalog.list_experiments() == []
    bad = tmp_path / "experiments" / "damaged"
    bad.mkdir(parents=True)
    (bad / "report.json").write_text("not-json")
    assert catalog.list_experiments()[0]["status"] == "invalid_artifact"
