"""Bounded JSON-lines RPC across incompatible upstream dependency graphs."""
from __future__ import annotations

import json
import os
import selectors
import signal
import subprocess
import threading
import time
from pathlib import Path

from .common import ROOT


class WorkerError(RuntimeError):
    """A transport or worker failure; callers must not assume a tick committed."""


class WorkerRemoteError(WorkerError):
    def __init__(self, message, *, failed=False, kind="RuntimeError"):
        super().__init__(message)
        self.failed = failed
        self.kind = kind


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
            bufsize=0, start_new_session=True,
        )
        self.lock = threading.RLock()
        self.buffer = bytearray()
        os.set_blocking(self.process.stdin.fileno(), False)

    def call(self, command: str, timeout: float = 180, **payload):
        with self.lock:
            if timeout <= 0:
                raise ValueError("RPC timeout must be positive")
            if self.process.poll() is not None:
                raise WorkerError(f"Worker exited; inspect {self.log}")
            request = (json.dumps({"command": command, **payload}) + "\n").encode()
            deadline = time.monotonic() + timeout
            try:
                with selectors.DefaultSelector() as writable:
                    writable.register(self.process.stdin, selectors.EVENT_WRITE)
                    remaining_bytes = memoryview(request)
                    while remaining_bytes:
                        remaining_time = deadline - time.monotonic()
                        if remaining_time <= 0 or not writable.select(remaining_time):
                            self.terminate()
                            raise TimeoutError(f"Worker timed out receiving a request; inspect {self.log}")
                        try:
                            count = os.write(self.process.stdin.fileno(), remaining_bytes)
                            remaining_bytes = remaining_bytes[count:]
                        except BlockingIOError:
                            continue
            except (BrokenPipeError, OSError) as exc:
                if isinstance(exc, TimeoutError):
                    raise
                raise WorkerError(f"Worker disconnected; inspect {self.log}") from exc
            with selectors.DefaultSelector() as selector:
                selector.register(self.process.stdout, selectors.EVENT_READ)
                while b"\n" not in self.buffer:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not selector.select(remaining):
                        self.terminate()
                        raise TimeoutError(f"Worker timed out; inspect {self.log}")
                    chunk = os.read(self.process.stdout.fileno(), 65536)
                    if not chunk:
                        raise WorkerError(f"Worker disconnected before completing a response; inspect {self.log}")
                    self.buffer.extend(chunk)
                    if len(self.buffer) > 16 * 1024 * 1024:
                        self.terminate()
                        raise WorkerError("Worker response exceeded 16 MiB")
            line, _, trailing = self.buffer.partition(b"\n")
            self.buffer = bytearray(trailing)
            try:
                result = json.loads(line)
                if not isinstance(result, dict) or type(result.get("ok")) is not bool:
                    raise ValueError("Expected an RPC response envelope")
            except (ValueError, UnicodeDecodeError) as exc:
                self.terminate()
                raise WorkerError(f"Worker returned an invalid response; inspect {self.log}") from exc
            if not result["ok"]:
                raise WorkerRemoteError(str(result.get("error", "Worker failed")),
                                        failed=bool(result.get("failed")), kind=result.get("kind", "RuntimeError"))
            return result.get("result")

    def terminate(self):
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                return
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
