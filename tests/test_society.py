import asyncio
import copy
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from worldlab.costs import BudgetExceeded, CostLedger
from worldlab.incident import observation, profiles, status_result
from worldlab.pilot_report import build_html, summarize
from worldlab.society_contract import validate_batch
from worldlab.society_policy import SocietyPolicy


def snapshot():
    return {'world': {'nodes': [{'id': i, 'name': str(i)} for i in range(5)],
            'edges': [[2, 1], [3, 1], [4, 1]],
            'posts': [{'post_id': 1, 'user_id': 1, 'original_post_id': None, 'root_id': 1,
                       'content': 'Un rumor', 'created_at': '09:00', 'verified': False}]},
            'run_id': 'private-runtime-id', 'scenario': {'population': 4, 'feed_limit': 8},
            'step': 0, 'time': '09:00', 'done': False, 'status': 'paused'}


def batch():
    return [{'actor': i, 'action': {'kind': 'wait', 'content': '', 'post_id': None}} for i in range(1, 5)]


def test_submitted_tick_validates_all_accounts_and_visible_reposts_before_commit():
    world = snapshot()
    assert len(validate_batch(world, batch(), 0)) == 4
    with pytest.raises(ValueError, match='Stale'):
        validate_batch(world, batch(), 1)
    with pytest.raises(ValueError, match='every active'):
        validate_batch(world, batch()[:-1], 0)
    duplicate = batch(); duplicate[3]['actor'] = 1
    with pytest.raises(ValueError, match='duplicate'):
        validate_batch(world, duplicate, 0)
    hidden = batch(); hidden[0]['action'] = {'kind': 'repost', 'content': '', 'post_id': 1}
    with pytest.raises(ValueError, match='visible'):
        validate_batch(world, hidden, 0)
    allowed = batch(); allowed[1]['action'] = {'kind': 'repost', 'content': '', 'post_id': 1}
    assert validate_batch(world, allowed, 0)['2']['kind'] == 'repost'
    injection = batch(); injection[0]['action']['verified'] = True
    with pytest.raises(ValueError, match='Only'):
        validate_batch(world, injection, 0)
    assert snapshot() == world


def test_scoped_account_view_does_not_leak_labels_global_state_or_condition():
    p = profiles(7, 4)
    view = observation(snapshot(), 2, p['2'], [], [])
    assert view['self']['id'] == 2 and view['following'] == [1]
    assert 'private-runtime-id' not in json.dumps(view)
    assert not {'scenario', 'metrics', 'world', 'truth', 'branch'} & view.keys()
    assert 'verified' not in view['feed'][0] and 'root_id' not in view['feed'][0]
    assert status_result('generic', 0) == status_result('diagnostic', 0)
    assert status_result('generic', 2) != status_result('diagnostic', 2)
    assert profiles(7) == profiles(7) and profiles(7) != profiles(8)


def test_concurrent_reservations_share_budget_and_uncertainty_stops_new_calls(tmp_path):
    ledger = CostLedger(tmp_path / 'costs.jsonl', '0.0015', max_in_flight=8)
    ids = [ledger.reserve('gpt-6-luna', 1000, 1000, {}) for _ in range(2)]
    # Each maximum is .000625; a third would exceed .0015 even before receipts.
    with pytest.raises(BudgetExceeded):
        ledger.reserve('gpt-6-luna', 1000, 1000, {})
    ledger.uncertain(ids[0], 'APITimeoutError')
    with pytest.raises(RuntimeError, match='unresolved'):
        ledger.reserve('gpt-6-luna', 1, 1, {})
    assert ledger.summary()['unresolved_reserved_usd'] == '0.0012500000'


def test_society_policy_uses_exact_prompt_and_saves_usage_before_invalid_action(tmp_path):
    body = {'id': 'resp_fixture', 'model': 'gpt-6-luna', 'status': 'completed', 'service_tier': 'default',
            'usage': {'input_tokens': 700, 'output_tokens': 80, 'output_tokens_details': {'reasoning_tokens': 10}},
            'output': [{'type': 'function_call', 'name': 'choose_action',
                        'arguments': json.dumps({'kind': 'inspect_status', 'content': '', 'post_id': None,
                                                 'reason': 'Consultar la página disponible', 'belief_loss': 55})}]}
    provider = SimpleNamespace(responses=SimpleNamespace(
        input_tokens=SimpleNamespace(count=AsyncMock(return_value=SimpleNamespace(input_tokens=700))),
        create=AsyncMock(return_value=SimpleNamespace(model_dump=lambda **kwargs: copy.deepcopy(body)))))
    ledger = CostLedger(tmp_path / 'costs.jsonl', 1)
    view = observation(snapshot(), 2, profiles(7,4)['2'], [], [])
    action, receipt = asyncio.run(SocietyPolicy(provider, ledger).decide(view, actor=2))
    assert action.kind == 'inspect_status' and receipt['belief_loss'] == 55
    request = provider.responses.create.call_args.kwargs
    assert request['store'] is False and request['service_tier'] == 'default'
    assert json.loads(request['input'][0]['content']) == view
    body['output'][0]['arguments'] = json.dumps({'kind': 'repost', 'post_id': 999, 'content': '', 'reason': 'guess', 'belief_loss': 99})
    with pytest.raises(ValueError, match='visible'):
        asyncio.run(SocietyPolicy(provider, ledger).decide(view, actor=2))
    assert ledger.summary()['completed_calls'] == 2
    with pytest.raises(ValueError, match='scoped'):
        asyncio.run(SocietyPolicy(provider, ledger).decide({**view, 'truth': True}))
    assert provider.responses.create.await_count == 2


def test_summary_keeps_negative_zero_and_positive_effects():
    report = {'experiments': []}
    for seed, difference in enumerate([-2, 0, 3]):
        report['experiments'].append({'status':'completed','branches':{
            'generic': {'trajectory':[{'rumor_sharers':4,'mean_belief_loss':50}], 'action_counts':{}},
            'diagnostic': {'trajectory':[{'rumor_sharers':4+difference,'mean_belief_loss':50+difference}], 'action_counts':{}}}})
    result = summarize(report)['paired_diagnostic_minus_generic']['rumor_sharers']
    assert result['negative'] == result['zero'] == result['positive'] == 1
    assert result['mean'] == pytest.approx(1/3)
    source = build_html({'title':'</script><script>bad()</script>'})
    assert '</script><script>bad()' not in source
    assert '\\u003c/script' in source
