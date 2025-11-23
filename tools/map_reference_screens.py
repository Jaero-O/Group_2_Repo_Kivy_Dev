#!/usr/bin/env python3
"""Map unnormalized reference screenshots to screen names by pixel diff.

Workflow:
  1. Capture current screens using AUTO_CAPTURE_ALL_SCREENS=1 (names derived
     from ScreenManager). Stored e.g. in screenshots/current/<screen>.png
  2. Place raw reference images (e.g. "Screenshot 2025-11-19 062603.png") in
     screenshots/references.
  3. Run this tool to compute diff for each reference against all current.
     It chooses the lowest percent_diff and reports mapping.
  4. With --apply it renames each reference file to <best_screen>.png
     (if target exists it appends _refN.png to avoid overwrites).

Usage:
  python tools/map_reference_screens.py --current screenshots/current \
      --references screenshots/references --output ref_mapping.json --apply

Notes:
  - Uses raw pixel diff (RGBA). If sizes differ current is resized to reference.
  - A confidence score is (1 - percent_diff). Low confidence (< min_conf) will
    skip rename unless --force provided.
"""
import os, sys, json, argparse
from dataclasses import dataclass, asdict
from typing import List, Tuple
from PIL import Image, ImageChops

@dataclass
class MappingResult:
    reference_file: str
    best_screen: str
    percent_diff: float
    confidence: float
    skipped: bool
    reason: str

def load_image(path: str) -> Image.Image:
    return Image.open(path).convert('RGBA')

def resize_like(a: Image.Image, b: Image.Image) -> Image.Image:
    if a.size == b.size:
        return a
    return a.resize(b.size, Image.LANCZOS)

def percent_diff(a: Image.Image, b: Image.Image) -> float:
    a = resize_like(a, b)
    diff = ImageChops.difference(a, b).getdata()
    total = len(diff)
    differing = 0
    for r,g,bl,a_ in diff:  # unpack RGBA
        if r or g or bl or a_:
            differing += 1
    return differing / total if total else 1.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--current', default='screenshots/current')
    ap.add_argument('--references', default='screenshots/references')
    ap.add_argument('--output', default='ref_mapping.json')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--min-conf', type=float, default=0.30, help='Minimum confidence (1 - percent_diff) required to rename.')
    ap.add_argument('--force', action='store_true', help='Rename even if confidence below threshold.')
    args = ap.parse_args()

    if not os.path.isdir(args.current):
        print(f"ERROR: current directory missing: {args.current}", file=sys.stderr)
        sys.exit(2)
    if not os.path.isdir(args.references):
        print(f"ERROR: references directory missing: {args.references}", file=sys.stderr)
        sys.exit(3)

    current_pngs = [f for f in os.listdir(args.current) if f.lower().endswith('.png')]
    reference_pngs = [f for f in os.listdir(args.references) if f.lower().endswith('.png')]

    # Load current images once
    current_images = {}
    for f in current_pngs:
        try:
            img = load_image(os.path.join(args.current, f))
            screen_name = os.path.splitext(f)[0]
            current_images[screen_name] = img
        except Exception as e:
            print(f"WARN: Failed loading current {f}: {e}", file=sys.stderr)

    results: List[MappingResult] = []
    for ref_file in reference_pngs:
        base_name = os.path.splitext(ref_file)[0].lower()
        # Skip if already normalized to an existing screen name
        if base_name in current_images:
            results.append(MappingResult(reference_file=ref_file, best_screen=base_name, percent_diff=0.0, confidence=1.0, skipped=True, reason='Already normalized name'))
            continue
        ref_path = os.path.join(args.references, ref_file)
        try:
            ref_img = load_image(ref_path)
        except Exception as e:
            results.append(MappingResult(reference_file=ref_file, best_screen='', percent_diff=1.0, confidence=0.0, skipped=True, reason=f'Failed to load: {e}'))
            continue
        best_screen = ''
        best_pd = 1.0
        for screen_name, cur_img in current_images.items():
            pd = percent_diff(cur_img, ref_img)
            if pd < best_pd:
                best_pd = pd
                best_screen = screen_name
        conf = 1 - best_pd
        skipped = False
        reason = ''
        if not best_screen:
            skipped = True
            reason = 'No candidates'
        elif conf < args.min_conf and not args.force:
            skipped = True
            reason = f'Low confidence {conf:.3f} < {args.min_conf}'
        else:
            # Apply rename if requested
            if args.apply:
                target_base = best_screen + '.png'
                target_path = os.path.join(args.references, target_base)
                if os.path.exists(target_path):
                    # Find unique suffix
                    i = 2
                    while True:
                        alt = os.path.join(args.references, f"{best_screen}_ref{i}.png")
                        if not os.path.exists(alt):
                            target_path = alt
                            break
                        i += 1
                try:
                    os.rename(ref_path, target_path)
                except Exception as e:
                    skipped = True
                    reason = f'Rename failed: {e}'
        results.append(MappingResult(reference_file=ref_file, best_screen=best_screen, percent_diff=best_pd, confidence=conf, skipped=skipped, reason=reason))

    summary = {'results':[asdict(r) for r in results], 'min_conf': args.min_conf}
    with open(args.output,'w') as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
