"""Read-only discovery and decision inspection; never triggers paid calls."""
import base64
import hashlib
import json
import re
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from .common import DATA
from .reports import read_artifact
from .pilot_report import build_html

router = APIRouter()


def directory(name):
    root = DATA / 'pilots'
    path = root / name
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', name) or root.is_symlink() or path.is_symlink() or not path.is_dir():
        raise HTTPException(404, 'Pilot not found')
    return path


def report_for(name):
    try:
        result = read_artifact(directory(name) / 'report.json')
        if result['kind'] != 'all-ai-incident-pilot':
            raise ValueError('Invalid pilot kind')
        return result
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(409, 'Invalid pilot artifact') from exc


@router.get('/lab/pilots')
def catalog():
    root = DATA / 'pilots'
    if not root.is_dir() or root.is_symlink():
        return []
    paths = sorted((p for p in root.iterdir() if not p.is_symlink() and p.is_dir() and (p / 'report.json').is_file()),
                   key=lambda p: (p / 'report.json').stat().st_mtime, reverse=True)
    result = []
    for p in paths[:30]:
        try:
            r = report_for(p.name)
            result.append({'id': p.name, 'title': r['title'], 'status': r['status'], 'kind': r['kind'],
                           'completed_pairs': r['summary']['pairs'], 'requested_pairs': r['requested_pairs'],
                           'population': r['config']['population'], 'steps': r['config']['steps'],
                           'api_cost_usd': r['cost']['estimated_cost_usd'], 'decisions': r['progress']['decisions']})
        except HTTPException:
            continue
    return result


@router.get('/pilots/{name}', response_class=HTMLResponse, include_in_schema=False)
def pilot(name: str):
    source = build_html(report_for(name))
    script = re.search(r'<script id="pilot-script">(.*?)</script>', source, re.S).group(1)
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    return HTMLResponse(source, headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
        'Content-Security-Policy': f"default-src 'none'; script-src 'sha256-{digest}'; connect-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"})


def journal(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 128 * 1024 * 1024:
        raise HTTPException(409, 'Missing, linked or oversized decision journal')
    with path.open() as stream:
        for line in stream:
            if not line.endswith('\n'):
                break  # An interrupted tail is never considered a committed decision.
            try:
                yield json.loads(line)
            except ValueError as exc:
                raise HTTPException(409, 'Invalid decision journal') from exc


@router.get('/lab/pilots/{name}/decisions')
def decisions(name: str, seed: int = Query(ge=0), branch: str = Query(pattern='^(generic|diagnostic)$'),
              step: int = Query(ge=0, le=9), actor: int | None = Query(default=None, ge=1, le=20)):
    report_for(name)
    rows, applied = [], set()
    for event in journal(directory(name) / 'decisions.jsonl'):
        if event.get('event') == 'decision' and event.get('seed') == seed and event.get('branch') == branch and event.get('step') == step:
            if actor is None or event.get('actor') == actor:
                rows.append(event)
        elif event.get('event') == 'applied_batch':
            applied.update(event['decision_ids'])
    return JSONResponse([{**r, 'applied': r['decision_id'] in applied} for r in sorted(rows, key=lambda r: r['actor'])],
                        headers={'Cache-Control': 'no-store'})


@router.get('/lab/pilots/{name}/files/{filename}')
def download(name: str, filename: str):
    if filename not in {'report.json', 'decisions.jsonl', 'costs.jsonl', 'audit.json'}:
        raise HTTPException(404, 'Unknown artifact')
    path = directory(name) / filename
    if path.is_symlink() or not path.is_file():
        raise HTTPException(404, 'Artifact not available yet')
    return FileResponse(path, filename='worldlab-' + name + '-' + filename,
                        media_type='application/x-ndjson' if filename.endswith('.jsonl') else 'application/json',
                        headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store'})
