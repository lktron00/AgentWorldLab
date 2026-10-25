"""Resumable, offline paired campaigns through the real three-engine transport."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import ExitStack
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

from .common import DATA, ROOT, write_json
from .client import LabClient
from .experiment import experiment_server, world_fingerprint
from .models import LabAction
from .scenarios import validate_scenario

POLICIES = ('open', 'friction')


def now():
    return datetime.now(timezone.utc).isoformat()


def case_config(path, population=None, steps=None):
    case = json.loads(path.read_text())
    if set(case) != {'title', 'question', 'context', 'population', 'steps', 'world', 'policies'}:
        raise ValueError('Invalid campaign case fields')
    for key in ('title', 'question', 'context'):
        if not isinstance(case[key], str) or not 1 <= len(case[key]) <= 2000:
            raise ValueError('Case text must contain 1–2000 characters')
    case['world'] = validate_scenario(case['world'])
    if population is not None:
        case['population'] = population
    if steps is not None:
        case['steps'] = steps
    if type(case['population']) is not int or not 4 <= case['population'] <= 100:
        raise ValueError('Population must be 4–100')
    if type(case['steps']) is not int or not 1 <= case['steps'] <= case['world']['max_steps']:
        raise ValueError('Steps must fit inside world.max_steps')
    if set(case['policies']) != set(POLICIES):
        raise ValueError('Both policy descriptions are required')
    for policy in case['policies'].values():
        if set(policy) != {'label', 'description'} or any(not isinstance(v, str) or not 1 <= len(v) <= 2000 for v in policy.values()):
            raise ValueError('Invalid policy descriptions')
    if case['world']['initial_verified']:
        raise ValueError('The rumor campaign requires an unverified initial message')
    return case


def provenance(case, start_seed, pairs):
    files = ('common.py', 'controller.py', 'scripted_agent.py', 'oasis_worker.py',
             'checkpoints.py', 'scenarios.py', 'observations.py', 'campaign.py', 'experiment.py')
    return {'case': case, 'start_seed': start_seed, 'pairs': pairs,
            'upstreams': json.loads((ROOT / 'upstreams.json').read_text()),
            'adapter_sha256': {name: hashlib.sha256((ROOT / 'worldlab' / name).read_bytes()).hexdigest() for name in files}}


def read_rows(path):
    if path.is_symlink():
        raise ValueError('A linked journal cannot be resumed')
    if not path.exists():
        return []
    rows = []
    with path.open() as stream:
        for number, line in enumerate(stream, 1):
            if not line.endswith('\n'):
                raise ValueError(f'Incomplete journal line {number}; preserve the journal and inspect it before resuming')
            row = json.loads(line)
            if type(row.get('seed')) is not int or row.get('status') != 'completed' or set(row.get('branches', {})) != set(POLICIES):
                raise ValueError(f'Invalid journal record {number}')
            for branch in row['branches'].values():
                if branch['initial_world_sha256'] != row['initial_world_sha256']:
                    raise ValueError('A pair does not share its initial world')
            rows.append(row)
    if len({r['seed'] for r in rows}) != len(rows):
        raise ValueError('Duplicate seeds in campaign journal')
    return rows


def journal_row(path, row):
    with path.open('a') as stream:
        stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def pair_snapshot(snapshot):
    posts = [p for p in snapshot['world']['posts'] if p['root_id'] == 1 and p['user_id'] != 0]
    return {'step': snapshot['step'], 'rumor_sharers': len({p['user_id'] for p in posts}),
            'reposts': sum(p['original_post_id'] is not None for p in posts)}


async def simulate_pair(client, http, case, seed, worker_index):
    started = time.monotonic()

    async def reset(**parameters):
        response = await http.post('/lab/reset-tickets', json=parameters)
        response.raise_for_status()
        return (await client.reset(ticket=response.json()['ticket'])).observation.snapshot

    async def snapshot(run_id):
        response = await http.get(f'/lab/runs/{run_id}/snapshot')
        response.raise_for_status()
        return response.json()

    observation = await reset(seed=seed, population=case['population'], policy='open', scenario=case['world'])
    initial = await snapshot(observation['run_id'])
    response = await http.post(f"/lab/runs/{initial['run_id']}/checkpoint")
    response.raise_for_status()
    checkpoint = response.json()['checkpoint_id']
    row = {'seed': seed, 'status': 'running', 'worker': worker_index, 'checkpoint_id': checkpoint,
           'initial_world_sha256': world_fingerprint(initial), 'branches': {},
           'cost': {'model_calls': 0, 'api_cost_usd': '0.0000000000', 'local_compute_cost_usd': None}}
    for name in POLICIES:
        if name == 'friction':
            observation = await reset(checkpoint_id=checkpoint, policy=name)
        full = await snapshot(observation['run_id'])
        if world_fingerprint(full) != row['initial_world_sha256']:
            raise RuntimeError('Paired worlds differ before intervention')
        branch = {'run_id': full['run_id'], 'initial_world_sha256': world_fingerprint(full),
                  'trajectory': [pair_snapshot(full)], 'world_sha256': [world_fingerprint(full)]}
        row['branches'][name] = branch
        for _ in range(case['steps']):
            observation = (await client.step(LabAction())).observation.snapshot
            full = await snapshot(observation['run_id'])
            branch['trajectory'].append(pair_snapshot(full))
            branch['world_sha256'].append(world_fingerprint(full))
        branch['final_world'] = full['world']
    row['status'] = 'completed'
    row['elapsed_seconds'] = round(time.monotonic() - started, 4)
    row['background_agent_decisions'] = 2 * case['population'] * case['steps']
    row['avoided_sharers_at_horizon'] = (row['branches']['open']['trajectory'][-1]['rumor_sharers']
                                        - row['branches']['friction']['trajectory'][-1]['rumor_sharers'])
    return row


def persist(output, report):
    from .campaign_report import summarize, build_html
    report['updated_at'] = now()
    report['summary'] = summarize(report['experiments'], report['case'])
    # Full OASIS states remain in the durable journal and engine directories;
    # only one illustrative pair is embedded in the portable overview.
    public = dict(report)
    public['experiments'] = [{**r, 'branches': {p: {k: v for k, v in b.items() if k != 'final_world'} for p, b in r['branches'].items()}} for r in report['experiments']]
    if report['experiments']:
        ordered = sorted(report['experiments'], key=lambda r: (r['avoided_sharers_at_horizon'], r['seed']))
        public['illustrative_pair'] = ordered[len(ordered) // 2]
    write_json(output / 'report.json', public)
    (output / 'report.html.tmp').write_text(build_html(public))
    (output / 'report.html.tmp').replace(output / 'report.html')


async def run(output, report, rows, workers):
    completed = {r['seed'] for r in rows}
    todo = asyncio.Queue()
    for seed in range(report['start_seed'], report['start_seed'] + report['requested_pairs']):
        if seed not in completed:
            todo.put_nowait(seed)
    with ExitStack() as servers:
        configs = []
        for index in range(min(workers, todo.qsize())):
            directory = output / f'worker-{index}'
            directory.mkdir(exist_ok=True)
            configs.append(servers.enter_context(experiment_server(directory, reuse_oasis=True)))

        async def consume(index, config):
            url, operator, agent = config
            async with LabClient(base_url=url, message_timeout_s=180, mode='simulation',
                                 headers={'Authorization': 'Bearer ' + agent}) as client, \
                    httpx.AsyncClient(base_url=url, timeout=180, trust_env=False,
                                      headers={'Authorization': 'Bearer ' + operator}) as http:
                while not todo.empty():
                    seed = todo.get_nowait()
                    row = await simulate_pair(client, http, report['case'], seed, index)
                    journal_row(output / 'pairs.jsonl', row)
                    rows.append(row)
                    todo.task_done()
                    if len(rows) % 5 == 0 or todo.empty():
                        persist(output, report)
                    print(f"pairs={len(rows)}/{report['requested_pairs']} seed={seed} "
                          f"open={row['branches']['open']['trajectory'][-1]['rumor_sharers']} "
                          f"pause={row['branches']['friction']['trajectory'][-1]['rumor_sharers']} "
                          f"seconds={row['elapsed_seconds']:.2f} api_usd=0", flush=True)
        tasks = [asyncio.create_task(consume(i, c)) for i, c in enumerate(configs)]
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case', type=Path, default=ROOT / 'scenarios/nubenorte-campaign.json')
    p.add_argument('--pairs', type=int, default=1000)
    p.add_argument('--start-seed', type=int, default=1000)
    p.add_argument('--population', type=int)
    p.add_argument('--steps', type=int)
    p.add_argument('--workers', type=int, choices=[1, 2], default=2)
    p.add_argument('--output', type=Path)
    p.add_argument('--resume', action='store_true')
    args = p.parse_args(argv)
    try:
        case = case_config(args.case, args.population, args.steps)
        if not 1 <= args.pairs <= 10000 or not 0 <= args.start_seed <= 2**32 - args.pairs:
            raise ValueError('Use 1–10000 pairs and distinct seeds within 0..2^32-1')
        output = (args.output or DATA / 'campaigns' / ('nubenorte-' + uuid.uuid4().hex[:8])).resolve()
        config = provenance(case, args.start_seed, args.pairs)
        if args.resume:
            if not output.is_dir() or output.is_symlink() or (output / 'provenance.json').is_symlink():
                raise ValueError('Resume requires the original campaign directory')
            if json.loads((output / 'provenance.json').read_text()) != config:
                raise ValueError('Configuration or runtime source changed; use the original source/settings or a new output')
            rows = read_rows(output / 'pairs.jsonl')
            if any(not args.start_seed <= r['seed'] < args.start_seed + args.pairs for r in rows):
                raise ValueError('Journal seeds are outside this campaign')
            report = json.loads((output / 'report.json').read_text())
            report['experiments'] = rows
        else:
            if output.exists():
                raise ValueError('Output already exists; use --resume with the same settings or choose a new directory')
            output.mkdir(parents=True)
            write_json(output / 'provenance.json', config)
            rows = []
            report = {'schema_version': 1, 'kind': 'scripted-policy-campaign', 'status': 'running',
                      'case': case, 'requested_pairs': args.pairs, 'start_seed': args.start_seed,
                      'started_at': now(), 'experiments': rows, 'segments': [], 'provenance': config,
                      'cost': {'model_calls': 0, 'api_cost_usd': '0.0000000000', 'local_compute_cost_usd': None}}
    except (ValueError, OSError, KeyError) as exc:
        p.error(str(exc))
    report['status'] = 'running'
    report.pop('error', None)
    started = time.monotonic()
    segment = {'started_at': now(), 'initial_pairs': len(rows)}
    report['segments'].append(segment)
    persist(output, report)
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    previous = signal.signal(signal.SIGTERM, interrupt)
    exit_code = 0
    try:
        if len(rows) < args.pairs:
            asyncio.run(run(output, report, rows, args.workers))
        if len(rows) != args.pairs:
            raise RuntimeError('Campaign stopped short of its requested pairs')
        report['status'] = 'completed'
    except KeyboardInterrupt:
        report['status'] = 'interrupted'
        exit_code = 130
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        exit_code = 1
    finally:
        signal.signal(signal.SIGTERM, previous)
        segment.update(finished_at=now(), elapsed_seconds=round(time.monotonic() - started, 3), completed_pairs=len(rows)-segment['initial_pairs'])
        persist(output, report)
    print(f"{report['status']}: {len(rows)}/{args.pairs} pairs; report={output / 'report.html'}; model API cost=US$0; local compute not priced", flush=True)
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
