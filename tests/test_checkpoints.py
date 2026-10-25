import sqlite3

import pytest

from worldlab.checkpoints import inventory, validate_checkpoint
from worldlab.common import write_json


@pytest.fixture
def checkpoint(tmp_path):
    source = tmp_path / "checkpoint"
    source.mkdir()
    with sqlite3.connect(source / "oasis.sqlite") as db:
        db.execute("CREATE TABLE example(value INTEGER)")
    write_json(source / "scenario.json", {"population": 1})
    write_json(source / "SOCIETY.json", {"agent_specs": [{"id": 1}]})
    write_json(source / "SOCIETY_STEP.json", {"step_count": 3, "current_time": "test-time"})
    write_json(source / "latest.json", {"step": 3, "time": "test-time", "status": "paused"})
    write_json(source / "agents/agent_0001/AGENT.json", {"step_count": 3})
    manifest = {"schema_version": 1, "step": 3, "upstreams": {"pinned": "revision"},
                "adapter_hashes": {"policy": "digest"}, "files": inventory(source)}
    write_json(source / "manifest.json", manifest)
    return source, manifest


def validate(source):
    return validate_checkpoint(source, upstreams={"pinned": "revision"}, adapter_hashes={"policy": "digest"})


def test_valid_checkpoint_has_consistent_clock_and_database(checkpoint):
    source, expected = checkpoint
    assert validate(source) == expected


def test_unlisted_file_cannot_silently_enter_a_restored_world(checkpoint):
    source, _ = checkpoint
    write_json(source / "unlisted.json", {})
    with pytest.raises(ValueError, match="inventory changed"):
        validate(source)


def test_nested_manifest_is_not_exempt_from_inventory(checkpoint):
    source, _ = checkpoint
    write_json(source / "nested/manifest.json", {})
    with pytest.raises(ValueError, match="inventory changed"):
        validate(source)


@pytest.mark.parametrize("target", ["scenario.json", "agents"])
def test_internal_symbolic_links_are_rejected_even_with_same_contents(checkpoint, target):
    source, _ = checkpoint
    original = source / target
    outside = source.parent / (target + ".outside")
    original.rename(outside)
    original.symlink_to(outside, target_is_directory=outside.is_dir())
    with pytest.raises(ValueError, match="symbolic links"):
        validate(source)


def test_checkpoint_directory_itself_cannot_be_a_symlink(checkpoint):
    source, _ = checkpoint
    alias = source.parent / "alias"
    alias.symlink_to(source, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic link"):
        validate(alias)


@pytest.mark.parametrize("path,changed", [
    ("latest.json", {"step": 9, "time": "test-time", "status": "paused"}),
    ("agents/agent_0001/AGENT.json", {"step_count": 9}),
])
def test_self_consistent_hashes_do_not_hide_divergent_clocks(checkpoint, path, changed):
    source, manifest = checkpoint
    write_json(source / path, changed)
    manifest["files"] = inventory(source)
    write_json(source / "manifest.json", manifest)
    with pytest.raises(ValueError, match="clock is inconsistent"):
        validate(source)


def test_corrupt_database_is_rejected_before_replacing_a_world(checkpoint):
    source, manifest = checkpoint
    (source / "oasis.sqlite").write_bytes(b"not a database")
    manifest["files"] = inventory(source)
    write_json(source / "manifest.json", manifest)
    with pytest.raises(ValueError, match="database is corrupt"):
        validate(source)
