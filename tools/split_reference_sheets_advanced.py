#!/usr/bin/env python3
"""Advanced border-to-border multi-screen splitter.

Goals:
  - Reset composite reference screenshots into individual screen crops.
  - Detect vertical (stacked) and horizontal (side-by-side) screen groupings.
  - Trim uniform outer border precisely (background color by majority of edge pixels).
  - Extract each screen from border to border (no padding retained).
  - Optionally attempt best-match naming vs current screenshots using pixel diff.

Usage:
  python tools/split_reference_sheets_advanced.py \
      --current screenshots/current --references screenshots/references --out screenshots/references \
      --min-width 300 --min-height 300 --assign-names

Heuristics:
  1. Background color is determined from edge sample (corners + midpoints). Mode used as bg.
  2. Row projection: fraction of non-bg pixels per row. Continuous runs above threshold form vertical segments.
  3. Each vertical segment undergoes column projection to find low-content separator columns.
  4. Within each cell we perform precise border trimming (top/bottom/left/right) to exclude residual background.
  5. If --assign-names, each crop is compared to current screen captures; if percent diff < 0.98 we adopt that name else a generic base+index name.

Outputs:
  - Cropped PNGs saved to --out.
  - JSON summary mapping: advanced_split_mapping.json.

Limitations:
  - Assumes composite background uniform.
  - Highly overlapping / stylized separators may reduce accuracy.
"""
import os, sys, json, argparse
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict
from collections import Counter
from PIL import Image, ImageChops

@dataclass
class CropRecord:
    source_file: str
    index: int
    bbox: Tuple[int,int,int,int]
    trimmed_bbox: Tuple[int,int,int,int]
    label_bbox: Tuple[int,int,int,int]
    label_hash: str
    assigned_name: str
    matched_screen: str
    percent_diff: float
    saved_path: str
    label_path: str

def load_image(path: str) -> Image.Image:
    return Image.open(path).convert('RGBA')

def bg_color(im: Image.Image) -> Tuple[int,int,int,int]:
    w,h = im.size
    pts = [
        (0,0),(w-1,0),(0,h-1),(w-1,h-1), # corners
        (w//2,0),(w//2,h-1),(0,h//2),(w-1,h//2) # mid edges
    ]
    pixels = [im.getpixel(p) for p in pts]
    cnt = Counter(pixels)
    return cnt.most_common(1)[0][0]

def trim_uniform_border(im: Image.Image, bg: Tuple[int,int,int,int], tol: int = 3) -> Image.Image:
    w,h = im.size
    px = im.load()
    bg_r,bg_g,bg_b,bg_a = bg
    min_x, min_y, max_x, max_y = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            r,g,b,a = px[x,y]
            if abs(r-bg_r)>tol or abs(g-bg_g)>tol or abs(b-bg_b)>tol or abs(a-bg_a)>0:
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y
    if max_x <= min_x or max_y <= min_y:
        return im
    return im.crop((min_x,min_y,max_x+1,max_y+1))

def projection_segments(vals: List[float], min_gap: int, min_len: int) -> List[Tuple[int,int]]:
    segs = []
    inside=False; start=0; gap=0
    for i,v in enumerate(vals):
        if v < 0.002: # background-ish row/col
            gap += 1
            if inside and gap >= min_gap:
                end = i - gap
                if end - start + 1 >= min_len:
                    segs.append((start,end))
                inside=False
        else:
            if not inside:
                inside=True; start=i
            gap=0
    if inside:
        end=len(vals)-1
        if end - start + 1 >= min_len:
            segs.append((start,end))
    return segs

def row_projection(im: Image.Image, bg: Tuple[int,int,int,int], tol:int=3) -> List[float]:
    w,h=im.size; px=im.load(); bg_r,bg_g,bg_b,bg_a=bg
    out=[]
    for y in range(h):
        non=0
        for x in range(w):
            r,g,b,a=px[x,y]
            if abs(r-bg_r)>tol or abs(g-bg_g)>tol or abs(b-bg_b)>tol:
                non+=1
        out.append(non/w)
    return out

def col_projection(im: Image.Image, bg: Tuple[int,int,int,int], tol:int=3) -> List[float]:
    w,h=im.size; px=im.load(); bg_r,bg_g,bg_b,bg_a=bg
    out=[]
    for x in range(w):
        non=0
        for y in range(h):
            r,g,b,a=px[x,y]
            if abs(r-bg_r)>tol or abs(g-bg_g)>tol or abs(b-bg_b)>tol:
                non+=1
        out.append(non/h)
    return out

def percent_diff(a: Image.Image, b: Image.Image) -> float:
    if a.size != b.size:
        b = b.resize(a.size, Image.LANCZOS)
    diff = ImageChops.difference(a,b).getdata()
    differing = sum(1 for px in diff if px[0] or px[1] or px[2] or px[3])
    return differing / len(diff) if diff else 1.0

def collect_current(current_dir: str) -> Dict[str,Image.Image]:
    imgs={}
    for f in os.listdir(current_dir):
        if f.lower().endswith('.png'):
            base=os.path.splitext(f)[0]
            # strip trailing digits
            i=len(base)-1
            while i>=0 and base[i].isdigit():
                i-=1
            if i < len(base)-1:
                base=base[:i+1]
            imgs[base.lower()]=load_image(os.path.join(current_dir,f))
    return imgs

def assign_name(crop: Image.Image, current_images: Dict[str,Image.Image], max_fail: float = 0.98) -> Tuple[str,str,float]:
    best_name=''; best_pd=1.0
    for name,img in current_images.items():
        pd = percent_diff(crop,img)
        if pd < best_pd:
            best_pd = pd; best_name = name
    if best_pd < max_fail:
        return best_name,best_name,best_pd
    return '',best_name,best_pd

def extract_label_region(cell: Image.Image, bg: Tuple[int,int,int,int], max_height: int = 120, tol: int = 3) -> Tuple[Image.Image, Tuple[int,int,int,int]]:
    """Heuristic label extraction: scan downward until content density exceeds threshold.
    We treat initial sparse region as potential label background then include next dense band.
    Returns (label_img, bbox) where bbox is relative to cell coordinates.
    """
    w,h = cell.size
    px = cell.load()
    bg_r,bg_g,bg_b,bg_a = bg
    densities = []
    for y in range(min(h, max_height)):
        non=0
        for x in range(w):
            r,g,b,a = px[x,y]
            if abs(r-bg_r)>tol or abs(g-bg_g)>tol or abs(b-bg_b)>tol:
                non += 1
        densities.append(non / w)
    # Find first row where density spikes (text/content) beyond small threshold
    content_thresh = 0.08  # adjustable
    start_label = 0
    end_label = 0
    state = 'bg'
    for i,val in enumerate(densities):
        if state == 'bg':
            if val > content_thresh:
                # include slight padding above if available
                start_label = max(0, i-2)
                state = 'in'
        elif state == 'in':
            # continue until density drops again or max reached
            if val < content_thresh/3:
                end_label = i
                break
    if state == 'in' and end_label == 0:
        end_label = min(len(densities)-1, start_label + 40)
    if end_label <= start_label:
        # fallback: fixed 12% height
        end_label = max(1, int(h*0.12))
    label_h = min(h, end_label - start_label)
    label_box = (0, start_label, w, start_label + label_h)
    return cell.crop(label_box), label_box

def md5_bytes(im: Image.Image) -> str:
    import io, hashlib as _hash
    buf = io.BytesIO()
    im.save(buf, format='PNG')
    return _hash.md5(buf.getvalue()).hexdigest()

def process_composite(path: str, current_images: Dict[str,Image.Image], assign: bool, extract_labels: bool, typical_width: int) -> List[CropRecord]:
    im = load_image(path)
    bg = bg_color(im)
    trimmed = trim_uniform_border(im, bg)
    h_trim = row_projection(trimmed, bg)
    vertical_segs = projection_segments(h_trim, min_gap=6, min_len=int(trimmed.height*0.25))
    if not vertical_segs:
        vertical_segs = [(0, trimmed.height-1)]
    records=[]
    idx=0
    for (y1,y2) in vertical_segs:
        v_crop = trimmed.crop((0,y1, trimmed.width, y2+1))
        # Column segmentation inside vertical crop
        c_proj = col_projection(v_crop, bg)
        horiz_segs = projection_segments(c_proj, min_gap=6, min_len=int(v_crop.width*0.25))
        if not horiz_segs:
            # Force multi-column split if very wide compared to typical single screen width
            if v_crop.width > typical_width * 1.8:
                approx_cols = int(round(v_crop.width / typical_width))
                approx_cols = max(1, min(approx_cols, 5))
                col_w = v_crop.width / approx_cols
                horiz_segs = [(int(i*col_w), int((i+1)*col_w)-1) for i in range(approx_cols)]
            else:
                horiz_segs=[(0, v_crop.width-1)]
        for (x1,x2) in horiz_segs:
            cell = v_crop.crop((x1,0,x2+1,v_crop.height))
            cell_trim = trim_uniform_border(cell, bg)
            assigned=''
            matched=''
            pd=1.0
            if assign:
                assigned, matched, pd = assign_name(cell_trim, current_images)
            name = assigned if assigned else f"{os.path.splitext(os.path.basename(path))[0].lower()}_seg{idx}"
            label_hash=''
            label_path=''
            label_box=(0,0,0,0)
            if extract_labels:
                label_img,label_box = extract_label_region(cell_trim, bg)
                label_hash = md5_bytes(label_img)
            records.append(CropRecord(source_file=os.path.basename(path), index=idx,
                                      bbox=(x1,y1,x2+1,y2+1),
                                      trimmed_bbox=(0,0,cell_trim.width,cell_trim.height),
                                      label_bbox=label_box,
                                      label_hash=label_hash,
                                      assigned_name=name, matched_screen=matched, percent_diff=pd,
                                      saved_path='', label_path=label_path))
            idx+=1
    return records

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--current', default='screenshots/current')
    ap.add_argument('--references', default='screenshots/references')
    ap.add_argument('--out', default='screenshots/references')
    ap.add_argument('--min-width', type=int, default=350, help='Treat images wider than this as composite candidates.')
    ap.add_argument('--min-height', type=int, default=300, help='Treat images taller than this as composite candidates.')
    ap.add_argument('--assign-names', action='store_true', help='Attempt best-match naming against current screenshots.')
    ap.add_argument('--mapping-output', default='advanced_split_mapping.json')
    ap.add_argument('--extract-labels', action='store_true', help='Extract top label region and save label_<name>.png plus hash.')
    args = ap.parse_args()

    if not os.path.isdir(args.current):
        print(f"ERROR: current dir missing: {args.current}", file=sys.stderr); sys.exit(2)
    if not os.path.isdir(args.references):
        print(f"ERROR: references dir missing: {args.references}", file=sys.stderr); sys.exit(3)
    os.makedirs(args.out, exist_ok=True)

    current_imgs = collect_current(args.current) if args.assign_names else {}
    # Determine typical width from current images (median)
    widths = sorted([im.width for im in current_imgs.values()]) if current_imgs else []
    typical_width = widths[len(widths)//2] if widths else 350
    ref_files = [f for f in os.listdir(args.references) if f.lower().endswith('.png')]
    all_records=[]
    for rf in ref_files:
        p = os.path.join(args.references, rf)
        try:
            im = load_image(p)
        except Exception as e:
            print(f"WARN: failed loading {rf}: {e}", file=sys.stderr)
            continue
        if im.width < args.min_width and im.height < args.min_height:
            continue  # already likely a single screen
        recs = process_composite(p, current_imgs, args.assign_names, args.extract_labels, typical_width)
        # Save crops
        for r in recs:
            try:
                # Reconstruct trimmed crop from original trimmed image region
                im_full = load_image(p)  # reload to avoid pointer issues
                bg = bg_color(im_full)
                trimmed_full = trim_uniform_border(im_full, bg)
                # Extract cell using bbox relative to trimmed image coordinate system
                x1,y1,x2,y2 = r.bbox
                cell = trimmed_full.crop((x1, y1, x2, y2))
                cell = trim_uniform_border(cell, bg)
                out_name = f"{r.assigned_name}.png"
                # Avoid overwriting existing reference screens of same name from earlier manual mapping
                if os.path.exists(os.path.join(args.out, out_name)) and r.percent_diff >= 0.50:
                    # differentiate
                    out_name = f"{r.assigned_name}_{r.index}.png"
                out_path = os.path.join(args.out, out_name)
                cell.save(out_path)
                r.saved_path = out_path
                if args.extract_labels and r.label_bbox != (0,0,0,0):
                    label_img = cell.crop(r.label_bbox)
                    label_name = f"label_{r.assigned_name}.png"
                    label_out = os.path.join(args.out, label_name)
                    label_img.save(label_out)
                    r.label_path = label_out
            except Exception as e:
                print(f"WARN: failed saving crop {r.assigned_name}: {e}", file=sys.stderr)
        all_records.extend(recs)

    summary = { 'total_crops': len(all_records), 'crops': [asdict(r) for r in all_records] }
    # Provide quick label hash mapping if extracted
    if any(r.label_hash for r in all_records):
        summary['label_hash_map'] = { r.label_hash: r.assigned_name for r in all_records if r.label_hash }
    with open(os.path.join(args.out, args.mapping_output),'w') as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
