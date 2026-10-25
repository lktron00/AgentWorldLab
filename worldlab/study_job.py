"""A finite, detached study supervisor. All generation stays inside one original USD cap."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from .common import DATA,ROOT,read_json,write_json
from .costs import amount
from .study import now

TRANSIENT={'APITimeoutError','APIConnectionError','WorkerDisappeared'}


def writer_active(output):
    path=output/'.writer.lock'
    if not path.exists():return False
    with path.open('a') as f:
        try:fcntl.flock(f,fcntl.LOCK_SH|fcntl.LOCK_NB)
        except BlockingIOError:return True
        return False


def completion(output,report):
    if report['status']!='completed':raise ValueError('Study has not completed')
    audit=read_json(output/'audit.json')
    if (not report.get('audit_verified') or not audit.get('verified') or not audit.get('budget_bounds_verified')
        or amount(audit['maximum_exposure_usd'])>amount(report['cumulative_budget_usd'])
        or audit['cost']!=report['cost']['additional']):
        raise ValueError('Completion requires verified decisions and a verified cumulative budget bound')
    record={'status':'completed','finished_at':report['finished_at'],'model':report['model'],
      'progress':report['progress'],'cost':report['cost'],'summary':report['summary'],
      'usage_complete':audit['usage_complete'],'audit_sha256':hashlib.sha256((output/'audit.json').read_bytes()).hexdigest(),
      'budget_bounds_verified':True,'unreceipted_requests':audit['unreceipted_requests']}
    write_json(output/'completion.json',record)
    lines=['# Estudio terminado','',f"Comparaciones completas: {report['progress']['completed_pairs']}. Decisiones registradas: {report['progress']['decisions']}; aplicadas: {report['progress']['applied_decisions']}.",
      '',f"Costo API confirmado según tokens reportados: US${report['cost']['total_confirmed_usd']}.",
      f"Máximo incluyendo reservas sin recibo: US${report['cost']['total_maximum_exposure_usd']} de US${report['cumulative_budget_usd']}.",
      f"Solicitudes sin recibo: {audit['unreceipted_requests']}. Sus máximos permanecen reservados; no se repitieron ni se consideran cargos confirmados.",
      '', '| Caso | Pares | Δ Brier diagnóstico − genérico |', '| --- | ---: | ---: |']
    for s in report['summary']:
        delta='—' if s['mean_paired_brier_difference'] is None else f"{s['mean_paired_brier_difference']:.6f}"
        lines.append(f"| {s['title']} | {s['pairs']} | {delta} |")
    lines+=['','Un delta negativo reduce el error respecto al estado sintético conocido. Los pares incompletos están excluidos de esta tabla.',
            'Los resultados describen modelos y fixtures sintéticos; no validan comportamiento humano.','',
            'La auditoría verifica observaciones, propuestas guardadas, acciones aplicadas, estados de los motores y el límite de gasto. Las solicitudes sin recibo solo tienen un máximo conservador, no un costo exacto.']
    (output/'results.md').write_text('\n'.join(lines)+'\n')
    return record


def run(output,max_pairs,max_restarts,probe_seconds=0):
    with (output/'.job.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return 3
        job={'pid':os.getpid(),'parent_pid':os.getppid(),'session_id':os.getsid(0),
             'started_at':now(),'status':'starting','restarts':0,'worker_pid':None,
             'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        child=None;stopping=False
        def stop(signum,frame):
            nonlocal stopping
            stopping=True
            if child is not None and child.poll() is None:child.send_signal(signal.SIGTERM)
        previous=signal.signal(signal.SIGTERM,stop)
        def save(status=None):
            if status:job['status']=status
            job['heartbeat_at']=now();job['parent_pid']=os.getppid();write_json(output/'job.json',job)
        try:
            if probe_seconds:
                save('probe')
                until=time.monotonic()+probe_seconds
                while time.monotonic()<until and not stopping:time.sleep(min(1,max(0,until-time.monotonic())))
                save('probe_completed');return 0
            for attempt in range(max_restarts+1):
                report=read_json(output/'report.json')
                if report['status']=='completed':completion(output,report);save('completed');return 0
                if stopping:save('stopped');return 0
                if writer_active(output):
                    save('waiting_for_existing_writer')
                    while writer_active(output) and not stopping:time.sleep(5);save()
                    if stopping:save('stopped');return 0
                    report=read_json(output/'report.json')
                    if report['status']=='completed':completion(output,report);save('completed');return 0
                if report['status'] in {'audit_failed','pair_limit','interrupted'}:
                    save('needs_attention');return 1
                error_type=(report.get('error') or {}).get('type')
                if attempt and report['status'] not in {'running'} and error_type not in TRANSIENT:
                    save('needs_attention');return 1
                # A report left running without a writer is an orphan; recovery audits its durable journals.
                if report['status']=='running':
                    report.update(status='needs_reconciliation',error={'type':'WorkerDisappeared','message':'El proceso anterior terminó sin guardar el cierre; se recuperan sus registros.'})
                    write_json(output/'report.json',report)
                before=len(report.get('resumptions',[]))
                job['restarts']=attempt;save('recovering')
                command=[sys.executable,'-m','worldlab.study_resume','--output',str(output),
                         '--max-pairs',str(max_pairs),'--quarantine-unknown']
                with (output/'worker.log').open('ab',buffering=0) as log:
                    child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                                           start_new_session=True,close_fds=True)
                    job['worker_pid']=child.pid;save('running')
                    while child.poll() is None:
                        time.sleep(5);save('stopping' if stopping else 'running')
                    code=child.returncode;child=None;job['worker_pid']=None;job['last_exit_code']=code
                report=read_json(output/'report.json')
                if stopping:save('stopped');return 0
                if report['status']=='completed':completion(output,report);save('completed');return 0
                if len(report.get('resumptions',[]))==before:
                    save('needs_attention');return 1
                if code<0:
                    report.update(status='needs_reconciliation',error={'type':'WorkerDisappeared','message':'El proceso terminó inesperadamente; se conservan sus reservas.'})
                    write_json(output/'report.json',report)
                save('recovering');time.sleep(min(30,2**attempt))
            save('restart_limit');return 1
        except Exception as exc:
            job['error_type']=type(exc).__name__;save('needs_attention');return 1
        finally:
            signal.signal(signal.SIGTERM,previous)
            job['finished_at']=now();save()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=DATA/'studies/nine-cases-10usd')
    p.add_argument('--max-pairs',type=int,default=200)
    p.add_argument('--max-restarts',type=int,default=12)
    p.add_argument('--detach',action='store_true')
    p.add_argument('--probe-seconds',type=int,default=0,help=argparse.SUPPRESS)
    a=p.parse_args(argv);output=a.output.resolve()
    if not output.is_dir() or not 1<=a.max_pairs<=300 or not 0<=a.max_restarts<=20 or not 0<=a.probe_seconds<=60:p.error('Invalid bounded job settings')
    if a.detach:
        with (output/'.job.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
            except BlockingIOError:
                print(json.dumps({'already_running':True,**read_json(output/'job.json')}));return 0
        command=[sys.executable,'-m','worldlab.study_job','--output',str(output),'--max-pairs',str(a.max_pairs),
                 '--max-restarts',str(a.max_restarts),'--probe-seconds',str(a.probe_seconds)]
        with (output/'job.log').open('ab',buffering=0) as log:
            child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                                   start_new_session=True,close_fds=True)
        print(json.dumps({'pid':child.pid,'job_file':str(output/'job.json'),'detached':True}));return 0
    return run(output,a.max_pairs,a.max_restarts,a.probe_seconds)


if __name__=='__main__':raise SystemExit(main())
