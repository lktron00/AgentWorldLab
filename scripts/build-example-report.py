#!/usr/bin/env python3
"""Rebuild the bundled report from sanitized recorded usage, without any API."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from worldlab.common import ROOT
from worldlab.reports import build_html_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    source, report, audit = build_html_report(ROOT / "examples/recorded-demo", download_url="example-report.json")
    target = ROOT / "web/example-report.html"
    json_target = ROOT / "web/example-report.json"
    json_source = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not target.is_file() or target.read_text() != source or not json_target.is_file() or json_target.read_text() != json_source:
            print("Bundled report is stale. Run python3 scripts/build-example-report.py")
            return 1
        print("Bundled report matches sanitized recorded data")
    else:
        target.write_text(source)
        json_target.write_text(json_source)
        print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
