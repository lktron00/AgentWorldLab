#!/usr/bin/env python3
"""Report installed runtimes and source revisions without exposing credentials."""
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from worldlab.source_integrity import source_changes
EXPECTED = {"agentsociety2": ("agentsociety2", "2.9.3"), "oasis": ("camel-oasis", "0.2.5"), "openenv": ("openenv", "0.10.1.dev0")}


def main():
    report = {"platform": platform.system(), "machine": platform.machine(), "runtimes": {}}
    healthy = True
    for name, spec in json.loads((ROOT / "upstreams.json").read_text()).items():
        package, expected = EXPECTED[name]
        python = ROOT / spec["environment"] / "bin/python"
        try:
            code = "import importlib.metadata,json,platform; print(json.dumps({'version':importlib.metadata.version(" + repr(package) + "),'python':platform.python_version(),'machine':platform.machine()}))"
            result = json.loads(subprocess.check_output([str(python), "-c", code], text=True, stderr=subprocess.PIPE, timeout=20))
            source = ROOT / "vendor" / name
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True, stderr=subprocess.PIPE).strip()
            dirty = "\n".join(source_changes(source, spec["commit"]))
            result.update(commit=commit, source_verification="raw_git_blobs", healthy=result["version"] == expected and commit == spec["commit"] and not dirty)
        except (OSError, subprocess.SubprocessError, ValueError):
            result = {"healthy": False, "error": "Missing or invalid runtime; run python3 scripts/bootstrap.py"}
        report["runtimes"][name] = result
        healthy = healthy and result["healthy"]
    print(json.dumps(report, indent=2))
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
