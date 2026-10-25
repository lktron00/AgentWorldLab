import os
import subprocess

from worldlab.source_integrity import source_changes


def repository(tmp_path):
    def git(*args, input=None):
        return subprocess.check_output(["git", "-c", "user.name=Source Test", "-c", "user.email=test@example.invalid",
                                        "-c", "commit.gpgsign=false", *args], cwd=tmp_path, input=input)
    git("init", "-q")
    (tmp_path / ".gitattributes").write_text("*.py text eol=lf\n")
    git("add", ".gitattributes")
    raw = b"print('pinned source')\r\n"
    blob = git("hash-object", "--no-filters", "-w", "--stdin", input=raw).decode().strip()
    git("update-index", "--add", "--cacheinfo", "100644", blob, "sample.py")
    git("commit", "-q", "-m", "Upstream CRLF blob with LF attributes")
    (tmp_path / "sample.py").write_bytes(raw)
    os.utime(tmp_path / "sample.py", (1, 1))  # Force a real content refresh.
    revision = git("rev-parse", "HEAD").decode().strip()
    return git, revision, raw


def test_raw_pinned_crlf_bytes_pass_even_when_git_status_normalizes_them(tmp_path):
    git, revision, raw = repository(tmp_path)
    assert b"sample.py" in git("status", "--porcelain")
    assert (tmp_path / "sample.py").read_bytes() == raw
    assert source_changes(tmp_path, revision) == []
    assert (tmp_path / "sample.py").read_bytes() == raw
    (tmp_path / "sample.py").write_bytes(raw + b"# actual user change\n")
    assert "sample.py" in source_changes(tmp_path, revision)


def test_index_only_edits_and_untracked_files_are_still_rejected(tmp_path):
    git, revision, raw = repository(tmp_path)
    changed = git("hash-object", "--no-filters", "-w", "--stdin", input=raw + b"# staged\n").decode().strip()
    git("update-index", "--cacheinfo", "100644", changed, "sample.py")
    (tmp_path / "new.py").write_text("# new user code\n")
    assert {"sample.py", "new.py"} <= set(source_changes(tmp_path, revision))
