"""One-command paired experiments, with a dedicated local server and durable costs."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import secrets
import signal
import socket
import statistics
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .ai_policy import OpenAIPolicy, VisibleFeedBaseline
from .client import LabClient
from .common import DATA, ROOT, read_json, write_json
from . import __version__
from .costs import BudgetExceeded, CostLedger, PRICE_BOOK, amount, usd
from .models import LabAction
from .errors import safe_error
from .scenarios import validate_scenario


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def world_fingerprint(snapshot):
    return fingerprint({key: snapshot[key] for key in ("world", "time", "step")})


def append_decision(path, value):
    with path.open("a") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


COMPARISON_METRICS = ("signal_sharers", "external_signal_reposts", "unverified_sharers",
                      "external_reposts", "external_unverified_posts")


def operator_metrics(snapshot):
    # OASIS seeds the scenario's initial signal as post 1. Other new posts
    # (including requests for evidence) must not count as that signal spreading.
    signal = {p["user_id"] for p in snapshot["world"]["posts"] if p["root_id"] == 1 and p["user_id"] != 0}
    own = [post for post in snapshot["world"]["posts"] if post["user_id"] == 0]
    return {**snapshot["metrics"], "step": snapshot["step"], "signal_sharers": len(signal),
            "external_signal_reposts": sum(p["root_id"] == 1 for p in own), "external_posts": len(own),
            "external_reposts": sum(p["original_post_id"] is not None for p in own),
            "external_unverified_posts": sum(not p["verified"] for p in own)}


def save_report(output, report, ledger):
    report["cost"] = ledger.summary()
    for row in report["experiments"]:
        row["estimated_model_cost_usd"] = usd(sum(amount(branch["estimated_cost_usd"]) for branch in row["branches"].values()))
    write_json(output / "report.json", report)
    lines = ["# Agent World Lab — paired experiment", "", f"Status: **{report['status']}**",
             f"Mode: `{report['mode']}`", "",
             f"Estimated model cost: **US${report['cost']['estimated_cost_usd']}**",
             f"Budget: US${report['cost']['budget_usd']}; unresolved calls: {report['cost']['unresolved_calls']}",
             "", "Costs use provider-reported tokens and the recorded price book; they are not a billing invoice.",
             "Infrastructure, taxes and development/Codex credits are excluded.", "",
             "| Seed | Branch | Initial signal sharers | External reposts | Model cost USD |",
             "| --- | --- | ---: | ---: | ---: |"]
    for row in report["experiments"]:
        for name, branch in row["branches"].items():
            end = branch["trajectory"][-1]
            lines.append(f"| {row['seed']} | {name} | {end['signal_sharers']} | {end['external_reposts']} | {branch['estimated_cost_usd']} |")
    lines += ["", "Both branches start from the same checkpoint and use the same background policy.",
              "The baseline reposts the newest eligible visible post; the candidate receives the same scoped view.",
              "A model is not guaranteed to reproduce its decisions. Scripted diffusion is not a human prediction.",
              "", "Artifacts: `report.json`, `decisions.jsonl`, `costs.jsonl`, `engine/runs/`, `engine/checkpoints/`."]
    if report.get("error"):
        lines += ["", f"Stopped: {report['error'].get('message', report['error'].get('type')) if isinstance(report['error'], dict) else report['error']}"]
    (output / "report.md").write_text("\n".join(lines) + "\n")


@contextmanager
def experiment_server(output):
    """Credentials are process-local and never written to reports or command lines."""
    operator, agent = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    server_env = dict(os.environ, PORT=str(port), WORLDLAB_DATA=str(output / "engine"),
                      WORLDLAB_OPERATOR_TOKEN=operator, WORLDLAB_AGENT_TOKEN=agent)
    server_env.pop("OPENAI_API_KEY", None)
    server_env.pop("OPENAI_BASE_URL", None)
    url = f"http://127.0.0.1:{port}"
    with (output / "server.log").open("w") as log:
        process = subprocess.Popen([sys.executable, "-m", "worldlab.agent_server"], cwd=ROOT,
                                   env=server_env, stdout=log, stderr=log)
        try:
            with httpx.Client(timeout=2, trust_env=False) as http:
                deadline = time.monotonic() + 90
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError("Scoped server exited; inspect server.log")
                    try:
                        if http.get(url + "/health").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.2)
                else:
                    raise TimeoutError("Scoped server startup timed out")
            yield url, operator, agent
        finally:
            process.terminate()
            try:
                process.wait(30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(5)


async def run_paired(args, url, operator_token, agent_token, candidate, ledger, report):
    async with LabClient(base_url=url, message_timeout_s=180, mode="simulation",
                         headers={"Authorization": "Bearer " + agent_token}) as client, \
            httpx.AsyncClient(base_url=url, timeout=180, trust_env=False,
                              headers={"Authorization": "Bearer " + operator_token}) as operator:
        async def snapshot(run_id):
            response = await operator.get(f"/lab/runs/{run_id}/snapshot")
            response.raise_for_status()
            return response.json()

        async def reset(**parameters):
            response = await operator.post("/lab/reset-tickets", json=parameters)
            response.raise_for_status()
            return (await client.reset(ticket=response.json()["ticket"])).observation.snapshot

        for seed in args.seeds:
            observation = await reset(seed=seed, population=args.population, scenario=report["scenario"], policy="open")
            for _ in range(args.warmup):
                observation = (await client.step(LabAction())).observation.snapshot
            initial = await snapshot(observation["run_id"])
            response = await operator.post(f"/lab/runs/{observation['run_id']}/checkpoint")
            response.raise_for_status()
            checkpoint_id = response.json()["checkpoint_id"]
            row = {"seed": seed, "checkpoint_id": checkpoint_id,
                   "initial_world_sha256": world_fingerprint(initial), "branches": {}}
            report["experiments"].append(row)
            for name, policy in (("baseline", VisibleFeedBaseline()), ("candidate", candidate)):
                observation = await reset(checkpoint_id=checkpoint_id)
                full = await snapshot(observation["run_id"])
                if world_fingerprint(full) != row["initial_world_sha256"]:
                    raise RuntimeError("Branches did not start from the exact checkpoint world")
                branch = {"run_id": observation["run_id"], "initial_world_sha256": world_fingerprint(full),
                          "status": "running", "trajectory": [operator_metrics(full)],
                          "world_sha256": [world_fingerprint(full)],
                          "estimated_cost_usd": usd(0)}
                row["branches"][name] = branch
                before = ledger.spent
                save_report(args.output, report, ledger)
                try:
                    for index in range(args.steps):
                        if observation["done"]:
                            raise RuntimeError("Episode ended before the planned horizon")
                        action, decision = await policy.decide(observation, seed=seed, branch=name)
                        decision_id = uuid.uuid4().hex
                        append_decision(args.output / "decisions.jsonl", {
                            "event": "decision", "decision_id": decision_id, "seed": seed, "branch": name,
                            "step": observation["step"], "observation": observation,
                            "observation_sha256": fingerprint(observation),
                            "action": action.model_dump(exclude={"metadata"}), **decision})
                        observation = (await client.step(action)).observation.snapshot
                        append_decision(args.output / "decisions.jsonl", {
                            "event": "applied", "decision_id": decision_id, "resulting_step": observation["step"]})
                        full = await snapshot(observation["run_id"])
                        branch["trajectory"].append(operator_metrics(full))
                        branch["world_sha256"].append(world_fingerprint(full))
                        branch["estimated_cost_usd"] = usd(ledger.spent - before)
                        save_report(args.output, report, ledger)
                        print(f"seed={seed} branch={name} step={index + 1}/{args.steps} cost_usd={branch['estimated_cost_usd']}", flush=True)
                    branch["status"] = "completed"
                finally:
                    branch["estimated_cost_usd"] = usd(ledger.spent - before)
                    save_report(args.output, report, ledger)
            if report["mode"] == "offline-baseline-self-check":
                verify_self_check(row)
            row["candidate_minus_baseline"] = {
                key: row["branches"]["candidate"]["trajectory"][-1][key] - row["branches"]["baseline"]["trajectory"][-1][key]
                for key in COMPARISON_METRICS}
            save_report(args.output, report, ledger)
    report["summary"] = {"pairs": len(report["experiments"]), "mean_candidate_minus_baseline": {
        key: statistics.mean(row["candidate_minus_baseline"][key] for row in report["experiments"])
        for key in COMPARISON_METRICS}}
    report["status"] = "completed"
    save_report(args.output, report, ledger)


def verify_self_check(pair):
    left, right = pair["branches"]["baseline"], pair["branches"]["candidate"]
    if left["world_sha256"] != right["world_sha256"] or left["trajectory"] != right["trajectory"]:
        raise RuntimeError("Offline self-check diverged: complete world trajectories must match")
    pair["full_trajectory_match"] = True


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--policy", choices=["openai", "baseline"], default="openai",
                   help="baseline is an OFFLINE self-check, never an AI run")
    p.add_argument("--model", choices=list(PRICE_BOOK["models"]), default="gpt-6-luna")
    p.add_argument("--effort", choices=["low", "medium", "high"], default="low")
    p.add_argument("--max-output-tokens", type=int, default=1024)
    p.add_argument("--budget-usd", default="0.10", help="Total generation budget across all seeds")
    p.add_argument("--seeds", type=int, nargs="+", default=[7, 8, 9])
    p.add_argument("--population", type=int, default=20)
    p.add_argument("--warmup", type=int, default=2)
    p.add_argument("--steps", type=int, default=5)
    p.add_argument("--scenario", type=Path)
    p.add_argument("--env-file", type=Path, default=ROOT / ".env")
    p.add_argument("--output", type=Path)
    return p


def main(argv=None):
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    try:
        scenario = validate_scenario(json.loads(args.scenario.read_text()) if args.scenario else None)
        if not (0 <= args.warmup and 1 <= args.steps and args.warmup + args.steps <= scenario["max_steps"]):
            raise ValueError("warmup + steps must fit inside scenario.max_steps")
        if not 4 <= args.population <= 100 or not 128 <= args.max_output_tokens <= 4096:
            raise ValueError("Population must be 4–100 and max output tokens 128–4096")
        if any(not 0 <= seed <= 2**32 - 1 for seed in args.seeds) or len(set(args.seeds)) != len(args.seeds):
            raise ValueError("Use distinct seeds from 0 to 2^32-1")
        amount(args.budget_usd)
    except (ValueError, ArithmeticError, OSError) as exc:
        argument_parser.error(str(exc) if not isinstance(exc, ArithmeticError) else "Budget must be a finite nonnegative USD amount")
    # The API key stays in the external process. Never send it to the simulation workers.
    api_key = None
    if args.policy == "openai":
        from dotenv import dotenv_values
        api_key = os.environ.get("OPENAI_API_KEY") or dotenv_values(args.env_file, interpolate=False).get("OPENAI_API_KEY")
        if not api_key:
            print("Missing OPENAI_API_KEY. Set it in the environment or .env; no model call was made.", file=sys.stderr)
            return 2
    args.output = (args.output or DATA / "experiments" / uuid.uuid4().hex).resolve()
    try:
        args.output.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        argument_parser.error(safe_error(exc)["message"])
    ledger = CostLedger(args.output / "costs.jsonl", args.budget_usd)
    report = {"schema_version": 1, "status": "running",
              "application": {"name": "Agent World Lab", "version": __version__,
                              "source_sha256": {name: hashlib.sha256((ROOT / "worldlab" / name).read_bytes()).hexdigest()
                                                for name in ("experiment.py", "ai_policy.py", "costs.py", "observations.py", "agent_server.py", "models.py")},
                              "upstreams": read_json(ROOT / "upstreams.json")},
              "started_at": datetime.now(timezone.utc).isoformat(),
              "mode": "real-openai" if args.policy == "openai" else "offline-baseline-self-check",
              "candidate": {"provider": args.policy, "model": args.model if api_key else None,
                            "effort": args.effort if api_key else None},
              "baseline": VisibleFeedBaseline.name, "metric_schema": "initial-signal-v1", "scenario": scenario,
              "config": {"seeds": args.seeds, "population": args.population, "warmup": args.warmup, "steps": args.steps},
              "price_book": PRICE_BOOK, "experiments": []}
    save_report(args.output, report, ledger)

    async def execute(url, operator, agent):
        if api_key:
            from openai import AsyncOpenAI
            # Explicit global standard endpoint. Do not inherit an arbitrary OPENAI_BASE_URL.
            async with AsyncOpenAI(api_key=api_key, base_url="https://api.openai.com/v1", max_retries=0, timeout=60) as provider:
                candidate = OpenAIPolicy(provider, ledger, args.model, args.effort, args.max_output_tokens)
                await run_paired(args, url, operator, agent, candidate, ledger, report)
        else:
            await run_paired(args, url, operator, agent, VisibleFeedBaseline(), ledger, report)

    previous_term = signal.getsignal(signal.SIGTERM)
    def interrupt(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, interrupt)
    try:
        with experiment_server(args.output) as (url, operator, agent):
            asyncio.run(execute(url, operator, agent))
    except BaseException as exc:
        report["status"] = "budget_exhausted" if isinstance(exc, BudgetExceeded) else "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        report["error"] = safe_error(exc)
        for row in report["experiments"]:
            for branch in row["branches"].values():
                if branch["status"] == "running":
                    branch["status"] = report["status"]
        print(report["error"]["message"], file=sys.stderr)
    finally:
        signal.signal(signal.SIGTERM, previous_term)
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        save_report(args.output, report, ledger)
        from .reports import write_html_report
        try:
            write_html_report(args.output)
        except (OSError, ValueError, TypeError, KeyError, ArithmeticError) as exc:
            report["render_error"] = type(exc).__name__
            if report["status"] == "completed":
                report["status"] = "report_failed"
            save_report(args.output, report, ledger)
            print("HTML report could not be rendered. Source results and cost journal remain saved; run scripts/report for an offline audit.", file=sys.stderr)
        print(f"Report: {args.output / 'report.html'}\nEstimated model cost: US${usd(ledger.spent)}; unresolved calls: {len(ledger.pending)}", flush=True)
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
