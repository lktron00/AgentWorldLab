"""All-AI Nube Norte pilot. Explicitly paid; the offline baseline stays unchanged."""
from __future__ import annotations
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import statistics
import sys
import time
import uuid

import httpx
from .common import DATA, ROOT, read_json, write_json
from .costs import BudgetExceeded, CostLedger, PRICE_BOOK, amount, usd
from .errors import safe_error
from .experiment import append_decision, experiment_server, fingerprint, world_fingerprint
from .incident import BRANCHES, BRANCH_LABELS, INITIAL_POST, TRUTH, observation, profiles, status_result
from .pilot_report import persist
from .society_models import SocietyAction, SocietyClient
from .society_policy import SocietyPolicy, INSTRUCTIONS, PROMPT_VERSION


def now():
    return datetime.now(timezone.utc).isoformat()


def frame(snapshot, decisions=()):
    posts = snapshot['world']['posts']
    beliefs = [d['belief_loss'] for d in decisions]
    return {'step': snapshot['step'],
            'rumor_sharers': len({p['user_id'] for p in posts if p['root_id'] == 1 and p['user_id'] != 0}),
            'rumor_reposts': sum(p['root_id'] == 1 and p['original_post_id'] is not None for p in posts),
            'total_posts': len(posts),
            'mean_belief_loss': statistics.mean(beliefs) if beliefs else None}


async def run(report, output, policy, ledger, url, token, *, concurrency=8):
    semaphore = asyncio.Semaphore(concurrency)
    config = report['config']
    async with SocietyClient(base_url=url, mode='simulation', message_timeout_s=180,
                             headers={'Authorization': 'Bearer ' + token}) as client, \
            httpx.AsyncClient(base_url=url, trust_env=False, timeout=180,
                              headers={'Authorization': 'Bearer ' + token}) as operator:
        async def reset(**params):
            response = await operator.post('/lab/reset-tickets', json=params)
            response.raise_for_status()
            return (await client.reset(ticket=response.json()['ticket'])).observation.snapshot

        for index in range(report['requested_pairs']):
            seed = config['start_seed'] + index
            identities = profiles(seed, config['population'])
            initial = await reset(seed=seed, population=config['population'], policy='open',
                                  scenario={'max_steps': config['steps'], 'initial_content': INITIAL_POST,
                                            'decision_mode': 'submitted', 'feed_limit': 8})
            response = await operator.post(f"/lab/runs/{initial['run_id']}/checkpoint")
            response.raise_for_status()
            checkpoint = response.json()['checkpoint_id']
            pair = {'seed': seed, 'status': 'running', 'checkpoint_id': checkpoint,
                    'initial_world_sha256': world_fingerprint(initial), 'profiles': identities, 'branches': {}}
            report['experiments'].append(pair)
            # Alternate execution order; condition never enters an account's model prompt.
            order = BRANCHES if index % 2 == 0 else tuple(reversed(BRANCHES))
            pair['execution_order'] = order
            for branch_name in order:
                snapshot = await reset(checkpoint_id=checkpoint)
                if world_fingerprint(snapshot) != pair['initial_world_sha256']:
                    raise RuntimeError('Paired worlds differ at the initial boundary')
                memory = {str(i): [] for i in range(1, config['population'] + 1)}
                checks = {str(i): [] for i in range(1, config['population'] + 1)}
                branch = {'run_id': snapshot['run_id'], 'status': 'running',
                          'initial_world_sha256': world_fingerprint(snapshot),
                          'trajectory': [frame(snapshot)], 'world_sha256': [world_fingerprint(snapshot)],
                          'call_ids': [], 'action_counts': {}, 'cost_usd': usd(0)}
                pair['branches'][branch_name] = branch
                persist(output, report, ledger)
                for step in range(config['steps']):
                    if snapshot['step'] != step or snapshot['done']:
                        raise RuntimeError('Unexpected society clock or horizon')
                    async def decide(actor):
                        key = str(actor)
                        view = observation(snapshot, actor, identities[key], memory[key], checks[key])
                        async with semaphore:
                            action, receipt = await policy.decide(view, seed=seed, branch=branch_name,
                                                                  actor=actor, step=step)
                        decision = {'event': 'decision', 'decision_id': uuid.uuid4().hex,
                                    'seed': seed, 'branch': branch_name, 'step': step, 'actor': actor,
                                    'observation': view, 'observation_sha256': fingerprint(view),
                                    'action': action.model_dump(), **receipt}
                        append_decision(output / 'decisions.jsonl', decision)
                        branch['call_ids'].append(receipt['call_id'])
                        report['decisions'] = report.get('decisions', 0) + 1
                        return decision
                    results = await asyncio.gather(*(decide(i) for i in range(1, config['population'] + 1)), return_exceptions=True)
                    # Finish and record in-flight paid requests even when a sibling request fails.
                    errors = [r for r in results if isinstance(r, BaseException)]
                    persist(output, report, ledger)
                    if errors:
                        raise errors[0]
                    decisions = sorted(results, key=lambda d: d['actor'])
                    action = SocietyAction(expected_step=step, actions=[{'actor': d['actor'], 'action': d['action']} for d in decisions])
                    snapshot = (await client.step(action)).observation.snapshot
                    if snapshot['step'] != step + 1:
                        raise RuntimeError('OpenEnv did not commit the expected society tick')
                    append_decision(output / 'decisions.jsonl', {
                        'event': 'applied_batch', 'seed': seed, 'branch': branch_name, 'run_id': snapshot['run_id'],
                        'step': step, 'resulting_step': snapshot['step'],
                        'decision_ids': [d['decision_id'] for d in decisions],
                        'world_sha256': world_fingerprint(snapshot)})
                    for d in decisions:
                        key = str(d['actor'])
                        remember = {'step': step, 'action': d['action'], 'reason': d['reason'], 'belief_loss': d['belief_loss']}
                        if d['action']['kind'] == 'inspect_status':
                            check = {'requested_at_step': step, 'result': status_result(branch_name, step)}
                            checks[key].append(check)
                            append_decision(output / 'decisions.jsonl', {'event': 'status_result', 'decision_id': d['decision_id'], **check})
                        memory[key].append(remember)
                    counts = Counter(branch['action_counts'])
                    counts.update(d['action']['kind'] for d in decisions)
                    branch['action_counts'] = dict(counts)
                    branch['trajectory'].append(frame(snapshot, decisions))
                    branch['world_sha256'].append(world_fingerprint(snapshot))
                    if ledger.summary()['completed_calls'] >= 100 and 'calibration' not in report:
                        used = ledger.summary()
                        report['calibration'] = {**used, 'decisions_sampled': used['completed_calls'],
                            'projected_cost_usd_at_same_average': usd(ledger.spent / used['completed_calls'] * report['progress']['planned_decisions']),
                            'note': 'Extrapolación del primer tramo; la memoria y el feed pueden aumentar el consumo.'}
                    persist(output, report, ledger)
                    print(f"seed={seed} branch={branch_name} tick={step+1}/{config['steps']} "
                          f"decisions={report['decisions']} api_usd={usd(ledger.spent)} unresolved={len(ledger.pending)}", flush=True)
                branch['status'] = 'completed'
                branch['final_world_sha256'] = world_fingerprint(snapshot)
                write_json(output / f'world-{seed}-{branch_name}.json', snapshot)
                persist(output, report, ledger)
            pair['status'] = 'completed'
            persist(output, report, ledger)
    expected = config['population'] * config['steps'] * report['requested_pairs'] * 2
    if report['decisions'] != expected or ledger.summary()['completed_calls'] != expected or ledger.pending:
        raise RuntimeError('A complete pilot requires exactly one accounted model decision per account and tick')
    report['status'] = 'completed'


def provenance(output):
    sources = {str(p.relative_to(ROOT)): p.read_text() for pattern in ('worldlab/*.py', 'web/pilot-report.html', 'scripts/pilot') for p in ROOT.glob(pattern)}
    write_json(output / 'provenance.json', {'sources': sources, 'upstreams': read_json(ROOT / 'upstreams.json'),
                                          'requirements': {p.name: p.read_text() for p in (ROOT / 'requirements').glob('*.txt')}})
    return {name: hashlib.sha256(text.encode()).hexdigest() for name, text in sources.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pairs', type=int, default=10)
    parser.add_argument('--population', type=int, default=20)
    parser.add_argument('--steps', type=int, default=10)
    parser.add_argument('--start-seed', type=int, default=3000)
    parser.add_argument('--budget-usd', default='10')
    parser.add_argument('--concurrency', type=int, default=8)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.pairs <= 10 or not 4 <= args.population <= 20 or not 1 <= args.steps <= 10:
            raise ValueError('This pilot permits 1–10 pairs, 4–20 accounts and 1–10 ticks')
        if not 0 < amount(args.budget_usd) <= 10 or not 1 <= args.concurrency <= 20:
            raise ValueError('Budget must be >0 and <=US$10; concurrency must be 1–20')
        if not 0 <= args.start_seed <= 2**32 - args.pairs:
            raise ValueError('Seeds must fit within 0..2^32-1')
    except (ValueError, ArithmeticError) as exc:
        parser.error(str(exc))
    from dotenv import dotenv_values
    api_key = os.environ.get('OPENAI_API_KEY') or dotenv_values(args.env_file, interpolate=False).get('OPENAI_API_KEY')
    if not api_key:
        print('Missing OPENAI_API_KEY in the private environment or .env; no model calls made.', file=sys.stderr)
        return 2
    output = (args.output or DATA / 'pilots' / ('nubenorte-luna-' + uuid.uuid4().hex[:8])).resolve()
    if output.exists():
        parser.error('Output already exists; previous decisions and budget are never overwritten')
    output.mkdir(parents=True)
    ledger = CostLedger(output / 'costs.jsonl', args.budget_usd, max_in_flight=args.concurrency)
    report = {'schema_version': 1, 'kind': 'all-ai-incident-pilot', 'title': 'Nube Norte · 20 cuentas que deciden con IA',
              'status': 'running', 'started_at': now(), 'requested_pairs': args.pairs,
              'config': {'population': args.population, 'steps': args.steps, 'start_seed': args.start_seed,
                         'concurrency': args.concurrency, 'model': 'gpt-6-luna', 'effort': 'low', 'max_output_tokens': 2048},
              'branches': BRANCH_LABELS, 'operator_truth': TRUTH, 'initial_post': INITIAL_POST,
              'prompt_version': PROMPT_VERSION, 'instructions': INSTRUCTIONS, 'price_book': PRICE_BOOK,
              'experiments': [], 'decisions': 0, 'source_sha256': provenance(output)}
    persist(output, report, ledger)
    started = time.monotonic()
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    previous = signal.signal(signal.SIGTERM, interrupt)
    try:
        from openai import AsyncOpenAI
        async def execute(url, token):
            # Explicit TLS-verified standard global endpoint; no inherited proxy/base URL or retries.
            async with AsyncOpenAI(api_key=api_key, base_url='https://api.openai.com/v1', max_retries=0,
                                   timeout=60, http_client=httpx.AsyncClient(trust_env=False, timeout=60)) as provider:
                await run(report, output, SocietyPolicy(provider, ledger), ledger, url, token, concurrency=args.concurrency)
        with experiment_server(output, reuse_oasis=True, society=True) as (url, operator, unused_agent):
            asyncio.run(execute(url, operator))
        persist(output, report, ledger)
        from .pilot_audit import audit_pilot
        write_json(output / 'audit.json', audit_pilot(output))
        report['audit_verified'] = True
    except BaseException as exc:
        report['status'] = 'budget_exhausted' if isinstance(exc, BudgetExceeded) else 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed'
        report['error'] = safe_error(exc)
        for pair in report['experiments']:
            if pair['status'] == 'running':
                pair['status'] = report['status']
            for branch in pair['branches'].values():
                if branch['status'] == 'running':
                    branch['status'] = report['status']
        print(json.dumps(report['error']), file=sys.stderr)
    finally:
        signal.signal(signal.SIGTERM, previous)
        report['finished_at'] = now()
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        persist(output, report, ledger)
        print(f"{report['status']}: {report['decisions']} decisions; API usage cost=US${usd(ledger.spent)}; "
              f"unresolved={len(ledger.pending)}; report={output / 'report.html'}", flush=True)
    return 0 if report['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
