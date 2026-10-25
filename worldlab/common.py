"""Dependency-free contracts shared by the three isolated Python runtimes."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("WORLDLAB_DATA", ROOT / "data")).resolve()
START = "2026-01-01T00:00:00+00:00"
TICK_SECONDS = 60
POLICIES = {"open", "friction"}


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def read_json(path: Path):
    return json.loads(path.read_text())


def safe_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{32}", value):
        raise ValueError("Expected a generated 32-character ID")
    return value


def policy_name(value: str) -> str:
    if value not in POLICIES:
        raise ValueError("Policy must be 'open' or 'friction'")
    return value


def draw(seed: int, step: int, agent: int, root: int) -> float:
    """Counter-based randomness: independent of scheduling and restart order."""
    digest = hashlib.sha256(f"{seed}:{step}:{agent}:{root}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def feed_for(snapshot: dict, agent_id: int) -> list[dict]:
    followed = {e[1] for e in snapshot["edges"] if e[0] == agent_id}
    posts = [p for p in snapshot["posts"] if p["user_id"] in followed]
    return sorted(posts, key=lambda p: p["post_id"], reverse=True)[:12]


def choose_action(snapshot: dict, agent_id: int, seed: int, step: int, policy: str) -> dict:
    """Explicit toy behavior, not a calibrated model of people or LLMs."""
    already_shared = {p["root_id"] for p in snapshot["posts"] if p["user_id"] == agent_id}
    for post in feed_for(snapshot, agent_id):
        if post["root_id"] in already_shared:
            continue
        probability = 0.6 + (agent_id % 4) * 0.1
        if policy == "friction" and not post["verified"]:
            probability *= 0.2
        if draw(seed, step, agent_id, post["root_id"]) < probability:
            return {"kind": "repost", "post_id": post["root_id"]}
    return {"kind": "wait"}


def metrics(snapshot: dict, population: int) -> dict:
    posts = snapshot["posts"]
    unverified = {p["user_id"] for p in posts if not p["verified"] and p["user_id"] != 0}
    verified = {p["user_id"] for p in posts if p["verified"] and p["user_id"] != 0}
    return {
        "posts": len(posts),
        "reposts": sum(p["original_post_id"] is not None for p in posts),
        "unverified_sharers": len(unverified),
        "verified_sharers": len(verified),
        "unverified_share_rate": len(unverified) / population,
        "population": population,
    }
