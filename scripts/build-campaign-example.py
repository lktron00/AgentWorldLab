#!/usr/bin/env python3
"""Rebuild the recorded Nube Norte explainer without engines or model calls."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from worldlab.campaign_report import build_html


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    report = json.loads((ROOT / 'examples/recorded-campaign/report.json').read_text())
    assert report['status'] == 'completed' and report.get('recording')
    assert report['summary']['pairs'] == len(report['experiments']) == report['requested_pairs'] == 1000
    assert report['summary']['model_calls'] == 0
    source = build_html(report)
    target = ROOT / 'web/nubenorte-report.html'
    if args.check:
        if not target.is_file() or target.read_text() != source:
            parser.error('Recorded campaign is stale; run python3 scripts/build-campaign-example.py')
        print('Recorded Nube Norte report matches the saved 1000-pair execution')
    else:
        target.write_text(source)
        print(target)


if __name__ == '__main__':
    main()
