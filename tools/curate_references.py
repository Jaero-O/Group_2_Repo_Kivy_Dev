#!/usr/bin/env python3
"""Curate a final canonical set of reference screenshots.

Logic:
  1. Load current screenshots from --current (default screenshots/current).
  2. Load all reference candidate PNGs from --references.
  3. Normalize current filenames by stripping trailing digits.
  4. For each current screen name, compute raw percent pixel diff against every
     candidate reference image (resize candidate to current size if needed).
  5. Select the candidate with minimum percent_diff as the canonical reference.
  6. Save (copy) / overwrite canonical file as <screen>.png in the references directory.
  7. Optionally prune: remove leftover candidate files not chosen (segmented *_seg* etc.).
  8. Emit JSON manifest summarizing chosen references and diff metrics.

Notes:
  - This is purely pixel-diff based; high diff values may indicate style/size mismatch.
  - You can re-run after improving UI parity to regenerate cleaner references.

Usage:
  python tools/curate_references.py --current screenshots/current --references screenshots/references --out screenshots/references --prune
"""
import os, sys, json, argparse, shutil
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
from PIL import Image, ImageChops

@dataclass
class Choice:
    screen: str
    candidate_file: str
    percent_diff: float
    width: int
    height: int
    saved_path: str

def load_image(path: str) -> Image.Image:
    return Image.open(path).convert('RGBA')

def normalize_current_filename(base: str) -> str:
    name = os.path.splitext(os.path.basename(base))[0]
    i = len(name) - 1
    while i >= 0 and name[i].isdigit():
        i -= 1
    if i < len(name) - 1:
        name = name[:i+1]
    return name.lower()

def percent_diff(a: Image.Image, b: Image.Image) -> float:
    if a.size != b.size:
        b = b.resize(a.size, Image.LANCZOS)
    diff = ImageChops.difference(a,b).getdata()
    differing = sum(1 for px in diff if px[0] or px[1] or px[2] or px[3])
    return differing / len(diff) if diff else 1.0

def collect_current(current_dir: str) -> Dict[str, str]:
    mapping = {}
    for f in os.listdir(current_dir):
        if f.lower().endswith('.png'):
            norm = normalize_current_filename(f)
            mapping[norm] = os.path.join(current_dir, f)
    return mapping

def collect_candidates(ref_dir: str) -> List[str]:
    return [os.path.join(ref_dir,f) for f in os.listdir(ref_dir) if f.lower().endswith('.png')]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--current', default='screenshots/current')
    ap.add_argument('--references', default='screenshots/references')
    ap.add_argument('--out', default='screenshots/references')
    ap.add_argument('--manifest', default='curated_references.json')
    ap.add_argument('--prune', action='store_true', help='Remove unused candidate reference files after curation.')
    args = ap.parse_args()

    if not os.path.isdir(args.current):
        print(f'ERROR: current dir missing: {args.current}', file=sys.stderr); sys.exit(2)
    if not os.path.isdir(args.references):
        print(f'ERROR: references dir missing: {args.references}', file=sys.stderr); sys.exit(3)

    current = collect_current(args.current)
    if not current:
        print('ERROR: no current screenshots found', file=sys.stderr); sys.exit(4)
    candidates = collect_candidates(args.references)
    if not candidates:
        print('ERROR: no reference candidates found', file=sys.stderr); sys.exit(5)

    # Pre-load candidate images to avoid repeated IO.
    candidate_images = {}
    for cpath in candidates:
        try:
            candidate_images[cpath] = load_image(cpath)
        except Exception as e:
            print(f'WARN: failed loading candidate {cpath}: {e}', file=sys.stderr)

    choices: List[Choice] = []
    chosen_files = set()
    for screen, cur_path in current.items():
        try:
            cur_img = load_image(cur_path)
        except Exception as e:
            print(f'WARN: skip screen {screen}, load failed: {e}', file=sys.stderr); continue
        best_file = ''
        best_pd = 1.0
        best_img = None
        for cpath, cimg in candidate_images.items():
            pd = percent_diff(cur_img, cimg)
            if pd < best_pd:
                best_pd = pd
                best_file = cpath
                best_img = cimg
        if not best_file:
            continue
        # Save canonical reference
        canonical_name = f'{screen}.png'
        out_path = os.path.join(args.out, canonical_name)
        try:
            # Overwrite with best candidate representation
            if best_img is not None:
                # Resize candidate to current size for direct comparison baseline
                if best_img.size != cur_img.size:
                    best_img = best_img.resize(cur_img.size, Image.LANCZOS)
                best_img.save(out_path)
            else:
                shutil.copy2(best_file, out_path)
            chosen_files.add(os.path.abspath(best_file))
            choices.append(Choice(screen=screen, candidate_file=os.path.basename(best_file), percent_diff=best_pd,
                                   width=cur_img.width, height=cur_img.height, saved_path=out_path))
        except Exception as e:
            print(f'WARN: failed saving canonical for {screen}: {e}', file=sys.stderr)

    # Optional prune: delete any candidate not used that is a segmentation artifact
    pruned = []
    if args.prune:
        for cpath in candidates:
            abs_c = os.path.abspath(cpath)
            base = os.path.basename(cpath).lower()
            if abs_c in chosen_files:
                continue
            # Heuristic: remove files containing `_seg` or starting with 'screenshot '
            if '_seg' in base or base.startswith('screenshot'):
                try:
                    os.remove(cpath)
                    pruned.append(base)
                except Exception as e:
                    print(f'WARN: failed pruning {base}: {e}', file=sys.stderr)

    summary = {
        'total_screens': len(current),
        'curated': [asdict(c) for c in choices],
        'missing': [s for s in current.keys() if not any(c.screen==s for c in choices)],
        'pruned': pruned
    }
    with open(os.path.join(args.out, args.manifest),'w') as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
