"""The actual OpenEnv server-side environment; each session owns a world."""
from __future__ import annotations

import threading
import uuid

from openenv.core.env_server.interfaces import Environment

from .common import DATA
from .models import LabAction, LabObservation, LabState
from .rpc import Worker

ACTIVE = {}


class LabEnvironment(Environment[LabAction, LabObservation, LabState]):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        super().__init__()
        self.worker = None
        self.latest = None
        self.lock = threading.RLock()

    def reset(self, seed=None, episode_id=None, **kwargs):
        with self.lock:
            if self.worker is None:
                self.worker = Worker(".venv", "worldlab.controller", DATA / "logs" / f"controller-{uuid.uuid4().hex}.log")
            result = self.worker.call("reset", seed=7 if seed is None else seed,
                                      population=kwargs.get("population", 20), policy=kwargs.get("policy"),
                                      checkpoint_id=kwargs.get("checkpoint_id"))
            if self.latest:
                ACTIVE.pop(self.latest["run_id"], None)
            self.latest = result
            ACTIVE[result["run_id"]] = self
            return LabObservation(snapshot=result, done=result["done"])

    def step(self, action: LabAction, timeout_s=None, **kwargs):
        with self.lock:
            if self.worker is None or self.latest is None:
                raise RuntimeError("Reset first")
            self.latest = self.worker.call("step", action=action.model_dump(exclude={"metadata"}))
            return LabObservation(snapshot=self.latest, done=self.latest["done"])

    @property
    def state(self):
        if self.latest is None:
            return LabState()
        return LabState(episode_id=self.latest["run_id"], run_id=self.latest["run_id"],
                        step_count=self.latest["step"], status=self.latest["status"])

    def checkpoint(self):
        with self.lock:
            if self.worker is None:
                raise RuntimeError("Reset first")
            return self.worker.call("checkpoint")

    def close(self):
        with self.lock:
            if self.latest:
                ACTIVE.pop(self.latest["run_id"], None)
            if self.worker:
                self.worker.close()
                self.worker = None
