"""AgentSociety 2 driver: one authoritative clock, OASIS as an EnvBase module."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import signal
import sys
import traceback
import uuid
from datetime import datetime
from pathlib import Path

from .common import DATA, ROOT, START, TICK_SECONDS, metrics, policy_name, read_json, safe_id, write_json

WIRE = sys.stdout
sys.stdout = sys.stderr
for key, value in {
    "MEM0_TELEMETRY": "False", "ANONYMIZED_TELEMETRY": "False",
    "RAY_USAGE_STATS_ENABLED": "0", "LITELLM_LOCAL_MODEL_COST_MAP": "True",
    "AGENTSOCIETY_LLM_API_KEY": "unused-offline-policy",
    "AGENTSOCIETY_LLM_API_BASE": "http://127.0.0.1:9/v1",
}.items():
    os.environ[key] = value

import ray
from agentsociety2.agent.service_proxy import LLMClients, ServiceProxy
from agentsociety2.env import EnvBase, RouterBase
from agentsociety2.society import AgentSociety
from agentsociety2.storage.replay_proxy import ReplayProxy

from .rpc import Worker
from .checkpoints import inventory, validate_checkpoint
from .scenarios import validate_scenario


class NoLLM:
    """Fail closed if a future adapter accidentally attempts a model call."""
    async def call(self, *args, **kwargs):
        raise RuntimeError("The scripted runtime never calls language models")


class OasisModule(EnvBase):
    """Apply proposals only after ALL agents observed the same tick boundary."""
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    async def step(self, tick, t):
        c = self.controller
        for aid in range(1, c.config["population"] + 1):
            agent = read_json(c.run_dir / "agents" / f"agent_{aid:04d}" / "AGENT.json")
            if agent["step_count"] != c.society.step_count + 1:
                raise RuntimeError("Agent clock diverged from society")
            action = agent["intent"]
            if action["kind"] != "wait":
                result = c.oasis.call("action", actor=aid, action=action, step=c.society.step_count + 1)
                c.event(aid, action, result)


class LabRouter(RouterBase):
    async def ask(self, ctx, instruction, readonly=False, **kwargs):
        raise RuntimeError("This prototype uses explicit typed actions, not a code-generating router")


class Controller:
    def __init__(self):
        self.society = None
        self.oasis = None
        self.failed = False
        # Capture the executing revision once; a developer editing a source file
        # while this process runs must not relabel an old world as the new code.
        self.code_hashes = self.adapter_hashes()
        self.upstreams = read_json(ROOT / "upstreams.json")

    async def reset(self, *, seed=7, population=20, policy=None, checkpoint_id=None, scenario=None, **kwargs):
        if type(seed) is not int or seed < 0 or seed > 2**32 - 1:
            raise ValueError("Seed must be an integer from 0 to 2^32-1")
        if type(population) is not int or not 4 <= population <= 100:
            raise ValueError("Population must be between 4 and 100")
        if policy is not None:
            policy_name(policy)
        parameters = validate_scenario(scenario)
        if checkpoint_id and scenario is not None:
            raise ValueError("A checkpoint keeps its scenario; only policy may be changed")
        source = None
        if checkpoint_id:
            source = DATA / "checkpoints" / safe_id(checkpoint_id)
            validate_checkpoint(source, upstreams=self.upstreams, adapter_hashes=self.code_hashes)
        self.failed = True
        await self.close_world()
        self.run_id = uuid.uuid4().hex
        self.run_dir = DATA / "runs" / self.run_id
        if source:
            shutil.copytree(source, self.run_dir)
            (self.run_dir / "manifest.json").unlink()
            if inventory(self.run_dir) != read_json(source / "manifest.json")["files"]:
                raise ValueError("Checkpoint changed while restoring")
            self.config = read_json(self.run_dir / "scenario.json")
            if policy is not None:
                self.config["policy"] = policy
            self.config["parent_checkpoint"] = checkpoint_id
        else:
            self.run_dir.mkdir(parents=True)
            self.config = {"seed": seed, "population": population, "policy": policy or "open", **parameters}
        write_json(self.run_dir / "scenario.json", self.config)
        provenance = self.run_dir / "provenance"
        provenance.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "worldlab/scripted_agent.py", provenance / "lab_agent.py")
        self.oasis = Worker(".venv-oasis", "worldlab.oasis_worker", self.run_dir / "oasis.log")
        self.oasis.call("open", database=str(self.run_dir / "oasis.sqlite"))
        if not source:
            self.oasis.call("seed", population=population, seed=seed,
                            content=self.config["initial_content"], verified=self.config["initial_verified"])
        if not ray.is_initialized():
            ray.init(num_cpus=2, include_dashboard=False, object_store_memory=100_000_000,
                     log_to_driver=False, _node_ip_address="127.0.0.1",
                     runtime_env={"worker_process_setup_hook": "worldlab.worker_setup.register"})
        self.module = OasisModule(self)
        self.router = LabRouter([self.module], llm_clients_spec={"coder": NoLLM(), "default": NoLLM()})
        self.proxy = ServiceProxy(env={}, llm=LLMClients(None, None), trace=None,
                                  replay=ReplayProxy(str(self.run_dir / "replay")), run_dir=self.run_dir)
        if source:
            self.society = await AgentSociety.from_workspace(self.run_dir, env_router=self.router, service_proxy=self.proxy)
        else:
            specs = [{"id": aid, "profile": {"id": aid, "name": f"Agent {aid:02}"},
                      "config": {"enable_todo_list": False}} for aid in range(1, population + 1)]
            self.society = AgentSociety(specs, "LabAgent", self.router, datetime.fromisoformat(START),
                                        self.run_dir, service_proxy=self.proxy, batch_size=10)
        await self.society.init()
        await self.society.to_workspace()
        state = self.snapshot()
        state["status"] = "paused"
        self.save_frame(state)
        self.failed = False
        return state

    def event(self, actor, action, result):
        record = {"step": self.society.step_count + 1, "actor": actor, "action": action, "result": result}
        with (self.run_dir / "events.jsonl").open("a") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def snapshot(self):
        if self.society is None:
            raise RuntimeError("Reset the environment before use")
        world = self.oasis.call("snapshot", step=self.society.step_count)
        return {
            "run_id": self.run_id, "step": self.society.step_count,
            "time": self.society.current_time.isoformat(), "scenario": self.config,
            "world": world, "metrics": metrics(world, self.config["population"]),
            "done": self.society.step_count >= self.config["max_steps"],
            "engines": {"agentsociety2": "2.9.3", "oasis": "0.2.5", "openenv": "0.10.1.dev0"},
            "status": "failed" if self.failed else "paused",
        }

    def save_frame(self, state):
        write_json(self.run_dir / "frames" / f'{state["step"]:04d}.json', state)
        write_json(self.run_dir / "latest.json", state)

    async def step(self, action):
        if self.society is None or self.failed:
            raise RuntimeError("Reset or restore a checkpoint before continuing")
        if self.society.step_count >= self.config["max_steps"]:
            raise ValueError("Episode finished; reset to start another")
        # Reject an invalid external action before changing either engine.
        kind = action["kind"]
        if kind not in {"wait", "post", "repost"}:
            raise ValueError("Unsupported action")
        if kind == "post" and not 1 <= len(action.get("content", "").strip()) <= 1000:
            raise ValueError("Post content must contain 1–1000 characters")
        if kind == "repost":
            posts = self.oasis.call("snapshot")["posts"]
            target = next((p for p in posts if p["post_id"] == action.get("post_id")), None)
            if target is None:
                raise ValueError("Post does not exist")
            if any(p["user_id"] == 0 and p["root_id"] == target["root_id"] for p in posts):
                raise ValueError("External agent already shared this post")
        try:
            result = self.oasis.call("action", actor=0, action=action, step=self.society.step_count + 1)
            if kind != "wait":
                self.event(0, action, result)
            frozen = self.oasis.call("snapshot")
            self.proxy.env = {"snapshot": frozen, "seed": self.config["seed"],
                              "step": self.society.step_count, "policy": self.config["policy"], "scenario": self.config}
            await self.society.step(TICK_SECONDS)
            state = self.snapshot()
            self.save_frame(state)
            return state
        except Exception as exc:
            self.failed = True  # Never continue from a partially committed tick.
            # Keep the last committed world, but make its failure visible to
            # clients and to operators inspecting runs after a process exit.
            try:
                last = read_json(self.run_dir / "latest.json")
                last.update(status="failed", error=str(exc))
                write_json(self.run_dir / "latest.json", last)
            except Exception:
                traceback.print_exc(file=sys.stderr)
            raise

    async def checkpoint(self):
        if self.society is None or self.failed:
            raise RuntimeError("Only a healthy paused world can be checkpointed")
        await self.society.to_workspace()
        checkpoint_id = uuid.uuid4().hex
        target = DATA / "checkpoints" / checkpoint_id
        staging = target.with_name(checkpoint_id + ".tmp")
        shutil.copytree(self.run_dir, staging, ignore=shutil.ignore_patterns("*.log", "*.sqlite", "__pycache__"))
        self.oasis.call("backup", path=str(staging / "oasis.sqlite"))
        manifest = {"schema_version": 1, "source_run": self.run_id, "step": self.society.step_count,
                    "upstreams": self.upstreams, "adapter_hashes": self.code_hashes,
                    "files": inventory(staging)}
        write_json(staging / "manifest.json", manifest)
        staging.rename(target)
        return {"checkpoint_id": checkpoint_id, "step": self.society.step_count}

    @staticmethod
    def adapter_hashes():
        return {name: hashlib.sha256((ROOT / "worldlab" / name).read_bytes()).hexdigest()
                for name in ("common.py", "scripted_agent.py", "controller.py", "oasis_worker.py", "checkpoints.py", "scenarios.py")}

    async def close_world(self):
        if self.society:
            await self.society.close()
            self.society = None
        if self.oasis:
            self.oasis.close()
            self.oasis = None


async def main():
    controller = Controller()
    try:
        for line in sys.stdin:
            command = None
            try:
                request = json.loads(line)
                command = request.pop("command")
                if command == "reset":
                    result = await controller.reset(**request)
                elif command == "step":
                    result = await controller.step(request["action"])
                elif command == "state":
                    result = controller.snapshot()
                elif command == "checkpoint":
                    result = await controller.checkpoint()
                elif command == "close":
                    await controller.close_world()
                    ray.shutdown()
                    result = None
                else:
                    raise ValueError(f"Unknown command: {command}")
                response = {"ok": True, "result": result}
            except Exception as exc:
                traceback.print_exc(file=sys.stderr)
                response = {"ok": False, "error": str(exc), "kind": type(exc).__name__, "failed": controller.failed}
            WIRE.write(json.dumps(response, ensure_ascii=False) + "\n")
            WIRE.flush()
            if command == "close":
                break
    finally:
        await controller.close_world()
        ray.shutdown()


if __name__ == "__main__":
    def terminate(signum, frame):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, terminate)
    asyncio.run(main())
