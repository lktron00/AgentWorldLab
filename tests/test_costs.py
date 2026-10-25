import json
from decimal import Decimal

import pytest

from worldlab.costs import BudgetExceeded, CostLedger, usage_cost


def usage():
    return {"input_tokens": 1000, "output_tokens": 200,
            "input_tokens_details": {"cached_tokens": 200, "cache_write_tokens": 100},
            "output_tokens_details": {"reasoning_tokens": 100}}


def test_price_cache_reads_writes_and_reasoning_without_double_counting():
    assert usage_cost("gpt-6-luna", usage()) == Decimal("0.0001845")
    invalid = usage()
    invalid["input_tokens_details"]["cached_tokens"] = 9999
    with pytest.raises(ValueError):
        usage_cost("gpt-6-luna", invalid)


def test_budget_rejects_before_generation_and_preserves_uncertain_calls(tmp_path):
    ledger = CostLedger(tmp_path / "costs.jsonl", "0.0001")
    with pytest.raises(BudgetExceeded):
        ledger.reserve("gpt-6-luna", 1000, 1024, {})
    assert ledger.summary()["completed_calls"] == 0
    ledger = CostLedger(tmp_path / "other.jsonl", "0.01")
    call = ledger.reserve("gpt-6-luna", 1000, 1024, {})
    ledger.uncertain(call, "TimeoutError")
    assert ledger.summary()["accounting"] == "incomplete_usage"
    assert ledger.summary()["unresolved_calls"] == 1
    with pytest.raises(RuntimeError, match="unresolved"):
        ledger.reserve("gpt-6-luna", 1000, 1024, {})


def test_receipt_is_durable_and_unknown_usage_does_not_become_free(tmp_path):
    path = tmp_path / "costs.jsonl"
    ledger = CostLedger(path, "0.10")
    call = ledger.reserve("gpt-6-luna", 1000, 1024, {"branch": "candidate"})
    receipt = ledger.received(call, "gpt-6-luna", {"id": "response1", "model": "gpt-6-luna",
                                                "usage": usage(), "service_tier": "default"}, 50)
    assert receipt["estimated_cost_usd"] == "0.0001845000"
    assert ledger.summary()["reasoning_tokens"] == 100
    assert [json.loads(line)["event"] for line in path.read_text().splitlines()] == ["ledger", "reserved", "response", "charged"]
    call = ledger.reserve("gpt-6-luna", 1000, 1024, {})
    with pytest.raises(RuntimeError, match="Missing usage"):
        ledger.received(call, "gpt-6-luna", {"model": "gpt-6-luna"}, 10)
    assert ledger.summary()["unresolved_calls"] == 1
    with pytest.raises(ValueError, match="existing cost ledger"):
        CostLedger(path, "0.10")


@pytest.mark.parametrize("budget", ["NaN", "Infinity", "-0.10"])
def test_invalid_budgets_cannot_bypass_limit(tmp_path, budget):
    with pytest.raises(ValueError):
        CostLedger(tmp_path / "costs.jsonl", budget)
