import copy
import json

import pytest

from worldlab.campaign import case_config, main, provenance, read_rows
from worldlab.campaign_report import build_html, quantile, summarize
from worldlab.common import ROOT


def sample_row(seed=1, normal=(1, 4, 6), pause=(1, 2, 3)):
    return {'seed': seed, 'status': 'completed', 'initial_world_sha256': 'a' * 64,
            'background_agent_decisions': 24, 'elapsed_seconds': 1.5,
            'avoided_sharers_at_horizon': normal[-1] - pause[-1],
            'branches': {name: {'initial_world_sha256': 'a' * 64,
                               'trajectory': [{'step': i, 'rumor_sharers': value} for i, value in enumerate(values)]}
                         for name, values in [('open', normal), ('friction', pause)]}}


def test_descriptive_summary_preserves_ties_and_negative_effects():
    rows = [sample_row(), sample_row(2, (1, 3, 3), (1, 4, 5)), sample_row(3, (1, 4, 4), (1, 4, 4))]
    s = summarize(rows, {'population': 6, 'steps': 2})
    assert s['worlds'] == 6 and s['background_agent_decisions'] == 72
    assert s['paired_effect']['mean'] == pytest.approx(1 / 3)
    assert (s['paired_effect']['positive_pairs'], s['paired_effect']['zero_pairs'], s['paired_effect']['negative_pairs']) == (1, 1, 1)
    assert s['branches']['friction']['half_shared_fraction'] == 1
    assert s['local_compute_cost_usd'] is None and s['api_cost_usd'] == '0.0000000000'
    assert quantile([0, 10], .1) == 1
    damaged = copy.deepcopy(rows)
    damaged[0]['branches']['friction']['initial_world_sha256'] = 'b' * 64
    with pytest.raises(ValueError, match='starting world'):
        summarize(damaged, {'population': 6, 'steps': 2})


def test_html_keeps_untrusted_content_as_json_text():
    payload = '</script><script>alert("private")</script>'
    source = build_html({'case': {'context': payload}})
    assert payload not in source and '\\u003c/script\\u003e' in source
    assert '__CAMPAIGN_DATA__' not in source


def test_journal_rejects_duplicate_seed_truncated_tail_and_mismatched_pairs(tmp_path):
    p = tmp_path / 'pairs.jsonl'
    row = sample_row()
    p.write_text(json.dumps(row) + '\n')
    assert read_rows(p)[0]['seed'] == 1
    p.write_text((json.dumps(row) + '\n') * 2)
    with pytest.raises(ValueError, match='Duplicate'):
        read_rows(p)
    p.write_text(json.dumps(row))
    with pytest.raises(ValueError, match='Incomplete'):
        read_rows(p)
    row['branches']['friction']['initial_world_sha256'] = 'b' * 64
    p.write_text(json.dumps(row) + '\n')
    with pytest.raises(ValueError, match='initial world'):
        read_rows(p)


def test_bad_campaign_args_fail_before_creating_output(tmp_path):
    output = tmp_path / 'absent'
    for extra in [['--pairs', '0'], ['--start-seed', '-1'], ['--population', '101']]:
        with pytest.raises(SystemExit) as e:
            main(['--output', str(output), *extra])
        assert e.value.code == 2 and not output.exists()
    case = case_config(ROOT / 'scenarios/nubenorte-campaign.json')
    assert case['population'] == 50 and case['steps'] == 8
    assert provenance(case, 1, 1000) != provenance(case, 2, 1000)
