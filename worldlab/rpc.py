"""Bounded JSON-lines RPC across incompatible upstream dependency graphs."""
from __future__ import annotations

import json
import os
import selectors
import signal
import subprocess
import threading
from pathlib import Path

from .common import ROOT


class Worker:
    def __init__(self, runtime: str, module: str, log: Path):
        python = ROOT / runtime / "bin/python"
        if not python.exists():
            raise RuntimeError("Dependencies missing. Run ./scripts/bootstrap.py first.")
        log.parent.mkdir(parents=True, exist_ok=True)
        self.log = log
        self.stderr = log.open("a")
        env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONUNBUFFERED="1")
        self.process = subprocess.Popen(
            [str(python), "-m", module], cwd=ROOT, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
            text=True, bufsize=1, start_new_session=True,
        )
        self.lock = threading.RLock()

    def call(self, command: str, timeout: float = 180, **payload):
        with self.lock:
            if self.process.poll() is not None:
                raise RuntimeError(f"Worker exited; inspect {self.log}")
            self.process.stdin.write(json.dumps({"command": command, **payload}) + "\n")
            self.process.stdin.flush()
            with selectors.DefaultSelector() as selector:
                selector.register(self.process.stdout, selectors.EVENT_READ)
                if not selector.select(timeout):
                    self.terminate()
                    raise TimeoutError(f"Worker timed out; inspect {self.log}")
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError(f"Worker disconnected; inspect {self.log}")
            result = json.loads(line)
            if not result["ok"]:
                raise RuntimeError(result["error"])
            return result.get("result")

    def terminate(self):
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(10)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(5)

    def close(self):
        try:
            if self.process.poll() is None:
                self.call("close", timeout=20)
                self.process.wait(10)
        except (OSError, RuntimeError, TimeoutError, subprocess.TimeoutExpired):
            self.terminate()
        finally:
            self.stderr.close()
            for stream in (self.process.stdin, self.process.stdout):
                stream.close()
