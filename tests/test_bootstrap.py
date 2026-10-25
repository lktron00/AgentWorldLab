"""Regression for an ARM host with a cached/aliased Intel Python."""
import json
import sys

import pytest

from scripts.bootstrap import check_runtime, python_request


def test_python_request_cannot_implicitly_match_the_other_architecture():
    assert "macos-aarch64" in python_request("3.12", "Darwin", "arm64")
    assert "linux-aarch64-gnu" in python_request("3.11", "Linux", "aarch64")
    assert "linux-x86_64-gnu" in python_request("3.12", "Linux", "x86_64")


def test_existing_foreign_runtime_is_rejected_without_deleting_environment(tmp_path):
    environment = tmp_path / "existing-environment"
    environment.mkdir()
    marker = environment / "user-file"
    marker.write_text("preserve")
    fake_python = environment / "python"
    fake_python.write_text("#!/bin/sh\nprintf '%s\\n' '" + json.dumps({"machine": "x86_64", "version": [3, 12]}) + "'\n")
    fake_python.chmod(0o755)
    with pytest.raises(SystemExit, match="was not deleted"):
        check_runtime(fake_python, "3.12", "arm64")
    assert marker.read_text() == "preserve"


def test_current_interpreter_probe_validates_actual_version_and_machine():
    import platform
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    result = check_runtime(sys.executable, version, platform.machine())
    assert result["machine"] == platform.machine()
