"""Standalone HTML reports and offline journal reconciliation for operators."""
from __future__ import annotations

import argparse
import base64
import copy
import html
import json
import math
from decimal import Decimal
from pathlib import Path

from .audit import AuditError, audit_ledger
from .common import write_json
from .costs import amount, usd


def read_artifact(path, maximum=16 * 1024 * 1024):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise AuditError(f"Missing, linked or oversized artifact: {path.name}")
    return json.loads(path.read_text())


def reconciled_report(directory):
    """Build a view without mutating source reports, journals or engine state."""
    report = copy.deepcopy(read_artifact(directory / "report.json"))
    audit = audit_ledger(directory / "costs.jsonl")
    report["cost"] = audit["summary"]
    report["price_book"] = audit["price_book"]
    report["audit"] = {key: audit[key] for key in ("recovered_receipts", "journal_truncated", "warnings", "budget_exceeded")}
    for pair in report["experiments"]:
        for name, branch in pair["branches"].items():
            calls = [c for c in audit["calls"] if c["seed"] == pair["seed"] and c["branch"] == name]
            branch["estimated_cost_usd"] = usd(sum((amount(c["receipt"]["estimated_cost_usd"]) for c in calls if c["receipt"]), Decimal(0)))
            branch["unresolved_calls"] = sum(c["receipt"] is None for c in calls)
        pair["estimated_model_cost_usd"] = usd(sum(amount(b["estimated_cost_usd"]) for b in pair["branches"].values()))
    if report["status"] == "running":
        report["status"] = "unfinished"
    if (audit["journal_truncated"] or audit["summary"]["unresolved_calls"] or audit["budget_exceeded"]):
        report["status"] = "needs_reconciliation"
    # A stale source summary must not claim completion over partial branches.
    if report["status"] == "completed" and (not report["experiments"] or any(
        set(pair["branches"]) != {"baseline", "candidate"}
        or any(b["status"] != "completed" for b in pair["branches"].values()) for pair in report["experiments"]
    )):
        report["status"] = "unfinished"
    return report, audit


def public_decisions(directory):
    path = directory / "decisions.jsonl"
    if not path.exists():
        return []
    if path.is_symlink() or path.stat().st_size > 64 * 1024 * 1024:
        raise AuditError("Linked or oversized decisions journal")
    decisions = []
    applied = set()
    with path.open() as stream:
        for line in stream:
            if not line.endswith("\n"):
                break  # A partial final decision is never rendered as committed.
            event = json.loads(line)
            if event.get("event") == "decision":
                decisions.append(event)
            elif event.get("event") == "applied":
                applied.add(event["decision_id"])
    return [{**d, "applied": d["decision_id"] in applied} for d in decisions[-200:]]


def esc(value):
    return html.escape(str(value), quote=True)


def display_usd(value):
    text = usd(value)
    return text.rstrip("0").rstrip(".") if "." in text else text


def data_link(value):
    encoded = base64.b64encode(json.dumps(value, ensure_ascii=False, indent=2).encode()).decode()
    return "data:application/json;base64," + encoded


def trajectory_chart(branches):
    all_points = [p for b in branches.values() for p in b.get("trajectory", [])]
    if not all_points:
        return '<p class="muted">No committed trajectory yet.</p>'
    start = min(int(p["step"]) for p in all_points)
    end = max(int(p["step"]) for p in all_points)
    maximum = max(1, *(int(p["signal_sharers"]) for p in all_points))
    parts = ['<svg viewBox="0 0 720 220" role="img" aria-label="Original signal sharers by simulation step">']
    for index in range(5):
        y = 180 - index * 40
        parts.append(f'<line x1="45" y1="{y}" x2="700" y2="{y}" stroke="#dde5df"/><text x="35" y="{y+4}" text-anchor="end">{maximum*index/4:g}</text>')
    for name, branch in branches.items():
        if name not in {"baseline", "candidate"}:
            continue
        color = "#bf8432" if name == "baseline" else "#217a62"
        points = []
        for frame in branch.get("trajectory", []):
            x = 45 + (int(frame["step"]) - start) / max(1, end - start) * 655
            y = 180 - int(frame["signal_sharers"]) / maximum * 160
            if not math.isfinite(x + y):
                raise AuditError("Non-finite chart value")
            points.append(f"{x:.2f},{y:.2f}")
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{color}"><title>{esc(name)} · step {int(frame["step"])}: {int(frame["signal_sharers"])} accounts</title></circle>')
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2.5"/>')
    parts += [f'<text x="45" y="208">Step {start}</text><text x="700" y="208" text-anchor="end">Step {end}</text>', '</svg>']
    return "".join(parts)


def render_html(report, audit, decisions, download_url=None):
    cost = report["cost"]
    mode = "Real external AI" if report.get("mode") == "real-openai" else "Offline baseline self-check"
    pairs = []
    for pair in report["experiments"]:
        rows = []
        for name, branch in pair["branches"].items():
            final = branch["trajectory"][-1]
            rows.append(f'<tr><td><span class="dot {esc(name)}"></span>{esc(name)}<span class="branch-status">{esc(branch["status"])}</span></td><td>{int(final["signal_sharers"])}</td><td>{int(final["external_reposts"])}</td><td>${esc(display_usd(branch["estimated_cost_usd"]))}</td></tr>')
        pairs.append(f'''<article class="panel"><div class="panel-head"><h2>Seed {esc(pair['seed'])}</h2><span class="muted">Same checkpoint · same background policy</span></div>
        {trajectory_chart(pair['branches'])}<div class="table-wrap"><table><thead><tr><th>Policy</th><th>Signal sharers</th><th>Reposts</th><th>Model USD</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
        <details><summary>Reproducibility</summary><p class="muted">Initial world + clock SHA-256</p><code class="hash">{esc(pair['initial_world_sha256'])}</code><p class="muted">Checkpoint {esc(pair['checkpoint_id'])}</p></details></article>''')
    receipt_rows = []
    for call in audit["calls"]:
        receipt = call["receipt"]
        if receipt:
            usage = receipt["usage"]
            detail = usage.get("input_tokens_details") or {}
            receipt_rows.append(f'<tr><td>{esc(call["seed"])}</td><td>{esc(call["branch"])}</td><td>{int(usage["input_tokens"])}</td><td>{int(usage["output_tokens"])}</td><td>{int(detail.get("cached_tokens", 0))} / {int(detail.get("cache_write_tokens", 0))}</td><td>${esc(display_usd(receipt["estimated_cost_usd"]))}</td></tr>')
        else:
            receipt_rows.append(f'<tr><td>{esc(call["seed"])}</td><td>{esc(call["branch"])}</td><td colspan="4">Usage unresolved · reserved ${esc(call["reserved_usd"])}</td></tr>')
    decision_cards = []
    for decision in decisions:
        action = decision["action"]
        text = action.get("content") or (f'Post #{action.get("post_id")}' if action.get("post_id") else "No publication")
        observation = json.dumps(decision.get("observation", {}), ensure_ascii=False, indent=2)
        decision_cards.append(f'''<details class="decision"><summary>Seed {esc(decision['seed'])} · {esc(decision['branch'])} · step {esc(decision['step'])} <b>{esc(action['kind'])}</b> <span class="muted">{'applied' if decision['applied'] else 'proposal; application unconfirmed'}</span></summary><p>{esc(text)}</p><p class="muted">{esc(decision.get('reason', ''))}</p><details><summary>Agent's limited observation</summary><pre>{esc(observation)}</pre></details></details>''')
    warnings = audit["warnings"]
    if cost["unresolved_calls"]:
        warnings = [*warnings, "Some generations have no verifiable usage receipt. Known costs are not the full bill; reconcile with provider billing before retrying."]
    alerts = ''.join(f'<p class="alert">{esc(message)}</p>' for message in warnings)
    if report.get("example"):
        alerts += f'<p class="muted">{esc(report.get("example_note", "Bundled recorded example"))}</p>'
    error = report.get("error")
    if error:
        message = error.get("message", error.get("type")) if isinstance(error, dict) else error
        alerts += f'<p class="alert">Experiment stopped: {esc(message)}</p>'
    prices = audit["price_book"]
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Agent World Lab · Experiment report</title><style>
    :root{{--ink:#243832;--muted:#718078;--line:#dce4dc;--green:#217a62}}*{{box-sizing:border-box}}body{{margin:0;background:#f5f6f2;color:var(--ink);font:14px system-ui,sans-serif}}main{{max-width:1120px;margin:auto;padding:36px 28px}}header{{display:flex;align-items:center;justify-content:space-between;gap:20px}}.brand{{font-weight:650;font-size:17px}}.brand i{{font-style:normal;color:var(--green);font-size:28px}}.badge{{padding:7px 10px;border:1px solid var(--line);border-radius:5px;background:white;font-size:11px}}h1{{font:42px Georgia,serif;letter-spacing:-1px;margin:30px 0 10px}}h2{{font-size:16px;margin:0}}.muted{{color:var(--muted);font-size:12px;line-height:1.7}}.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}}.stat,.panel{{background:white;border:1px solid var(--line);border-radius:9px}}.stat{{padding:19px}}.stat span{{display:block;font-size:11px;color:var(--muted)}}.stat b{{display:block;margin:12px 0 5px;font:27px Georgia,serif;overflow-wrap:anywhere}}.pairs{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}.panel{{margin-bottom:18px;padding:20px}}.panel-head{{display:flex;align-items:baseline;justify-content:space-between;gap:15px;margin-bottom:12px}}.panel-head span{{font-size:10px}}svg{{display:block;width:100%;height:auto}}svg text{{fill:#718078;font:11px system-ui,sans-serif}}table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{padding:11px 8px;border-bottom:1px solid #edf1ec;text-align:right;white-space:nowrap}}th{{font-size:10px;color:var(--muted);font-weight:500}}th:first-child,td:first-child{{text-align:left}}.table-wrap{{overflow:auto}}.dot{{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:7px}}.baseline{{background:#bf8432}}.candidate{{background:#217a62}}details{{border-top:1px solid #edf1ec;padding-top:12px;margin-top:12px}}summary{{font-size:12px;cursor:pointer;line-height:1.7}}summary b{{margin:0 12px;color:var(--green)}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f6f8f5;padding:14px;border-radius:5px;font-size:11px;line-height:1.7}}.hash{{font-size:10px;overflow-wrap:anywhere}}.branch-status{{display:block;color:var(--muted);font-size:9px;margin-top:4px}}.stat:first-child b{{font-size:24px;white-space:nowrap;letter-spacing:-.5px}}.decision p{{font-size:12px;line-height:1.7}}.alert{{padding:13px 16px;background:#fff0dd;border:1px solid #ead5b6;border-radius:6px;font-size:12px}}a{{color:var(--green)}}.button{{display:inline-block;border:1px solid var(--line);border-radius:5px;padding:9px 12px;text-decoration:none;font-size:12px;background:white}}footer{{font-size:11px;line-height:1.8;color:var(--muted);border-top:1px solid var(--line);padding-top:20px}}@media(max-width:900px){{.pairs{{grid-template-columns:1fr}}}}@media(max-width:760px){{main{{padding:24px 16px}}h1{{font-size:34px}}.stats{{grid-template-columns:repeat(2,1fr)}}.pairs{{grid-template-columns:1fr}}.panel-head{{display:block}}.panel{{padding:16px}}.stat{{padding:15px}}}}
    </style></head><body><main><header><div class="brand"><i>◈</i> Agent World Lab</div><span class="badge">{'EXAMPLE · ' if report.get('example') else ''}{esc(report['status'].upper())}</span></header>
    <h1>One checkpoint. Two policies.</h1><p class="muted">{esc(mode)} · {esc((report.get('candidate') or {}).get('model') or 'Scripted decisions')} · {esc(report.get('started_at', ''))}</p>
    {alerts}<section class="stats"><article class="stat"><span>Known estimated model cost</span><b>${esc(display_usd(cost['estimated_cost_usd']))}</b><span>USD · budget ${esc(display_usd(cost['budget_usd']))}</span></article><article class="stat"><span>Provider receipts</span><b>{int(cost['completed_calls'])}</b><span>{int(cost['unresolved_calls'])} unresolved calls</span></article><article class="stat"><span>Input / output tokens</span><b>{int(cost['input_tokens']):,} / {int(cost['output_tokens']):,}</b><span>Reasoning included in output</span></article><article class="stat"><span>Paired seeds</span><b>{len(report['experiments'])}</b><span>Frozen starting world and clock</span></article></section>
    <section class="pairs">{''.join(pairs)}</section><article class="panel"><div class="panel-head"><h2>Cost audit</h2><span class="muted">{int(audit['recovered_receipts'])} receipts recovered from saved responses</span></div><div class="table-wrap"><table><thead><tr><th>Seed</th><th>Policy</th><th>Input</th><th>Output</th><th>Cache read / write</th><th>Estimated USD</th></tr></thead><tbody>{''.join(receipt_rows) or '<tr><td colspan="6">No model calls. Baseline self-check costs $0 in model usage.</td></tr>'}</tbody></table></div><p class="muted">Rates recorded {esc(prices.get('checked_at', ''))} · {esc(cost['accounting'])}. Estimates exclude compute, taxes, discounts and Codex development credits; they are not a provider invoice.</p></article>
    <article class="panel"><div class="panel-head"><h2>Decisions and observations</h2><span class="muted">Last 200 proposals · application recorded separately</span></div>{''.join(decision_cards) or '<p class="muted">No decisions recorded yet.</p>'}</article>
    <p><a class="button" download="worldlab-report.json" href="{esc(download_url or data_link(report))}">Download audited JSON ↓</a></p><footer>The baseline reposts the newest eligible visible item. The candidate receives the same limited view. Signal sharers count only the scenario's original signal, excluding account 0. New questions are separate posts. These are descriptive synthetic outcomes, not human predictions or proof of general model superiority. Model decisions are not guaranteed deterministic.</footer></main></body></html>'''


def build_html_report(directory, download_url=None):
    report, audit = reconciled_report(directory)
    decisions = public_decisions(directory)
    return render_html(report, audit, decisions, download_url=download_url), report, audit


def write_html_report(directory):
    source, report, audit = build_html_report(directory)
    path = directory / "report.html"
    temporary = directory / "report.html.tmp"
    temporary.write_text(source)
    temporary.replace(path)
    write_json(directory / "audit.json", {"summary": audit["summary"], **report["audit"]})
    return path, report, audit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="An existing experiment directory")
    parser.add_argument("--check", action="store_true", help="Read-only audit; do not write report.html/audit.json")
    args = parser.parse_args(argv)
    try:
        if args.check:
            report, audit = reconciled_report(args.directory)
        else:
            path, report, audit = write_html_report(args.directory)
            print(f"Report: {path}")
        print(json.dumps({"status": report["status"], "cost": report["cost"], "audit": report["audit"]}, indent=2))
        return 0 if report["status"] == "completed" else 1
    except (AuditError, OSError, ValueError, TypeError, KeyError, ArithmeticError) as exc:
        print(f"Cannot audit experiment: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
