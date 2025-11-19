"""Compare performance artifacts to detect regressions.

Reads JSON metric files in artifacts/performance and prints a summary.
Optionally exits with non-zero code if avg_duration regresses beyond threshold.

Usage:
    python scripts/compare_performance.py [--fail-on-regression] [--threshold 1.2]

Threshold multiplier applies to average stress duration vs historical mean (excluding latest).
"""
import os
import sys
import json
from statistics import mean
from glob import glob

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PERF_DIR = os.path.join(PROJECT_ROOT, 'artifacts', 'performance')

def load_artifacts():
    files = sorted(glob(os.path.join(PERF_DIR, 'perf_*.json')))
    artifacts = []
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                artifacts.append((f, json.load(fh)))
        except Exception:
            pass
    return artifacts

def compute_regression(artifacts, threshold):
    if len(artifacts) < 2:
        return None
    *historical, latest = artifacts
    historical_avgs = [a[1].get('stress_summary', {}).get('avg_duration') for a in historical]
    historical_avgs = [v for v in historical_avgs if v is not None]
    latest_avg = latest[1].get('stress_summary', {}).get('avg_duration')
    if not historical_avgs or latest_avg is None:
        return None
    baseline = mean(historical_avgs)
    limit = baseline * threshold
    return {
        'baseline_avg': baseline,
        'latest_avg': latest_avg,
        'threshold_limit': limit,
        'regression': latest_avg > limit,
        'latest_file': latest[0]
    }

def main(argv):
    fail = '--fail-on-regression' in argv
    try:
        idx = argv.index('--threshold')
        threshold = float(argv[idx+1])
    except Exception:
        threshold = 1.2
    artifacts = load_artifacts()
    if not artifacts:
        print('No performance artifacts found.')
        return 0
    print(f'Loaded {len(artifacts)} artifact(s).')
    reg = compute_regression(artifacts, threshold)
    if reg:
        print('Regression check:')
        for k,v in reg.items():
            print(f'  {k}: {v}')
        if fail and reg['regression']:
            print('Performance regression detected.')
            return 1
    else:
        print('Insufficient data for regression check.')
    return 0

if __name__ == '__main__':
    code = main(sys.argv[1:])
    sys.exit(code)
