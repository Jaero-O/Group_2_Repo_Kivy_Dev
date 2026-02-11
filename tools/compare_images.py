#!/usr/bin/env python3
"""Image comparison utility for pixel-level UI regression checks.

Usage (basic):
  python tools/compare_images.py --current screenshots/current_result0001.png --reference path/to/target.png \
      --out-combined screenshots/compare_side_by_side.png \
      --out-diff screenshots/compare_diff_heatmap.png \
      --out-json screenshots/compare_metrics.json

Optional arguments:
  --threshold INT          Per-channel absolute difference threshold to count a pixel as differing (default 0)
  --crop x,y,w,h           Restrict metrics to a crop region (still shows full images in outputs)
  --scale-mode MODE        How to reconcile size mismatch: pad (default), current_to_reference, reference_to_current
  --spacing INT            Spacing (px) between images in combined output (default 12)
  --bg R,G,B               Background color for padding/combined image (default 255,255,255)
  --label-current TEXT     Label for current image (default CURRENT)
  --label-reference TEXT   Label for reference image (default REFERENCE)
  --font-size INT          Font size for labels (default 18)

Metrics JSON example:
{
  "width": 480,
  "height": 800,
  "pixel_count": 384000,
  "differing_pixels": 532,
  "percent_diff": 0.1385,
  "mean_abs_diff_per_channel": [3.12, 2.05, 1.88],
  "max_abs_diff_per_channel": [255, 255, 255],
  "rmse_per_channel": [12.7, 10.4, 9.8],
  "overall_mean_abs_diff": 2.35
}

Diff heatmap legend:
  Black = identical
  Yellow/Red = increasingly different (scaled by per-pixel summed abs diff)

No external dependencies beyond Pillow. Avoids heavier libs (e.g., scikit-image) for portability.
"""

import argparse
import json
import math
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


@dataclass
class ComparisonResult:
    width: int
    height: int
    differing_pixels: int
    pixel_count: int
    percent_diff: float
    mean_abs_diff_per_channel: List[float]
    max_abs_diff_per_channel: List[int]
    rmse_per_channel: List[float]
    overall_mean_abs_diff: float
    crop: Optional[Tuple[int, int, int, int]] = None


def parse_crop(value: Optional[str]) -> Optional[Tuple[int, int, int, int]]:
    if not value:
        return None
    parts = value.split(',')
    if len(parts) != 4:
        raise ValueError("--crop must have 4 comma-separated integers: x,y,w,h")
    x, y, w, h = map(int, parts)
    if w <= 0 or h <= 0:
        raise ValueError("Crop width/height must be positive")
    return x, y, w, h


def load_image(path: str) -> Image.Image:
    try:
        return Image.open(path).convert('RGBA')
    except Exception as e:
        print(f"Error loading image '{path}': {e}", file=sys.stderr)
        sys.exit(2)


def pad_to(img: Image.Image, width: int, height: int, bg: Tuple[int, int, int]) -> Image.Image:
    if img.width == width and img.height == height:
        return img
    canvas = Image.new('RGBA', (width, height), (*bg, 255))
    canvas.paste(img, (0, 0), img)
    return canvas


def scale_to(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    return img.resize((target_w, target_h), Image.LANCZOS)


def reconcile_sizes(current: Image.Image, reference: Image.Image, mode: str, bg: Tuple[int, int, int]) -> Tuple[Image.Image, Image.Image]:
    if current.size == reference.size:
        return current, reference
    if mode == 'current_to_reference':
        current = scale_to(current, reference.width, reference.height)
    elif mode == 'reference_to_current':
        reference = scale_to(reference, current.width, current.height)
    else:  # pad (default)
        width = max(current.width, reference.width)
        height = max(current.height, reference.height)
        current = pad_to(current, width, height, bg)
        reference = pad_to(reference, width, height, bg)
    return current, reference


def compute_metrics(current: Image.Image, reference: Image.Image, threshold: int, crop: Optional[Tuple[int, int, int, int]]) -> ComparisonResult:
    if current.size != reference.size:
        raise ValueError("Images must be same size for metric computation after reconciliation")
    width, height = current.size
    if crop:
        x, y, w, h = crop
        x2, y2 = x + w, y + h
        if not (0 <= x < width and 0 <= y < height and x2 <= width and y2 <= height):
            raise ValueError("Crop outside image bounds")
        c_region = current.crop((x, y, x2, y2))
        r_region = reference.crop((x, y, x2, y2))
        width, height = w, h
    else:
        c_region = current
        r_region = reference

    c_pixels = c_region.load()
    r_pixels = r_region.load()

    differing = 0
    pixel_count = width * height
    sum_abs = [0, 0, 0]
    sum_sq = [0, 0, 0]
    max_abs = [0, 0, 0]

    for j in range(height):
        for i in range(width):
            cr, cg, cb, ca = c_pixels[i, j]
            rr, rg, rb, ra = r_pixels[i, j]
            dr = abs(cr - rr)
            dg = abs(cg - rg)
            db = abs(cb - rb)
            if dr > threshold or dg > threshold or db > threshold:
                differing += 1
            sum_abs[0] += dr
            sum_abs[1] += dg
            sum_abs[2] += db
            sum_sq[0] += dr * dr
            sum_sq[1] += dg * dg
            sum_sq[2] += db * db
            if dr > max_abs[0]:
                max_abs[0] = dr
            if dg > max_abs[1]:
                max_abs[1] = dg
            if db > max_abs[2]:
                max_abs[2] = db

    mean_abs = [round(x / pixel_count, 4) for x in sum_abs]
    rmse = [round(math.sqrt(x / pixel_count), 4) for x in sum_sq]
    overall_mean = round(sum(sum_abs) / (3 * pixel_count), 4)
    percent_diff = round((differing / pixel_count) * 100, 6)
    return ComparisonResult(
        width=current.width,
        height=current.height,
        differing_pixels=differing,
        pixel_count=pixel_count,
        percent_diff=percent_diff,
        mean_abs_diff_per_channel=mean_abs,
        max_abs_diff_per_channel=max_abs,
        rmse_per_channel=rmse,
        overall_mean_abs_diff=overall_mean,
        crop=crop,
    )


def make_diff_heatmap(current: Image.Image, reference: Image.Image) -> Image.Image:
    # Visualize differences: sum abs diff mapped to yellow-red gradient.
    if current.size != reference.size:
        raise ValueError("Images must be same size for diff heatmap")
    width, height = current.size
    c_pixels = current.load()
    r_pixels = reference.load()
    out = Image.new('RGBA', (width, height))
    o_pixels = out.load()
    max_sum = 0
    sums = []
    for j in range(height):
        row = []
        for i in range(width):
            cr, cg, cb, ca = c_pixels[i, j]
            rr, rg, rb, ra = r_pixels[i, j]
            s = abs(cr - rr) + abs(cg - rg) + abs(cb - rb)
            row.append(s)
            if s > max_sum:
                max_sum = s
        sums.append(row)
    if max_sum == 0:
        return Image.new('RGBA', (width, height), (0, 0, 0, 255))
    for j in range(height):
        for i in range(width):
            s = sums[j][i]
            norm = s / max_sum  # 0..1
            # Map: 0 -> black, mid -> yellow, 1 -> red.
            if norm == 0:
                o_pixels[i, j] = (0, 0, 0, 255)
            else:
                # Interpolate between yellow (255,255,0) and red (255,0,0) by norm.
                r = 255
                g = int(255 * (1 - norm))
                b = 0
                o_pixels[i, j] = (r, g, b, 255)
    return out


def add_label_band(im: Image.Image, text: str, font_size: int, bg: Tuple[int, int, int]) -> Image.Image:
    band_h = font_size + 10
    out = Image.new('RGBA', (im.width, im.height + band_h), (*bg, 255))
    out.paste(im, (0, band_h))
    draw = ImageDraw.Draw(out)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    draw.text((8, 4), text, fill=(0, 0, 0, 255), font=font)
    return out


def make_combined(current: Image.Image, reference: Image.Image, spacing: int, bg: Tuple[int, int, int], label_current: str, label_reference: str, font_size: int) -> Image.Image:
    c_l = add_label_band(current, label_current, font_size, bg)
    r_l = add_label_band(reference, label_reference, font_size, bg)
    target_h = max(c_l.height, r_l.height)
    canvas = Image.new('RGBA', (c_l.width + r_l.width + spacing, target_h), (*bg, 255))
    canvas.paste(c_l, (0, 0), c_l)
    canvas.paste(r_l, (c_l.width + spacing, 0), r_l)
    return canvas


def write_json(path: str, result: ComparisonResult):
    data = {
        'width': result.width,
        'height': result.height,
        'pixel_count': result.pixel_count,
        'differing_pixels': result.differing_pixels,
        'percent_diff': result.percent_diff,
        'mean_abs_diff_per_channel': result.mean_abs_diff_per_channel,
        'max_abs_diff_per_channel': result.max_abs_diff_per_channel,
        'rmse_per_channel': result.rmse_per_channel,
        'overall_mean_abs_diff': result.overall_mean_abs_diff,
    }
    if result.crop:
        data['crop'] = {'x': result.crop[0], 'y': result.crop[1], 'w': result.crop[2], 'h': result.crop[3]}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Metrics JSON written: {path}")


def parse_bg(value: str) -> Tuple[int, int, int]:
    parts = value.split(',')
    if len(parts) != 3:
        raise ValueError("--bg must be R,G,B")
    return tuple(int(p) for p in parts)


def main():
    ap = argparse.ArgumentParser(description='Side-by-side image comparison with metrics and diff heatmap.')
    ap.add_argument('--current', required=True, help='Path to current screenshot')
    ap.add_argument('--reference', required=True, help='Path to reference screenshot')
    ap.add_argument('--out-combined', help='Path to save labeled side-by-side PNG')
    ap.add_argument('--out-diff', help='Path to save diff heatmap PNG')
    ap.add_argument('--out-json', help='Path to write metrics JSON')
    ap.add_argument('--threshold', type=int, default=0, help='Channel diff threshold to count pixel as differing')
    ap.add_argument('--crop', help='x,y,w,h optional crop region for metrics')
    ap.add_argument('--scale-mode', choices=['pad', 'current_to_reference', 'reference_to_current'], default='pad', help='Size reconciliation strategy')
    ap.add_argument('--spacing', type=int, default=12, help='Spacing between images in combined output')
    ap.add_argument('--bg', default='255,255,255', help='Background/padding RGB')
    ap.add_argument('--label-current', default='CURRENT', help='Label text for current image')
    ap.add_argument('--label-reference', default='REFERENCE', help='Label text for reference image')
    ap.add_argument('--font-size', type=int, default=18, help='Font size for labels')
    args = ap.parse_args()

    crop = parse_crop(args.crop)
    bg = parse_bg(args.bg)

    current = load_image(args.current)
    reference = load_image(args.reference)
    current, reference = reconcile_sizes(current, reference, args.scale_mode, bg)

    try:
        metrics = compute_metrics(current, reference, args.threshold, crop)
    except ValueError as e:
        print(f"Metric computation error: {e}", file=sys.stderr)
        sys.exit(3)

    if args.out_combined:
        combined = make_combined(current, reference, args.spacing, bg, args.label_current, args.label_reference, args.font_size)
        combined.convert('RGB').save(args.out_combined, 'PNG')
        print(f"Combined saved: {args.out_combined}")

    if args.out_diff:
        diff_im = make_diff_heatmap(current, reference)
        diff_im.convert('RGB').save(args.out_diff, 'PNG')
        print(f"Diff heatmap saved: {args.out_diff}")

    if args.out_json:
        write_json(args.out_json, metrics)

    # Print summary to stdout for quick glance
    print("--- Image Comparison Summary ---")
    print(f"Dimensions: {metrics.width}x{metrics.height}")
    if metrics.crop:
        print(f"Crop used: {metrics.crop}")
    print(f"Differing pixels: {metrics.differing_pixels} / {metrics.pixel_count} ({metrics.percent_diff:.6f}%)")
    print(f"Mean abs diff (R,G,B): {metrics.mean_abs_diff_per_channel}")
    print(f"RMSE (R,G,B): {metrics.rmse_per_channel}")
    print(f"Overall mean abs diff: {metrics.overall_mean_abs_diff}")


if __name__ == '__main__':
    main()
