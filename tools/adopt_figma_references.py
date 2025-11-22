#!/usr/bin/env python3
"""Adopt newest Figma-provided screens as canonical references.

Steps:
- Detect likely Figma assets by last-modified time and filename patterns.
- Map Figma filenames to canonical app screen names.
- Copy/rename selected Figma images into the references directory as <screen>.png.
- Remove any other PNGs in references not in the adopted set (keeping JSON manifests).

Usage:
  python tools/adopt_figma_references.py \
    --references screenshots/references \
    --figma-dir screenshots/references_figma
"""
import os, sys, argparse, shutil, json
from datetime import datetime, timedelta


CANONICAL_SCREENS = [
    'about_us','anthracnose','guide','help','home','image_selection','loading',
    'precaution','records','result','save','scan','scanning','share','system_spec','welcome'
]

# Mapping of substring in Figma filename (lower) to canonical screen name
SUBSTRING_MAP = [
    ('about us screen', 'about_us'),
    ('anthracnose disease screen', 'anthracnose'),
    ('guidelines and precautions screen', 'precaution'),
    ('system specification screen', 'system_spec'),
    ('share screen', 'share'),
    ('help screen', 'help'),
    ('image selection screen', 'image_selection'),
    ('records screen', 'records'),
    ('save capture screen', 'save'),
    ('scanning screen', 'scanning'),
    ('scan screen', 'scan'),
    ('home screen', 'home'),
    ('first screen', 'welcome'),
    ('result', 'result'),  # capture/full result
]

EXCLUDE_SUBSTRINGS = [
    'vector', 'rectangle', 'icon', 'mdi_', 'material-symbols', 'group ', 'artboard', 'qr-code', 'browser-error', 'software-platform', 'files-icon', 'question-mark', 'leaf-icon', '(stroke)', 'back.png'
]

def is_likely_figma_screen(name: str) -> bool:
    n = name.lower()
    if any(s in n for s in EXCLUDE_SUBSTRINGS):
        return False
    # Prefer obvious screen keywords
    return 'screen' in n or n == 'result.png' or n == 'home.png'

def map_figma_to_canonical(name: str) -> str:
    n = name.lower()
    for sub, canon in SUBSTRING_MAP:
        if sub in n:
            return canon
    return ''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--references', default='screenshots/references')
    ap.add_argument('--figma-dir', default='screenshots/references_figma')
    ap.add_argument('--lookback-mins', type=int, default=120, help='Consider files modified within this many minutes as Figma additions.')
    ap.add_argument('--manifest', default='adopted_figma.json')
    args = ap.parse_args()

    os.makedirs(args.figma_dir, exist_ok=True)
    if not os.path.isdir(args.references):
        print(f'ERROR: references dir missing: {args.references}', file=sys.stderr); sys.exit(2)

    now = datetime.now()
    cutoff = now - timedelta(minutes=args.lookback_mins)

    # Gather figma candidates either from figma_dir or directly from references by time window
    candidates = []
    src_dir = args.figma_dir if os.listdir(args.figma_dir) else args.references
    for f in os.listdir(src_dir):
        if not f.lower().endswith('.png'):
            continue
        p = os.path.join(src_dir, f)
        ts = datetime.fromtimestamp(os.path.getmtime(p))
        if ts >= cutoff or src_dir != args.references:
            candidates.append((f, p, ts))

    # Filter to likely screen images
    candidates = [c for c in candidates if is_likely_figma_screen(c[0])]
    if not candidates:
        print('ERROR: No Figma screen candidates found. Adjust lookback or verify uploads.', file=sys.stderr)
        sys.exit(3)

    # Choose best per canonical name (latest timestamp wins if multiple)
    chosen = {}
    extras_for_guide = []
    for fname, path, ts in candidates:
        canon = map_figma_to_canonical(fname)
        if not canon:
            continue
        if canon == 'precaution':
            # Also use the same image for 'guide' if no dedicated Guide screen provided
            extras_for_guide.append((fname, path, ts))
        prev = chosen.get(canon)
        if not prev or ts > prev['ts']:
            chosen[canon] = {'src': path, 'name': fname, 'ts': ts}

    if 'guide' not in chosen and extras_for_guide:
        # Duplicate precaution for guide if missing
        pick = sorted(extras_for_guide, key=lambda x: x[2], reverse=True)[0]
        chosen['guide'] = {'src': pick[1], 'name': pick[0], 'ts': pick[2]}

    # Copy/rename into references
    adopted = []
    for canon, meta in chosen.items():
        dst = os.path.join(args.references, f'{canon}.png')
        shutil.copy2(meta['src'], dst)
        adopted.append({'screen': canon, 'source_file': os.path.basename(meta['src']), 'saved_as': os.path.basename(dst), 'timestamp': meta['ts'].isoformat()})

    # Prune other PNGs in references not adopted
    adopted_basenames = set([f"{a['screen']}.png" for a in adopted])
    for f in os.listdir(args.references):
        if f.lower().endswith('.png') and f not in adopted_basenames:
            try:
                os.remove(os.path.join(args.references, f))
            except Exception:
                pass

    summary = {
        'adopted': adopted,
        'final_files': sorted(list(adopted_basenames)),
    }
    with open(os.path.join(args.references, args.manifest),'w') as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
