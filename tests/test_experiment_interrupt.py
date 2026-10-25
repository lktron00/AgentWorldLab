"""Real CLI interruption: no provider calls, durable costs and child cleanup."""
import json
import os
import re
import signal
import subprocess
import sys
import time

import pytest

from worldlab.audit import audit_ledger
from worldlab.common import ROOT


@pytest.mark.integration
def test_sigterm_preserves_report_and_stops_owned_server(tmp_path):
    output = tmp_path / "interrupted-experiment"
    with (tmp_path / "cli.log").open("w") as log:
        env = {key: value for key, value in os.environ.items() if key != "OPENAI_API_KEY"}
        process = subprocess.Popen([sys.executable, "-m", "worldlab.experiment", "--policy", "baseline",
                                    "--seeds", "7", "--population", "4", "--warmup", "0", "--steps", "20",
                                    "--output", str(output)], cwd=ROOT, env=env, stdout=log, stderr=log,
                                   start_new_session=True)
        try:
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail("CLI ended before interruption: " + (tmp_path / "cli.log").read_text())
                path = output / "report.json"
                if path.exists():
                    report = json.loads(path.read_text())
                    if report["experiments"] and any(len(b["trajectory"]) >= 2 for b in report["experiments"][0]["branches"].values()):
                        break
                time.sleep(0.05)
            else:
                pytest.fail("Timed out waiting for the first committed CLI step")
            process.send_signal(signal.SIGTERM)
            assert process.wait(timeout=45) == 1
            report = json.loads((output / "report.json").read_text())
            assert report["status"] == "interrupted"
            assert report["error"]["type"] == "KeyboardInterrupt"
            assert (output / "report.html").is_file()
            audit = audit_ledger(output / "costs.jsonl")
            assert audit["summary"]["estimated_cost_usd"] == "0.0000000000"
            assert audit["summary"]["unresolved_calls"] == 0
            server_log = (output / "server.log").read_text()
            server_pid = int(re.search(r"Started server process \[(\d+)\]", server_log).group(1))
            with pytest.raises(ProcessLookupError):
                os.kill(server_pid, 0)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(45)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(5)
