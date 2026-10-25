import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from worldlab.costs import CostLedger
from worldlab.study import Saver,study_frame,prior_debit
from worldlab.study_cases import CASES,profiles,tool_result,view
from worldlab.study_policy import StudyPolicy
from worldlab.experiment import experiment_server
from worldlab.pilot import run as run_pair


def test_case_pack_covers_true_false_and_misleading_evidence():
    assert len(CASES)==9 and len({c['id'] for c in CASES})==9
    assert {c['domain'] for c in CASES}=={'cloud','billing','security'}
    assert {c['truth'] for c in CASES}=={True,False}
    for c in CASES:
        assert tool_result(c,'generic','inspect_status',0,1)==tool_result(c,'diagnostic','inspect_status',0,1)
        assert tool_result(c,'generic','inspect_status',2,1)!=tool_result(c,'diagnostic','inspect_status',2,1)
        assert 'truth' not in tool_result(c,'diagnostic','inspect_record',3,1)
        assert len(profiles(c,7))==20


@pytest.mark.integration
@pytest.mark.parametrize('with_hold',[False,True])
def test_two_cases_reuse_shared_budget_real_engines_and_index(tmp_path,with_hold):
    counter=0
    async def create(**request):
        nonlocal counter
        counter+=1
        if with_hold and counter==17:
            import httpx
            from openai import APIConnectionError
            raise APIConnectionError(request=httpx.Request('POST','https://api.openai.com/v1/responses'))
        o=json.loads(request['input'][0]['content'])
        kind='inspect_record' if o['step']==0 else 'wait'
        d={'kind':kind,'content':'','post_id':None,'reason':'Offline protocol fixture, not a real inference',
           'belief_problem':50,'evidence_assessment':'insufficient','evidence_refs':[]}
        body={'id':f'resp_study_fixture_{counter}','model':'gpt-6-luna','status':'completed','service_tier':'default',
              'usage':{'input_tokens':1000,'output_tokens':100,'output_tokens_details':{'reasoning_tokens':0}},
              'output':[{'type':'function_call','name':'choose_action','arguments':json.dumps(d)}]}
        return SimpleNamespace(model_dump=lambda **kwargs:copy.deepcopy(body))
    provider=SimpleNamespace(responses=SimpleNamespace(input_tokens=SimpleNamespace(count=AsyncMock(return_value=SimpleNamespace(input_tokens=1000))),create=create))
    ledger=CostLedger(tmp_path/'costs.jsonl','1',max_in_flight=4)
    previous=tmp_path/'previous';previous.mkdir()
    prior=CostLedger(previous/'costs.jsonl','1')
    call=prior.reserve('gpt-6-luna',1000,2048,{})
    prior.received(call,'gpt-6-luna',{'id':'resp_prior_offline_fixture','model':'gpt-6-luna','service_tier':'default','usage':{'input_tokens':1000,'output_tokens':100}},1)
    import hashlib
    from worldlab.study_policy import INSTRUCTIONS
    study={'instructions':INSTRUCTIONS,'kind':'balanced-ai-case-study','status':'running','cases':CASES[:3] if with_hold else CASES[:2],'runs':[],
           'previous_pilot':{'path':str(previous),'cost_usd':'0.0001500000','costs_sha256':hashlib.sha256((previous/'costs.jsonl').read_bytes()).hexdigest()},'cumulative_budget_usd':'10'}
    saver=Saver(tmp_path,study,ledger)
    async def exercise(url,token):
        nonlocal ledger,saver
        for index,case in enumerate(study['cases']):
            r={'status':'running','case_id':case['id'],'case_definition':case,'requested_pairs':1,
               'config':{'population':4,'steps':2,'start_seed':777+index},'experiments':[],'decisions':0}
            study['runs'].append(r)
            try:
                await run_pair(r,tmp_path,StudyPolicy(provider,ledger,case,tmp_path),ledger,url,token,
                    concurrency=4,case=case,save_fn=saver,frame_fn=lambda s,d=():study_frame(case,s,d))
            except Exception:
                if not with_hold or index!=1:raise
                r['status']='stopped'
                for pair in r['experiments']:
                    pair['status']='incomplete'
                    for branch in pair['branches'].values():branch['status']='incomplete'
                for cid in list(ledger.pending):ledger.quarantine(cid,'Offline transport-failure fixture; maximum retained')
            saver()
            if index==0 or (with_hold and index==1):
                if index==0:
                    saver.db.execute('DELETE FROM decisions WHERE id=(SELECT id FROM decisions ORDER BY rowid DESC LIMIT 1)')
                    saver.db.commit()
                before=ledger.spent
                saver.close()
                from worldlab.study_resume import reopen_ledger
                ledger=reopen_ledger(tmp_path/'costs.jsonl',allow_quarantined=with_hold)
                assert ledger.spent==before
                saver=Saver(tmp_path,study,ledger,resume=True)
    try:
        with experiment_server(tmp_path,reuse_oasis=True,society=True) as (url,token,_):asyncio.run(exercise(url,token))
        assert study['progress']['completed_pairs']==2 and study['progress']['applied_decisions']==32
        assert study['cost']['additional']['completed_calls']==32
        assert study['cost']['total_confirmed_usd']=='0.0049500000'
        assert saver.db.execute('SELECT count(*) FROM decisions WHERE applied=1').fetchone()[0]==32
        rows=saver.db.execute('SELECT body FROM decisions WHERE step=1').fetchall()
        assert all(json.loads(row[0])['observation']['checks'][0]['result']['id'].startswith('private-record-') for row in rows)
    finally:saver.close()
    from worldlab.study_audit import audit_study
    audit=audit_study(tmp_path,allow_quarantined=with_hold)
    assert audit['usage_complete'] is (not with_hold)
    assert audit['unreceipted_requests']==int(with_hold)
    assert audit['verified'] and audit['scope']['applied_decisions']==32
    assert audit['total_confirmed_usd']=='0.0049500000'
    from worldlab.common import write_json
    from worldlab.study_job import completion
    study.update(status='completed',audit_verified=True,model='gpt-6-luna',finished_at='offline-fixture')
    write_json(tmp_path/'audit.json',audit)
    done=completion(tmp_path,study)
    assert done['status']=='completed' and done['unreceipted_requests']==int(with_hold)
    assert (tmp_path/'results.md').is_file()


def test_actual_study_routes_and_sqlite_filters(tmp_path,monkeypatch):
    import sqlite3
    from fastapi.testclient import TestClient
    from worldlab import study_catalog
    from worldlab.server import app
    monkeypatch.setattr(study_catalog,'DATA',tmp_path)
    folder=tmp_path/'studies'/'fixture';folder.mkdir(parents=True)
    report={'kind':'balanced-ai-case-study','status':'running','title':'Fixture','population':20,'steps':10,
            'progress':{'completed_pairs':0},'cost':{'total_confirmed_usd':'0.8736880250'}}
    (folder/'report.json').write_text(json.dumps(report))
    with sqlite3.connect(folder/'decisions.sqlite') as db:
        db.execute('CREATE TABLE decisions(id TEXT,seed INTEGER,branch TEXT,step INTEGER,actor INTEGER,case_id TEXT,body TEXT,applied INTEGER)')
        db.execute('INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?)',('d',7,'generic',0,1,'cloud-index',json.dumps({'actor':1}),1))
    with TestClient(app,base_url='http://127.0.0.1') as client:
        assert client.get('/lab/studies').json()[0]['api_cost_usd']=='0.8736880250'
        result=client.get('/lab/studies/fixture/decisions?case_id=cloud-index&seed=7&branch=generic&step=0').json()
        assert result==[{'actor':1,'applied':True}]
        assert client.get('/studies/fixture').status_code==200
        assert client.get('/lab/studies/fixture/files/decisions.sqlite').status_code==409
        assert client.get('/lab/studies/fixture/files/.env').status_code==404


def test_resume_keeps_spend_and_blocks_unresolved_usage(tmp_path):
    from worldlab.study_resume import reopen_ledger
    from worldlab.costs import BudgetExceeded
    path=tmp_path/'costs.jsonl'
    ledger=CostLedger(path,'0.002',max_in_flight=4)
    call=ledger.reserve('gpt-6-luna',1000,2048,{'seed':7,'branch':'generic'})
    ledger.received(call,'gpt-6-luna',{'id':'resp_resume_fixture','model':'gpt-6-luna',
        'service_tier':'default','usage':{'input_tokens':1000,'output_tokens':100}},1)
    reopened=reopen_ledger(path)
    assert reopened.summary()==ledger.summary()
    assert reopened.contexts[call]==ledger.contexts[call]
    assert sum(json.loads(line)['event']=='ledger' for line in path.read_text().splitlines())==1
    with pytest.raises(BudgetExceeded):reopened.reserve('gpt-6-luna',10000,2048,{})
    pending=reopened.reserve('gpt-6-luna',1000,2048,{})
    reopened.uncertain(pending,'APITimeoutError')
    with pytest.raises(ValueError,match='unresolved'):reopen_ledger(path)


@pytest.mark.parametrize('failures',[1,3])
def test_input_count_timeout_never_duplicates_generation(tmp_path,monkeypatch,failures):
    import httpx
    from openai import APITimeoutError
    monkeypatch.setattr('worldlab.study_policy.asyncio.sleep',AsyncMock())
    timeout=APITimeoutError(request=httpx.Request('POST','https://api.openai.com/v1/responses/input_tokens'))
    count=AsyncMock(side_effect=[timeout]*failures+[SimpleNamespace(input_tokens=1000)])
    d={'kind':'wait','content':'','post_id':None,'reason':'Offline retry fixture','belief_problem':50,
       'evidence_assessment':'insufficient','evidence_refs':[]}
    body={'id':'resp_count_retry_fixture','model':'gpt-6-luna','status':'completed','service_tier':'default',
          'usage':{'input_tokens':1000,'output_tokens':100},
          'output':[{'type':'function_call','name':'choose_action','arguments':json.dumps(d)}]}
    create=AsyncMock(return_value=SimpleNamespace(model_dump=lambda **kwargs:copy.deepcopy(body)))
    provider=SimpleNamespace(responses=SimpleNamespace(input_tokens=SimpleNamespace(count=count),create=create))
    ledger=CostLedger(tmp_path/'costs.jsonl','1')
    policy=StudyPolicy(provider,ledger,CASES[0],tmp_path)
    observation={'view':'study-agent-v1','self':{'id':1},'feed':[],'own_posts':[],'checks':[],'memory':[]}
    if failures==3:
        with pytest.raises(APITimeoutError):asyncio.run(policy.decide(observation))
        create.assert_not_awaited()
        assert ledger.summary()['completed_calls']==0 and not ledger.pending
    else:
        action,receipt=asyncio.run(policy.decide(observation))
        assert action.kind=='wait' and count.await_count==2 and create.await_count==1
        assert ledger.summary()['completed_calls']==1 and not ledger.pending


def test_quarantine_preserves_the_full_bound_across_restart(tmp_path):
    from worldlab.audit import audit_ledger,AuditError
    from worldlab.costs import BudgetExceeded
    from worldlab.study_resume import reopen_ledger
    path=tmp_path/'costs.jsonl';ledger=CostLedger(path,'0.0023',max_in_flight=1)
    lost=ledger.reserve('gpt-6-luna',1000,2048,{'seed':1,'branch':'generic'})
    ledger.uncertain(lost,'APIConnectionError');maximum=ledger.pending[lost]
    ledger.quarantine(lost,'Offline failure fixture; never retry')
    assert ledger.spent==0 and ledger.held[lost]==maximum and not ledger.pending
    with pytest.raises(ValueError):reopen_ledger(path)
    ledger=reopen_ledger(path,allow_quarantined=True)
    active=ledger.reserve('gpt-6-luna',1000,2048,{'seed':2,'branch':'generic'})
    ledger.received(active,'gpt-6-luna',{'id':'resp_bound_fixture','model':'gpt-6-luna','service_tier':'default',
        'usage':{'input_tokens':1000,'output_tokens':100}},1)
    with pytest.raises(BudgetExceeded):ledger.reserve('gpt-6-luna',10000,2048,{})
    assert ledger.summary()==audit_ledger(path)['summary']
    assert ledger.summary()['quarantined_calls']==1 and ledger.summary()['completed_calls']==1
    assert ledger.summary()['unresolved_reserved_usd']==format(maximum,'.10f')
    events=[json.loads(line) for line in path.read_text().splitlines()]
    next(e for e in events if e['event']=='quarantined')['reserved_usd']='0'
    path.write_text(''.join(json.dumps(e)+'\n' for e in events))
    with pytest.raises(AuditError,match='changed'):audit_ledger(path)


def test_supervisor_respects_a_stopped_run(tmp_path,monkeypatch):
    from worldlab.study_job import run
    (tmp_path/'report.json').write_text(json.dumps({'status':'interrupted'}))
    popen=AsyncMock()
    monkeypatch.setattr('worldlab.study_job.subprocess.Popen',popen)
    assert run(tmp_path,200,3)==1
    popen.assert_not_called()
    assert json.loads((tmp_path/'job.json').read_text())['status']=='needs_attention'


def test_catalog_does_not_report_a_missing_writer_as_running(tmp_path,monkeypatch):
    import fcntl
    from worldlab import study_catalog
    monkeypatch.setattr(study_catalog,'DATA',tmp_path)
    folder=tmp_path/'studies'/'orphan';folder.mkdir(parents=True)
    (folder/'report.json').write_text(json.dumps({'kind':'balanced-ai-case-study','status':'running','resumptions':[{}]}))
    assert study_catalog.report_for('orphan')['status']=='needs_reconciliation'
    with (folder/'.writer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert study_catalog.report_for('orphan')['status']=='running'
    assert study_catalog.report_for('orphan')['status']=='needs_reconciliation'
