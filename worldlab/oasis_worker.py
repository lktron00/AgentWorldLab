"""Actual OASIS Platform and SQLite; no synthetic replacement engine."""
from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
import traceback
from datetime import datetime
from pathlib import Path

WIRE = sys.stdout
sys.stdout = sys.stderr  # Upstream prints diagnostics during database creation.

from oasis.clock.clock import Clock
from oasis.social_platform.platform import Platform

from .common import START


class OasisWorld:
    platform: Platform | None = None

    async def dispatch(self, request):
        cmd = request["command"]
        if cmd == "open":
            self.platform = Platform(
                db_path=request["database"], sandbox_clock=Clock(),
                start_time=datetime.fromisoformat(START), recsys_type="random",
            )
            # SQLite's default durable mode, overriding OASIS's OFF setting.
            self.platform.db.execute("PRAGMA synchronous = FULL")
            self.platform.db.execute(
                "CREATE TABLE IF NOT EXISTS worldlab_labels "
                "(post_id INTEGER PRIMARY KEY, verified INTEGER NOT NULL)"
            )
            return {"engine": "oasis", "version": "0.2.5"}
        if cmd in {"close", "close_world"}:
            if self.platform:
                self.platform.db.close()
                self.platform = None
            return None
        p = self.platform
        if p is None:
            raise RuntimeError("Open a world first")
        p.sandbox_clock.time_step = request.get("step", p.sandbox_clock.time_step)
        if cmd == "seed":
            count = request["population"]
            for aid in range(count + 1):
                self.check(await p.sign_up(aid, (f"agent-{aid}", "External" if aid == 0 else f"Agent {aid:02}", "Scripted test agent")))
            # Directed ring with two local links and a seed-dependent long link.
            edges = {(0, 1), (0, 2)}  # External agent has an ordinary, limited feed.
            for aid in range(1, count + 1):
                for offset in (1, 2, 5 + request["seed"] % 3):
                    target = (aid - 1 - offset) % count + 1
                    if aid != target:
                        edges.add((aid, target))
                if aid % 5 == 1:
                    edges.add((aid, 0))
            for source, target in sorted(edges):
                self.check(await p.follow(source, target))
            result = self.check(await p.create_post(1, request["content"]))
            p.db.execute("INSERT INTO worldlab_labels VALUES (?, ?)", (result["post_id"], int(request["verified"])))
            p.db.commit()
            return self.snapshot()
        if cmd == "action":
            action, actor = request["action"], request["actor"]
            kind = action["kind"]
            if kind == "wait":
                return {"success": True}
            if kind == "post":
                result = self.check(await p.create_post(actor, action["content"]))
                p.db.execute("INSERT INTO worldlab_labels VALUES (?, ?)", (result["post_id"], int(action.get("verified", False))))
                p.db.commit()
                return result
            if kind == "repost":
                return self.check(await p.repost(actor, action["post_id"]))
            raise ValueError(f"Unknown social action: {kind}")
        if cmd == "snapshot":
            return self.snapshot()
        if cmd == "backup":
            with sqlite3.connect(request["path"]) as destination:
                p.db.backup(destination)
            return True
        raise ValueError(f"Unknown OASIS command: {cmd}")

    @staticmethod
    def check(result):
        if not result.get("success"):
            raise ValueError(f"OASIS rejected action: {result}")
        return result

    def snapshot(self):
        db = self.platform.db
        def rows(query):
            cursor = db.execute(query)
            names = [d[0] for d in cursor.description]
            return [dict(zip(names, row)) for row in cursor.fetchall()]
        posts = rows("SELECT post_id,user_id,original_post_id,content,created_at,num_shares FROM post ORDER BY post_id")
        by_id = {p["post_id"]: p for p in posts}
        labels = dict(db.execute("SELECT post_id,verified FROM worldlab_labels"))
        for post in posts:
            root_id = post["original_post_id"] or post["post_id"]
            post["root_id"] = root_id
            post["content"] = by_id[root_id]["content"]
            post["verified"] = bool(labels.get(root_id, 0))
        return {
            "posts": posts,
            "nodes": rows("SELECT user_id AS id,name FROM user ORDER BY user_id"),
            "edges": [list(row) for row in db.execute("SELECT follower_id,followee_id FROM follow ORDER BY follower_id,followee_id")],
        }


async def main():
    world = OasisWorld()
    try:
        for line in sys.stdin:
            request = json.loads(line)
            try:
                result = await world.dispatch(request)
                response = {"ok": True, "result": result}
            except Exception as exc:
                traceback.print_exc(file=sys.stderr)
                response = {"ok": False, "error": str(exc)}
            WIRE.write(json.dumps(response, ensure_ascii=False) + "\n")
            WIRE.flush()
            if request["command"] == "close":
                return
    finally:
        if world.platform:
            try:
                world.platform.db.close()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())
