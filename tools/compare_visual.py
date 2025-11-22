#!/usr/bin/env python3
"""Compare latest visual metrics against baseline.

Artifacts layout (created by test_visual_figma_alignment):
  artifacts/visual/vis_<timestamp>.json  (historical runs)
  artifacts/visual/latest.json            (last run)
  artifacts/visual/baseline.json          (first run or manually curated)

Exit codes:
  0 - success / no regression
  4 - regression detected (avg percent_diff exceeded tolerance)
  5 - missing required files

Usage:
  python tools/compare_visual.py --artifacts-dir artifacts/visual --screens welcome,home,scan --tolerance-mult 1.05

Logic:
  Compute average percent_diff over selected screens for baseline and latest.
  If latest_avg > baseline_avg * tolerance_mult => regression.

Environment overrides:
  VIS_COMPARE_DIR, VIS_COMPARE_SCREENS, VIS_COMPARE_TOL_MULT
"""
import os, json, argparse, sys
from pathlib import Path

def load_metrics(path: Path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        metrics = {m['screen']: m for m in data.get('metrics', [])}
        return metrics
    except Exception as e:
        print(f"ERROR: failed parsing metrics file {path}: {e}", file=sys.stderr)
        return {}

def avg_percent(metrics: dict, screens: list):
    vals = []
    for s in screens:
        m = metrics.get(s)
        if not m:
            continue
        pct = m.get('percent_diff')
        if pct is None:
            continue
        vals.append(float(pct))
    return sum(vals)/len(vals) if vals else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--artifacts-dir', default=os.environ.get('VIS_COMPARE_DIR','artifacts/visual'))
    ap.add_argument('--screens', default=os.environ.get('VIS_COMPARE_SCREENS','welcome,home,scan,scanning,result'))
    ap.add_argument('--tolerance-mult', default=os.environ.get('VIS_COMPARE_TOL_MULT','1.05'))
    args = ap.parse_args()

    artifacts_dir = Path(args.artifacts_dir)
    screens = [s.strip().lower() for s in args.screens.split(',') if s.strip()]
    try:
        tol_mult = float(args.tolerance_mult)
    except ValueError:
        print(f"ERROR: invalid tolerance-mult {args.tolerance_mult}", file=sys.stderr)
        sys.exit(5)

    baseline_path = artifacts_dir / 'baseline.json'
    latest_path = artifacts_dir / 'latest.json'
    if not baseline_path.exists() or not latest_path.exists():
        print(f"ERROR: baseline or latest missing in {artifacts_dir}", file=sys.stderr)
        sys.exit(5)

    baseline_metrics = load_metrics(baseline_path)
    latest_metrics = load_metrics(latest_path)
    if not baseline_metrics or not latest_metrics:
        print("ERROR: failed loading metrics", file=sys.stderr)
        sys.exit(5)

    baseline_avg = avg_percent(baseline_metrics, screens)
    latest_avg = avg_percent(latest_metrics, screens)
    if baseline_avg is None or latest_avg is None:
        print("ERROR: insufficient metrics for selected screens", file=sys.stderr)
        sys.exit(5)

    regression = latest_avg > baseline_avg * tol_mult
    result = {
        'screens': screens,
        'baseline_avg_percent_diff': baseline_avg,
        'latest_avg_percent_diff': latest_avg,
        'tolerance_multiplier': tol_mult,
        'regression': regression
    }
    print(json.dumps(result, indent=2))
    if regression:
        sys.exit(4)
    sys.exit(0)

if __name__ == '__main__':
    main()
