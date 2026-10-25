"""Resume one study ledger, retaining full bounds for explicitly quarantined unknown usage."""
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
import uuid

import httpx
from .audit import audit_ledger
from .common import DATA,ROOT,read_json,write_json
from .costs import CostLedger,BudgetExceeded,PRICE_BOOK,amount
from .errors import safe_error
from .experiment import experiment_server,append_decision,fingerprint
from .pilot import provenance
from .study import Saver,execute,now,prior_debit
from .study_audit import audit_study
from .study_cases import CASES
from .study_policy import INSTRUCTIONS,Decision
from .society_models import AccountAction
from .observations import validate_agent_action


def reopen_ledger(path,*,allow_quarantined=False,quarantine_unknown=False):
    audit=audit_ledger(path,maximum=1024*1024*1024)
    if audit['warnings'] or audit['journal_truncated'] or audit['budget_exceeded']:
        raise ValueError('Cannot resume with unverified or incomplete usage events')
    if audit['price_book']!=PRICE_BOOK:raise ValueError('The recorded price book changed')
    unknown=[c for c in audit['calls'] if c['receipt'] is None]
    if unknown and not (quarantine_unknown or (allow_quarantined and all(c['quarantined'] for c in unknown))):
        raise ValueError('Cannot resume with unresolved usage without retaining its full quarantine bound')
    writer=object.__new__(CostLedger);writer.path=path
    if audit['recovered_receipts']:
        if not quarantine_unknown:raise ValueError('Uncommitted receipts require explicit recovery')
        for c in audit['calls']:
            if c['receipt'] is not None and not c['charged']:writer.append({'event':'charged',**c['receipt']})
        audit=audit_ledger(path,maximum=1024*1024*1024)
    with path.open() as stream:
        header=json.loads(next(stream));contexts={}
        for line in stream:
            e=json.loads(line)
            if e['event']=='reserved':
                contexts[e['call_id']]={k:v for k,v in e.items() if k not in {'event','at','call_id','model','input_tokens_counted','reserved_usd'}}
    ledger=writer
    ledger.budget=amount(header['budget_usd']);ledger.max_in_flight=header['max_in_flight']
    ledger.spent=amount(audit['summary']['estimated_cost_usd']);ledger.receipts=audit['receipts']
    ledger.pending={c['call_id']:amount(c['reserved_usd']) for c in unknown if not c['quarantined']}
    ledger.held={c['call_id']:amount(c['reserved_usd']) for c in unknown if c['quarantined']}
    ledger.uncertain_calls=set(ledger.pending);ledger.contexts=contexts
    if quarantine_unknown:
        for call_id in list(ledger.pending):ledger.quarantine(call_id,'Stopped worker; preserve full bound, never retry this request')
    expected=audit_ledger(path,maximum=1024*1024*1024)['summary'] if quarantine_unknown else audit['summary']
    if ledger.summary()!=expected:raise ValueError('Reopened accounting differs from the audit')
    return ledger


def recover_saved_proposals(output,ledger):
    """Recover durable responses lost between receipt and decision writes; never apply or regenerate."""
    known=set();journal=output/'decisions.jsonl'
    if journal.exists():
        for line in journal.open():
            if not line.endswith('\n'):raise ValueError('Truncated decision journal requires repair')
            e=json.loads(line)
            if e['event'] in {'decision','invalid_proposal'}:known.add(e['call_id'])
    missing={r['call_id']:r for r in ledger.receipts if r['call_id'] not in known}
    if not missing:return
    for line in (output/'costs.jsonl').open():
        e=json.loads(line)
        if e['event']!='response' or e['call_id'] not in missing:continue
        call_id=e['call_id'];receipt=missing[call_id];context=ledger.contexts[call_id]
        body=e['response'];view=json.loads(context['request']['input'][0]['content'])
        fields={k:context[k] for k in ('seed','branch','step','actor','case_id')}
        try:
            calls=[c for c in body.get('output',[]) if c.get('type')=='function_call']
            if body.get('status')!='completed' or len(calls)!=1 or calls[0].get('name')!='choose_action':raise ValueError('Incomplete proposal')
            d=Decision.model_validate_json(calls[0]['arguments'])
            action=AccountAction(kind=d.kind,content=d.content,post_id=d.post_id)
            validate_agent_action(action.model_dump(),view)
        except ValueError as exc:
            append_decision(journal,{'event':'invalid_proposal',**fields,'call_id':call_id,
              'attempt':context.get('attempt',0),'error_type':type(exc).__name__,'note':'Recovered durable response; never applied or retried.'})
            continue
        visible={f'post-{p["post_id"]}' for p in view['feed']+view['own_posts']}|{c['result']['id'] for c in view['checks']}
        visible|={f'post-{m["action"]["post_id"]}' for m in view['memory'] if m['action'].get('post_id') is not None}
        append_decision(journal,{'event':'decision','decision_id':uuid.uuid4().hex,**fields,**receipt,
          'observation':view,'observation_sha256':fingerprint(view),'action':action.model_dump(),
          'reason':d.reason,'belief_problem':d.belief_problem,'evidence_assessment':d.evidence_assessment,
          'evidence_refs':d.evidence_refs,'invalid_evidence_refs':[ref for ref in d.evidence_refs if ref not in visible],
          'prompt_version':context['prompt_version'],'recovered_after_exit':True})


def preflight(output,*,quarantine_unknown=False):
    study=read_json(output/'report.json')
    allowed={'failed','interrupted','needs_reconciliation','running'} if quarantine_unknown else {'failed','interrupted'}
    if study['status'] not in allowed:raise ValueError('Only a stopped study may resume')
    if (study['cases']!=CASES or study['instructions']!=INSTRUCTIONS or study['model']!='gpt-6-luna'
        or study['effort']!='low' or study['population']!=20 or study['steps']!=10):
        raise ValueError('The experiment design changed')
    if prior_debit(Path(study['previous_pilot']['path']))!=study['previous_pilot']:raise ValueError('Prior debit changed')
    ledger=reopen_ledger(output/'costs.jsonl',allow_quarantined=quarantine_unknown,quarantine_unknown=quarantine_unknown)
    if ledger.budget+amount(study['previous_pilot']['cost_usd'])!=amount(study['cumulative_budget_usd']):
        raise ValueError('Original cumulative budget does not match the ledger')
    recover_saved_proposals(output,ledger)
    for run in study['runs']:
        if run['status']=='running':run['status']='stopped'
        for pair in run['experiments']:
            if pair['status']=='running':pair['status']='incomplete'
            for branch in pair['branches'].values():
                if branch['status']=='running':branch['status']='incomplete'
    saver=Saver(output,study,ledger,resume=True)
    try:saver()
    finally:saver.close()
    proof=audit_study(output,allow_quarantined=quarantine_unknown)
    return study,ledger,proof


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=DATA/'studies/nine-cases-10usd')
    p.add_argument('--max-pairs',type=int,default=200)
    p.add_argument('--quarantine-unknown',action='store_true',help='Retain unknown generation maxima, never retry them')
    args=p.parse_args(argv);output=args.output.resolve()
    if not output.is_dir() or not 1<=args.max_pairs<=300:p.error('Existing study and 1–300 pair limit required')
    with (output/'.writer.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:p.error('Another writer holds the study lock')
        original=read_json(output/'report.json')
        phase=output/'resumptions'/f'{len(original.get("resumptions",[]))+1:03d}-{uuid.uuid4().hex[:8]}'
        phase.mkdir(parents=True)
        write_json(phase/'prior-report.json',original)
        entry={'started_at':now(),'previous_status':original['status'],'previous_error':original.get('error'),
          'costs_sha256_before':hashlib.sha256((output/'costs.jsonl').read_bytes()).hexdigest(),
          'source_sha256':provenance(phase),'phase_path':str(phase.relative_to(output)),
          'protocol':'Same model and observations; unknown usage keeps its full bound and is never regenerated.'}
        try:study,ledger,proof=preflight(output,quarantine_unknown=args.quarantine_unknown)
        except (ValueError,OSError,KeyError) as exc:p.error(str(exc))
        start=len(study['runs'])
        if start>=args.max_pairs:p.error('Pair limit must exceed existing attempted pairs')
        from dotenv import dotenv_values
        key=os.environ.get('OPENAI_API_KEY') or dotenv_values(ROOT/'.env',interpolate=False).get('OPENAI_API_KEY')
        if not key:p.error('Missing private OPENAI_API_KEY; no generation was attempted')
        write_json(phase/'prior-audit.json',proof)
        if (output/'server.log').exists():shutil.copy2(output/'server.log',phase/'prior-server.log')
        if (output/'audit.json').exists():(output/'audit.json').replace(phase/'previous-audit.json')
        entry.update(next_index=start,next_seed=100000+start,prior_cost=proof['total_confirmed_usd'],
                     quarantined_calls=len(ledger.held))
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
                    proof=audit_study(output,allow_quarantined=args.quarantine_unknown)
                    write_json(output/'audit.json',proof);study['audit_verified']=True
                    study['usage_complete']=proof['usage_complete']
                except Exception as exc:study['status']='audit_failed';study['error']=safe_error(exc)
            write_json(output/'report.json',study)
            print(f"{study['status']}: {study['progress']['completed_pairs']} complete pairs; confirmed_usd={study['cost']['total_confirmed_usd']}; maximum_usd={study['cost']['total_maximum_exposure_usd']}",flush=True)
        return 0 if study['status']=='completed' else 1


if __name__=='__main__':raise SystemExit(main())
