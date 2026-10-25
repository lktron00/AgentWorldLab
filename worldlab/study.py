"""Balanced multi-case study spending the remainder of one cumulative USD budget."""
import argparse
import asyncio
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import statistics
import sys
import time

import httpx
from .audit import audit_ledger
from .common import DATA,ROOT,write_json
from .costs import BudgetExceeded,CostLedger,amount,usd
from .errors import safe_error
from .experiment import experiment_server
from .pilot import run as run_pair,provenance
from .study_cases import CASES
from .study_policy import StudyPolicy,INSTRUCTIONS,PROMPT_VERSION,InvalidModelDecision,TokenPacer


def now():return datetime.now(timezone.utc).isoformat()


def study_frame(case,snapshot,decisions=()):
    p=[d['belief_problem']/100 for d in decisions]
    posts=snapshot['world']['posts']
    return {'step':snapshot['step'],'mean_belief_problem':statistics.mean(p)*100 if p else None,
      'mean_brier':statistics.mean((v-int(case['truth']))**2 for v in p) if p else None,
      'initial_message_sharers':len({p['user_id'] for p in posts if p['root_id']==1 and p['user_id']!=0}),
      'posts':len(posts)}


class Saver:
    def __init__(self,output,study,ledger):
        self.output,self.study,self.ledger=output,study,ledger
        self.offset=0
        self.db=sqlite3.connect(output/'decisions.sqlite')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE decisions (id TEXT PRIMARY KEY,seed INTEGER,branch TEXT,step INTEGER,actor INTEGER,case_id TEXT,body TEXT,applied INTEGER NOT NULL DEFAULT 0)')
        self.db.execute('CREATE INDEX lookup ON decisions(case_id,seed,branch,step,actor)')
        self.db.commit()

    def index(self):
        path=self.output/'decisions.jsonl'
        if not path.exists():return
        with path.open() as stream:
            stream.seek(self.offset)
            while True:
                before=stream.tell();line=stream.readline()
                if not line or not line.endswith('\n'):
                    self.offset=before;break
                event=json.loads(line)
                if event['event']=='decision':
                    self.db.execute('INSERT INTO decisions(id,seed,branch,step,actor,case_id,body) VALUES (?,?,?,?,?,?,?)',
                      (event['decision_id'],event['seed'],event['branch'],event['step'],event['actor'],event['case_id'],line))
                elif event['event']=='applied_batch':
                    self.db.executemany('UPDATE decisions SET applied=1 WHERE id=?',[(i,) for i in event['decision_ids']])
                self.offset=stream.tell()
        self.db.commit()

    def __call__(self,output=None,report=None,ledger=None):
        self.index()
        study=self.study;ledger=self.ledger
        # Derive exact allocations from the shared receipts, including invalid paid attempts.
        allocations={}
        for receipt in ledger.receipts:
            context=ledger.contexts[receipt['call_id']]
            key=context.get('seed'),context.get('branch')
            allocations[key]=allocations.get(key,Decimal(0))+amount(receipt['estimated_cost_usd'])
        for run in study['runs']:
            for pair in run['experiments']:
                for name,b in pair['branches'].items():b['cost_usd']=usd(allocations.get((pair['seed'],name),0))
                pair['cost_usd']=usd(sum((amount(b['cost_usd']) for b in pair['branches'].values()),Decimal(0)))
        summary=[]
        for case in study['cases']:
            runs=[r for r in study['runs'] if r['case_id']==case['id']]
            pairs=[p for r in runs for p in r['experiments'] if p['status']=='completed']
            by_branch={}
            for name in ('generic','diagnostic'):
                branches=[p['branches'][name] for p in pairs]
                counts=Counter()
                for b in branches:counts.update(b['action_counts'])
                by_branch[name]={'mean_probability':statistics.mean(b['trajectory'][-1]['mean_belief_problem'] for b in branches) if branches else None,
                  'mean_brier':statistics.mean(b['trajectory'][-1]['mean_brier'] for b in branches) if branches else None,
                  'action_counts':dict(counts)}
            differences=[p['branches']['diagnostic']['trajectory'][-1]['mean_brier']-p['branches']['generic']['trajectory'][-1]['mean_brier'] for p in pairs]
            summary.append({'case_id':case['id'],'title':case['title'],'pairs':len(pairs),'by_branch':by_branch,
              'mean_paired_brier_difference':statistics.mean(differences) if differences else None,
              'diagnosis_better':sum(v<0 for v in differences),'tied':differences.count(0),'diagnosis_worse':sum(v>0 for v in differences),
              'cost_usd':usd(sum((allocations.get((p['seed'],b),Decimal(0)) for r in runs for p in r['experiments'] for b in p['branches']),Decimal(0)))})
        current=ledger.summary();previous=amount(study['previous_pilot']['cost_usd'])
        study.update(updated_at=now(),summary=summary,cost={'additional':current,
          'previous_pilot_usd':usd(previous),'total_confirmed_usd':usd(previous+ledger.spent),
          'total_maximum_exposure_usd':usd(previous+ledger.spent+sum(ledger.pending.values(),Decimal(0))),
          'cumulative_budget_usd':study['cumulative_budget_usd']},
          progress={'completed_pairs':sum(s['pairs'] for s in summary),'decisions':sum(r['decisions'] for r in study['runs']),
                    'applied_decisions':self.db.execute('SELECT count(*) FROM decisions WHERE applied=1').fetchone()[0],
                    'model_calls':current['completed_calls'],'cases_with_completed_pairs':sum(s['pairs']>0 for s in summary)})
        write_json(self.output/'report.json',study)

    def close(self):
        self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        self.db.close()


def prior_debit(path):
    audit=audit_ledger(path/'costs.jsonl')
    report=json.loads((path/'report.json').read_text())
    proof=json.loads((path/'audit.json').read_text())
    if report['status']!='completed' or not proof['verified'] or audit['summary']['unresolved_calls'] or audit['journal_truncated']:
        raise ValueError('Prior pilot must have complete, audited provider receipts')
    if audit['summary']!=proof['cost']:raise ValueError('Prior pilot receipts differ from its audit')
    return {'path':str(path),'cost_usd':audit['summary']['estimated_cost_usd'],
            'costs_sha256':hashlib.sha256((path/'costs.jsonl').read_bytes()).hexdigest(),'model_calls':audit['summary']['completed_calls']}


async def execute(study,output,ledger,saver,provider,url,token,max_pairs):
    pacer=TokenPacer()
    for index in range(max_pairs):
        case=study['cases'][index%len(study['cases'])]
        seed=100000+index
        report={'kind':'study-case-pair','status':'running','case_id':case['id'],'case_definition':case,
          'requested_pairs':1,'config':{'population':20,'steps':10,'start_seed':seed},'experiments':[],'decisions':0}
        study['runs'].append(report);saver()
        try:
            await run_pair(report,output,StudyPolicy(provider,ledger,case,output,pacer),ledger,url,token,
                concurrency=20,case=case,save_fn=saver,frame_fn=lambda snapshot,decisions=():study_frame(case,snapshot,decisions))
        except BaseException as exc:
            report['status']='invalid_model_output' if isinstance(exc,InvalidModelDecision) else 'stopped'
            for p in report['experiments']:
                if p['status']=='running':p['status']='incomplete'
                for b in p['branches'].values():
                    if b['status']=='running':b['status']='incomplete'
            saver()
            if isinstance(exc,InvalidModelDecision) and not ledger.pending:
                print(f'case={case["id"]} invalid model output; usage retained, next case scheduled',flush=True)
                continue
            raise
        saver()
        print(f"case={case['id']} completed_pairs={study['progress']['completed_pairs']} total_usd={study['cost']['total_confirmed_usd']}",flush=True)
    study['status']='pair_limit'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-pilot',type=Path,default=DATA/'pilots/nubenorte-luna-20x10')
    parser.add_argument('--budget-total-usd',default='10')
    parser.add_argument('--max-pairs',type=int,default=200)
    parser.add_argument('--output',type=Path,default=DATA/'studies/nine-cases-10usd')
    args=parser.parse_args(argv)
    try:
        previous=prior_debit(args.previous_pilot.resolve());total=amount(args.budget_total_usd)
        remaining=total-amount(previous['cost_usd'])
        if not 0<remaining or total>10 or not 1<=args.max_pairs<=300:raise ValueError('Use a cumulative cap <=US$10, above the verified prior spend, and 1–300 pairs')
        if args.output.exists():raise ValueError('Study output already exists; never overwrite or reset a budget ledger')
    except (ValueError,OSError,KeyError) as exc:parser.error(str(exc))
    from dotenv import dotenv_values
    key=os.environ.get('OPENAI_API_KEY') or dotenv_values(ROOT/'.env',interpolate=False).get('OPENAI_API_KEY')
    if not key:parser.error('Missing private OPENAI_API_KEY; no generation was attempted')
    output=args.output.resolve();output.mkdir(parents=True)
    ledger=CostLedger(output/'costs.jsonl',remaining,max_in_flight=20)
    study={'schema_version':1,'kind':'balanced-ai-case-study','status':'running','started_at':now(),
      'title':'Nueve casos · evidencia y decisiones de IA','cases':CASES,'previous_pilot':previous,
      'cumulative_budget_usd':usd(total),'additional_budget_usd':usd(remaining),'model':'gpt-6-luna','effort':'low',
      'population':20,'steps':10,'concurrency':20,'instructions':INSTRUCTIONS,'prompt_version':PROMPT_VERSION,
      'runs':[],'source_sha256':provenance(output)}
    saver=Saver(output,study,ledger);saver();started=time.monotonic()
    def interrupt(signum,frame):raise KeyboardInterrupt
    previous_signal=signal.signal(signal.SIGTERM,interrupt)
    try:
        from openai import AsyncOpenAI
        async def go(url,token):
            async with AsyncOpenAI(api_key=key,base_url='https://api.openai.com/v1',max_retries=0,timeout=90,
                http_client=httpx.AsyncClient(trust_env=False,timeout=90)) as provider:
                await execute(study,output,ledger,saver,provider,url,token,args.max_pairs)
        with experiment_server(output,reuse_oasis=True,society=True) as (url,token,_):asyncio.run(go(url,token))
    except BudgetExceeded:
        study['status']='completed';study['stop_reason']='Remaining funds cannot reserve another bounded request'
    except BaseException as exc:
        study['status']='needs_reconciliation' if ledger.pending else 'interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed'
        study['error']=safe_error(exc)
    finally:
        signal.signal(signal.SIGTERM,previous_signal)
        study['finished_at']=now();study['elapsed_seconds']=round(time.monotonic()-started,3)
        saver();saver.close()
        if study['status'] in {'completed','pair_limit'} and not ledger.pending:
            try:
                from .study_audit import audit_study
                write_json(output/'audit.json',audit_study(output))
                study['audit_verified']=True
            except Exception as exc:
                study['status']='audit_failed';study['error']=safe_error(exc)
            write_json(output/'report.json',study)
        print(f"{study['status']}: {study['progress']['completed_pairs']} complete pairs; total_api_usd={study['cost']['total_confirmed_usd']}; exposure={study['cost']['total_maximum_exposure_usd']}",flush=True)
    return 0 if study['status']=='completed' else 1


if __name__=='__main__':raise SystemExit(main())
