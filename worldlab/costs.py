"""Durable provider-usage ledger. USD estimates are distinct from invoices."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


PRICE_BOOK = {
    "currency": "USD", "checked_at": "2026-10-25", "service_tier": "default",
    "context": "Text only, <=272000 input tokens, standard global endpoint",
    "models": {
        "gpt-6-luna": {"input": "0.10", "cached_input": "0.01", "cache_write": "0.125", "output": "0.50",
                       "source": "https://developers.openai.com/api/docs/models/gpt-6-luna"},
        "gpt-6.1-sol": {"input": "2.00", "cached_input": "0.10", "cache_write": "2.50", "output": "10.00",
                       "source": "https://developers.openai.com/api/docs/models/gpt-6.1-sol"},
    },
}


def amount(value):
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("Cost and budget must be finite and nonnegative")
    return result


def usd(value):
    return format(amount(value), ".10f")


def token_count(value):
    if type(value) is not int or value < 0:
        raise ValueError("Provider token counts must be nonnegative integers")
    return value


def usage_cost(model, usage, price_book=None):
    rates = (price_book or PRICE_BOOK)["models"][model]
    incoming = token_count(usage["input_tokens"])
    outgoing = token_count(usage["output_tokens"])
    details = usage.get("input_tokens_details") or {}
    cached = token_count(details.get("cached_tokens", 0))
    writes = token_count(details.get("cache_write_tokens", 0))
    reasoning = token_count((usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0))
    if cached + writes > incoming or reasoning > outgoing:
        raise ValueError("Inconsistent provider usage breakdown")
    # Reasoning is already INCLUDED in output_tokens. Never charge it twice.
    return ((incoming - cached - writes) * amount(rates["input"])
            + cached * amount(rates["cached_input"]) + writes * amount(rates["cache_write"])
            + outgoing * amount(rates["output"])) / 1_000_000


class BudgetExceeded(RuntimeError):
    pass


class CostLedger:
    def __init__(self, path: Path, budget, *, max_in_flight=1):
        self.path, self.budget = path, amount(budget)
        if type(max_in_flight) is not int or not 1 <= max_in_flight <= 20:
            raise ValueError("max_in_flight must be 1–20")
        self.max_in_flight = max_in_flight
        self.uncertain_calls = set()
        self.spent = Decimal(0)
        self.pending = {}
        self.held = {}
        self.receipts = []
        self.contexts = {}
        if path.exists():
            raise ValueError("Use a new experiment directory; an existing cost ledger is never overwritten")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.append({"event": "ledger", "budget_usd": usd(self.budget), "price_book": PRICE_BOOK,
                     "max_in_flight": max_in_flight,
                     "basis": "Provider-reported usage × recorded rates; excludes infrastructure, tax and Codex credits"})

    def append(self, event):
        with self.path.open("a") as stream:
            stream.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), **event}, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def reserve(self, model, input_tokens, max_output_tokens, context):
        if self.uncertain_calls or len(self.pending) >= self.max_in_flight:
            raise RuntimeError("An unresolved API call or the in-flight limit prevents further spending")
        if not 0 < token_count(input_tokens) <= 32_000:
            raise ValueError("This runner permits 1–32000 counted input tokens per call")
        rates = PRICE_BOOK["models"][model]
        maximum = (input_tokens * max(amount(rates["input"]), amount(rates["cache_write"]))
                   + token_count(max_output_tokens) * amount(rates["output"])) / 1_000_000
        if self.spent + sum(self.pending.values(), Decimal(0)) + sum(self.held.values(), Decimal(0)) + maximum > self.budget:
            raise BudgetExceeded("Remaining budget cannot cover this call's reserved maximum")
        call_id = uuid.uuid4().hex
        self.append({"event": "reserved", "call_id": call_id, "model": model,
                     "input_tokens_counted": input_tokens, "reserved_usd": usd(maximum), **context})
        self.pending[call_id] = maximum
        self.contexts[call_id] = dict(context)
        return call_id

    def received(self, call_id, model, response, latency_ms):
        if call_id not in self.pending and call_id not in self.held:
            raise ValueError("Cannot charge a call without a pending reservation")
        # Preserve the response and usage BEFORE parsing an action: invalid decisions still cost money.
        self.append({"event": "response", "call_id": call_id, "response": response, "latency_ms": latency_ms})
        usage = response.get("usage")
        returned_model = response.get("model", "")
        if (not usage or response.get("service_tier") not in (None, "default", "standard")
                or not (returned_model == model or returned_model.startswith(model + "-"))):
            raise RuntimeError("Missing usage or unverified returned model/tier; cost remains unresolved")
        cost = usage_cost(model, usage)
        receipt = {"call_id": call_id, "response_id": response.get("id"), "model": returned_model,
                   "usage": usage, "estimated_cost_usd": usd(cost), "latency_ms": latency_ms}
        self.append({"event": "charged", **receipt})
        self.spent += cost
        self.pending.pop(call_id, None)
        self.held.pop(call_id, None)
        self.uncertain_calls.discard(call_id)
        self.receipts.append(receipt)
        if self.spent > self.budget:
            raise BudgetExceeded("Reported usage exceeded the budget; experiment stopped")
        return receipt

    def uncertain(self, call_id, error_type):
        self.uncertain_calls.add(call_id)
        self.append({"event": "unresolved", "call_id": call_id, "error_type": error_type,
                     "note": "No usage receipt; call may have been billed. No retry or zero-cost claim."})

    def quarantine(self, call_id, reason):
        """Retain an unknown request's entire bound without treating it as billed or free."""
        if call_id not in self.pending or call_id not in self.uncertain_calls:
            raise ValueError('Only a stopped, uncertain request may be quarantined')
        maximum = self.pending[call_id]
        self.append({'event': 'quarantined', 'call_id': call_id, 'reserved_usd': usd(maximum),
                     'reason': reason, 'note': 'No usage receipt. Full reservation retained; request never replayed.'})
        self.held[call_id] = self.pending.pop(call_id)
        self.uncertain_calls.remove(call_id)

    def summary(self):
        unknown = {**self.held, **self.pending}
        result = {"currency": "USD", "estimated_cost_usd": usd(self.spent),
                "budget_usd": usd(self.budget), "completed_calls": len(self.receipts),
                "unresolved_calls": len(unknown),
                "unresolved_reserved_usd": usd(sum(unknown.values(), Decimal(0))),
                "accounting": "estimated_from_reported_usage" if not unknown else "incomplete_usage",
                "input_tokens": sum(r["usage"]["input_tokens"] for r in self.receipts),
                "output_tokens": sum(r["usage"]["output_tokens"] for r in self.receipts),
                "reasoning_tokens": sum((r["usage"].get("output_tokens_details") or {}).get("reasoning_tokens", 0)
                                        for r in self.receipts)}

        if self.held:
            result.update(quarantined_calls=len(self.held), quarantined_reserved_usd=usd(sum(self.held.values(), Decimal(0))))
        return result
