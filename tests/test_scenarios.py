import pytest

from worldlab.common import choose_action
from worldlab.scenarios import validate_scenario


@pytest.mark.parametrize("parameters", [
    {"max_steps": True}, {"max_steps": 1001}, {"feed_limit": 0},
    {"initial_content": " "}, {"initial_verified": 1},
    {"friction_multiplier": float("nan")}, {"friction_multiplier": -0.1},
    {"friction_multiplier": True}, {"unknown": 1}, [],
])
def test_invalid_scenarios(parameters):
    with pytest.raises(ValueError):
        validate_scenario(parameters)


def test_zero_friction_stops_unverified_sharing():
    scenario = validate_scenario({"friction_multiplier": 0})
    world = {"posts": [{"user_id": 2, "post_id": 1, "root_id": 1, "verified": False}], "edges": [[3, 2]]}
    for seed in range(10):
        assert choose_action(world, 3, seed, 0, "friction", scenario) == {"kind": "wait"}


def test_scenario_defaults_are_independent():
    changed = validate_scenario()
    changed["max_steps"] = 1
    assert validate_scenario()["max_steps"] == 30
