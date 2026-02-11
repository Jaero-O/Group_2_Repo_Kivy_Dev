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
import argparse
from pathlib import Path

# Disable Kivy argument parsing before importing any kivy modules
os.environ['KIVY_NO_ARGS'] = '1'

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'kivy-lcd-app'))

from ml.predictor import DiseasePredictor
from ml.processing.severity import compute_severity
from ml.processing.severity_constants import severity_stage
from app.core import db


def main():
    parser = argparse.ArgumentParser(description="Batch inference to populate real predictions")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N records")
    parser.add_argument("--batch-size", type=int, default=100, help="Commit every N records")
    args = parser.parse_args()

    # Locate model and labels
    model_path = os.getenv("MANGOFY_MODEL_PATH", str(PROJECT_ROOT / "ml" / "Plant_Disease_Prediction" / "tflite" / "mango_mobilenetv2.tflite"))
    labels_path = os.getenv("MANGOFY_LABELS_PATH", str(PROJECT_ROOT / "ml" / "Plant_Disease_Prediction" / "tflite" / "labels.txt"))

    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}. Set MANGOFY_MODEL_PATH or place model in default location.")
        return 1

    print(f"Loading model: {model_path}")
    predictor = DiseasePredictor(model_path, labels_path)
    print(f"Model loaded with {predictor.num_classes} classes: {predictor.labels}")

    # Pre-populate disease and severity level caches to avoid nested connections
    disease_cache = {}
    severity_cache = {}
    
    # Query all scan records with severity_percentage = 0.0
    conn = db.get_connection()
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

        for i, (scan_id, image_path) in enumerate(rows, start=1):
            try:
                # Predict disease
                label, confidence = predictor.predict(image_path)
                
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
                    SET disease_id = ?, severity_percentage = ?, severity_level_id = ?
                    WHERE id = ?
                    """,
                    (disease_id, severity_pct, severity_level_id, scan_id)
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
