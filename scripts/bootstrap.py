#!/usr/bin/env python3
"""Fetch immutable upstream revisions and install three isolated runtimes."""
import json
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args, cwd=ROOT):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run(args, cwd=cwd, check=True, timeout=1200)


def main():
    system, machine = platform.system(), platform.machine()
    if not ((system == "Darwin" and machine == "arm64") or
            (system == "Linux" and machine in {"aarch64", "x86_64"})):
        raise SystemExit("Supported targets: macOS ARM64 and Linux ARM64/x86_64. On other hosts, use Docker.")
    if not shutil.which("uv") or not shutil.which("git"):
        raise SystemExit("Install uv and Git first. See README.md.")
    uv = shutil.which("uv")
    # An Intel Homebrew uv can appear first in PATH on Apple Silicon. It
    # resolves Intel wheels even when the Python invoking this script is ARM.
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        candidates = [Path(uv), Path.home() / ".local/bin/uv", Path("/opt/homebrew/bin/uv")]
        native = [p for p in candidates if p.is_file() and "arm64" in
                  subprocess.check_output(["file", "-b", str(p)], text=True)]
        if not native:
            raise SystemExit("Install the ARM-native uv binary (see README); PATH currently resolves an Intel uv.")
        uv = str(native[0])
    pins = json.loads((ROOT / "upstreams.json").read_text())
    vendor = ROOT / "vendor"
    vendor.mkdir(exist_ok=True)
    for name, spec in pins.items():
        source = vendor / name
        if not source.exists():
            # Never mistake an interrupted download for an installed upstream.
            staging = Path(tempfile.mkdtemp(prefix=f".{name}-", dir=vendor))
            try:
                run("git", "init", "-q", cwd=staging)
                run("git", "remote", "add", "origin", spec["url"], cwd=staging)
                run("git", "fetch", "--depth=1", "origin", spec["commit"], cwd=staging)
                run("git", "checkout", "--detach", "FETCH_HEAD", cwd=staging)
                staging.rename(source)
            except BaseException:
                # This directory was created by this invocation, never user code.
                shutil.rmtree(staging, ignore_errors=True)
                raise
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=source, text=True).strip()
        if revision != spec["commit"] or dirty:
            print(f"Expected source revision: {spec['commit']}; found: {revision}", flush=True)
            if dirty:
                print("Changed upstream paths (no contents):\n" + dirty, flush=True)
            raise SystemExit(f"{source} differs from its pinned revision. Preserve your edits before reinstalling.")
        run(uv, "python", "install", spec["python"])
        environment = ROOT / spec["environment"]
        if not environment.exists():
            run(uv, "venv", "--python", spec["python"], str(environment))
        run(uv, "pip", "install", "--python", str(environment / "bin/python"),
            "-r", str(ROOT / "requirements" / f"{name}.txt"))
    print("\nReady: ./scripts/serve → http://127.0.0.1:8765")


if __name__ == "__main__":
    main()
