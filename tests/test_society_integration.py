"""Real engines, offline submitted decisions. This fixture makes no paid AI claim."""
import asyncio
import json
import sqlite3
import httpx
import pytest
from worldlab.experiment import experiment_server, world_fingerprint
from worldlab.society_models import SocietyAction, SocietyClient


@pytest.mark.integration
def test_real_society_all_waits_stay_waits_and_rejected_batch_cannot_advance(tmp_path):
    async def exercise(url, token, denied):
        headers={'Authorization': 'Bearer '+token}
        async with httpx.AsyncClient(base_url=url, headers=headers, timeout=180) as http:
            assert (await http.post('/lab/reset-tickets',headers={'Authorization':'Bearer '+denied},json={})).status_code == 403
            async with SocietyClient(base_url=url, mode='simulation', headers=headers, message_timeout_s=180) as client:
                async def reset(**kwargs):
                    r=await http.post('/lab/reset-tickets',json=kwargs);r.raise_for_status()
                    return (await client.reset(ticket=r.json()['ticket'])).observation.snapshot
                initial=await reset(population=4,scenario={'decision_mode':'submitted','max_steps':3})
                checkpoint=(await http.post('/lab/runs/'+initial['run_id']+'/checkpoint')).json()['checkpoint_id']
                def tick(step):
                    return SocietyAction(expected_step=step,actions=[{'actor':i,'action':{'kind':'wait'}} for i in range(1,5)])
                waited=(await client.step(tick(0))).observation.snapshot
                assert waited['step']==1 and len(waited['world']['posts'])==1
                assert waited['world']==initial['world']
                with pytest.raises(Exception,match='Stale'):
                    await client.step(tick(0))
                duplicate=tick(1);duplicate.actions[-1].actor=1
                with pytest.raises(Exception,match='duplicate'):
                    await client.step(duplicate)
                hidden=tick(1);hidden.actions[0].action.kind='repost';hidden.actions[0].action.post_id=999
                with pytest.raises(Exception,match='visible'):
                    await client.step(hidden)
                assert (await client.state()).step_count==1
                inspected=tick(1);inspected.actions[2].action.kind='inspect_status'
                inspected=(await client.step(inspected)).observation.snapshot
                assert len(inspected['world']['posts'])==1
                restored=await reset(checkpoint_id=checkpoint)
                assert world_fingerprint(restored)==world_fingerprint(initial)
                mixed=tick(0);mixed.actions[0].action.kind='post';mixed.actions[0].action.content='Fixture offline de publicación'
                mixed.actions[1].action.kind='repost';mixed.actions[1].action.post_id=1
                moved=(await client.step(mixed)).observation.snapshot
                assert moved['step']==1 and len(moved['world']['posts'])==3
                posts=moved['world']['posts']
                assert [p['user_id'] for p in posts]==[1,1,2] # ID-ordered commit.
                path=tmp_path/'engine/runs'/moved['run_id']
                events=[json.loads(line) for line in (path/'events.jsonl').read_text().splitlines()]
                assert len(events)==4 and [e['actor'] for e in events]==[1,2,3,4]
                for p in (path/'agents').glob('*/AGENT.json'):
                    assert json.loads(p.read_text())['step_count']==1
                with sqlite3.connect(path/'oasis.sqlite') as db:
                    assert db.execute('SELECT count(*) FROM post').fetchone()[0]==3
    with experiment_server(tmp_path,reuse_oasis=True,society=True) as (url,token,denied):
        asyncio.run(exercise(url,token,denied))


@pytest.mark.integration
def test_runner_and_offline_audit_cover_every_model_decision_with_real_engines(tmp_path):
    """SDK-shaped deterministic fixture; tests never make a real paid inference."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from worldlab.costs import CostLedger
    from worldlab.incident import BRANCH_LABELS
    from worldlab.pilot import run
    from worldlab.pilot_report import persist
    from worldlab.pilot_audit import audit_pilot
    from worldlab.society_policy import SocietyPolicy
    counter=0
    async def create(**request):
        nonlocal counter
        counter+=1
        view=json.loads(request['input'][0]['content'])
        diagnostic=any('technical_attachment' in c['result'] for c in view['status_checks'])
        kind='inspect_status' if view['step'] in (0,2) else 'post' if diagnostic else 'wait'
        arguments={'kind':kind,'content':f'Fixture de diagnóstico de cuenta {view["self"]["id"]}' if kind=='post' else '',
                   'post_id':None,'reason':'Fixture de transporte y persistencia; no inferencia IA real',
                   'belief_loss':10 if diagnostic else 60}
        body={'id':f'resp_offline_fixture_{counter}','model':'gpt-6-luna','status':'completed','service_tier':'default',
              'usage':{'input_tokens':1000,'output_tokens':100,'input_tokens_details':{'cached_tokens':0},'output_tokens_details':{'reasoning_tokens':0}},
              'output':[{'type':'function_call','name':'choose_action','arguments':json.dumps(arguments)}]}
        return SimpleNamespace(model_dump=lambda **kwargs:body)
    provider=SimpleNamespace(responses=SimpleNamespace(input_tokens=SimpleNamespace(count=AsyncMock(return_value=SimpleNamespace(input_tokens=1000))),create=create))
    ledger=CostLedger(tmp_path/'costs.jsonl',10,max_in_flight=4)
    report={'kind':'all-ai-incident-pilot','status':'running','requested_pairs':1,
            'config':{'population':4,'steps':4,'start_seed':77},'branches':BRANCH_LABELS,'experiments':[],'decisions':0}
    with experiment_server(tmp_path,reuse_oasis=True,society=True) as (url,token,_):
        asyncio.run(run(report,tmp_path,SocietyPolicy(provider,ledger),ledger,url,token,concurrency=4))
    persist(tmp_path,report,ledger)
    audit=audit_pilot(tmp_path)
    assert audit['verified'] and audit['scope']['model_decisions']==32
    assert audit['scope']['engine_frames']==10 and audit['scope']['applied_actions']==32
    assert audit['scope']['distinct_provider_responses']==32
    assert audit['cost']['estimated_cost_usd']=='0.0048000000'
    assert report['summary']['paired_diagnostic_minus_generic']['mean_belief_loss']['mean']==-50
    # A changed proposed action must be detected even when its receipt is intact.
    journal=tmp_path/'decisions.jsonl'
    source=journal.read_text(); rows=[json.loads(line) for line in source.splitlines()]
    changed=next(e for e in rows if e['event']=='decision' and e['action']['kind']=='post')
    changed['action']['content']='Tampered fixture'
    journal.write_text(''.join(json.dumps(e)+'\n' for e in rows))
    from worldlab.audit import AuditError
    with pytest.raises(AuditError):
        audit_pilot(tmp_path)
