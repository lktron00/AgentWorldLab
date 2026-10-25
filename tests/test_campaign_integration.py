import json
import sqlite3

import pytest

from worldlab.campaign import main, read_rows
from worldlab.common import ROOT


@pytest.mark.integration
def test_campaign_reused_real_engines_noop_rule_and_completed_resume(tmp_path):
    case = json.loads((ROOT / 'scenarios/nubenorte-campaign.json').read_text())
    case['population'] = 6
    case['steps'] = 3
    case['world']['friction_multiplier'] = 1.0
    case_path = tmp_path / 'case.json'
    case_path.write_text(json.dumps(case))
    output = tmp_path / 'campaign'
    args = ['--case', str(case_path), '--pairs', '2', '--start-seed', '70', '--workers', '1', '--output', str(output)]
    assert main(args) == 0
    report = json.loads((output / 'report.json').read_text())
    assert report['status'] == 'completed' and report['summary']['pairs'] == 2
    assert report['summary']['paired_effect']['mean'] == 0
    rows = read_rows(output / 'pairs.jsonl')
    engine = output / 'worker-0/engine'
    for row in rows:
        assert row['branches']['open']['world_sha256'] == row['branches']['friction']['world_sha256']
        assert row['cost']['model_calls'] == 0 and row['cost']['local_compute_cost_usd'] is None
        for branch in row['branches'].values():
            with sqlite3.connect(engine / 'runs' / branch['run_id'] / 'oasis.sqlite') as db:
                assert db.execute('SELECT count(*) FROM user').fetchone()[0] == 7
                assert db.execute('SELECT count(*) FROM post').fetchone()[0] == len(branch['final_world']['posts'])
    original = (output / 'pairs.jsonl').read_bytes()
    worlds = {p.name for p in (engine / 'runs').iterdir()}
    assert main(args + ['--resume']) == 0
    assert (output / 'pairs.jsonl').read_bytes() == original
    assert {p.name for p in (engine / 'runs').iterdir()} == worlds
    # A new rule must never silently join an existing campaign.
    case['world']['friction_multiplier'] = .3
    case_path.write_text(json.dumps(case))
    with pytest.raises(SystemExit):
        main(args + ['--resume'])
    assert (output / 'pairs.jsonl').read_bytes() == original


@pytest.mark.integration
def test_interrupted_campaign_keeps_complete_pairs_and_resumes(tmp_path):
    import os
    import signal
    import subprocess
    import sys
    import time
    output = tmp_path / 'interrupted'
    args = ['--pairs', '6', '--population', '4', '--steps', '2', '--workers', '1', '--output', str(output)]
    log_path = tmp_path / 'interrupt.log'
    with log_path.open('w') as log:
        process = subprocess.Popen([sys.executable, '-m', 'worldlab.campaign', *args], cwd=ROOT, stdout=log, stderr=log)
        try:
            deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                journal=output/'pairs.jsonl'
                if journal.exists() and journal.read_text().endswith('\n'):
                    break
                if process.poll() is not None:
                    pytest.fail(log_path.read_text())
                time.sleep(.1)
            else:
                pytest.fail('No committed campaign pair before deadline')
            process.send_signal(signal.SIGTERM)
            assert process.wait(timeout=60)==130,log_path.read_text()
        finally:
            if process.poll() is None:
                process.kill();process.wait(timeout=10)
    partial=read_rows(output/'pairs.jsonl')
    assert 1<=len(partial)<6
    report=json.loads((output/'report.json').read_text())
    assert report['status']=='interrupted' and report['summary']['pairs']==len(partial)
    original={r['seed']:r for r in partial}
    assert main(args+['--resume'])==0
    rows=read_rows(output/'pairs.jsonl')
    assert len(rows)==6 and len({r['seed'] for r in rows})==6
    assert all(next(r for r in rows if r['seed']==seed)==value for seed,value in original.items())
