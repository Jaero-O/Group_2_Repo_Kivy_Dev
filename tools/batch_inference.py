"""Batch inference on all DB scan records to populate real predictions and severity.

Usage:
    python tools/batch_inference.py [--limit N] [--batch-size N]

Loads the TFLite model once, then processes all scan records with severity_percentage=0.0,
running prediction + severity calculation and updating DB fields:
  - disease_id (from predicted label)
  - severity_percentage (from compute_severity)
  - severity_level_id (from severity_stage mapping)

Safe for resuming: processes only records with zero severity, so re-running is idempotent.
"""
import os
import sys
import json
import argparse
from pathlib import Path

# Disable Kivy argument parsing before importing any kivy modules
os.environ['KIVY_NO_ARGS'] = '1'

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'kivy-lcd-app'))

import sqlite3
from importlib.machinery import SourceFileLoader

# Load classify_leaf directly from file to avoid importing app.core package (Kivy dependency)
classify_leaf_path = PROJECT_ROOT / 'kivy-lcd-app' / 'app' / 'core' / 'classify_leaf.py'
classify_leaf_mod = SourceFileLoader('classify_leaf', str(classify_leaf_path)).load_module()
load_session = classify_leaf_mod.load_session
classify_image = classify_leaf_mod.classify_image

from ml.processing.severity import compute_severity
from ml.processing.severity_constants import severity_stage


def main():
    parser = argparse.ArgumentParser(description="Batch inference to populate real predictions")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N records")
    parser.add_argument("--batch-size", type=int, default=100, help="Commit every N records")
    parser.add_argument("--force", action="store_true", help="Re-run inference for all records, not only severity=0")
    args = parser.parse_args()

    # Locate model and labels
    model_path = os.getenv("MANGOFY_MODEL_PATH", str(PROJECT_ROOT / "kivy-lcd-app" / "app" / "scan" / "resnet_leafdisease_datasetresized.onnx"))

    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}. Set MANGOFY_MODEL_PATH or place model in default location.")
        return 1

    print(f"Loading ONNX model: {model_path}")
    session = load_session(model_path)
    print(f"Model loaded from {model_path}")

    # Pre-populate disease and severity level caches to avoid nested connections
    disease_cache = {}
    severity_cache = {}
    
    # query scan records based on flag, optionally all records for re-evaluation
    db_path = os.getenv("MANGOFY_DB_PATH", str(PROJECT_ROOT / "kivy-lcd-app" / "mangofy.db"))
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout for locks
    try:
        cur = conn.cursor()

        # Build disease cache
        cur.execute("SELECT id, name FROM tbl_disease")
        for did, dname in cur.fetchall():
            disease_cache[dname] = did
        
        # Build severity cache
        cur.execute("SELECT id, name FROM tbl_severity_level")
        for sid, sname in cur.fetchall():
            severity_cache[sname] = sid
        
        # Ensure basic severity levels exist
        for stage_name in ['Healthy', 'Early Stage', 'Advanced Stage']:
            if stage_name not in severity_cache:
                cur.execute("INSERT INTO tbl_severity_level(name) VALUES (?)", (stage_name,))
                severity_cache[stage_name] = cur.lastrowid
        conn.commit()
        
        if args.force:
            cur.execute("SELECT id, image_path FROM tbl_scan_record ORDER BY id ASC")
        else:
            cur.execute("SELECT id, image_path FROM tbl_scan_record WHERE severity_percentage = 0.0 ORDER BY id ASC")
        rows = cur.fetchall()
        if args.limit:
            rows = rows[:args.limit]

        total = len(rows)
        print(f"Found {total} records to process.")
        if total == 0:
            return 0

        processed = 0
        errors = 0

        def resolve_image_path(scan_id, image_path):
            app_scan_prefix = str(PROJECT_ROOT / 'kivy-lcd-app' / 'app' / 'scan')
            data_scans_prefix = str(PROJECT_ROOT / 'data' / 'scans')

            # 1) direct path exists
            if image_path and os.path.exists(image_path):
                return image_path

            # 2) converted app/scan -> data/scans path
            if image_path and image_path.startswith(app_scan_prefix):
                candidate = image_path.replace(app_scan_prefix, data_scans_prefix, 1)
                if os.path.exists(candidate):
                    return candidate

            # 3) old path fragment /scan_*/output_image_reduced.jpg -> data/scans mapping
            if image_path and '/scan_' in image_path and image_path.endswith('output_image_reduced.jpg'):
                candidate = os.path.join(data_scans_prefix, os.path.basename(os.path.dirname(image_path)), 'output_image_reduced.jpg')
                if os.path.exists(candidate):
                    return candidate

            # 4) from json_path scan_dir/reduced_image
            cur2 = conn.cursor()
            cur2.execute("SELECT json_path FROM tbl_scan_record WHERE id=?", (scan_id,))
            row = cur2.fetchone()
            if row and row[0] and os.path.exists(row[0]):
                try:
                    payload = json.loads(open(row[0], 'r', encoding='utf-8').read())
                    for field in ['reduced_image', 'output_image_reduced', 'image_path', 'full_image_path']:
                        val = payload.get(field)
                        if isinstance(val, str) and os.path.exists(val):
                            return val
                    scan_dir = payload.get('scan_dir')
                    if scan_dir:
                        candidate = os.path.join(scan_dir, 'output_image_reduced.jpg')
                        if os.path.exists(candidate):
                            return candidate
                except Exception:
                    pass

            # 5) try alternate extensions
            if image_path:
                base, ext = os.path.splitext(image_path)
                for alt_ext in ['.jpg', '.png', '.jpeg']:
                    if ext.lower() != alt_ext:
                        candidate = base + alt_ext
                        if os.path.exists(candidate):
                            return candidate

            # 6) search by same scan folder basename in data/scans
            if image_path and os.path.basename(image_path) == 'output_image_reduced.jpg':
                candidate_dir = os.path.basename(os.path.dirname(image_path))
                candidate = os.path.join(data_scans_prefix, candidate_dir, 'output_image_reduced.jpg')
                if os.path.exists(candidate):
                    return candidate

            return None

        for i, (scan_id, image_path) in enumerate(rows, start=1):
            image_path = image_path or ''
            image_path = resolve_image_path(scan_id, image_path)
            if not image_path:
                errors += 1
                print(f"Error processing scan_id={scan_id}, image={image_path}: file not found")
                continue

            if not image_path or not os.path.exists(image_path):
                # try common extension fallback (.jpg <-> .png)
                if image_path:
                    base, ext = os.path.splitext(image_path)
                    alt_ext = '.png' if ext.lower() == '.jpg' else '.jpg' if ext.lower() == '.png' else None
                    if alt_ext:
                        candidate = base + alt_ext
                        if os.path.exists(candidate):
                            image_path = candidate

                if not image_path or not os.path.exists(image_path):
                    errors += 1
                    print(f"Error processing scan_id={scan_id}, image={image_path}: file not found")
                    continue

            try:
                # Predict disease + raw probabilities
                result = classify_image(session, image_path)
                label = result.get('class', 'Unknown')
                confidence = result.get('confidence', 0.0)
                probs = result.get('probabilities', {})

                pred_anthracnose = float(probs.get('Anthracnose', 0.0))
                pred_healthy = float(probs.get('Healthy', 0.0))
                pred_bacterial_canker = float(probs.get('Bacterial Canker', 0.0))
                pred_cutting_weevil = float(probs.get('Cutting Weevil', 0.0))
                pred_powdery_mildew = float(probs.get('Powdery Mildew', 0.0))
                pred_sooty_mould = float(probs.get('Sooty Mould', 0.0))

                # Get or create disease_id using cache
                if label not in disease_cache:
                    cur.execute("INSERT INTO tbl_disease(name) VALUES (?)", (label,))
                    disease_cache[label] = cur.lastrowid
                disease_id = disease_cache[label]

                # Compute severity
                severity_pct = compute_severity(image_path)

                # Map to severity stage
                sev_level_name = severity_stage(severity_pct, label)
                severity_level_id = severity_cache.get(sev_level_name)

                # Update record
                cur.execute(
                    """
                    UPDATE tbl_scan_record
                    SET disease_id = ?, disease_class = ?, confidence_score = ?,
                        severity_percentage = ?, severity_level_id = ?, severity_level = ?,
                        pred_anthracnose = ?, pred_healthy = ?, pred_bacterial_canker = ?,
                        pred_cutting_weevil = ?, pred_powdery_mildew = ?, pred_sooty_mould = ?
                    WHERE id = ?
                    """,
                    (disease_id, label, confidence,
                     severity_pct, severity_level_id, sev_level_name,
                     pred_anthracnose, pred_healthy, pred_bacterial_canker,
                     pred_cutting_weevil, pred_powdery_mildew, pred_sooty_mould,
                     scan_id)
                )
                processed += 1

                if i % args.batch_size == 0:
                    conn.commit()
                    print(f"Progress: {i}/{total} ({100*i//total}%)")

            except Exception as e:
                errors += 1
                print(f"Error processing scan_id={scan_id}, image={image_path}: {e}")

        conn.commit()
        print(f"\nBatch inference complete. Processed: {processed}, Errors: {errors}")

    finally:
        conn.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
