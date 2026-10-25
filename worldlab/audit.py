"""Offline reconciliation of an append-only experiment cost journal. No API calls."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from .costs import amount, token_count, usage_cost, usd


class AuditError(ValueError):
    pass


def receipt_for(model, response, price_book, call_id, latency_ms=0):
    usage = response.get("usage")
    returned = response.get("model", "")
    if (not usage or not isinstance(returned, str)
            or response.get("service_tier") not in (None, "default", "standard")
            or not (returned == model or returned.startswith(model + "-"))):
        raise AuditError("Provider usage, returned model or processing tier is unverified")
    if not isinstance(response.get("id"), str) or not response["id"]:
        raise AuditError("Provider response ID is missing")
    return {"call_id": call_id, "response_id": response["id"], "model": returned,
            "usage": usage, "estimated_cost_usd": usd(usage_cost(model, usage, price_book)),
            "latency_ms": latency_ms}


def audit_ledger(path: Path, *, maximum=128 * 1024 * 1024):
    """Reconstruct receipts from saved responses, never invent zero-cost failures.

    A response may be durable even if the process died before the charged event.
    Its reported usage is sufficient to reconstruct a receipt at recorded rates.
    A partial tail is flagged; malformed or contradictory complete events fail.
    """
    if path.is_symlink() or not path.is_file():
        raise AuditError("Expected a local costs.jsonl file, not a symbolic link")
    if path.stat().st_size > maximum:
        raise AuditError("Cost journal exceeds the configured audit limit")
    header = None
    calls = {}
    warnings = []
    truncated = False
    response_ids = set()
    with path.open("rb") as stream:
        line_number = 0
        while True:
            line = stream.readline(4 * 1024 * 1024 + 1)
            if not line:
                break
            line_number += 1
            if len(line) > 4 * 1024 * 1024:
                raise AuditError(f"Journal line {line_number} exceeds the 4 MiB limit")
            complete = line.endswith(b"\n")
            if not complete:
                truncated = True
                warnings.append("Partial final journal line; accounting may be incomplete")
            try:
                event = json.loads(line)
            except (ValueError, UnicodeDecodeError) as exc:
                if not complete:
                    break
                raise AuditError(f"Malformed journal event at line {line_number}") from exc
            if not isinstance(event, dict):
                raise AuditError(f"Expected an object at journal line {line_number}")
            kind = event.get("event")
            if header is None:
                if kind != "ledger" or not complete:
                    raise AuditError("A complete price-book/header event must be first")
                header = event
                try:
                    budget = amount(header["budget_usd"])
                    price_book = header["price_book"]
                    if price_book["currency"] != "USD" or price_book["service_tier"] != "default":
                        raise ValueError("Unsupported currency or tier")
                    for rates in price_book["models"].values():
                        for rate in ("input", "cached_input", "cache_write", "output"):
                            amount(rates[rate])
                except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                    raise AuditError("Invalid recorded price book or budget") from exc
                continue
            call_id = event.get("call_id")
            if not isinstance(call_id, str) or not call_id:
                raise AuditError(f"Missing call ID at journal line {line_number}")
            if kind == "reserved":
                if call_id in calls:
                    raise AuditError("Duplicate call reservation")
                if event.get("model") not in price_book["models"]:
                    raise AuditError("Reserved model has no recorded price")
                amount(event["reserved_usd"])
                calls[call_id] = {"reservation": event, "receipt": None, "charged": False}
                continue
            if call_id not in calls:
                raise AuditError("Response or receipt has no preceding reservation")
            call = calls[call_id]
            if kind == "response":
                if "response_seen" in call:
                    raise AuditError("Multiple provider responses for one reservation")
                call["response_seen"] = True
                try:
                    receipt = receipt_for(call["reservation"]["model"], event["response"], price_book,
                                          call_id, event.get("latency_ms", 0))
                except (AuditError, ValueError, TypeError, KeyError) as exc:
                    warnings.append(f"Call {call_id}: usage could not be verified ({type(exc).__name__})")
                else:
                    if receipt["response_id"] in response_ids:
                        raise AuditError("Provider response ID appears in more than one call")
                    response_ids.add(receipt["response_id"])
                    call["receipt"] = receipt
            elif kind == "charged":
                if call["charged"] or call["receipt"] is None:
                    raise AuditError("Duplicate or unverifiable charged event")
                receipt = call["receipt"]
                if (event.get("response_id") != receipt["response_id"]
                        or event.get("model") != receipt["model"] or event.get("usage") != receipt["usage"]
                        or amount(event["estimated_cost_usd"]) != amount(receipt["estimated_cost_usd"])):
                    raise AuditError("Charged event contradicts the saved provider usage")
                call["charged"] = True
            elif kind == "unresolved":
                # A timeout can happen after a durable response; prefer its usage
                # if present, otherwise retain the reservation as unknown.
                call["error_type"] = event.get("error_type")
            else:
                raise AuditError(f"Unsupported journal event: {kind}")
    if header is None:
        raise AuditError("Cost journal is empty")
    receipts = [c["receipt"] for c in calls.values() if c["receipt"] is not None]
    unresolved = [c["reservation"] for c in calls.values() if c["receipt"] is None]
    spent = sum((amount(r["estimated_cost_usd"]) for r in receipts), Decimal(0))
    unknown = sum((amount(r["reserved_usd"]) for r in unresolved), Decimal(0))
    summary = {"currency": "USD", "estimated_cost_usd": usd(spent), "budget_usd": usd(budget),
               "completed_calls": len(receipts), "unresolved_calls": len(unresolved),
               "unresolved_reserved_usd": usd(unknown),
               "accounting": "incomplete_journal" if truncated else "incomplete_usage" if unresolved else "estimated_from_reported_usage",
               "input_tokens": sum(token_count(r["usage"]["input_tokens"]) for r in receipts),
               "output_tokens": sum(token_count(r["usage"]["output_tokens"]) for r in receipts),
               "reasoning_tokens": sum(token_count((r["usage"].get("output_tokens_details") or {}).get("reasoning_tokens", 0)) for r in receipts)}
    return {"summary": summary, "price_book": price_book, "receipts": receipts,
            "calls": [{"call_id": key, "seed": call["reservation"].get("seed"),
                       "branch": call["reservation"].get("branch"), "receipt": call["receipt"],
                       "reserved_usd": call["reservation"]["reserved_usd"]} for key, call in calls.items()],
            "recovered_receipts": sum(c["receipt"] is not None and not c["charged"] for c in calls.values()),
            "journal_truncated": truncated, "warnings": warnings,
            "budget_exceeded": spent > budget}
