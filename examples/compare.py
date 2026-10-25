"""Paired policy experiments using the public API and real saved worlds."""
import argparse
import asyncio
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import httpx
from worldlab.client import LabClient
from worldlab.common import write_json
from worldlab.models import LabAction
from worldlab.scenarios import validate_scenario


async def compare(args):
    scenario = validate_scenario(json.loads(args.scenario.read_text()) if args.scenario else None)
    if args.warmup < 0 or args.steps < 1 or args.warmup + args.steps > scenario["max_steps"]:
        raise ValueError("warmup + steps must fit inside the scenario's max_steps")
    rows = []
    async with LabClient(base_url=args.url, message_timeout_s=180) as client, httpx.AsyncClient(base_url=args.url, timeout=180) as http:
        for seed in args.seeds:
            initial = (await client.reset(seed=seed, population=args.population, scenario=scenario)).observation.snapshot
            for _ in range(args.warmup):
                initial = (await client.step(LabAction())).observation.snapshot
            response = await http.post(f"/lab/runs/{initial['run_id']}/checkpoint")
            response.raise_for_status()
            checkpoint = response.json()["checkpoint_id"]
            row = {"seed": seed, "checkpoint_id": checkpoint, "initial": initial["metrics"], "branches": {}}
            for policy in ("open", "friction"):
                current = (await client.reset(checkpoint_id=checkpoint, policy=policy)).observation.snapshot
                trajectory = [current["metrics"]]
                for _ in range(args.steps):
                    current = (await client.step(LabAction())).observation.snapshot
                    trajectory.append(current["metrics"])
                row["branches"][policy] = {"run_id": current["run_id"], "trajectory": trajectory}
            rows.append(row)
            # Persist each finished pair, so a later failed seed loses no results.
            write_json(args.output, {"scenario": scenario, "experiments": rows})
            ends = {p: row["branches"][p]["trajectory"][-1]["unverified_sharers"] for p in ("open", "friction")}
            print(f"seed={seed}: open={ends['open']}, friction={ends['friction']}", flush=True)
    differences = [r["branches"]["open"]["trajectory"][-1]["unverified_sharers"] - r["branches"]["friction"]["trajectory"][-1]["unverified_sharers"] for r in rows]
    summary = {"paired_mean_difference": statistics.mean(differences), "seeds": len(rows),
               "interpretation": "Descriptive effect of scripted rules; not a real-population estimate"}
    write_json(args.output, {"scenario": scenario, "experiments": rows, "summary": summary})
    print(f"Saved {args.output}; paired mean difference: {summary['paired_mean_difference']:.2f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 8, 9])
    parser.add_argument("--population", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/comparison.json"))
    asyncio.run(compare(parser.parse_args()))


if __name__ == "__main__":
    main()
