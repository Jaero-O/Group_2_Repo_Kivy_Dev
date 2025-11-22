#!/usr/bin/env python3
"""Extract central white card from screenshots and perform focused comparison.

Usage:
  python tools/extract_card_and_compare.py \
      --current screenshots/current_result0001.png \
      --reference screenshots/image.png \
      --out-dir screenshots

Outputs in out-dir:
  card_current.png            Cropped current card
  card_reference_scaled.png   Cropped + scaled reference card
  card_side_by_side.png       Labeled side-by-side composite
  card_diff_heatmap.png       Heatmap of pixel differences
  card_metrics.json           Metrics JSON (same fields as compare_images)

Detection heuristic:
  Finds bounding box of pixels where R,G,B >= WHITE_MIN (default 235) and
  alpha > 200, then selects largest area cluster approximated by simple bbox.
  Assumes a single dominant white card on darker background.

Limitations:
  Rounded corners / subtle gradients still treated as white. For multi-card
  layouts supply --manual-crop.
"""

import argparse
import json
import math
import sys
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

WHITE_MIN = 235


def load_rgba(path: str) -> Image.Image:
    try:
        return Image.open(path).convert('RGBA')
    except Exception as e:
        print(f"Failed to load {path}: {e}", file=sys.stderr)
        sys.exit(2)


def detect_card(im: Image.Image) -> Tuple[int, int, int, int]:
    pixels = im.load()
    w, h = im.size
    min_x, min_y = w, h
    max_x, max_y = 0, 0
    count = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a > 200 and r >= WHITE_MIN and g >= WHITE_MIN and b >= WHITE_MIN:
                count += 1
                if x < min_x: min_x = x
                if y < min_y: min_y = y
                if x > max_x: max_x = x
                if y > max_y: max_y = y
    if count == 0:
        raise RuntimeError("No white card detected. Adjust WHITE_MIN or provide manual crop.")
    # Add small padding shrink to remove outer glow/shadow if any
    pad = 2
    min_x = max(0, min_x + pad)
    min_y = max(0, min_y + pad)
    max_x = min(w - 1, max_x - pad)
    max_y = min(h - 1, max_y - pad)
    return min_x, min_y, max_x - min_x + 1, max_y - min_y + 1


def crop(im: Image.Image, box: Tuple[int, int, int, int]) -> Image.Image:
    x, y, w, h = box
    return im.crop((x, y, x + w, y + h))


def scale_to_width(im: Image.Image, width: int) -> Image.Image:
    if im.width == width:
        return im
    ratio = width / im.width
    height = int(im.height * ratio)
    return im.resize((width, height), Image.LANCZOS)


def compute_metrics(a: Image.Image, b: Image.Image) -> dict:
    if a.size != b.size:
        raise ValueError("Images must have same size for metrics")
    w, h = a.size
    pa = a.load(); pb = b.load()
    differing = 0
    pixel_count = w * h
    sum_abs = [0, 0, 0]
    sum_sq = [0, 0, 0]
    max_abs = [0, 0, 0]
    for y in range(h):
        for x in range(w):
            ar, ag, ab, aa = pa[x, y]
            br, bg, bb, ba = pb[x, y]
            dr = abs(ar - br)
            dg = abs(ag - bg)
            db = abs(ab - bb)
            if dr or dg or db:
                differing += 1
            sum_abs[0] += dr; sum_abs[1] += dg; sum_abs[2] += db
            sum_sq[0] += dr * dr; sum_sq[1] += dg * dg; sum_sq[2] += db * db
            if dr > max_abs[0]: max_abs[0] = dr
            if dg > max_abs[1]: max_abs[1] = dg
            if db > max_abs[2]: max_abs[2] = db
    mean_abs = [round(v / pixel_count, 4) for v in sum_abs]
    rmse = [round(math.sqrt(v / pixel_count), 4) for v in sum_sq]
    overall_mean = round(sum(sum_abs) / (3 * pixel_count), 4)
    percent_diff = round(differing / pixel_count * 100, 6)
    return {
        'width': w,
        'height': h,
        'pixel_count': pixel_count,
        'differing_pixels': differing,
        'percent_diff': percent_diff,
        'mean_abs_diff_per_channel': mean_abs,
        'max_abs_diff_per_channel': max_abs,
        'rmse_per_channel': rmse,
        'overall_mean_abs_diff': overall_mean,
    }


def diff_heatmap(a: Image.Image, b: Image.Image) -> Image.Image:
    if a.size != b.size:
        raise ValueError("Images must have same size")
    w, h = a.size
    pa = a.load(); pb = b.load()
    out = Image.new('RGBA', (w, h))
    po = out.load()
    max_sum = 0
    sums = [[0]*w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            ar, ag, ab, aa = pa[x, y]
            br, bg, bb, ba = pb[x, y]
            s = abs(ar - br) + abs(ag - bg) + abs(ab - bb)
            sums[y][x] = s
            if s > max_sum: max_sum = s
    if max_sum == 0:
        return Image.new('RGBA', (w, h), (0,0,0,255))
    for y in range(h):
        for x in range(w):
            s = sums[y][x]
            if s == 0:
                po[x, y] = (0,0,0,255)
            else:
                norm = s / max_sum
                r = 255
                g = int(255 * (1 - norm))
                b = 0
                po[x, y] = (r, g, b, 255)
    return out


def label(im: Image.Image, text: str) -> Image.Image:
    band = 26
    canvas = Image.new('RGBA', (im.width, im.height + band), (255,255,255,255))
    canvas.paste(im, (0, band))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype('arial.ttf', 16)
    except Exception:
        font = ImageFont.load_default()
    draw.text((6,4), text, fill=(0,0,0,255), font=font)
    return canvas


def side_by_side(a_lab: Image.Image, b_lab: Image.Image) -> Image.Image:
    h = max(a_lab.height, b_lab.height)
    spacing = 12
    out = Image.new('RGBA', (a_lab.width + b_lab.width + spacing, h), (255,255,255,255))
    out.paste(a_lab, (0,0), a_lab)
    out.paste(b_lab, (a_lab.width + spacing, 0), b_lab)
    return out


def main():
    ap = argparse.ArgumentParser(description='Crop card region and compare.')
    ap.add_argument('--current', required=True)
    ap.add_argument('--reference', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--manual-crop-ref', help='Manual crop for reference x,y,w,h')
    ap.add_argument('--manual-crop-cur', help='Manual crop for current x,y,w,h')
    ap.add_argument('--scale-to', choices=['current','reference'], default='current', help='Which width to scale to')
    args = ap.parse_args()

    cur = load_rgba(args.current)
    ref = load_rgba(args.reference)

    if args.manual_crop_cur:
        x,y,w,h = map(int, args.manual_crop_cur.split(','))
        card_cur_box = (x,y,w,h)
    else:
        card_cur_box = detect_card(cur)

    if args.manual_crop_ref:
        x,y,w,h = map(int, args.manual_crop_ref.split(','))
        card_ref_box = (x,y,w,h)
    else:
        try:
            card_ref_box = detect_card(ref)
        except RuntimeError:
            # fallback to full image
            card_ref_box = (0,0,ref.width,ref.height)

    cur_card = crop(cur, card_cur_box)
    ref_card = crop(ref, card_ref_box)

    if args.scale_to == 'current':
        ref_card_scaled = scale_to_width(ref_card, cur_card.width)
        cur_scaled = cur_card
    else:
        cur_scaled = scale_to_width(cur_card, ref_card.width)
        ref_card_scaled = ref_card

    # Equalize heights by padding shorter one to align bottom
    max_h = max(cur_scaled.height, ref_card_scaled.height)
    def pad_h(im):
        if im.height == max_h: return im
        canvas = Image.new('RGBA', (im.width, max_h), (255,255,255,255))
        canvas.paste(im, (0,0))
        return canvas
    cur_final = pad_h(cur_scaled)
    ref_final = pad_h(ref_card_scaled)

    if cur_final.size != ref_final.size:
        # pad width if mismatch due to rounding
        max_w = max(cur_final.width, ref_final.width)
        def pad_w(im):
            if im.width == max_w: return im
            canvas = Image.new('RGBA', (max_w, im.height), (255,255,255,255))
            canvas.paste(im, (0,0))
            return canvas
        cur_final = pad_w(cur_final)
        ref_final = pad_w(ref_final)

    metrics = compute_metrics(cur_final, ref_final)
    heat = diff_heatmap(cur_final, ref_final)
    side = side_by_side(label(cur_final, 'CURRENT CARD'), label(ref_final, 'REFERENCE CARD'))

    out_dir = args.out_dir.rstrip('/\\')
    (cur_card.convert('RGB')).save(f'{out_dir}/card_current.png')
    (ref_card.convert('RGB')).save(f'{out_dir}/card_reference.png')
    (ref_final.convert('RGB')).save(f'{out_dir}/card_reference_scaled.png')
    side.convert('RGB').save(f'{out_dir}/card_side_by_side.png')
    heat.convert('RGB').save(f'{out_dir}/card_diff_heatmap.png')
    with open(f'{out_dir}/card_metrics.json','w',encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)

    print('Card current box:', card_cur_box)
    print('Card reference box:', card_ref_box)
    print('Metrics:', json.dumps(metrics, indent=2))

if __name__ == '__main__':
    main()
