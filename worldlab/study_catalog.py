"""Read-only multi-case study browser. Decision queries use a derived SQLite index."""
import base64
import hashlib
import fcntl
import json
import re
import sqlite3
from fastapi import APIRouter,HTTPException,Query
from fastapi.responses import HTMLResponse,FileResponse,JSONResponse,Response
from .common import DATA,ROOT
from .reports import read_artifact

router=APIRouter()


def directory(name):
    root=DATA/'studies';path=root/name
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',name) or root.is_symlink() or path.is_symlink() or not path.is_dir():
        raise HTTPException(404,'Study not found')
    return path


def held_lock(path):
    if path.is_symlink() or not path.is_file():return False
    with path.open('r') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_SH|fcntl.LOCK_NB)
        except BlockingIOError:return True
        return False


def report_for(name):
    try:
        report=read_artifact(directory(name)/'report.json')
        if report['kind']!='balanced-ai-case-study':raise ValueError('Invalid study')
        folder=directory(name)
        if (folder/'job.json').is_file() and not (folder/'job.json').is_symlink():
            report['job']=read_artifact(folder/'job.json')
        if report['status']=='running' and report.get('resumptions') and not held_lock(folder/'.writer.lock'):
            active=held_lock(folder/'.job.lock')
            report['status']='recovering' if active else 'needs_reconciliation'
            if not active:report['error']={'type':'WriterNotRunning','message':'El proceso no está activo. El último corte se conserva; requiere recuperación.'}
        return report
    except (ValueError,OSError,KeyError) as exc:raise HTTPException(409,'Invalid study artifact') from exc


@router.get('/lab/studies')
def catalog():
    root=DATA/'studies'
    if not root.is_dir() or root.is_symlink():return []
    paths=sorted((p for p in root.iterdir() if p.is_dir() and not p.is_symlink() and (p/'report.json').is_file()),key=lambda p:(p/'report.json').stat().st_mtime,reverse=True)
    result=[]
    for path in paths[:30]:
        try:
            r=report_for(path.name)
            result.append({'id':path.name,'kind':r['kind'],'title':r['title'],'status':r['status'],
              'completed_pairs':r['progress']['completed_pairs'],'requested_pairs':'presupuesto',
              'population':r['population'],'steps':r['steps'],'api_cost_usd':r['cost']['total_confirmed_usd']})
        except HTTPException:continue
    return result


@router.get('/studies/{name}',include_in_schema=False)
def page(name:str):
    payload=json.dumps(report_for(name),ensure_ascii=False,separators=(',',':'))
    for a,b in (('&','\\u0026'),('<','\\u003c'),('>','\\u003e'),('\u2028','\\u2028'),('\u2029','\\u2029')):payload=payload.replace(a,b)
    source=(ROOT/'web/study-report.html').read_text().replace('__STUDY_DATA__',payload)
    script=re.search(r'<script id="study-script">(.*?)</script>',source,re.S).group(1)
    digest=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    return HTMLResponse(source,headers={'Cache-Control':'no-store','Content-Security-Policy':f"default-src 'none'; script-src 'sha256-{digest}'; connect-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"})


@router.get('/lab/studies/{name}/decisions')
def decisions(name:str,case_id:str=Query(pattern='^[a-z0-9-]{1,60}$'),seed:int=Query(ge=0),
 branch:str=Query(pattern='^(generic|diagnostic)$'),step:int=Query(ge=0,le=9),actor:int|None=Query(default=None,ge=1,le=20)):
    path=directory(name)/'decisions.sqlite'
    if path.is_symlink() or not path.is_file():raise HTTPException(409,'Decision index not available')
    query='SELECT body,applied FROM decisions WHERE case_id=? AND seed=? AND branch=? AND step=?';args=[case_id,seed,branch,step]
    if actor is not None:query+=' AND actor=?';args.append(actor)
    with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as db:
        result=[{**json.loads(body),'applied':bool(applied)} for body,applied in db.execute(query+' ORDER BY actor LIMIT 20',args)]
    return JSONResponse(result,headers={'Cache-Control':'no-store'})


@router.get('/lab/studies/{name}/files/{filename}')
def download(name:str,filename:str):
    if filename not in {'report.json','costs.jsonl','decisions.jsonl','audit.json','decisions.sqlite','completion.json','results.md'}:raise HTTPException(404,'Unknown artifact')
    path=directory(name)/filename
    if path.is_symlink() or not path.is_file():raise HTTPException(404,'Artifact unavailable')
    if filename in {'decisions.sqlite','costs.jsonl','decisions.jsonl','audit.json','completion.json','results.md'}:
        if report_for(name)['status'] in {'running','recovering'} or held_lock(directory(name)/'.job.lock'):
            raise HTTPException(409,'Complete exports are available after the job stops; use the live decision viewer meanwhile')
    if filename=='report.json':
        return Response(path.read_bytes(),media_type='application/json',headers={'Content-Disposition':f'attachment; filename=worldlab-{name}-report.json','Cache-Control':'no-store'})
    return FileResponse(path,filename='worldlab-'+name+'-'+filename,headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
