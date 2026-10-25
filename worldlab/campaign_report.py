"""Descriptive statistics and a portable, interactive campaign explainer."""
from __future__ import annotations

import json
import math
from pathlib import Path
import statistics

from .common import ROOT


def quantile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = math.floor(index)
    return ordered[lower] + (ordered[math.ceil(index)] - ordered[lower]) * (index - lower)


def summarize(rows, case):
    count = len(rows)
    result = {'pairs': count, 'worlds': 2 * count, 'population_per_world': case['population'],
              'background_agent_decisions': sum(r['background_agent_decisions'] for r in rows),
              'paired_runtime_seconds': round(sum(r['elapsed_seconds'] for r in rows), 3),
              'api_cost_usd': '0.0000000000', 'model_calls': 0,
              'local_compute_cost_usd': None, 'branches': {}}
    if not count:
        return result
    for row in rows:
        if row['status'] != 'completed' or len(row['branches']) != 2:
            raise ValueError('Summary requires complete pairs')
        for b in row['branches'].values():
            if len(b['trajectory']) != case['steps'] + 1 or b['initial_world_sha256'] != row['initial_world_sha256']:
                raise ValueError('Pair horizon or starting world differs')
    for name in ('open', 'friction'):
        trajectories = [r['branches'][name]['trajectory'] for r in rows]
        ends = [t[-1]['rumor_sharers'] for t in trajectories]
        result['branches'][name] = {'mean': statistics.mean(ends), 'median': statistics.median(ends),
            'p10': quantile(ends, .1), 'p90': quantile(ends, .9),
            'half_shared_fraction': sum(n >= case['population'] / 2 for n in ends) / count,
            'trajectory': [{'step': i, 'mean': statistics.mean(t[i]['rumor_sharers'] for t in trajectories),
                            'p10': quantile([t[i]['rumor_sharers'] for t in trajectories], .1),
                            'p90': quantile([t[i]['rumor_sharers'] for t in trajectories], .9)}
                           for i in range(case['steps'] + 1)]}
    deltas = [r['branches']['open']['trajectory'][-1]['rumor_sharers'] -
              r['branches']['friction']['trajectory'][-1]['rumor_sharers'] for r in rows]
    result['paired_effect'] = {'mean': statistics.mean(deltas), 'median': statistics.median(deltas),
                              'p10': quantile(deltas, .1), 'p90': quantile(deltas, .9),
                              'positive_pairs': sum(d > 0 for d in deltas),
                              'zero_pairs': deltas.count(0), 'negative_pairs': sum(d < 0 for d in deltas)}
    denominator = result['branches']['open']['mean']
    result['relative_difference_of_means'] = statistics.mean(deltas) / denominator if denominator else None
    return result


def build_html(report):
    data = json.dumps(report, ensure_ascii=False, separators=(',', ':'))
    # No user text is inserted as executable markup or interpreted with innerHTML.
    data = data.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    data = data.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    return (ROOT / 'web/campaign-report.html').read_text().replace('__CAMPAIGN_DATA__', data)
