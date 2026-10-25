"""Resume a stopped, fully reconciled study; retain its one original generation ledger."""
import argparse
import asyncio
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import time

import httpx
from .audit import audit_ledger
from .common import DATA,ROOT,read_json,write_json
from .costs import CostLedger,BudgetExceeded,PRICE_BOOK,amount
from .errors import safe_error
from .experiment import experiment_server
from .pilot import provenance
from .study import Saver,execute,now,prior_debit
from .study_audit import audit_study
from .study_cases import CASES
from .study_policy import INSTRUCTIONS


def reopen_ledger(path):
    audit=audit_ledger(path,maximum=1024*1024*1024)
    if (audit['warnings'] or audit['journal_truncated'] or audit['recovered_receipts']
        or audit['summary']['unresolved_calls'] or audit['budget_exceeded']):
        raise ValueError('Cannot resume with unverified, unresolved or incomplete usage')
    if audit['price_book']!=PRICE_BOOK:raise ValueError('The recorded price book changed')
    with path.open() as stream:
        header=json.loads(next(stream));contexts={}
        for line in stream:
            e=json.loads(line)
            if e['event']=='reserved':
                contexts[e['call_id']]={k:v for k,v in e.items() if k not in {'event','at','call_id','model','input_tokens_counted','reserved_usd'}}
    ledger=object.__new__(CostLedger)
    ledger.path=path;ledger.budget=amount(header['budget_usd']);ledger.max_in_flight=header['max_in_flight']
    ledger.spent=amount(audit['summary']['estimated_cost_usd']);ledger.receipts=audit['receipts']
    ledger.pending={};ledger.uncertain_calls=set();ledger.contexts=contexts
    if ledger.summary()!=audit['summary']:raise ValueError('Reopened accounting differs from the audit')
    return ledger


def preflight(output):
    study=read_json(output/'report.json')
    if study['status'] not in {'failed','interrupted'}:raise ValueError('Only a stopped study may resume')
    if (study['cases']!=CASES or study['instructions']!=INSTRUCTIONS or study['model']!='gpt-6-luna'
        or study['effort']!='low' or study['population']!=20 or study['steps']!=10):
        raise ValueError('The experiment design changed')
    if prior_debit(Path(study['previous_pilot']['path']))!=study['previous_pilot']:raise ValueError('Prior debit changed')
    proof=audit_study(output)
    ledger=reopen_ledger(output/'costs.jsonl')
    if ledger.budget+amount(study['previous_pilot']['cost_usd'])!=amount(study['cumulative_budget_usd']):
        raise ValueError('Original cumulative budget does not match the ledger')
    return study,ledger,proof


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=DATA/'studies/nine-cases-10usd')
    p.add_argument('--max-pairs',type=int,default=200)
    args=p.parse_args(argv);output=args.output.resolve()
    if not output.is_dir() or not 1<=args.max_pairs<=300:p.error('Existing study and 1–300 pair limit required')
    with (output/'.writer.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:p.error('Another resume writer holds the study lock')
        try:study,ledger,proof=preflight(output)
        except (ValueError,OSError,KeyError) as exc:p.error(str(exc))
        start=len(study['runs'])
        if start>=args.max_pairs:p.error('Pair limit must exceed existing attempted pairs')
        from dotenv import dotenv_values
        key=os.environ.get('OPENAI_API_KEY') or dotenv_values(ROOT/'.env',interpolate=False).get('OPENAI_API_KEY')
        if not key:p.error('Missing private OPENAI_API_KEY; no generation was attempted')
        phase=output/'resumptions'/f'{len(study.get("resumptions",[]))+1:03d}'
        phase.mkdir(parents=True)
        write_json(phase/'prior-report.json',study);write_json(phase/'prior-audit.json',proof)
        if (output/'server.log').exists():shutil.copy2(output/'server.log',phase/'prior-server.log')
        if (output/'audit.json').exists():(output/'audit.json').replace(phase/'previous-audit.json')
        entry={'started_at':now(),'next_index':start,'next_seed':100000+start,
          'previous_status':study['status'],'previous_error':study.get('error'),
          'costs_sha256_before':hashlib.sha256((output/'costs.jsonl').read_bytes()).hexdigest(),
          'prior_cost':proof['total_confirmed_usd'],'source_sha256':provenance(phase),
          'protocol':'Same cases, model, actions, prompts and prices; retry input counting only, never generation.'}
        study.setdefault('resumptions',[]).append(entry)
        old_elapsed=study.get('elapsed_seconds',0)
        for k in ('error','finished_at','audit_verified','stop_reason'):study.pop(k,None)
        study['status']='running';saver=Saver(output,study,ledger,resume=True);saver();started=time.monotonic()
        def interrupt(signum,frame):raise KeyboardInterrupt
        old_signal=signal.signal(signal.SIGTERM,interrupt)
        try:
            from openai import AsyncOpenAI
            async def go(url,token):
                async with AsyncOpenAI(api_key=key,base_url='https://api.openai.com/v1',max_retries=0,timeout=90,
                    http_client=httpx.AsyncClient(trust_env=False,timeout=90)) as provider:
                    await execute(study,output,ledger,saver,provider,url,token,args.max_pairs,start_index=start)
            with experiment_server(output,reuse_oasis=True,society=True) as (url,token,_):asyncio.run(go(url,token))
        except BudgetExceeded:
            study['status']='completed';study['stop_reason']='Remaining funds cannot reserve another bounded request'
        except BaseException as exc:
            study['status']='needs_reconciliation' if ledger.pending else 'interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed'
            study['error']=safe_error(exc)
        finally:
            signal.signal(signal.SIGTERM,old_signal)
            study['finished_at']=now();entry['finished_at']=study['finished_at']
            study['elapsed_seconds']=round(old_elapsed+time.monotonic()-started,3)
            saver();saver.close()
            if study['status'] in {'completed','pair_limit'} and not ledger.pending:
                try:
                    write_json(output/'audit.json',audit_study(output));study['audit_verified']=True
                except Exception as exc:study['status']='audit_failed';study['error']=safe_error(exc)
            write_json(output/'report.json',study)
            print(f"{study['status']}: {study['progress']['completed_pairs']} complete pairs; total_api_usd={study['cost']['total_confirmed_usd']}; exposure={study['cost']['total_maximum_exposure_usd']}",flush=True)
        return 0 if study['status']=='completed' else 1


if __name__=='__main__':raise SystemExit(main())
