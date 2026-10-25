import copy
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from worldlab import campaign_catalog as catalog
from worldlab.common import ROOT


def test_campaign_catalog_preserves_text_and_blocks_path_and_symlink_escapes(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, 'DATA', tmp_path)
    path=tmp_path/'campaigns'/'test-case'
    path.mkdir(parents=True)
    case=json.loads((ROOT/'scenarios/nubenorte-campaign.json').read_text())
    case['context']='</script><img src=x onerror=alert(1)>'
    report={'kind':'scripted-policy-campaign','status':'completed','case':case,
            'requested_pairs':1,'start_seed':1,'summary':{'pairs':0,'worlds':0,'background_agent_decisions':0},
            'experiments':[],'segments':[],'provenance':{},'cost':{'api_cost_usd':'0'}}
    (path/'report.json').write_text(json.dumps(report))
    (path.parent/'linked').symlink_to(path,target_is_directory=True)
    app=FastAPI();app.include_router(catalog.router)
    with TestClient(app) as client:
        items=client.get('/lab/campaigns').json()
        assert len(items)==1 and items[0]['id']=='test-case'
        r=client.get('/campaigns/test-case')
        assert r.status_code==200 and case['context'] not in r.text
        assert "script-src 'sha256-" in r.headers['content-security-policy']
        assert client.get('/campaigns/linked').status_code==404
        assert client.get('/campaigns/%2E%2E').status_code==404
        download=client.get('/lab/campaigns/test-case/report.json?download=1')
        assert download.status_code==200 and 'attachment' in download.headers['content-disposition']
        assert download.json()['case']['context']==case['context']
        (path/'report.json').unlink()
        other=tmp_path/'external.json';other.write_text(json.dumps(report))
        (path/'report.json').symlink_to(other)
        assert client.get('/campaigns/test-case').status_code==409
        assert client.get('/lab/campaigns').json()==[]
