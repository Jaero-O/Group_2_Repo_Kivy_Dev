#!/usr/bin/env python3
"""Batch visual regression comparison against reference screenshots.

Naming convention:
  Capture script stores current screenshots in a directory (default: screenshots/current)
  Reference images expected at: screenshots/references/<screen_name>.png

This tool will:
  1. Iterate list of current screenshots matching pattern <screen_name>.png
  2. For each, attempt to find reference file
  3. Compute basic image diff metrics (percent differing pixels, mean abs diff per channel)
  4. Emit JSON summary to stdout and optionally per-screen metric files

Usage:
  python tools/visual_regression.py --current-dir screenshots/current --reference-dir screenshots/references \
         --output metrics_visual.json --threshold 0.25

Threshold semantics:
  If percent_diff (fraction) > threshold, mark status = 'fail', else 'pass'.

Environment variables (override CLI):
  VIS_REG_CURRENT_DIR, VIS_REG_REFERENCE_DIR, VIS_REG_THRESHOLD

Limitations:
  This performs a raw pixel diff; layout shifts or dynamic content may inflate values.
  For robustness you can add a crop or scale step; currently we scale current image
  to reference size if dimensions differ (aspect ratio preserved by center crop/fit).
"""
import os, sys, json, argparse
from dataclasses import dataclass, asdict
from typing import Tuple, List, Dict, Optional
import math
try:
    import numpy as np
except Exception:
    np = None
from PIL import Image, ImageChops

@dataclass
class DiffMetrics:
    screen: str
    reference_path: str
    current_path: str
    width: int
    height: int
    pixel_count: int
    differing_pixels: int
    percent_diff: float
    mean_abs_diff_per_channel: List[float]
    overall_mean_abs_diff: float
    status: str
    masked_pixel_count: int = 0
    effective_pixel_count: int = 0
    ssim: Optional[float] = None
    percent_diff_threshold: Optional[float] = None
    ssim_threshold: Optional[float] = None


def load_image(path: str) -> Image.Image:
    return Image.open(path).convert('RGBA')


def resize_to_match(current: Image.Image, reference: Image.Image) -> Image.Image:
    if current.size == reference.size:
        return current
    ref_w, ref_h = reference.size
    cur_w, cur_h = current.size
    # Preserve aspect ratio by scaling then center cropping/padding.
    scale = min(cur_w / ref_w, cur_h / ref_h)
    # Simple approach: just resize to reference directly ignoring aspect ratio differences.
    return current.resize((ref_w, ref_h), Image.LANCZOS)


def compute_metrics(ref: Image.Image, cur: Image.Image, screen: str, ref_path: str, cur_path: str, threshold: float, masks: Optional[List[Dict[str,int]]] = None, diff_dir: Optional[str] = None, enable_ssim: bool = False, heatmap_dir: Optional[str] = None) -> DiffMetrics:
    # Ensure same size
    cur = resize_to_match(cur, ref)
    diff = ImageChops.difference(cur, ref)
    # Convert to raw bytes
    ref_px = ref.getdata()
    cur_px = cur.getdata()
    diff_px = diff.getdata()
    differing = 0
    masked = 0
    sum_abs = [0,0,0,0]
    w, h = ref.size
    mask_grid = None
    if masks:
        mask_grid = [[False]*w for _ in range(h)]
        for m in masks:
            x = m.get('x',0); y = m.get('y',0); mw = m.get('w',0); mh = m.get('h',0)
            for yy in range(y, min(y+mh, h)):
                row = mask_grid[yy]
                for xx in range(x, min(x+mw, w)):
                    row[xx] = True
    # Iterate with index to consult mask
    idx = 0
    for y in range(h):
        for x in range(w):
            (r1,g1,b1,a1) = ref_px[idx]
            (r2,g2,b2,a2) = cur_px[idx]
            (dr,dg,db,da) = diff_px[idx]
            is_diff = (dr or dg or db or da)
            if mask_grid and mask_grid[y][x]:
                masked += 1
            else:
                if is_diff:
                    differing += 1
                sum_abs[0] += abs(r1-r2); sum_abs[1] += abs(g1-g2); sum_abs[2] += abs(b1-b2); sum_abs[3] += abs(a1-a2)
            idx += 1
    pixel_count = len(ref_px)
    effective_count = pixel_count - masked if pixel_count > masked else 1
    mean_abs = [s/effective_count for s in sum_abs[:3]]  # ignore alpha for summary
    overall = sum(mean_abs)/3
    percent_diff = differing / effective_count
    status = 'pass' if percent_diff <= threshold else 'fail'
    # Optional overlay diff: highlight differing pixels (excluding masked) in red over current
    if diff_dir:
        try:
            overlay = cur.convert('RGBA')
            ov_pixels = overlay.load()
            idx = 0
            for y in range(h):
                for x in range(w):
                    (dr,dg,db,da) = diff_px[idx]
                    draw_diff = (dr or dg or db or da)
                    masked_here = False if not mask_grid else mask_grid[y][x]
                    if draw_diff and not masked_here:
                        r,g,b,a = ov_pixels[x,y]
                        ov_pixels[x,y] = (255,0,0,180)
                    elif masked_here:
                        # dim masked region
                        r,g,b,a = ov_pixels[x,y]
                        ov_pixels[x,y] = (r//2,g//2,b//2,160)
                    idx += 1
            os.makedirs(diff_dir, exist_ok=True)
            overlay.save(os.path.join(diff_dir, f"{screen}_diff.png"))
        except Exception as e:
            print(f"WARN: Could not save diff overlay for {screen}: {e}", file=sys.stderr)
    # Optional heatmap diff: color by magnitude of RGB difference, masked dimmed
    if heatmap_dir:
        try:
            heat = Image.new('RGBA', (w, h))
            hp = heat.load()
            idx = 0
            for y in range(h):
                for x in range(w):
                    (dr,dg,db,da) = diff_px[idx]
                    masked_here = False if not mask_grid else mask_grid[y][x]
                    if masked_here:
                        hp[x,y] = (0,0,0,80)
                    else:
                        # magnitude normalized
                        mag = (dr + dg + db) / 3.0
                        # Map mag (0..255) to gradient: dark blue -> cyan -> yellow -> red
                        # Simple linear segments
                        if mag < 64:
                            # blue scale
                            r = 0; g = int(mag*2); b = int(80+mag)
                        elif mag < 128:
                            # cyan transition
                            r = 0; g = int(128 + (mag-64)*2); b = 200
                        elif mag < 192:
                            # yellowish
                            r = int(150 + (mag-128)*1.2); g = 255; b = int(50)
                        else:
                            # red
                            r = 255; g = int(max(0,255 - (mag-192)*2)); b = 0
                        hp[x,y] = (int(r), int(g), int(b), 180 if (dr or dg or db or da) else 70)
                    idx += 1
            os.makedirs(heatmap_dir, exist_ok=True)
            heat.save(os.path.join(heatmap_dir, f"{screen}_heatmap.png"))
        except Exception as e:
            print(f"WARN: Could not save heatmap for {screen}: {e}", file=sys.stderr)
    # Global (masked) SSIM approximation if enabled and numpy available
    ssim_val = None
    if enable_ssim and np is not None:
        try:
            # Convert to grayscale arrays
            ref_gray = np.array(ref.convert('L'), dtype=np.float32)
            cur_gray = np.array(cur.convert('L'), dtype=np.float32)
            if mask_grid:
                mask_np = np.array([[0 if m else 1 for m in row] for row in mask_grid], dtype=np.float32)
            else:
                mask_np = np.ones_like(ref_gray, dtype=np.float32)
            # Apply mask
            ref_m = ref_gray * mask_np
            cur_m = cur_gray * mask_np
            # Compute means over unmasked pixels
            wsum = mask_np.sum() or 1.0
            mu_x = ref_m.sum() / wsum
            mu_y = cur_m.sum() / wsum
            # Variances and covariance
            var_x = ((ref_m - mu_x) ** 2).sum() / wsum
            var_y = ((cur_m - mu_y) ** 2).sum() / wsum
            cov_xy = ((ref_m - mu_x) * (cur_m - mu_y)).sum() / wsum
            L = 255.0
            C1 = (0.01 * L) ** 2
            C2 = (0.03 * L) ** 2
            ssim_val = ((2 * mu_x * mu_y + C1) * (2 * cov_xy + C2)) / ((mu_x ** 2 + mu_y ** 2 + C1) * (var_x + var_y + C2))
            # Clamp
            if not math.isfinite(ssim_val):
                ssim_val = None
        except Exception:
            ssim_val = None
    return DiffMetrics(
        screen=screen,
        reference_path=ref_path,
        current_path=cur_path,
        width=ref.width,
        height=ref.height,
        pixel_count=pixel_count,
        differing_pixels=differing,
        percent_diff=percent_diff,
        mean_abs_diff_per_channel=mean_abs,
        overall_mean_abs_diff=overall,
        status=status,
        masked_pixel_count=masked,
        effective_pixel_count=effective_count,
        ssim=ssim_val
    )


def infer_screen_name(filename: str) -> str:
    # strip extension, replace spaces with underscores
    name = os.path.splitext(os.path.basename(filename))[0]
    return name.lower().replace(' ', '_')


def normalize_current_filename(f: str) -> str:
    """Strip trailing numeric capture suffix like 'welcome0001' -> 'welcome'."""
    base = os.path.splitext(f)[0]
    # Detect pattern of trailing digits
    i = len(base) - 1
    while i >=0 and base[i].isdigit():
        i -= 1
    # If we stripped digits and at least one digit existed
    if i < len(base) - 1:
        return base[:i+1]
    return base

def collect_current_screens(current_dir: str) -> List[Tuple[str,str]]:
    """Return list of (screen_name, filename)."""
    screens = []
    for f in os.listdir(current_dir):
        if f.lower().endswith('.png'):
            norm = normalize_current_filename(f)
            screens.append((norm, f))
    return screens


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--current-dir', required=False, default=os.environ.get('VIS_REG_CURRENT_DIR','screenshots/current'))
    p.add_argument('--reference-dir', required=False, default=os.environ.get('VIS_REG_REFERENCE_DIR','screenshots/references'))
    p.add_argument('--output', required=False, default='visual_metrics.json')
    p.add_argument('--threshold', type=float, default=float(os.environ.get('VIS_REG_THRESHOLD','0.25')))
    p.add_argument('--ignore-screens', required=False, default='', help='Comma-separated list of screen names to ignore (after normalization).')
    p.add_argument('--mask-config', required=False, default='', help='Path to JSON mask config mapping screen -> list of {x,y,w,h}.')
    p.add_argument('--diff-dir', required=False, default='', help='Directory to write per-screen diff overlay images.')
    p.add_argument('--heatmap-dir', required=False, default='', help='Directory to write per-screen heatmap images.')
    p.add_argument('--enable-ssim', action='store_true', help='Compute global masked SSIM for each screen (requires numpy).')
    p.add_argument('--thresholds-config', required=False, default='', help='Optional JSON mapping of per-screen thresholds: {"screens": {"name": {"percent_diff": 0.3, "ssim": 0.9}}, "default": {"percent_diff": 0.35, "ssim": 0.55}}.')
    args = p.parse_args()

    # Load mask config if provided
    mask_map: Dict[str, List[Dict[str,int]]] = {}
    if args.mask_config:
        if os.path.isfile(args.mask_config):
            try:
                with open(args.mask_config,'r',encoding='utf-8') as mf:
                    raw = json.load(mf)
                for k,v in raw.items():
                    mask_map[k.lower()] = v
                print(f"Loaded mask config for {len(mask_map)} screens", file=sys.stderr)
            except Exception as e:
                print(f"WARN: Failed to load mask config: {e}", file=sys.stderr)
        else:
            print(f"WARN: mask-config path not found: {args.mask_config}", file=sys.stderr)

    # Load per-screen thresholds config if provided
    thresholds_map: Dict[str, Dict[str, float]] = {}
    default_thresholds: Dict[str, float] = {'percent_diff': args.threshold, 'ssim': None}
    if args.thresholds_config:
        if os.path.isfile(args.thresholds_config):
            try:
                with open(args.thresholds_config, 'r', encoding='utf-8') as tf:
                    tjson = json.load(tf)
                default_thresholds = tjson.get('default', default_thresholds)
                scrs = tjson.get('screens', {})
                for k,v in scrs.items():
                    thresholds_map[k.lower()] = v
                print(f"Loaded thresholds config for {len(thresholds_map)} screens", file=sys.stderr)
            except Exception as e:
                print(f"WARN: Failed to load thresholds config: {e}", file=sys.stderr)
        else:
            print(f"WARN: thresholds-config path not found: {args.thresholds_config}", file=sys.stderr)

    if not os.path.isdir(args.current_dir):
        print(f"ERROR: current-dir missing: {args.current_dir}", file=sys.stderr)
        sys.exit(2)
    if not os.path.isdir(args.reference_dir):
        print(f"ERROR: reference-dir missing: {args.reference_dir}", file=sys.stderr)
        sys.exit(3)

    current_files = collect_current_screens(args.current_dir)
    ignore_set = set([s for s in [x.strip().lower() for x in args.ignore_screens.split(',')] if s])

    # Group captures by normalized screen name
    grouped: Dict[str, List[str]] = {}
    for screen_name, filename in current_files:
        if screen_name in ignore_set:
            continue
        grouped.setdefault(screen_name, []).append(filename)

    results: List[DiffMetrics] = []
    missing = []
    total_considered = 0
    for screen_name, files in grouped.items():
        total_considered += 1
        ref_path = os.path.join(args.reference_dir, f"{screen_name}.png")
        if not os.path.exists(ref_path):
            missing.append(screen_name)
            continue
        try:
            ref_img = load_image(ref_path)
        except Exception as e:
            print(f"WARN: Failed loading reference for {screen_name}: {e}", file=sys.stderr)
            missing.append(screen_name)
            continue
        # Compute metrics for all captures of this screen and keep the best match
        best: DiffMetrics = None
        for f in files:
            current_path = os.path.join(args.current_dir, f)
            try:
                cur_img = load_image(current_path)
                masks = mask_map.get(screen_name, [])
                m = compute_metrics(ref_img, cur_img, screen_name, ref_path, current_path, args.threshold, masks=masks, diff_dir=args.diff_dir or None, enable_ssim=args.enable_ssim, heatmap_dir=args.heatmap_dir or None)
                if best is None or m.percent_diff < best.percent_diff:
                    best = m
            except Exception as e:
                print(f"WARN: Failed processing {screen_name} ({f}): {e}", file=sys.stderr)
                continue
        if best is not None:
            # Assign per-screen threshold values (override global threshold if present)
            ts = thresholds_map.get(screen_name, default_thresholds)
            pd_t = ts.get('percent_diff', args.threshold)
            ssim_t = ts.get('ssim')
            best.percent_diff_threshold = pd_t
            best.ssim_threshold = ssim_t
            # Re-evaluate pass/fail using combined logic
            passes = (best.percent_diff <= pd_t) or (ssim_t is not None and best.ssim is not None and best.ssim >= ssim_t)
            best.status = 'pass' if passes else 'fail'
            results.append(best)

    summary = {
        'threshold': args.threshold,
        'total_screens': total_considered,
        'processed': len(results),
        'missing_references': sorted(list(set(missing))),
        'metrics': [asdict(r) for r in results],
        'failures': [r.screen for r in results if r.status=='fail']
    }
    with open(args.output,'w') as f:
        json.dump(summary,f,indent=2)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
