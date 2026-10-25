"""Streaming offline audit for a budget-limited study, including an incomplete final pair."""
import hashlib
import json
from pathlib import Path
from decimal import Decimal
import sqlite3
from .audit import AuditError,audit_ledger
from .common import read_json,write_json
from .costs import amount,usd
from .experiment import fingerprint,world_fingerprint
from .society_contract import validate_batch
from .study_cases import view,tool_result


def lines(path):
    with path.open() as stream:
        for line in stream:
            if not line.endswith('\n'):raise AuditError('Truncated journal')
            yield json.loads(line)


def audit_study(output):
    output=Path(output);report=read_json(output/'report.json')
    accounting=audit_ledger(output/'costs.jsonl',maximum=1024*1024*1024)
    if accounting['warnings'] or accounting['journal_truncated'] or accounting['summary']['unresolved_calls']:
        raise AuditError('Usage must be reconciled before this dataset can be verified')
    previous=amount(report['previous_pilot']['cost_usd']);cap=amount(report['cumulative_budget_usd'])
    previous_path=Path(report['previous_pilot']['path'])/'costs.jsonl'
    if hashlib.sha256(previous_path.read_bytes()).hexdigest()!=report['previous_pilot']['costs_sha256']:
        raise AuditError('The prior debit changed')
    prior=audit_ledger(previous_path)
    if amount(prior['summary']['estimated_cost_usd'])!=previous or prior['summary']['unresolved_calls'] or cap>10:
        raise AuditError('The cumulative cap or the prior confirmed cost is invalid')
    if report['cost']['additional']!=accounting['summary'] or amount(report['cost']['total_confirmed_usd'])!=previous+amount(accounting['summary']['estimated_cost_usd']):
        raise AuditError('The report cost differs from provider-reported usage')
    reservations={};proposals={};pending={};spent=Decimal(0);peak=previous
    for e in lines(output/'costs.jsonl'):
        if e['event']=='reserved':
            pending[e['call_id']]=amount(e['reserved_usd'])
            request=e['request'];observation=json.loads(request['input'][0]['content'])
            if request['instructions']!=report['instructions'] or request['model']!='gpt-6-luna':raise AuditError('Unexpected instructions or model')
            if observation['view']!='study-agent-v1' or {'world','truth','metrics','case_id','branch','scenario'} & observation.keys():raise AuditError('Privileged model input')
            reservations[e['call_id']]={'seed':e['seed'],'branch':e['branch'],'step':e['step'],'actor':e['actor'],
              'case_id':e['case_id'],'observation_hash':fingerprint(observation),'counted':e['input_tokens_counted']}
        elif e['event']=='response':
            body=e['response'];calls=[c for c in body.get('output',[]) if c.get('type')=='function_call']
            proposal=None
            if body.get('status')=='completed' and len(calls)==1 and calls[0].get('name')=='choose_action':
                try:proposal=json.loads(calls[0]['arguments'])
                except ValueError:pass
            proposals[e['call_id']]=proposal
        elif e['event']=='charged':
            value=amount(e['estimated_cost_usd'])
            if value>pending[e['call_id']]:raise AuditError('Reported cost exceeded its reservation')
            pending.pop(e['call_id']);spent+=value
            if e['usage']['input_tokens']>reservations[e['call_id']]['counted']:raise AuditError('Input count mismatch')
        exposure=previous+spent+sum(pending.values(),Decimal(0));peak=max(peak,exposure)
        if exposure>cap:raise AuditError('Cumulative budget exceeded, including simultaneous reservations')
    receipts={r['call_id']:r for r in accounting['receipts']}
    decisions={};batches={};invalid=set();decision_ids=set()
    for e in lines(output/'decisions.jsonl'):
        if e['event']=='invalid_proposal':invalid.add(e['call_id']);continue
        if e['event']=='applied_batch':
            key=e['seed'],e['branch'],e['step']
            if key in batches:raise AuditError('Duplicate committed tick')
            batches[key]=e;continue
        if e['event']!='decision':continue
        key=e['seed'],e['branch'],e['step'],e['actor']
        if key in decisions or e['decision_id'] in decision_ids:raise AuditError('Duplicate model decision')
        reservation=reservations[e['call_id']];receipt=receipts[e['call_id']]
        if any(reservation[k]!=e[k] for k in ('seed','branch','step','actor','case_id')):raise AuditError('Receipt assigned to another account')
        if fingerprint(e['observation'])!=reservation['observation_hash'] or e['observation_sha256']!=reservation['observation_hash']:raise AuditError('Actual provider observation mismatch')
        proposal={**e['action'],'reason':e['reason'],'belief_problem':e['belief_problem'],
          'evidence_assessment':e['evidence_assessment'],'evidence_refs':e['evidence_refs']}
        if proposal!=proposals[e['call_id']]:raise AuditError('Applied proposal differs from the model response')
        if any(e[k]!=receipt[k] for k in ('response_id','model','usage','estimated_cost_usd')):raise AuditError('Decision cost receipt mismatch')
        decisions[key]=e;decision_ids.add(e['decision_id'])
    used={d['call_id'] for d in decisions.values()}
    if used&invalid or used|invalid!=set(receipts):raise AuditError('Each paid receipt needs a valid decision or a recorded invalid proposal')
    applied=0;frames_verified=0;databases=0;complete_pairs=0
    with sqlite3.connect(f'file:{output/"decisions.sqlite"}?mode=ro',uri=True) as db:
        if db.execute('SELECT count(*) FROM decisions').fetchone()[0]!=len(decisions):raise AuditError('Derived index count mismatch')
        for run in report['runs']:
            case=run['case_definition'];count=run['config']['population']
            for pair in run['experiments']:
                complete_pairs+=pair['status']=='completed'
                for branch_name,branch in pair['branches'].items():
                    root=output/'engine/runs'/branch['run_id']
                    frames=[read_json(root/'frames'/f'{i:04d}.json') for i in range(len(branch['trajectory']))]
                    if [world_fingerprint(f) for f in frames]!=branch['world_sha256'] or branch['world_sha256'][0]!=pair['initial_world_sha256']:raise AuditError('Engine trajectory or paired initial world changed')
                    frames_verified+=len(frames)
                    events=list(lines(root/'events.jsonl')) if (root/'events.jsonl').exists() else []
                    if len(events)!=(len(frames)-1)*count:raise AuditError('Engine action count mismatch')
                    memory={str(i):[] for i in range(1,count+1)};checks={str(i):[] for i in range(1,count+1)}
                    for step in range(len(frames)-1):
                        tick=[decisions[pair['seed'],branch_name,step,i] for i in range(1,count+1)]
                        batch=batches[pair['seed'],branch_name,step]
                        if batch['decision_ids']!=[d['decision_id'] for d in tick] or batch['world_sha256']!=branch['world_sha256'][step+1]:raise AuditError('Committed batch mismatch')
                        validate_batch(frames[step],[{'actor':d['actor'],'action':d['action']} for d in tick],step)
                        for d in tick:
                            key=str(d['actor']);expected=view(case,frames[step],d['actor'],pair['profiles'][key],memory[key],checks[key])
                            if expected!=d['observation']:raise AuditError('Scoped observation reconstruction failed')
                            event=events[step*count+d['actor']-1]
                            if event['actor']!=d['actor'] or event['action']!=d['action']:raise AuditError('Engine applied another action')
                            indexed=db.execute('SELECT body,applied FROM decisions WHERE id=?',(d['decision_id'],)).fetchone()
                            if indexed is None or not indexed[1] or json.loads(indexed[0])!=d:raise AuditError('Indexed decision mismatch')
                            memory[key].append({'step':step,'action':d['action'],'reason':d['reason'],'belief_problem':d['belief_problem']})
                            if d['action']['kind'] in ('inspect_status','inspect_record'):
                                checks[key].append({'requested_at_step':step,'result':tool_result(case,branch_name,d['action']['kind'],step,d['actor'])})
                            applied+=1
                    with sqlite3.connect(f'file:{root/"oasis.sqlite"}?mode=ro',uri=True) as oasis:
                        fields=('post_id','user_id','original_post_id','created_at','num_shares','content')
                        posts=oasis.execute('SELECT p.post_id,p.user_id,p.original_post_id,p.created_at,p.num_shares,r.content FROM post p JOIN post r ON r.post_id=COALESCE(p.original_post_id,p.post_id) ORDER BY p.post_id').fetchall()
                        if posts!=[tuple(p[k] for k in fields) for p in frames[-1]['world']['posts']]:raise AuditError('OASIS differs from final frame')
                    databases+=1
        if db.execute('SELECT count(*) FROM decisions WHERE applied=1').fetchone()[0]!=applied:raise AuditError('Applied index count differs from engine events')
    if applied!=report['progress']['applied_decisions'] or complete_pairs!=report['progress']['completed_pairs']:raise AuditError('Report progress mismatch')
    return {'verified':True,'basis':'Offline reconstruction; no model calls','model':'gpt-6-luna',
      'scope':{'complete_pairs':complete_pairs,'valid_decisions':len(decisions),'applied_decisions':applied,
               'unapplied_proposals':len(decisions)-applied,'invalid_paid_proposals':len(invalid),
               'distinct_provider_responses':len(receipts),'engine_frames':frames_verified,'oasis_databases':databases},
      'cost':accounting['summary'],'previous_pilot_usd':usd(previous),'total_confirmed_usd':usd(previous+spent),
      'peak_confirmed_plus_reserved_usd':usd(peak),'auditor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__=='__main__':
    import sys
    path=Path(sys.argv[1]).resolve();result=audit_study(path);write_json(path/'audit.json',result);print(json.dumps(result,indent=2))
