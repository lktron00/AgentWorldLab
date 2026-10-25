"""Exercise real process/pipe failure modes without loading simulation engines."""
import sys
import time

import pytest

from worldlab import rpc


@pytest.fixture
def worker(tmp_path, monkeypatch):
    monkeypatch.setattr(rpc, "ROOT", tmp_path)
    python = tmp_path / "runtime/bin/python"
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    running = []

    def start(code):
        (tmp_path / "child.py").write_text(code)
        instance = rpc.Worker("runtime", "child", tmp_path / "child.log")
        running.append(instance)
        return instance

    yield start
    for instance in running:
        instance.close()


def test_partial_line_cannot_escape_rpc_deadline(worker):
    child = worker('import sys,time\nsys.stdin.readline()\nsys.stdout.write("{")\nsys.stdout.flush()\ntime.sleep(60)\n')
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        child.call("test", timeout=0.2)
    assert time.monotonic() - started < 3
    assert child.process.poll() is not None


def test_eof_in_middle_of_response_is_a_transport_failure(worker):
    child = worker('import sys\nsys.stdin.readline()\nprint("{",end="",flush=True)\n')
    with pytest.raises(rpc.WorkerError, match="before completing"):
        child.call("test", timeout=2)


def test_worker_that_does_not_read_cannot_block_request_write(worker):
    child = worker('import time\ntime.sleep(60)\n')
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        child.call("test", timeout=0.2, payload="x" * 2_000_000)
    assert time.monotonic() - started < 3
    assert child.process.poll() is not None


@pytest.mark.parametrize("response", ['not json', '{}', '{"ok":"yes"}'])
def test_bad_envelope_terminates_desynchronized_process(worker, response):
    child = worker(f'import sys,time\nsys.stdin.readline()\nprint({response!r},flush=True)\ntime.sleep(60)\n')
    with pytest.raises(rpc.WorkerError, match="invalid response"):
        child.call("test", timeout=2)
    assert child.process.poll() is not None


def test_remote_rejection_preserves_channel_and_failure_metadata(worker):
    child = worker('''import json,sys
for line in sys.stdin:
    cmd=json.loads(line)["command"]
    result={"ok":False,"error":"bad action","failed":False,"kind":"ValueError"} if cmd=="reject" else {"ok":True,"result":42}
    print(json.dumps(result),flush=True)
    if cmd=="close": break
''')
    with pytest.raises(rpc.WorkerRemoteError) as error:
        child.call("reject")
    assert not error.value.failed
    assert error.value.kind == "ValueError"
    assert child.call("accepted") == 42
