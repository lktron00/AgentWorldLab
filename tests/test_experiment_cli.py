import copy
import json

import pytest

from worldlab.errors import safe_error
from worldlab.experiment import main, verify_self_check


@pytest.mark.parametrize("options", [
    ["--budget-usd", "NaN"], ["--budget-usd", "not-a-price"], ["--budget-usd", "-1"],
    ["--seeds", "7", "7"], ["--steps", "-1"], ["--population", "1"],
])
def test_invalid_cli_configuration_fails_before_output_or_spending(tmp_path, capsys, options):
    output = tmp_path / "must-not-exist"
    with pytest.raises(SystemExit) as result:
        main(["--policy", "baseline", "--output", str(output), *options])
    assert result.value.code == 2
    assert not output.exists()
    assert "error:" in capsys.readouterr().err


def test_existing_output_is_preserved_with_actionable_error(tmp_path, capsys):
    (tmp_path / "keep.json").write_text("original")
    with pytest.raises(SystemExit):
        main(["--policy", "baseline", "--output", str(tmp_path)])
    assert (tmp_path / "keep.json").read_text() == "original"
    assert "Choose a new directory" in capsys.readouterr().err


def test_public_provider_error_never_echoes_exception_body_or_api_key():
    AuthenticationError = type("AuthenticationError", (Exception,), {})
    secret = "sk-private-value-that-must-never-be-printed"
    error = AuthenticationError("Incorrect API key provided: " + secret)
    error.status_code = 401
    public = safe_error(error)
    assert secret not in json.dumps(public)
    assert public["http_status"] == 401
    assert "private API key" in public["message"]


def test_self_check_detects_different_worlds_even_when_aggregate_metrics_match():
    branch = {"trajectory": [{"signal_sharers": 3}], "world_sha256": ["a" * 64]}
    pair = {"branches": {"baseline": copy.deepcopy(branch), "candidate": copy.deepcopy(branch)}}
    verify_self_check(pair)
    assert pair["full_trajectory_match"] is True
    pair["branches"]["candidate"]["world_sha256"] = ["b" * 64]
    with pytest.raises(RuntimeError, match="complete world"):
        verify_self_check(pair)
