"""Local OpenEnv API plus a dependency-free experiment dashboard."""
import io
import os
import zipfile
from contextlib import nullcontext

os.environ["ENABLE_WEB_INTERFACE"] = "false"
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from openenv.core.env_server import create_app

from .common import DATA, ROOT, read_json, safe_id
from .environment import ACTIVE, LabEnvironment
from .models import LabAction, LabObservation, LabState
from .security import LocalAccessMiddleware

app = create_app(LabEnvironment, LabAction, LabObservation, env_name="agent_world_lab",
                 max_concurrent_envs=2, state_cls=LabState)
app.add_middleware(LocalAccessMiddleware)
app.mount("/assets", StaticFiles(directory=ROOT / "web"), name="assets")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "web/index.html")


def run_path(run_id):
    try:
        path = DATA / "runs" / safe_id(run_id)
        if path.is_symlink() or not path.is_dir():
            raise ValueError("Run not found")
        return path
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/lab/runs")
def list_runs():
    paths = sorted((DATA / "runs").glob("*/latest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [read_json(p) for p in paths[:30]]


@app.get("/lab/runs/{run_id}/frames")
def frames(run_id: str):
    path = run_path(run_id)
    env = ACTIVE.get(run_id)
    with env.lock if env else nullcontext():
        return [read_json(p) for p in sorted((path / "frames").glob("*.json"))]


@app.post("/lab/runs/{run_id}/checkpoint")
def checkpoint(run_id: str):
    run_path(run_id)
    env = ACTIVE.get(run_id)
    if env is None:
        raise HTTPException(409, "Checkpoint requires a connected, paused session")
    try:
        return env.checkpoint()
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/lab/runs/{run_id}/export")
def export(run_id: str):
    path = run_path(run_id)
    archive = io.BytesIO()
    env = ACTIVE.get(run_id)
    # Pin a tick boundary while reading mutable metadata and the event journal.
    with env.lock if env else nullcontext(), zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for file in sorted(path.rglob("*")):
            if file.is_file() and file.suffix in {".json", ".jsonl"}:
                zipped.write(file, file.relative_to(path))
        pins = ROOT / "upstreams.json"
        if pins.exists():
            zipped.write(pins, "upstreams.json")
    return Response(archive.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="worldlab-{run_id[:8]}.zip"'})


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8765")), workers=1)


if __name__ == "__main__":
    main()
