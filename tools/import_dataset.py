"""Import images from a folder into the mangofy DB.

Usage:
    python tools/import_dataset.py "C:\path\to\Downloads\Database" 

This script will:
- Walk the source directory for image files
- Create a destination under `data/imported_dataset/<disease>/...` (preserves disease folder)
- Insert disease rows based on parent folder name
- Create a default tree named 'Imported Dataset' (unless env overrides)
- Copy images into project, generate thumbnails, and insert scan records if not present

Designed to be idempotent and safe for repeated runs.
"""
import os
import sys
import shutil
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data" / "imported_dataset"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}


def is_image_file(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in IMAGE_EXTS


def main(src_dir: str):
    src = Path(src_dir)
    if not src.exists():
        print(f"Source path does not exist: {src}")
        return 1

    # Import DB helpers lazily
    sys.path.insert(0, str(PROJECT_ROOT / 'kivy-lcd-app'))
    from app.core import db, image_thumb

    default_tree = os.getenv("MANGOFY_DEFAULT_TREE", "Imported Dataset")
    tree_id = db.insert_tree(default_tree)

    # Walk and collect image files
    to_process = []
    for root, dirs, files in os.walk(src):
        for f in files:
            p = Path(root) / f
            if is_image_file(p):
                to_process.append(p)

    print(f"Found {len(to_process)} image files to consider.")
    if len(to_process) == 0:
        return 0

    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    inserted = 0
    skipped = 0

    conn = db.get_connection()
    try:
        cur = conn.cursor()
        for src_path in to_process:
            # Determine disease by parent directory name (one level up)
            disease_name = src_path.parent.name or "Unknown"
            disease_id = db.get_or_create_disease(disease_name)

            # Destination path: data/imported_dataset/<disease>/<filename>
            rel_dir = DATA_ROOT / disease_name
            rel_dir.mkdir(parents=True, exist_ok=True)
            dst_path = rel_dir / src_path.name

            # If destination file missing, copy it
            if not dst_path.exists():
                try:
                    shutil.copy2(src_path, dst_path)
                except Exception as e:
                    print(f"Failed to copy {src_path} -> {dst_path}: {e}")
                    skipped += 1
                    continue

            # Skip if DB already has this image path
            cur.execute("SELECT id FROM tbl_scan_record WHERE image_path=?", (str(dst_path),))
            if cur.fetchone():
                skipped += 1
                continue

            # Generate thumbnail
            thumb = image_thumb.generate_thumbnail(str(dst_path))

            # Insert scan record with minimal metadata (severity unknown)
            try:
                db.insert_scan_record(
                    tree_id=tree_id,
                    disease_id=disease_id,
                    severity_level_id=None,
                    severity_percentage=0.0,
                    image_path=str(dst_path),
                    thumbnail_path=thumb,
                    notes="Imported from dataset"
                )
                inserted += 1
            except Exception as e:
                print(f"DB insert failed for {dst_path}: {e}")
                skipped += 1

        conn.commit()
    finally:
        conn.close()

    print(f"Import complete. Inserted: {inserted}, Skipped: {skipped}")
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python tools/import_dataset.py <source_dir>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
