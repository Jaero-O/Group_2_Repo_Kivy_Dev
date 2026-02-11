#!/usr/bin/env python3
"""Label-aware splitting of composite reference screenshots.

Adds simple heuristics:
  - Detect candidate vertical or horizontal splits (like original splitter).
  - Extract a label strip from the top of each crop (default 12% of height capped at 100px).
  - Save both crop and label image.
  - Attempt heuristic name inference: fuzzy match of known screen names in average hue clusters of label (placeholder) or using provided manual map file.

Because OCR is not installed, actual text recognition is skipped. Users may
replace label_* images manually with proper names or supply a JSON map.

Optional external mapping:
  Provide --name-map path to JSON: {"label_hash":"screen_name", ...}
  Hash computed as md5 of raw label PNG bytes. This allows later re-use.

Usage:
  python tools/split_reference_sheets_labels.py \
      --current screenshots/current --references screenshots/references \
      --out screenshots/references --min-conf 0.10
"""
import os, sys, json, argparse, hashlib
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict
from PIL import Image, ImageChops

@dataclass
class LabelCropMatch:
    source_file: str
    index: int
    bbox: Tuple[int,int,int,int]
    label_bbox: Tuple[int,int,int,int]
    matched_screen: str
    inferred_screen: str
    percent_diff: float
    confidence: float
    crop_file: str
    label_file: str
    skipped: bool
    reason: str = ''
    label_hash: str = ''

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

def trim_uniform_border(im: Image.Image, tol: int = 3) -> Image.Image:
    """Trim uniform border using the corner pixel as background reference.
    tol: maximum absolute channel difference to treat as background.
    """
    bg = im.getpixel((0,0))
    # Build mask of non-background.
    w, h = im.size
    # Fast path: if already close to target aspect (portrait), skip heavy scan.
    from itertools import product
    min_x, min_y, max_x, max_y = w, h, 0, 0
    bg_r, bg_g, bg_b, bg_a = bg
    pixels = im.load()
    for y in range(h):
        row_has = False
        for x in range(w):
            r,g,b,a = pixels[x,y]
            if abs(r-bg_r) > tol or abs(g-bg_g) > tol or abs(b-bg_b) > tol:
                # treat transparent as content if alpha differs
                if a != bg_a or a > 0:
                    row_has = True
                    if x < min_x: min_x = x
                    if x > max_x: max_x = x
        if row_has:
            if y < min_y: min_y = y
            if y > max_y: max_y = y
    if max_x <= min_x or max_y <= min_y:
        return im  # nothing detected
    # Add small inward margin guard (avoid cropping into UI): none for now.
    return im.crop((min_x, min_y, max_x+1, max_y+1))

def _separator_rows(im: Image.Image, bg, tol: int) -> Tuple[list, list]:
    w,h = im.size
    pixels = im.load()
    bg_r,bg_g,bg_b,bg_a = bg
    non_bg_fraction_per_row = []
    for y in range(h):
        non_bg = 0
        for x in range(w):
            r,g,b,a = pixels[x,y]
            if abs(r-bg_r) > tol or abs(g-bg_g) > tol or abs(b-bg_b) > tol:
                non_bg += 1
        non_bg_fraction_per_row.append(non_bg / w)
    return non_bg_fraction_per_row, []

def _segments_from_projection(vals: list, min_gap: int, min_seg_height: int) -> list:
    segments = []
    h = len(vals)
    inside = False
    start = 0
    gap_count = 0
    for y,v in enumerate(vals):
        if v < 0.002:  # near-empty row treated as gap
            gap_count += 1
            if inside and gap_count >= min_gap:
                # close current segment at previous row
                end = y - gap_count
                if end - start >= min_seg_height:
                    segments.append((start,end))
                inside = False
        else:
            if not inside:
                inside = True
                start = y
            gap_count = 0
    if inside:
        end = h-1
        if end - start >= min_seg_height:
            segments.append((start,end))
    return segments

def choose_split(img: Image.Image, target_wh: Tuple[int,int]) -> List[Tuple[int,int,int,int]]:
    tw, th = target_wh
    w, h = img.size
    candidates = []
    # heuristic grid proposals first (legacy approach)
    for n in range(2,7):
        seg_h = h / n
        if abs(seg_h - th) <= th * 0.5:
            boxes = [(0, int(i*seg_h), w, int((i+1)*seg_h)) for i in range(n)]
            score = sum(abs((bx[3]-bx[1]) - th) for bx in boxes)/n
            candidates.append(('v', score, boxes))
    for n in range(2,7):
        seg_w = w / n
        if abs(seg_w - tw) <= tw * 0.5:
            boxes = [(int(i*seg_w), 0, int((i+1)*seg_w), h) for i in range(n)]
            score = sum(abs((bx[2]-bx[0]) - tw) for bx in boxes)/n
            candidates.append(('h', score, boxes))
    if candidates:
        candidates.sort(key=lambda x: x[1])
        return candidates[0][2]
    # Dynamic projection-based segmentation
    bg = img.getpixel((0,0))
    row_proj,_ = _separator_rows(img, bg, tol=3)
    segs = _segments_from_projection(row_proj, min_gap=8, min_seg_height=int(th*0.4))
    boxes = []
    if len(segs) > 1:
        for (sy,ey) in segs:
            boxes.append((0, sy, w, ey+1))
    else:
        boxes = [(0,0,w,h)]
    # Attempt column split for any overly wide segment
    refined = []
    for (x1,y1,x2,y2) in boxes:
        seg_w = x2 - x1
        seg_h = y2 - y1
        if seg_w > seg_h * 1.3:  # landscape ordering implies possible columns
            # simple two-column attempt
            mid = x1 + seg_w//2
            refined.append((x1,y1,mid,y2))
            refined.append((mid,y1,x2,y2))
        else:
            refined.append((x1,y1,x2,y2))
    return refined

def md5_bytes(im: Image.Image) -> str:
    import io
    buf = io.BytesIO()
    im.save(buf, format='PNG')
    return hashlib.md5(buf.getvalue()).hexdigest()

def infer_screen_from_label_hash(label_hash: str, name_map: Dict[str,str]) -> str:
    return name_map.get(label_hash,'')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--current', default='screenshots/current')
    ap.add_argument('--references', default='screenshots/references')
    ap.add_argument('--out', default='screenshots/references')
    ap.add_argument('--min-conf', type=float, default=0.10)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--mapping-output', default='label_split_mapping.json')
    ap.add_argument('--name-map', help='JSON file mapping label_hash -> screen_name', default='')
    args = ap.parse_args()

    name_map = {}
    if args.name_map and os.path.exists(args.name_map):
        try:
            name_map = json.load(open(args.name_map,'r'))
        except Exception as e:
            print(f"WARN: failed loading name-map: {e}", file=sys.stderr)

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
    widths.sort(); heights.sort()
    tw = widths[len(widths)//2]; th = heights[len(heights)//2]
    target_wh = (tw, th)

    ref_files = [f for f in os.listdir(args.references) if f.lower().endswith('.png')]
    results: List[LabelCropMatch] = []
    for rf in ref_files:
        base_norm = normalize_name(rf)
        if base_norm in current_images:
            continue  # Already a single-screen reference.
        ref_path = os.path.join(args.references, rf)
        try:
            sheet = load_image(ref_path)
        except Exception as e:
            results.append(LabelCropMatch(source_file=rf, index=-1, bbox=(0,0,0,0), label_bbox=(0,0,0,0), matched_screen='', inferred_screen='', percent_diff=1.0, confidence=0.0, crop_file='', label_file='', skipped=True, reason=f'load failed: {e}'))
            continue
        # First trim uniform outer border to reduce noise before splitting.
        sheet_trimmed = trim_uniform_border(sheet)
        boxes = choose_split(sheet_trimmed, target_wh)
        for idx, box in enumerate(boxes):
            x1,y1,x2,y2 = box
            crop = sheet_trimmed.crop(box)
            # Trim border per crop as well.
            crop = trim_uniform_border(crop)
            # Label region heuristics
            label_h = min(int((y2 - y1) * 0.12), 100)  # 12% or 100px
            label_box = (0,0,(x2 - x1), label_h)
            label_img = crop.crop(label_box)
            label_hash = md5_bytes(label_img)
            inferred = infer_screen_from_label_hash(label_hash, name_map)

            # Match by visual diff regardless of inference
            best_screen=''
            best_pd=1.0
            for screen_name, cur_img in current_images.items():
                pd = percent_diff(crop, cur_img)
                if pd < best_pd:
                    best_pd = pd; best_screen = screen_name
            conf = 1 - best_pd
            skipped=False; reason=''
            crop_filename=''
            label_filename=''
            target_screen = inferred or best_screen
            if target_screen and (conf >= args.min_conf or args.force):
                crop_filename = f"{target_screen}.png"
                out_crop = os.path.join(args.out, crop_filename)
                if os.path.exists(out_crop):
                    crop_filename = f"{target_screen}_labelcrop{idx}.png"
                    out_crop = os.path.join(args.out, crop_filename)
                try:
                    crop.save(out_crop)
                except Exception as e:
                    skipped=True; reason=f'crop save failed: {e}'
                label_filename = f"label_{target_screen}_{idx}.png"
                try:
                    label_img.save(os.path.join(args.out, label_filename))
                except Exception:
                    pass
            else:
                skipped=True; reason='low confidence'
                crop_filename = f"unmatched_{base_norm}_{idx}.png"
                label_filename = f"label_unmatched_{base_norm}_{idx}.png"
                try:
                    crop.save(os.path.join(args.out, crop_filename))
                    label_img.save(os.path.join(args.out, label_filename))
                except Exception:
                    pass
            results.append(LabelCropMatch(source_file=rf, index=idx, bbox=box, label_bbox=label_box, matched_screen=best_screen, inferred_screen=inferred, percent_diff=best_pd, confidence=conf, crop_file=crop_filename, label_file=label_filename, skipped=skipped, reason=reason, label_hash=label_hash))

    summary = {'target_wh': target_wh, 'min_conf': args.min_conf, 'matches':[asdict(r) for r in results]}
    out_map = os.path.join(args.out, args.mapping_output)
    with open(out_map,'w') as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
