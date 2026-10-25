import copy

import pytest

from worldlab.observations import agent_view, validate_agent_action


def snapshot():
    def post(pid, author, root=None, **kwargs):
        return {"post_id": pid, "user_id": author, "root_id": root or pid,
                "original_post_id": root, "content": f"public {pid}", "created_at": "2026-01-01",
                "num_shares": 42, "verified": False, **kwargs}
    return {"run_id": "a" * 32, "step": 2, "time": "2026-01-01", "done": False, "status": "paused",
            "scenario": {"feed_limit": 2, "seed": 999, "initial_verified": True},
            "metrics": {"secret": 123}, "world": {
                "nodes": [{"id": 0, "name": "External"}, {"id": 1, "name": "Visible"}, {"id": 3, "name": "HIDDEN"}],
                "edges": [[0, 1], [3, 1]],
                "posts": [post(1, 1), post(2, 3, content="HIDDEN POST"), post(3, 1, root=1),
                          post(4, 0, root=1), post(5, 1)]}}


def test_scoped_view_does_not_depend_on_hidden_information():
    raw = snapshot()
    view = agent_view(raw)
    assert view.keys() == {"view", "run_id", "step", "time", "done", "status", "self", "following", "own_posts", "feed", "actions"}
    assert [p["post_id"] for p in view["feed"]] == [5, 3]
    assert view["feed"][1]["can_repost"] is False
    altered = copy.deepcopy(raw)
    altered["metrics"] = {"different": 999}
    altered["scenario"]["seed"] = 77
    altered["world"]["posts"][1]["content"] = "DIFFERENT SECRET"
    altered["world"]["nodes"][2]["name"] = "DIFFERENT SECRET"
    altered["world"]["edges"].append([3, 2])
    for p in altered["world"]["posts"]:
        p["verified"] = True
        p["num_shares"] += 100
    assert agent_view(altered) == view
    assert "HIDDEN" not in str(view)
    assert "verified" not in str(view)
    assert "num_shares" not in str(view)


@pytest.mark.parametrize("action", [
    {"kind": "repost", "post_id": 2},  # Hidden post, although it exists.
    {"kind": "repost", "post_id": 1},  # Outside the bounded feed.
    {"kind": "repost", "post_id": 3},  # Root already shared.
    {"kind": "post", "content": "claim", "verified": True},
])
def test_permissions_reject_hidden_posts_and_self_assigned_truth(action):
    with pytest.raises(ValueError):
        validate_agent_action(action, agent_view(snapshot()))


def test_permissions_allow_visible_post_and_ordinary_publication():
    view = agent_view(snapshot())
    validate_agent_action({"kind": "repost", "post_id": 5}, view)
    validate_agent_action({"kind": "post", "content": "evidence?", "verified": False}, view)


def test_signal_metric_distinguishes_questions_from_original_signal():
    from worldlab.experiment import operator_metrics
    raw = snapshot()
    raw["world"]["posts"].append({"post_id": 6, "user_id": 0, "root_id": 6,
                                  "original_post_id": None, "verified": False, "content": "Evidence?"})
    raw["world"]["posts"].append({"post_id": 7, "user_id": 3, "root_id": 6,
                                  "original_post_id": 6, "verified": False})
    metrics = operator_metrics(raw)
    assert metrics["signal_sharers"] == 1
    assert metrics["external_signal_reposts"] == 1
    assert metrics["external_unverified_posts"] == 2
