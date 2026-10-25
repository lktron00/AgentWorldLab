"""Real three-engine scoped server; no paid provider is invoked by tests."""
import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from worldlab.ai_policy import VisibleFeedBaseline
from worldlab.client import LabClient
from worldlab.costs import CostLedger
from worldlab.experiment import experiment_server, run_paired
from worldlab.models import LabAction
from worldlab.scenarios import validate_scenario


@pytest.fixture(scope="module")
def scoped_server(tmp_path_factory):
    data = tmp_path_factory.mktemp("scoped-engines")
    with experiment_server(data) as (url, operator, agent):
        yield url, operator, agent, data


@pytest.mark.integration
def test_real_agent_view_enforced_and_operator_data_requires_separate_token(scoped_server):
    url, operator, agent, data = scoped_server

    async def exercise():
        async with LabClient(base_url=url, headers={"Authorization": "Bearer " + agent}, message_timeout_s=180) as client:
            async with httpx.AsyncClient(base_url=url, timeout=180) as http:
                response = await http.post("/lab/reset-tickets", json={"seed": 7, "population": 4},
                                           headers={"Authorization": "Bearer " + operator})
                assert response.status_code == 200
                ticket = response.json()["ticket"]
            view = (await client.reset(ticket=ticket)).observation.snapshot
            with pytest.raises(Exception, match="operator-issued"):
                await client.reset(observation_mode="full", scenario={"initial_verified": True})
            with pytest.raises(Exception, match="consumed"):
                await client.reset(ticket=ticket)
            assert view["view"] == "agent-v1"
            assert "world" not in view and "metrics" not in view and "scenario" not in view
            assert view["following"] == [1, 2]
            assert view["feed"] and "verified" not in view["feed"][0]
            async with httpx.AsyncClient(base_url=url, timeout=180) as http:
                route = f"/lab/runs/{view['run_id']}/snapshot"
                assert (await http.get(route, headers={"Authorization": "Bearer " + agent})).status_code == 403
                full = (await http.get(route, headers={"Authorization": "Bearer " + operator})).json()
                assert "world" in full and "metrics" in full
            with pytest.raises(Exception, match="verification"):
                await client.step(LabAction(kind="post", content="Self-certified claim", verified=True))
            assert (await client.state()).step_count == 0
            # Guessing an unavailable ID must not reveal it or advance the clock.
            with pytest.raises(Exception, match="visible feed"):
                await client.step(LabAction(kind="repost", post_id=999999))
            assert (await client.state()).step_count == 0
            moved = (await client.step(LabAction(kind="repost", post_id=view["feed"][0]["post_id"]))).observation.snapshot
            assert moved["step"] == 1 and moved["own_posts"]
            assert "verified" not in moved["own_posts"][0]
            async with httpx.AsyncClient(base_url=url, timeout=180) as http:
                full = (await http.get(route, headers={"Authorization": "Bearer " + operator})).json()
            visible_ids = {p["post_id"] for p in moved["feed"]}
            hidden = next(p for p in full["world"]["posts"] if p["user_id"] not in (0, 1, 2) and p["post_id"] not in visible_ids)
            with pytest.raises(Exception, match="visible feed"):
                await client.step(LabAction(kind="repost", post_id=hidden["post_id"]))
            with pytest.raises(Exception, match="visible feed"):
                await client.step(LabAction(kind="repost", post_id=1))
            assert (await client.state()).step_count == 1

    asyncio.run(exercise())


@pytest.mark.integration
def test_paired_runner_restores_exact_world_and_saves_decisions_and_zero_cost(scoped_server, tmp_path):
    url, operator, agent, data = scoped_server
    args = SimpleNamespace(seeds=[7], population=4, warmup=1, steps=2, output=tmp_path)
    ledger = CostLedger(tmp_path / "costs.jsonl", "0.10")
    report = {"status": "running", "mode": "offline-baseline-self-check", "scenario": validate_scenario(), "experiments": []}
    asyncio.run(run_paired(args, url, operator, agent, VisibleFeedBaseline(), ledger, report))
    assert report["status"] == "completed"
    row = report["experiments"][0]
    baseline, candidate = row["branches"]["baseline"], row["branches"]["candidate"]
    assert baseline["initial_world_sha256"] == candidate["initial_world_sha256"] == row["initial_world_sha256"]
    assert baseline["trajectory"] == candidate["trajectory"]
    assert baseline["world_sha256"] == candidate["world_sha256"]
    assert len(baseline["world_sha256"]) == 3
    assert row["full_trajectory_match"] is True
    assert row["candidate_minus_baseline"] == {"signal_sharers": 0, "external_signal_reposts": 0, "unverified_sharers": 0, "external_reposts": 0, "external_unverified_posts": 0}
    events = [json.loads(line) for line in (tmp_path / "decisions.jsonl").read_text().splitlines()]
    assert len([e for e in events if e["event"] == "decision"]) == 4
    assert len([e for e in events if e["event"] == "applied"]) == 4
    assert ledger.summary()["estimated_cost_usd"] == "0.0000000000"
    assert ledger.summary()["completed_calls"] == 0
    assert (tmp_path / "report.md").is_file()
    assert "operator" not in (tmp_path / "report.json").read_text()
