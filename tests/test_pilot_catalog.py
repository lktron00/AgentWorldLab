import json
from fastapi.testclient import TestClient
from worldlab import pilot_catalog
from worldlab.server import app


def test_actual_operator_app_wires_pilot_catalog_decisions_and_downloads(tmp_path,monkeypatch):
    monkeypatch.setattr(pilot_catalog,'DATA',tmp_path)
    folder=tmp_path/'pilots'/'fixture';folder.mkdir(parents=True)
    report={'kind':'all-ai-incident-pilot','title':'Fixture','status':'completed','summary':{'pairs':1},
            'requested_pairs':1,'config':{'population':4,'steps':2},'cost':{'estimated_cost_usd':'0.001'},'progress':{'decisions':16}}
    (folder/'report.json').write_text(json.dumps(report))
    row={'event':'decision','seed':7,'branch':'generic','step':0,'actor':1,'decision_id':'d1'}
    (folder/'decisions.jsonl').write_text(json.dumps(row)+'\n'+json.dumps({'event':'applied_batch','decision_ids':['d1']})+'\n')
    with TestClient(app,base_url='http://127.0.0.1') as client:
        assert client.get('/lab/pilots').json()[0]['api_cost_usd']=='0.001'
        response=client.get('/pilots/fixture')
        assert response.status_code==200
        assert "connect-src 'self'" in response.headers['content-security-policy']
        result=client.get('/lab/pilots/fixture/decisions?seed=7&branch=generic&step=0').json()
        assert result[0]['applied'] is True
        assert client.get('/lab/pilots/fixture/decisions?seed=7&branch=generic&step=0&actor=2').json()==[]
        assert client.get('/lab/pilots/fixture/decisions?seed=7&branch=unknown&step=0').status_code==422
        response=client.get('/lab/pilots/fixture/files/report.json')
        assert response.status_code==200 and 'attachment' in response.headers['content-disposition']
        assert client.get('/lab/pilots/fixture/files/.env').status_code==404
        (folder/'costs.jsonl').symlink_to(folder/'report.json')
        assert client.get('/lab/pilots/fixture/files/costs.jsonl').status_code==404
        linked=tmp_path/'pilots'/'linked';linked.symlink_to(folder,target_is_directory=True)
        assert client.get('/pilots/linked').status_code==404
