"""Verify pinned Git source bytes without checkout newline-filter false positives."""
import hashlib
import os
import stat
import subprocess


def git_output(source, *arguments):
    return subprocess.check_output(["git", *arguments], cwd=source, timeout=60)


def source_changes(source, revision):
    """Return real content/mode, index or untracked changes from a pinned tree.

    Some upstream blobs contain CRLF despite text=eol=lf attributes. Git status
    can call a byte-identical checkout dirty after stat refresh. Hash the raw
    worktree as Git blobs instead; never normalize or modify upstream files.
    """
    algorithm = git_output(source, "rev-parse", "--show-object-format").decode().strip()
    changes = set()
    entries = git_output(source, "ls-tree", "-r", "-z", "--full-tree", revision)
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        metadata, _, filename = entry.partition(b"\t")
        mode, kind, expected = metadata.decode().split(" ")
        name = os.fsdecode(filename)
        path = source / name
        if kind != "blob":
            changes.add(name + " (unsupported Git entry)")
            continue
        if mode == "120000":
            if not path.is_symlink():
                changes.add(name)
                continue
            data = os.fsencode(os.readlink(path))
            digest = hashlib.new(algorithm, b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        else:
            if path.is_symlink() or not path.is_file():
                changes.add(name)
                continue
            info = path.stat()
            if bool(info.st_mode & stat.S_IXUSR) != (mode == "100755"):
                changes.add(name)
            hasher = hashlib.new(algorithm, b"blob " + str(info.st_size).encode() + b"\0")
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    hasher.update(chunk)
            digest = hasher.hexdigest()
        if digest != expected:
            changes.add(name)
    # Also preserve staged edits that aren't currently reflected in worktree
    # bytes, and new unignored files. This is not a relaxed dirty-tree check.
    for arguments in (("diff", "--cached", "--no-ext-diff", "--name-only", "-z", revision, "--"),
                      ("ls-files", "--others", "--exclude-standard", "-z")):
        changes.update(os.fsdecode(name) for name in git_output(source, *arguments).split(b"\0") if name)
    return sorted(changes)
