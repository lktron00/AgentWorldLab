"""Small, portable scenario contract shared across isolated runtimes."""
import math

DEFAULTS = {
    "max_steps": 30,
    "initial_content": "SEÑAL SINTÉTICA: el registro Orion podría estar comprometido. Sin verificar.",
    "initial_verified": False,
    "friction_multiplier": 0.2,
    "feed_limit": 12,
    "decision_mode": "scripted",
}


def validate_scenario(value=None):
    if value is None:
        value = {}
    if not isinstance(value, dict) or value.keys() - DEFAULTS.keys():
        raise ValueError("Unknown scenario parameters; see scenarios/diffusion.json")
    result = DEFAULTS | value
    for key, maximum in (("max_steps", 1000), ("feed_limit", 100)):
        if type(result[key]) is not int or not 1 <= result[key] <= maximum:
            raise ValueError(f"{key} must be an integer between 1 and {maximum}")
    content = result["initial_content"]
    if not isinstance(content, str) or not 1 <= len(content.strip()) <= 1000:
        raise ValueError("initial_content must contain 1–1000 characters")
    if type(result["initial_verified"]) is not bool:
        raise ValueError("initial_verified must be a boolean")
    multiplier = result["friction_multiplier"]
    if type(multiplier) not in (int, float) or not math.isfinite(multiplier) or not 0 <= multiplier <= 1:
        raise ValueError("friction_multiplier must be a number between 0 and 1")
    if result["decision_mode"] not in ("scripted", "submitted"):
        raise ValueError("decision_mode must be scripted or submitted")
    return result
