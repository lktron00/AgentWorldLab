#!/usr/bin/env python3
"""Publish a recorded study or verify its portable public bundle. Never calls models."""
import argparse
import base64
from collections import Counter, defaultdict
from decimal import Decimal
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import statistics

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ('seed','branch','step','actor','case_id','observation','observation_sha256',
          'action','model','usage','estimated_cost_usd','reason','belief_problem',
          'belief_loss','evidence_assessment','evidence_refs','invalid_evidence_refs','prompt_version')

def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()

def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')

def read_lines(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            if not line.endswith('\n'): raise ValueError('Truncated public journal')
            yield json.loads(line)

def write_lines(path, rows):
    # mtime=0 makes rebuilds byte-identical. No source filename enters the archive.
    with path.open('wb') as target:
        with gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0) as stream:
            for row in rows: stream.write(encoded(row)+b'\n')

def public_decision(row, applied):
    result = {k: row[k] for k in FIELDS if k in row}
    result['id'] = f"{row.get('case_id','pilot')}-{row['seed']}-{row['branch']}-{row['step']}-{row['actor']}"
    result['applied'] = bool(applied)
    if '/Users/' in json.dumps(result) or re.search(r'sk-(?:proj-)?[A-Za-z0-9_-]{20,}', json.dumps(result)):
        raise ValueError('Unexpected private content in a synthetic observation')
    return result

def usage_cost(usage, rates):
    incoming = usage['input_tokens']; outgoing = usage['output_tokens']
    details = usage.get('input_tokens_details') or {}
    cached = details.get('cached_tokens', 0); writes = details.get('cache_write_tokens', 0)
    reasoning = (usage.get('output_tokens_details') or {}).get('reasoning_tokens', 0)
    if not all(type(v) is int and v >= 0 for v in (incoming,outgoing,cached,writes,reasoning)):
        raise ValueError('Invalid public token usage')
    if cached+writes > incoming or reasoning > outgoing: raise ValueError('Inconsistent public usage')
    return ((incoming-cached-writes)*Decimal(rates['input']) + cached*Decimal(rates['cached_input'])
            + writes*Decimal(rates['cache_write']) + outgoing*Decimal(rates['output']))/1_000_000

def html(report, decisions, template):
    buffer=io.BytesIO()
    with gzip.GzipFile(filename='',mode='wb',fileobj=buffer,mtime=0) as stream:
        stream.write(encoded({'report':report,'decisions':decisions}))
    packed=base64.b64encode(buffer.getvalue()).decode()
    source=template.replace('__PACKED_RECORDING__',packed)
    script=re.search(r'<script id="viewer">(.*?)</script>',source,re.S).group(1)
    digest=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    return source.replace('__SCRIPT_HASH__',digest)

def export(root, source):
    source=source.resolve();r=json.loads((source/'report.json').read_text())
    a=json.loads((source/'audit.json').read_text());c=json.loads((source/'completion.json').read_text())
    if r['status']!='completed' or not a['verified'] or not a['budget_bounds_verified']:
        raise ValueError('Only a completed, budget-audited study can be published')
    if c['audit_sha256']!=hashlib.sha256((source/'audit.json').read_bytes()).hexdigest():
        raise ValueError('Completion does not match the final audit')
    for key in ('progress','cost','summary'):
        if r[key]!=c[key]:raise ValueError('Completion and report differ')
    folder=root/'examples/recorded-study';folder.mkdir(parents=True,exist_ok=True)
    with (source/'costs.jsonl').open() as stream: price=json.loads(next(stream))['price_book']
    pairs=[];incomplete=[]
    for run in r['runs']:
        for pair in run['experiments']:
            item={'case_id':run['case_id'],'seed':pair['seed'],'status':pair['status'],
                  'initial_world_sha256':pair['initial_world_sha256'],'branches':{}}
            for name,branch in pair['branches'].items():
                item['branches'][name]={k:branch[k] for k in ('trajectory','action_counts','cost_usd') if k in branch}
            (pairs if pair['status']=='completed' else incomplete).append(item)
    selected={case['id']:min(p['seed'] for p in pairs if p['case_id']==case['id']) for case in r['cases']}
    report={k:r[k] for k in ('status','title','model','effort','population','steps','instructions','prompt_version',
              'cases','progress','cost','summary','started_at','finished_at','stop_reason')}
    report.update(schema_version=1,kind='recorded-all-ai-study',recording=True,
        selected_pair_seeds=selected,complete_pairs=len(pairs),incomplete_pairs=incomplete,
        recording_scope='All valid decisions and all completed comparisons; viewer shows the first completed pair per case.',
        publication_scope='Provider IDs, local paths, raw provider payloads and engine databases are omitted. This bundle is not a complete engine replay or full audit reproduction.',
        source_report_sha256=hashlib.sha256((source/'report.json').read_bytes()).hexdigest(),
        source_audit_sha256=hashlib.sha256((source/'audit.json').read_bytes()).hexdigest(),
        runtime_source_sha256=r['resumptions'][-1]['source_sha256'])
    sample=[]
    with sqlite3.connect(f'file:{source/"decisions.sqlite"}?mode=ro',uri=True) as db:
        def rows():
            for body,applied in db.execute('SELECT body,applied FROM decisions ORDER BY seed,branch,step,actor'):
                row=public_decision(json.loads(body),applied)
                if row['seed']==selected[row['case_id']]:sample.append(row)
                yield row
        write_lines(folder/'decisions.jsonl.gz',rows())
    invalid=[]
    for row in read_lines(source/'decisions.jsonl'):
        if row.get('event')=='invalid_proposal':
            invalid.append({k:v for k,v in row.items() if k!='call_id'})
    # Include their genuine saved usage, rather than treating invalid paid attempts as free.
    contexts={};held={};paid_invalid=[]
    wanted={}
    for row in read_lines(source/'decisions.jsonl'):
        if row.get('event')=='invalid_proposal':wanted[row['call_id']]=row
    for e in read_lines(source/'costs.jsonl'):
        if e['event']=='reserved':
            contexts[e['call_id']]={k:e[k] for k in ('seed','branch','step','actor','case_id','reserved_usd')}
        elif e['event']=='quarantined':held[e['call_id']]=contexts[e['call_id']]
        elif e['event']=='charged' and e['call_id'] in wanted:
            row=wanted[e['call_id']]
            paid_invalid.append({**{k:v for k,v in row.items() if k!='call_id'},'model':r['model'],
                                 'usage':e['usage'],'estimated_cost_usd':e['estimated_cost_usd']})
    write_json(folder/'report.json',report)
    write_json(folder/'comparisons.json',pairs)
    write_json(folder/'execution-audit.json',a)
    write_json(folder/'price-book.json',price)
    write_json(folder/'invalid-proposals.json',paid_invalid)
    write_json(folder/'unreceipted-requests.json',list(held.values()))
    write_lines(folder/'sample-decisions.jsonl.gz',sample)
    source_html=html(report,sample,(root/'web/recorded-study-template.html').read_text())
    (folder/'index.html').write_text(source_html);(root/'web/recorded-study.html').write_text(source_html)
    # The earlier all-AI pilot is published separately, and remains the same cumulative debit.
    pilot=source.parent.parent/'pilots/nubenorte-luna-20x10';pr=json.loads((pilot/'report.json').read_text())
    pa=json.loads((pilot/'audit.json').read_text())
    if not pa['verified'] or pr['cost']['estimated_cost_usd']!=r['cost']['previous_pilot_usd']:
        raise ValueError('Pilot and study debit differ')
    pf=root/'examples/recorded-pilot';pf.mkdir(parents=True,exist_ok=True)
    pub={k:pr[k] for k in ('title','status','config','summary','cost','instructions','prompt_version','price_book','started_at','finished_at')}
    pub.update(recording=True,schema_version=1,kind='recorded-all-ai-pilot',decisions=pr['decisions'])
    write_json(pf/'report.json',pub);write_json(pf/'execution-audit.json',pa)
    applied=set()
    for e in read_lines(pilot/'decisions.jsonl'):
        if e.get('event')=='applied_batch':applied.update(e['decision_ids'])
    write_lines(pf/'decisions.jsonl.gz',(public_decision(e,e['decision_id'] in applied)
                for e in read_lines(pilot/'decisions.jsonl') if e.get('event')=='decision'))
    artifacts={}
    for f in sorted([*folder.iterdir(),*pf.iterdir()]):
        if f.name in {'manifest.json','README.md'} or not f.is_file():continue
        artifacts[f.relative_to(root).as_posix()]={'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
    write_json(folder/'manifest.json',{'schema_version':1,'scope':'Public package integrity, not the complete private execution audit','artifacts':artifacts})
    return verify(root)

def verify(root):
    folder=root/'examples/recorded-study';r=json.loads((folder/'report.json').read_text())
    a=json.loads((folder/'execution-audit.json').read_text());manifest=json.loads((folder/'manifest.json').read_text())
    for name,meta in manifest['artifacts'].items():
        path=root/name
        if path.stat().st_size!=meta['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=meta['sha256']:
            raise ValueError(f'Public artifact mismatch: {name}')
    if r['progress']['completed_pairs']!=102 or len(r['cases'])!=9 or not r['recording']:
        raise ValueError('Unexpected recorded study scope')
    pairs=json.loads((folder/'comparisons.json').read_text())
    if len(pairs)!=102 or len(r['incomplete_pairs'])!=4:raise ValueError('Incomplete pairs entered the comparison')
    pair_lookup={(p['seed'],b):p for p in pairs for b in ('generic','diagnostic')}
    counts=Counter();cost=Decimal(0);seen=set();sample=[];final=defaultdict(list);actions=defaultdict(Counter)
    rates=json.loads((folder/'price-book.json').read_text())['models'][r['model']]
    for row in read_lines(folder/'decisions.jsonl.gz'):
        key=(row['seed'],row['branch'],row['step'],row['actor'])
        if key in seen:raise ValueError('Duplicate public decision')
        seen.add(key)
        if fingerprint(row['observation'])!=row['observation_sha256']:raise ValueError('Public observation changed')
        if usage_cost(row['usage'],rates)!=Decimal(row['estimated_cost_usd']):raise ValueError('Public decision cost changed')
        cost+=Decimal(row['estimated_cost_usd']);counts['decisions']+=1;counts['applied']+=row['applied']
        if row['seed']==r['selected_pair_seeds'][row['case_id']]:sample.append(row)
        if (row['seed'],row['branch']) in pair_lookup:
            if not row['applied']:raise ValueError('Unapplied decision in a completed pair')
            actions[row['seed'],row['branch']][row['action']['kind']]+=1
            if row['step']==9:final[row['seed'],row['branch']].append(row['belief_problem'])
    if counts!={'decisions':41770,'applied':41720}:raise ValueError('Public decision count changed')
    for p in pairs:
        truth=next(c['truth'] for c in r['cases'] if c['id']==p['case_id'])
        for b in ('generic','diagnostic'):
            values=final[p['seed'],b];branch=p['branches'][b]
            if len(values)!=20 or sum(actions[p['seed'],b].values())!=200:raise ValueError('Missing completed world decisions')
            if actions[p['seed'],b]!=branch['action_counts']:raise ValueError('Public action counts differ')
            if abs(statistics.mean(values)-branch['trajectory'][-1]['mean_belief_problem'])>1e-10:raise ValueError('Public mean differs')
            if abs(statistics.mean((v/100-int(truth))**2 for v in values)-branch['trajectory'][-1]['mean_brier'])>1e-12:raise ValueError('Public Brier differs')
    for s in r['summary']:
        rows=[p for p in pairs if p['case_id']==s['case_id']]
        deltas=[p['branches']['diagnostic']['trajectory'][-1]['mean_brier']-p['branches']['generic']['trajectory'][-1]['mean_brier'] for p in rows]
        if len(rows)!=s['pairs'] or abs(statistics.mean(deltas)-s['mean_paired_brier_difference'])>1e-12:
            raise ValueError('Public aggregate differs from paired comparisons')
    invalid=json.loads((folder/'invalid-proposals.json').read_text())
    if len(invalid)!=3:raise ValueError('Missing paid invalid proposals')
    for row in invalid:
        if usage_cost(row['usage'],rates)!=Decimal(row['estimated_cost_usd']):raise ValueError('Invalid attempt cost differs')
        cost+=Decimal(row['estimated_cost_usd'])
    if cost!=Decimal(r['cost']['additional']['estimated_cost_usd']):raise ValueError('Public costs do not reconcile')
    held=json.loads((folder/'unreceipted-requests.json').read_text())
    bound=sum((Decimal(e['reserved_usd']) for e in held),Decimal(0))
    confirmed=cost+Decimal(r['cost']['previous_pilot_usd'])
    if len(held)!=17 or str(bound)!=r['cost']['additional']['quarantined_reserved_usd']:raise ValueError('Unknown reservations changed')
    if confirmed!=Decimal(r['cost']['total_confirmed_usd']) or confirmed+bound!=Decimal(r['cost']['total_maximum_exposure_usd']) or confirmed+bound>10:
        raise ValueError('Cumulative public budget does not reconcile')
    if a['cost']!=r['cost']['additional'] or not a['verified'] or not a['budget_bounds_verified'] or a['usage_complete']:
        raise ValueError('Recorded audit scope differs')
    sample_saved=list(read_lines(folder/'sample-decisions.jsonl.gz'))
    if sample!=sample_saved or len(sample)!=3600:raise ValueError('Viewer sample differs from full archive')
    expected=html(r,sample,(root/'web/recorded-study-template.html').read_text())
    if (folder/'index.html').read_text()!=expected or (root/'web/recorded-study.html').read_text()!=expected:
        raise ValueError('Recorded HTML is stale')
    pf=root/'examples/recorded-pilot';pr=json.loads((pf/'report.json').read_text())
    pcost=Decimal(0);pc=Counter()
    for row in read_lines(pf/'decisions.jsonl.gz'):
        if not row['applied'] or fingerprint(row['observation'])!=row['observation_sha256']:raise ValueError('Pilot decision changed')
        value=usage_cost(row['usage'],pr['price_book']['models'][pr['config']['model']])
        if value!=Decimal(row['estimated_cost_usd']):raise ValueError('Pilot cost changed')
        pcost+=value;pc['decisions']+=1
    if pc['decisions']!=4000 or pcost!=Decimal(r['cost']['previous_pilot_usd']):raise ValueError('Prior pilot debit differs')
    return {'verified':True,'scope':'Public decision, observation, usage, comparison and archive integrity checks; original engine audit is recorded evidence.',
            'study_decisions':counts['decisions'],'applied_study_decisions':counts['applied'],
            'pilot_decisions':pc['decisions'],'complete_pairs':len(pairs),'viewer_sample':len(sample),
            'confirmed_cumulative_usd':str(confirmed),'maximum_cumulative_usd':str(confirmed+bound)}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args();root=args.root.resolve()
    if args.check:result=verify(root)
    else:result=export(root,args.source or root/'data/studies/nine-cases-10usd')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
