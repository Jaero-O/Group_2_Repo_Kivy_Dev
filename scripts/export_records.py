"""
export_records.py

Exports scan records and referenced image paths.
Usage:
    python scripts/export_records.py [--db PATH] [--out DIR] [--copy-images]

Outputs:
 - JSON file with joined records (records.json)
 - CSV file with image paths (image_paths.csv)
 - Optionally copies image files into the output directory under `images/`.
"""
import sqlite3
import os
import sys
import json
import csv
import shutil

COMMON_LOCATIONS = []
if sys.platform == 'win32':
    COMMON_LOCATIONS = [
        os.path.join(os.getcwd(), 'mangofy.db'),
        os.path.join(os.environ.get('APPDATA', ''), 'mangofy', 'mangofy.db')
    ]
elif sys.platform == 'darwin':
    COMMON_LOCATIONS = [
        os.path.join(os.getcwd(), 'mangofy.db'),
        os.path.expanduser('~/Library/Application Support/mangofy/mangofy.db')
    ]
else:
    COMMON_LOCATIONS = [
        os.path.join(os.getcwd(), 'mangofy.db'),
        os.path.expanduser('~/.config/mangofy/mangofy.db')
    ]


def find_db(provided_path=None):
    if provided_path:
        if os.path.exists(provided_path):
            return provided_path
        else:
            raise FileNotFoundError(f"Provided DB path not found: {provided_path}")
    for p in COMMON_LOCATIONS:
        if p and os.path.exists(p):
            return p
    raise FileNotFoundError('Could not locate mangofy.db in common locations. Provide --db PATH')


def export(db_path, out_dir, copy_images=False):
    os.makedirs(out_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = '''
    SELECT r.id, r.scan_timestamp, r.severity_percentage, r.image_path,
           d.name as disease_name, s.name as severity_name, t.name as tree_name
    FROM tbl_scan_record r
    LEFT JOIN tbl_disease d ON r.disease_id = d.id
    LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
    LEFT JOIN tbl_tree t ON r.tree_id = t.id
    WHERE 1=1
    ORDER BY r.scan_timestamp DESC
    '''

    cur.execute(query)
    rows = [dict(r) for r in cur.fetchall()]

    json_path = os.path.join(out_dir, 'records.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    csv_path = os.path.join(out_dir, 'image_paths.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['record_id', 'image_path'])
        for r in rows:
            writer.writerow([r['id'], r['image_path']])

    if copy_images:
        images_out = os.path.join(out_dir, 'images')
        os.makedirs(images_out, exist_ok=True)
        missing = []
        for r in rows:
            img = r.get('image_path')
            if not img:
                continue
            # Support relative paths - try to resolve against project root and absolute path
            candidates = [img, os.path.join(os.getcwd(), img)]
            copied = False
            for c in candidates:
                if c and os.path.exists(c):
                    try:
                        shutil.copy2(c, images_out)
                        copied = True
                        break
                    except Exception as e:
                        print(f"Failed to copy {c}: {e}")
            if not copied:
                missing.append(img)
        if missing:
            print(f"Missing images that could not be copied (listed in image_paths.csv): {len(missing)}")

    conn.close()
    print(f"Export complete. JSON: {json_path}, CSV: {csv_path}")


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--db', help='Path to mangofy.db')
    p.add_argument('--out', help='Output directory', default='db_export')
    p.add_argument('--copy-images', help='Copy referenced images to output dir', action='store_true')
    args = p.parse_args()

    try:
        db = find_db(args.db)
    except FileNotFoundError as e:
        print(e)
        sys.exit(2)

    export(db, args.out, copy_images=args.copy_images)
