"""Descriptive paired results: both branches use AI, either may have a larger outcome."""
import json
import statistics
from decimal import Decimal
from .common import ROOT, write_json
from .costs import amount, usd
from .incident import BRANCHES


def summarize(report):
    pairs = [r for r in report['experiments'] if r.get('status') == 'completed']
    result = {'pairs': len(pairs), 'by_branch': {}, 'paired_diagnostic_minus_generic': {}}
    for branch in BRANCHES:
        completed = [r['branches'][branch] for r in pairs]
        result['by_branch'][branch] = {
            'mean_rumor_sharers': statistics.mean(b['trajectory'][-1]['rumor_sharers'] for b in completed) if completed else None,
            'mean_belief_loss': statistics.mean(b['trajectory'][-1]['mean_belief_loss'] for b in completed) if completed else None,
            'status_consultations': sum(b['action_counts'].get('inspect_status', 0) for b in completed),
            'posts': sum(b['action_counts'].get('post', 0) for b in completed),
            'reposts': sum(b['action_counts'].get('repost', 0) for b in completed),
            'waits': sum(b['action_counts'].get('wait', 0) for b in completed)}
    for metric in ('rumor_sharers', 'mean_belief_loss'):
        differences = [r['branches']['diagnostic']['trajectory'][-1][metric] - r['branches']['generic']['trajectory'][-1][metric] for r in pairs]
        result['paired_diagnostic_minus_generic'][metric] = {
            'mean': statistics.mean(differences) if differences else None,
            'median': statistics.median(differences) if differences else None,
            'negative': sum(d < 0 for d in differences), 'zero': differences.count(0), 'positive': sum(d > 0 for d in differences),
            'values': differences}
    return result


def build_html(report):
    payload = json.dumps(report, ensure_ascii=False, separators=(',', ':'))
    for before, after in (('&', '\\u0026'), ('<', '\\u003c'), ('>', '\\u003e'), ('\u2028', '\\u2028'), ('\u2029', '\\u2029')):
        payload = payload.replace(before, after)
    return (ROOT / 'web/pilot-report.html').read_text().replace('__PILOT_DATA__', payload)


def persist(output, report, ledger):
    report['cost'] = ledger.summary()
    report['progress'] = {'decisions': report.get('decisions', 0), 'planned_decisions': report['config']['population'] * report['config']['steps'] * report['requested_pairs'] * 2}
    report['summary'] = summarize(report)
    for pair in report['experiments']:
        for name, branch in pair['branches'].items():
            receipts = [r for r in ledger.receipts if ledger.contexts[r['call_id']].get('seed') == pair['seed'] and ledger.contexts[r['call_id']].get('branch') == name]
            branch['cost_usd'] = usd(sum((amount(r['estimated_cost_usd']) for r in receipts), Decimal(0)))
        pair['cost_usd'] = usd(sum((amount(b['cost_usd']) for b in pair['branches'].values()), Decimal(0)))
    write_json(output / 'report.json', report)
    temp = output / 'report.html.tmp'
    temp.write_text(build_html(report))
    temp.replace(output / 'report.html')
