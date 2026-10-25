import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from worldlab.ai_policy import OpenAIPolicy
from worldlab.costs import BudgetExceeded, CostLedger


def view():
    return {"view": "agent-v1", "step": 0, "feed": [{"post_id": 1, "can_repost": True}]}


def provider(arguments=None, **changes):
    body = {"id": "resp_local_fixture", "model": "gpt-6-luna", "status": "completed", "service_tier": "default",
            "usage": {"input_tokens": 1000, "output_tokens": 200,
                      "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                      "output_tokens_details": {"reasoning_tokens": 50}},
            "output": [{"type": "function_call", "name": "choose_action",
                        "arguments": json.dumps(arguments or {"kind": "wait", "content": "", "post_id": None, "reason": "Insufficient evidence"})}]}
    body.update(changes)
    response = SimpleNamespace(model_dump=lambda **kwargs: copy.deepcopy(body))
    return SimpleNamespace(responses=SimpleNamespace(
        input_tokens=SimpleNamespace(count=AsyncMock(return_value=SimpleNamespace(input_tokens=1000))),
        create=AsyncMock(return_value=response)))


def test_provider_gets_only_scoped_view_and_standard_bounded_request(tmp_path):
    client = provider()
    ledger = CostLedger(tmp_path / "costs.jsonl", "0.10")
    action, decision = asyncio.run(OpenAIPolicy(client, ledger).decide(view()))
    assert action.kind == "wait"
    assert decision["estimated_cost_usd"] == "0.0002000000"
    request = client.responses.create.call_args.kwargs
    assert json.loads(request["input"][0]["content"]) == view()
    assert request["store"] is False
    assert request["service_tier"] == "default"
    assert request["parallel_tool_calls"] is False
    assert request["max_output_tokens"] == 1024


@pytest.mark.parametrize("changes", [
    {"status": "incomplete"}, {"output": []},
    {"output": [{"type": "function_call", "name": "choose_action", "arguments": "invalid json"}]},
])
def test_invalid_model_outputs_still_have_cost_and_no_fallback(tmp_path, changes):
    client = provider(**changes)
    ledger = CostLedger(tmp_path / "costs.jsonl", "0.10")
    with pytest.raises(ValueError):
        asyncio.run(OpenAIPolicy(client, ledger).decide(view()))
    assert ledger.summary()["completed_calls"] == 1
    assert client.responses.create.await_count == 1


def test_hallucinated_hidden_post_rejected_after_usage_is_saved(tmp_path):
    client = provider({"kind": "repost", "content": "", "post_id": 9999, "reason": "guess"})
    ledger = CostLedger(tmp_path / "costs.jsonl", "0.10")
    with pytest.raises(ValueError, match="visible feed"):
        asyncio.run(OpenAIPolicy(client, ledger).decide(view()))
    assert ledger.summary()["completed_calls"] == 1


def test_budget_prevents_generation_and_timeout_stays_unresolved(tmp_path):
    client = provider()
    ledger = CostLedger(tmp_path / "budget.jsonl", "0.00001")
    with pytest.raises(BudgetExceeded):
        asyncio.run(OpenAIPolicy(client, ledger).decide(view()))
    client.responses.create.assert_not_awaited()
    ledger = CostLedger(tmp_path / "timeout.jsonl", "0.10")
    client.responses.create.side_effect = TimeoutError()
    with pytest.raises(TimeoutError):
        asyncio.run(OpenAIPolicy(client, ledger).decide(view()))
    assert ledger.summary()["unresolved_calls"] == 1
    assert client.responses.create.await_count == 1


def test_privileged_snapshot_never_crosses_model_boundary(tmp_path):
    client = provider()
    ledger = CostLedger(tmp_path / "costs.jsonl", "0.10")
    with pytest.raises(ValueError, match="scoped"):
        asyncio.run(OpenAIPolicy(client, ledger).decide({**view(), "world": {"secret": 1}}))
    client.responses.input_tokens.count.assert_not_awaited()
