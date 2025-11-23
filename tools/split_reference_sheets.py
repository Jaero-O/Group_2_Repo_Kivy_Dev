#!/usr/bin/env python3
"""Split composite reference screenshots into individual screen images and map them.

Heuristics:
  - Current captured screens live in screenshots/current with names like scan0001.png
  - We normalize current names by stripping trailing digits (scan0001 -> scan)
  - Reference composite images may contain multiple screens stacked vertically or horizontally.
  - We infer layout by checking divisors of width and height against the target aspect ratio of current images.

Process:
  1. Load all current images; determine their (median) aspect ratio.
  2. For each reference image not already normalized (e.g. 'result.png' is skipped):
     a. Try vertical split: for n in 2..6 if height/n close to target_height.
     b. Try horizontal split: for n in 2..6 if width/n close to target_width.
     c. Choose the split producing crops whose aspect ratios most closely match target.
     d. If no good candidate, fallback to whole image.
  3. For each crop, compute pixel diff to every current image; pick best (lowest percent diff).
  4. If confidence (1 - percent_diff) >= min_conf, write crop as <best_screen>.png into output directory.
     Otherwise write as unmatched_<original>_<index>.png for manual review.
  5. Emit JSON mapping file.

Usage:
  python tools/split_reference_sheets.py \
      --current screenshots/current \
      --references screenshots/references \
      --out screenshots/references \
      --min-conf 0.15

Notes:
  - Resizes current candidate to crop size before diff.
  - Confidence threshold default is low due to large style differences.
"""
import os, sys, json, argparse
from dataclasses import dataclass, asdict
from typing import List, Tuple
from PIL import Image, ImageChops

@dataclass
class CropMatch:
    source_file: str
    index: int
    bbox: Tuple[int,int,int,int]
    matched_screen: str
    percent_diff: float
    confidence: float
    saved_as: str
    skipped: bool
    reason: str = ''

def load_image(path: str) -> Image.Image:
    return Image.open(path).convert('RGBA')

def normalize_name(fname: str) -> str:
    base = os.path.splitext(os.path.basename(fname))[0]
    i = len(base) - 1
    while i >= 0 and base[i].isdigit():
        i -= 1
    if i < len(base) - 1:
        base = base[:i+1]
    return base.lower()

def percent_diff(a: Image.Image, b: Image.Image) -> float:
    if a.size != b.size:
        b = b.resize(a.size, Image.LANCZOS)
    diff = ImageChops.difference(a, b).getdata()
    differing = sum(1 for px in diff if px[0] or px[1] or px[2] or px[3])
    return differing / len(diff) if diff else 1.0

def choose_split(img: Image.Image, target_wh: Tuple[int,int]) -> List[Tuple[int,int,int,int]]:
    tw, th = target_wh
    w, h = img.size
    candidates = []
    # vertical stacking
    for n in range(2,7):
        seg_h = h / n
        if abs(seg_h - th) <= th * 0.4:  # 40% tolerance
            boxes = [(0, int(i*seg_h), w, int((i+1)*seg_h)) for i in range(n)]
            score = sum(abs((bx[3]-bx[1]) - th) for bx in boxes)/n
            candidates.append(('v', score, boxes))
    # horizontal stacking
    for n in range(2,7):
        seg_w = w / n
        if abs(seg_w - tw) <= tw * 0.4:
            boxes = [(int(i*seg_w), 0, int((i+1)*seg_w), h) for i in range(n)]
            score = sum(abs((bx[2]-bx[0]) - tw) for bx in boxes)/n
            candidates.append(('h', score, boxes))
    if not candidates:
        return [(0,0,w,h)]
    candidates.sort(key=lambda x: x[1])
    return candidates[0][2]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--current', default='screenshots/current')
    ap.add_argument('--references', default='screenshots/references')
    ap.add_argument('--out', default='screenshots/references')
    ap.add_argument('--min-conf', type=float, default=0.15)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--mapping-output', default='split_mapping.json')
    args = ap.parse_args()

    if not os.path.isdir(args.current):
        print(f"ERROR: current directory missing: {args.current}", file=sys.stderr); sys.exit(2)
    if not os.path.isdir(args.references):
        print(f"ERROR: references directory missing: {args.references}", file=sys.stderr); sys.exit(3)
    os.makedirs(args.out, exist_ok=True)

    current_files = [f for f in os.listdir(args.current) if f.lower().endswith('.png')]
    current_images = {}
    widths = []
    heights = []
    for f in current_files:
        try:
            img = load_image(os.path.join(args.current, f))
            nm = normalize_name(f)
            current_images[nm] = img
            widths.append(img.width); heights.append(img.height)
        except Exception as e:
            print(f"WARN: failed loading current {f}: {e}", file=sys.stderr)
    if not widths:
        print("ERROR: no current images loaded", file=sys.stderr); sys.exit(4)
    # Use median dimensions as target
    widths.sort(); heights.sort()
    tw = widths[len(widths)//2]; th = heights[len(heights)//2]
    target_wh = (tw, th)

    ref_files = [f for f in os.listdir(args.references) if f.lower().endswith('.png')]
    results: List[CropMatch] = []
    for rf in ref_files:
        base_norm = normalize_name(rf)
        # Skip already normalized single-screen references
        if base_norm in current_images:
            continue
        ref_path = os.path.join(args.references, rf)
        try:
            sheet = load_image(ref_path)
        except Exception as e:
            results.append(CropMatch(source_file=rf, index=-1, bbox=(0,0,0,0), matched_screen='', percent_diff=1.0, confidence=0.0, saved_as='', skipped=True, reason=f'load failed: {e}'))
            continue
        boxes = choose_split(sheet, target_wh)
        for idx, box in enumerate(boxes):
            x1,y1,x2,y2 = box
            crop = sheet.crop(box)
            # Compare to each current image
            best_screen=''
            best_pd=1.0
            for screen_name, cur_img in current_images.items():
                pd = percent_diff(crop, cur_img)
                if pd < best_pd:
                    best_pd = pd; best_screen = screen_name
            conf = 1 - best_pd
            skipped=False; reason=''
            filename=''
            if best_screen and (conf >= args.min_conf or args.force):
                # Save crop
                filename = f"{best_screen}.png"
                out_path = os.path.join(args.out, filename)
                # Avoid overwrite if file exists and differs significantly
                if os.path.exists(out_path):
                    filename = f"{best_screen}_crop{idx}.png"
                    out_path = os.path.join(args.out, filename)
                try:
                    crop.save(out_path)
                except Exception as e:
                    skipped=True; reason=f'save failed: {e}'
            else:
                skipped=True; reason='low confidence'
                filename = f"unmatched_{base_norm}_{idx}.png"
                try:
                    crop.save(os.path.join(args.out, filename))
                except Exception:
                    pass
            results.append(CropMatch(source_file=rf, index=idx, bbox=box, matched_screen=best_screen, percent_diff=best_pd, confidence=conf, saved_as=filename, skipped=skipped, reason=reason))

    summary = {'target_wh': target_wh, 'min_conf': args.min_conf, 'matches':[asdict(r) for r in results]}
    out_map = os.path.join(args.out, args.mapping_output)
    with open(out_map,'w') as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
