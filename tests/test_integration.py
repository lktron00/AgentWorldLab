"""No mocked engines: live TCP WebSocket + OpenEnv client + Ray + OASIS SQLite."""
import asyncio
import io
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import zipfile

import httpx
import pytest

from worldlab.client import LabClient
from worldlab.common import ROOT
from worldlab.models import LabAction


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    data = tmp_path_factory.mktemp("worldlab-integration")
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    env = dict(os.environ, PORT=str(port), WORLDLAB_DATA=str(data))
    log = (data / "server.log").open("w")
    process = subprocess.Popen([sys.executable, "-m", "worldlab.server"], cwd=ROOT, env=env, stdout=log, stderr=log)
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                if httpx.get(url + "/health", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if process.poll() is not None:
                pytest.fail((data / "server.log").read_text())
            time.sleep(0.2)
        else:
            pytest.fail("Server startup timeout: " + (data / "server.log").read_text())
        yield url, data
    finally:
        process.terminate()
        try:
            process.wait(30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(5)
        log.close()


@pytest.mark.integration
def test_real_engines_checkpoint_replay_branch_and_client(server):
    url, data = server

    async def exercise():
        async with LabClient(base_url=url, message_timeout_s=180) as client:
            initial = (await client.reset(seed=7, population=20)).observation.snapshot
            assert initial["step"] == 0
            assert len(initial["world"]["nodes"]) == 21
            assert initial["metrics"]["posts"] == 1
            run_id = initial["run_id"]
            for _ in range(2):
                saved = (await client.step(LabAction())).observation.snapshot
            assert saved["metrics"]["reposts"] > 0
            async with httpx.AsyncClient(base_url=url, timeout=30) as http:
                response = await http.post(f"/lab/runs/{run_id}/checkpoint")
                assert response.status_code == 200, response.text
                checkpoint = response.json()["checkpoint_id"]
            baseline = []
            for _ in range(5):
                baseline.append((await client.step(LabAction())).observation.snapshot)
            # Restoring the same checkpoint must reproduce every subsequent world,
            # not merely match an aggregate count at the end.
            restored = (await client.reset(checkpoint_id=checkpoint)).observation.snapshot
            assert restored["world"] == saved["world"]
            assert restored["time"] == saved["time"]
            for expected in baseline:
                actual = (await client.step(LabAction())).observation.snapshot
                assert actual["world"] == expected["world"]
                assert actual["metrics"] == expected["metrics"]
                assert actual["time"] == expected["time"]
            # Changed policy, same initial state and counter-based random draws.
            branch = (await client.reset(checkpoint_id=checkpoint, policy="friction")).observation.snapshot
            assert branch["world"] == saved["world"]
            for _ in range(5):
                branch = (await client.step(LabAction())).observation.snapshot
            assert branch["metrics"]["unverified_sharers"] < baseline[-1]["metrics"]["unverified_sharers"]
            # An external agent acts through the typed OpenEnv client.
            posted = (await client.step(LabAction(kind="post", content="Controlled correction", verified=True))).observation.snapshot
            assert any(p["user_id"] == 0 and p["verified"] for p in posted["world"]["posts"])
            assert (await client.state()).step_count == posted["step"]
            # Unknown post must not advance the clock or poison a healthy world.
            with pytest.raises(Exception):
                await client.step(LabAction(kind="repost", post_id=999999))
            assert (await client.state()).step_count == posted["step"]
            current = (await client.step(LabAction())).observation.snapshot
            assert current["step"] == posted["step"] + 1
            run = data / "runs" / current["run_id"]
            with sqlite3.connect(run / "oasis.sqlite") as db:
                assert db.execute("SELECT count(*) FROM post").fetchone()[0] == current["metrics"]["posts"]
                assert db.execute("SELECT count(*) FROM trace WHERE action='repost'").fetchone()[0] > 0
            for agent in (run / "agents").glob("*/AGENT.json"):
                assert json.loads(agent.read_text())["step_count"] == current["step"]
            assert (run / "replay" / "_schema.json").is_file()
            async with httpx.AsyncClient(base_url=url) as http:
                frames = (await http.get(f"/lab/runs/{current['run_id']}/frames")).json()
                assert frames[-1]["world"] == current["world"]
                export = await http.get(f"/lab/runs/{current['run_id']}/export")
                with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
                    assert "upstreams.json" in archive.namelist()
                    assert "events.jsonl" in archive.namelist()
                    provenance = json.loads(archive.read("provenance/adapters.json"))
                    assert "def choose_action" in provenance["sources"]["common.py"]
                    assert len(provenance["hashes"]["common.py"]) == 64
                    assert "oasis.txt" in json.loads(archive.read("provenance/runtime.json"))["requirements"]
        # Close destroys the runtime; the checkpoint must survive a fresh process.
        async with LabClient(base_url=url, message_timeout_s=180) as fresh:
            recovered = (await fresh.reset(checkpoint_id=checkpoint)).observation.snapshot
            assert recovered["world"] == saved["world"]
            assert recovered["time"] == saved["time"]
            assert recovered["run_id"] != saved["run_id"]
            manifest = data / "checkpoints" / checkpoint / "scenario.json"
            original = manifest.read_text()
            manifest.write_text(original + " ")
            with pytest.raises(Exception):
                await fresh.reset(checkpoint_id=checkpoint)
            assert (await fresh.state()).step_count == saved["step"]
            manifest.write_text(original)

    asyncio.run(exercise())


@pytest.mark.integration
def test_partial_tick_failure_is_visible_and_requires_recovery(server):
    url, data = server

    async def exercise():
        async with LabClient(base_url=url, message_timeout_s=180) as client:
            initial = (await client.reset(seed=7, population=4)).observation.snapshot
            async with httpx.AsyncClient(base_url=url, timeout=30) as http:
                response = await http.post(f"/lab/runs/{initial['run_id']}/checkpoint")
                checkpoint = response.json()["checkpoint_id"]
                # Corrupt one agent's clock after a healthy checkpoint. The
                # real AgentSociety task will run, then the barrier must fail.
                path = data / "runs" / initial["run_id"] / "agents/agent_0001/AGENT.json"
                agent = json.loads(path.read_text())
                agent["step_count"] = 99
                path.write_text(json.dumps(agent))
                with pytest.raises(Exception, match="clock diverged"):
                    await client.step(LabAction())
                state = await client.state()
                assert state.status == "failed"
                assert state.step_count == 0
                assert state.error
                with pytest.raises(Exception, match="failed"):
                    await client.step(LabAction())
                response = await http.post(f"/lab/runs/{initial['run_id']}/checkpoint")
                assert response.status_code == 409
                saved = json.loads((path.parents[2] / "latest.json").read_text())
                assert saved["status"] == "failed"
                assert saved["world"] == initial["world"]
            recovered = (await client.reset(checkpoint_id=checkpoint)).observation.snapshot
            assert recovered["world"] == initial["world"]
            assert recovered["status"] == "paused"
            assert (await client.step(LabAction())).observation.snapshot["step"] == 1

    asyncio.run(exercise())


@pytest.mark.integration
def test_sessions_are_independent_and_checkpoint_waits_for_tick(server):
    url, data = server

    async def exercise():
        async with LabClient(base_url=url, message_timeout_s=180) as left, LabClient(base_url=url, message_timeout_s=180) as right:
            a = (await left.reset(population=4, scenario={"max_steps": 2, "initial_content": "Left world", "initial_verified": True})).observation.snapshot
            b = (await right.reset(population=4, scenario={"initial_content": "Right world"})).observation.snapshot
            assert a["run_id"] != b["run_id"]
            async with httpx.AsyncClient(base_url=url, timeout=180) as http:
                moved, response = await asyncio.gather(
                    left.step(LabAction(kind="post", content="Only in left")),
                    http.post(f"/lab/runs/{a['run_id']}/checkpoint"),
                )
                assert response.status_code == 200, response.text
                checkpoint = response.json()["checkpoint_id"]
                manifest = json.loads((data / "checkpoints" / checkpoint / "manifest.json").read_text())
                restored = (await left.reset(checkpoint_id=checkpoint)).observation.snapshot
                assert restored["step"] == manifest["step"]
                expected = a if manifest["step"] == 0 else moved.observation.snapshot
                assert restored["world"] == expected["world"]
            assert (await right.state()).step_count == 0
            other = (await right.step(LabAction())).observation.snapshot
            assert all(p["content"] == "Right world" for p in other["world"]["posts"])
            while not restored["done"]:
                restored = (await left.step(LabAction())).observation.snapshot
            assert restored["step"] == 2
            with pytest.raises(Exception, match="Episode finished"):
                await left.step(LabAction())
            assert (await left.state()).status == "paused"

    asyncio.run(exercise())
