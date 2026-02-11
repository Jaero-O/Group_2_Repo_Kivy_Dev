#!/usr/bin/env python3
"""Bundle visual regression artifacts into a single ZIP archive.

Includes:
  - Metrics JSON file
  - Diff overlays directory (PNG files)
  - Heatmap directory (PNG files)
  - Reference images (PNG)
  - Optional current capture set

Usage:
  python tools/bundle_visual_artifacts.py \
      --metrics screenshots/references/visual_metrics_masked_alt.json \
      --diff-dir screenshots/diff_overlays_alt \
      --heatmap-dir screenshots/heatmaps_alt \
      --references-dir screenshots/references \
      --current-dir screenshots/current_alt \
      --output artifacts/visual_regression_bundle.zip
"""
import os, argparse, zipfile, sys

def add_dir(zf: zipfile.ZipFile, root: str, arc_prefix: str, exts=(".png", ".json")):
    if not root or not os.path.isdir(root):
        return
    for fname in os.listdir(root):
        fpath = os.path.join(root, fname)
        if os.path.isfile(fpath):
            if exts is None or any(fname.lower().endswith(e) for e in exts):
                arcname = os.path.join(arc_prefix, fname)
                zf.write(fpath, arcname)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--metrics', required=True, help='Path to metrics JSON file.')
    ap.add_argument('--diff-dir', required=False, default='', help='Directory containing diff overlay PNGs.')
    ap.add_argument('--heatmap-dir', required=False, default='', help='Directory containing heatmap PNGs.')
    ap.add_argument('--references-dir', required=False, default='screenshots/references', help='Directory of reference PNGs.')
    ap.add_argument('--current-dir', required=False, default='', help='Directory of current capture PNGs.')
    ap.add_argument('--output', required=False, default='artifacts/visual_regression_bundle.zip', help='Output ZIP path.')
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        # Metrics
        if os.path.isfile(args.metrics):
            zf.write(args.metrics, os.path.join('metrics', os.path.basename(args.metrics)))
        # Directories
        add_dir(zf, args.diff_dir, 'diff_overlays')
        add_dir(zf, args.heatmap_dir, 'heatmaps')
        add_dir(zf, args.references_dir, 'references')
        add_dir(zf, args.current_dir, 'current')
    print(f"Artifact bundle written: {args.output}")

if __name__ == '__main__':
    main()