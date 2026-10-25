"""Read-only experiment discovery for the trusted local operator dashboard."""
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from .common import DATA
from .reports import build_html_report, read_artifact

router = APIRouter()


def experiment_path(name):
    root = DATA / "experiments"
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", name):
        raise HTTPException(404, "Experiment not found")
    path = root / name
    if root.is_symlink() or path.is_symlink() or not path.is_dir():
        raise HTTPException(404, "Experiment not found")
    return path


@router.get("/lab/experiments")
def list_experiments():
    root = DATA / "experiments"
    if not root.is_dir() or root.is_symlink():
        return []
    candidates = [p for p in root.iterdir() if p.is_dir() and not p.is_symlink()
                  and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", p.name) and (p / "report.json").is_file()]
    candidates.sort(key=lambda p: (p / "report.json").stat().st_mtime, reverse=True)
    items = []
    for path in candidates[:50]:
        try:
            report = read_artifact(path / "report.json")
            journal = path / "costs.jsonl"
            needs_audit = journal.is_symlink() or not journal.is_file() or journal.stat().st_mtime_ns > (path / "report.json").stat().st_mtime_ns
            cost = report.get("cost", {})
            items.append({"id": path.name, "status": "needs_audit" if needs_audit else report["status"],
                          "mode": report["mode"], "started_at": report.get("started_at"),
                          "model": (report.get("candidate") or {}).get("model"),
                          "seeds": len(report["experiments"]),
                          "estimated_cost_usd": None if needs_audit else cost.get("estimated_cost_usd"),
                          "completed_calls": cost.get("completed_calls", 0),
                          "report_url": f"/lab/experiments/{path.name}/report"})
        except (OSError, ValueError, TypeError, KeyError):
            # A damaged local artifact must not hide all other experiments.
            items.append({"id": path.name, "status": "invalid_artifact", "mode": "unknown",
                          "report_url": f"/lab/experiments/{path.name}/report"})
    return items


def audited(name):
    path = experiment_path(name)
    try:
        return build_html_report(path, download_url=f"/lab/experiments/{name}/report.json?download=1")
    except (OSError, ValueError, TypeError, KeyError, ArithmeticError) as exc:
        raise HTTPException(409, "Experiment audit failed; run scripts/report locally for details") from exc


@router.get("/lab/experiments/{name}/report", response_class=HTMLResponse)
def experiment_report(name: str):
    source, report, audit = audited(name)
    return HTMLResponse(source, headers={
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'",
    })


@router.get("/lab/experiments/{name}/report.json")
def experiment_json(name: str, download: bool = False):
    source, report, audit = audited(name)
    headers = {"Cache-Control": "no-store"}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="worldlab-{name}.json"'
    return JSONResponse(report, headers=headers)
