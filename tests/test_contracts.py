import pytest
from pydantic import ValidationError

from worldlab.common import choose_action, draw, safe_id
from worldlab.models import LabAction


def test_action_cannot_impersonate_other_agents():
    with pytest.raises(ValidationError):
        LabAction(kind="post", content="hello", actor_id=8)


@pytest.mark.parametrize("payload", [
    {"kind": "post", "content": " "}, {"kind": "repost"},
    {"kind": "repost", "post_id": -1}, {"kind": "wait", "verified": True},
    {"kind": "post", "content": "x" * 1001}, {"kind": "reset"},
])
def test_invalid_actions_rejected_before_engine_mutation(payload):
    with pytest.raises(ValidationError):
        LabAction(**payload)


@pytest.mark.parametrize("value", ["../secret", "/tmp/example", "abc", "a"*31 + "/"])
def test_ids_cannot_escape_data_directory(value):
    with pytest.raises(ValueError):
        safe_id(value)


def test_agents_only_react_to_followed_accounts_and_never_repost_twice():
    post = {"user_id": 2, "post_id": 1, "root_id": 1, "verified": True}
    assert choose_action({"posts": [post], "edges": []}, 3, 7, 0, "open") == {"kind": "wait"}
    own = dict(post, user_id=3, post_id=2)
    assert choose_action({"posts": [post, own], "edges": [[3,2]]}, 3, 7, 0, "open") == {"kind": "wait"}


def test_random_draw_independent_of_other_calls():
    expected = draw(7, 3, 18, 1)
    for agent in range(20):
        draw(99, 20, agent, 50)
    assert draw(7, 3, 18, 1) == expected
