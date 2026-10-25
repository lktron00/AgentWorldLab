"""Validate the complete inventory before a checkpoint can replace a live world."""
import hashlib
import sqlite3
from pathlib import Path, PurePosixPath

from .common import read_json


def inventory(root: Path) -> dict[str, str]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Checkpoint must be a real directory")
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Checkpoints cannot contain symbolic links")
        name = path.relative_to(root).as_posix()
        if path.is_file() and name != "manifest.json":
            result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def validate_checkpoint(source: Path, *, upstreams: dict, adapter_hashes: dict) -> dict:
    if source.is_symlink() or not source.is_dir() or (source / "manifest.json").is_symlink():
        raise ValueError("Checkpoint not found or contains a symbolic link")
    manifest = read_json(source / "manifest.json")
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported checkpoint version")
    if manifest.get("upstreams") != upstreams:
        raise ValueError("Checkpoint requires different upstream revisions")
    if manifest.get("adapter_hashes") != adapter_hashes:
        raise ValueError("Checkpoint policy/adapter version differs from this installation")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Checkpoint is missing its file inventory")
    for name, digest in files.items():
        relative = PurePosixPath(name)
        if (not isinstance(name, str) or relative.is_absolute() or ".." in relative.parts
                or relative.as_posix() != name or "\\" in name or name == "manifest.json"):
            raise ValueError("Invalid checkpoint path")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("Invalid checkpoint digest")
    actual = inventory(source)
    if actual.keys() != files.keys():
        raise ValueError("Checkpoint file inventory changed")
    for name, digest in files.items():
        if actual[name] != digest:
            raise ValueError(f"Checkpoint integrity failed: {name}")
    required = {"oasis.sqlite", "scenario.json", "SOCIETY.json", "SOCIETY_STEP.json", "latest.json"}
    if not required.issubset(files):
        raise ValueError("Checkpoint is missing required world state")
    clock = read_json(source / "SOCIETY_STEP.json")
    latest = read_json(source / "latest.json")
    if (clock["step_count"] != manifest["step"] or latest["step"] != manifest["step"]
            or clock["current_time"] != latest["time"] or latest["status"] != "paused"):
        raise ValueError("Checkpoint world clock is inconsistent")
    specs = read_json(source / "SOCIETY.json")["agent_specs"]
    for spec in specs:
        agent = read_json(source / "agents" / f"agent_{int(spec['id']):04d}" / "AGENT.json")
        if agent["step_count"] != clock["step_count"]:
            raise ValueError("Checkpoint agent clock is inconsistent")
    try:
        uri = (source / "oasis.sqlite").resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as database:
            if database.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise ValueError("Checkpoint database is corrupt")
    except sqlite3.DatabaseError as exc:
        raise ValueError("Checkpoint database is corrupt") from exc
    return manifest
