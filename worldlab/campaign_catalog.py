"""Read-only local campaign discovery. These endpoints never start a simulation."""
import base64
import hashlib
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from .common import DATA, ROOT
from .reports import read_artifact
from .campaign_report import build_html

router = APIRouter()


def campaign_path(name):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', name):
        raise HTTPException(404, 'Campaign not found')
    root = DATA / 'campaigns'
    path = root / name
    if root.is_symlink() or path.is_symlink() or not path.is_dir():
        raise HTTPException(404, 'Campaign not found')
    return path


def read_campaign(name):
    try:
        report = read_artifact(campaign_path(name) / 'report.json')
        if report['kind'] != 'scripted-policy-campaign':
            raise ValueError('Not a campaign')
        return report
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(409, 'Campaign artifact is invalid') from exc


@router.get('/campaigns', include_in_schema=False)
def catalog():
    return FileResponse(ROOT / 'web/campaigns.html')


@router.get('/lab/campaigns')
def campaigns():
    root = DATA / 'campaigns'
    if not root.is_dir() or root.is_symlink():
        return []
    paths = [p for p in root.iterdir() if p.is_dir() and not p.is_symlink() and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', p.name) and (p / 'report.json').is_file()]
    paths.sort(key=lambda p: (p / 'report.json').stat().st_mtime, reverse=True)
    items = []
    for path in paths[:30]:
        try:
            r = read_campaign(path.name)
            items.append({'id': path.name, 'title': r['case']['title'], 'status': r['status'],
                          'completed_pairs': r['summary']['pairs'], 'requested_pairs': r['requested_pairs'],
                          'population': r['case']['population'], 'steps': r['case']['steps'],
                          'api_cost_usd': r['cost']['api_cost_usd']})
        except HTTPException:
            continue
    return items


@router.get('/campaigns/{name}', response_class=HTMLResponse, include_in_schema=False)
def campaign_report(name: str):
    try:
        source = build_html(read_campaign(name))
        script = re.search(r'<script id="campaign-script">(.*?)</script>', source, re.S).group(1)
        digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise HTTPException(409, 'Campaign report cannot be rendered') from exc
    return HTMLResponse(source, headers={
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
        'Content-Security-Policy': f"default-src 'none'; script-src 'sha256-{digest}'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"})


@router.get('/lab/campaigns/{name}/report.json')
def campaign_json(name: str, download: bool = False):
    headers = {'Cache-Control': 'no-store'}
    if download:
        headers['Content-Disposition'] = f'attachment; filename="worldlab-{name}.json"'
    return JSONResponse(read_campaign(name), headers=headers)


@router.get('/lab/examples/nubenorte/report.json')
def recorded_campaign_json():
    return FileResponse(ROOT / 'examples/recorded-campaign/report.json',
                        media_type='application/json', filename='worldlab-nubenorte.json',
                        headers={'X-Content-Type-Options': 'nosniff'})
