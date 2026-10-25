#!/usr/bin/env python3
"""Fetch immutable upstream revisions and install three isolated runtimes."""
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from worldlab.source_integrity import source_changes


def run(*args, cwd=ROOT):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run(args, cwd=cwd, check=True, timeout=1200)


def python_request(version, system, machine):
    architecture = "aarch64" if machine in {"arm64", "aarch64"} else "x86_64"
    operating_system, libc = ("macos", "none") if system == "Darwin" else ("linux", "gnu")
    return f"cpython-{version}-{operating_system}-{architecture}-{libc}"


def check_runtime(python, version, expected_machine):
    code = "import json,platform,sys; print(json.dumps({'machine':platform.machine(),'version':list(sys.version_info[:2])}))"
    info = json.loads(subprocess.check_output([str(python), "-c", code], text=True, timeout=20))
    normalize = lambda value: "aarch64" if value in {"arm64", "aarch64"} else value
    if (normalize(info["machine"]) != normalize(expected_machine)
            or info["version"] != [int(part) for part in version.split(".")]):
        raise SystemExit(f"{python} uses {info['machine']} Python {info['version']}; expected {expected_machine} Python {version}. "
                         "Preserve or move this incompatible environment before rerunning bootstrap; it was not deleted.")
    return info


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
        dirty = "\n".join(source_changes(source, spec["commit"]))
        if revision != spec["commit"] or dirty:
            print(f"Expected source revision: {spec['commit']}; found: {revision}", flush=True)
            if dirty:
                print("Changed upstream paths (no contents):\n" + dirty, flush=True)
            raise SystemExit(f"{source} differs from its pinned revision. Preserve your edits before reinstalling.")
        request = python_request(spec["python"], system, machine)
        # A bare 3.12 request can select a cached Intel interpreter on Apple
        # Silicon even with an ARM uv. Select architecture/libc explicitly and
        # never replace the user's global Python command links.
        run(uv, "python", "install", "--no-bin", request)
        interpreter = subprocess.check_output([uv, "python", "find", "--managed-python", request], text=True).strip()
        check_runtime(interpreter, spec["python"], machine)
        environment = ROOT / spec["environment"]
        if not environment.exists():
            run(uv, "venv", "--python", interpreter, str(environment))
        check_runtime(environment / "bin/python", spec["python"], machine)
        run(uv, "pip", "install", "--python", str(environment / "bin/python"),
            "-r", str(ROOT / "requirements" / f"{name}.txt"))
    print("\nReady: ./scripts/serve → http://127.0.0.1:8765")


if __name__ == "__main__":
    main()
