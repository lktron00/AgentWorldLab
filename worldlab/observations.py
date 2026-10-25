"""Server-side external-agent view. Ground-truth labels stay with the operator."""
from .common import feed_for

PUBLIC_POST_FIELDS = ("post_id", "user_id", "original_post_id", "content", "created_at")


def agent_view(snapshot, actor=0):
    world = snapshot["world"]
    own = [p for p in world["posts"] if p["user_id"] == actor]
    shared_roots = {p["root_id"] for p in own}
    feed = feed_for(world, actor, snapshot["scenario"]["feed_limit"])
    return {
        "view": "agent-v1", "run_id": snapshot["run_id"],
        "step": snapshot["step"], "time": snapshot["time"],
        "done": snapshot["done"], "status": snapshot["status"],
        "self": next(dict(n) for n in world["nodes"] if n["id"] == actor),
        "following": [target for source, target in world["edges"] if source == actor],
        "own_posts": [{k: p[k] for k in PUBLIC_POST_FIELDS} for p in own[-12:]],
        "feed": [{**{k: p[k] for k in PUBLIC_POST_FIELDS},
                  "can_repost": p["root_id"] not in shared_roots} for p in feed],
        "actions": ["wait", "post", "repost"],
    }


def validate_agent_action(action, observation):
    """Identical guard on server and policy boundary; never resolve hidden IDs."""
    if action.get("verified", False):
        raise ValueError("Agents cannot assign ground-truth verification labels")
    if action["kind"] == "repost" and action.get("post_id") not in {
        p["post_id"] for p in observation["feed"] if p["can_repost"]
    }:
        raise ValueError("Repost requires an eligible post in the current visible feed")
