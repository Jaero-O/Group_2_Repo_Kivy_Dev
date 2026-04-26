#!/usr/bin/env python3
"""Import external dataset images into mangofy.db and run model inference."""
import json
import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from importlib.machinery import SourceFileLoader
classify_leaf_path = PROJECT_ROOT / 'kivy-lcd-app' / 'app' / 'core' / 'classify_leaf.py'
classify_leaf_mod = SourceFileLoader('classify_leaf', str(classify_leaf_path)).load_module()
load_session = classify_leaf_mod.load_session
classify_image = classify_leaf_mod.classify_image

from ml.processing.severity import compute_severity
from ml.processing.severity_constants import severity_stage

MODEL_PATH = os.getenv('MANGOFY_MODEL_PATH', str(PROJECT_ROOT / 'kivy-lcd-app' / 'app' / 'scan' / 'resnet_leafdisease_datasetresized.onnx'))
SCAN_DIRS = [
    PROJECT_ROOT / 'data' / 'database',
    PROJECT_ROOT / 'data' / 'imported_dataset'
]
VALID_EXT = {'.jpg', '.jpeg', '.png'}


def find_image_files(root_dir):
    for p in root_dir.rglob('*'):
        if p.is_file() and p.suffix.lower() in VALID_EXT:
            yield p


def get_or_create(conn, table, name):
    if name is None:
        return None
    name = name.strip()
    if name == '':
        return None
    cur = conn.cursor()
    cur.execute(f"SELECT id FROM {table} WHERE name=?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(f"INSERT INTO {table}(name) VALUES(?)", (name,))
    conn.commit()
    return cur.lastrowid


def ensure_disease_and_severity(conn, label, severity_pct):
    disease_id = get_or_create(conn, 'tbl_disease', label if label not in ['Unknown', None] else None)
    stage_name = severity_stage(severity_pct, label)
    severity_id = get_or_create(conn, 'tbl_severity_level', stage_name)
    return disease_id, severity_id, stage_name


def query_record_by_image_path(conn, image_path):
    cur = conn.cursor()
    cur.execute("SELECT id FROM tbl_scan_record WHERE image_path=?", (image_path,))
    row = cur.fetchone()
    return row[0] if row else None


def insert_scan_record(conn, tree_id, disease_id, severity_level_id,
                       severity_percentage, image_path, thumbnail_path=None,
                       notes=None, confidence_score=None, total_leaf_area=None,
                       lesion_area=None, disease_class=None, severity_level=None,
                       pred_anthracnose=None, pred_healthy=None,
                       pred_bacterial_canker=None, pred_cutting_weevil=None,
                       pred_powdery_mildew=None, pred_sooty_mould=None,
                       source='imported'):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tbl_scan_record(tree_id, disease_id, severity_level_id, disease_class, severity_level, severity_percentage,
                                     confidence_score, pred_anthracnose, pred_healthy, pred_bacterial_canker, pred_cutting_weevil,
                                     pred_powdery_mildew, pred_sooty_mould, total_leaf_area, lesion_area,
                                     image_path, thumbnail_path, notes, source, scan_status, scan_timestamp)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (tree_id, disease_id, severity_level_id, disease_class, severity_level, severity_percentage,
         confidence_score, pred_anthracnose, pred_healthy, pred_bacterial_canker, pred_cutting_weevil,
         pred_powdery_mildew, pred_sooty_mould, total_leaf_area, lesion_area,
         image_path, thumbnail_path, notes, source,
         'imported', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    return cur.lastrowid


def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Model not found at {MODEL_PATH}")
        return 1

    print(f"Loading model: {MODEL_PATH}")
    session = load_session(MODEL_PATH)

    added = 0
    skipped = 0
    errors = 0

    # Ensure that imported records are linked to a dedicated imported dataset tree.
    conn = sqlite3.connect(str(PROJECT_ROOT / 'kivy-lcd-app' / 'mangofy.db'))
    conn.execute('PRAGMA foreign_keys=ON')
    imported_tree_id = get_or_create(conn, 'tbl_tree', 'Imported Dataset')
    
    for scan_base in SCAN_DIRS:
        if not scan_base.exists():
            print(f"Warning: folder not found: {scan_base}")
            continue

        for img_path in find_image_files(scan_base):
            # normalize to full absolute path
            img_path_str = str(img_path.resolve())

            # skip duplicate path in DB
            if query_record_by_image_path(conn, img_path_str):
                skipped += 1
                continue

            try:
                # Pre-validate image can be decoded; skip broken files.
                from PIL import Image
                with Image.open(img_path_str) as img:
                    img.verify()
            except Exception as e:
                errors += 1
                print(f"Skipped invalid image {img_path_str}: {e}")
                continue

            try:
                classification = classify_image(session, img_path_str)
                label = classification.get('class', 'Unknown')
                confidence = float(classification.get('confidence', 0.0))

                severity_pct = compute_severity(img_path_str)
                disease_id, severity_id, severity_name = ensure_disease_and_severity(conn, label, severity_pct)

                source = 'imported_dataset' if 'imported_dataset' in str(scan_base) else 'database' if 'database' in str(scan_base) else 'external'
                record_id = insert_scan_record(
                    conn,
                    tree_id=imported_tree_id,
                    disease_id=disease_id,
                    severity_level_id=severity_id,
                    severity_percentage=severity_pct,
                    image_path=img_path_str,
                    thumbnail_path=None,
                    notes=f"Imported from external dataset ({scan_base.name})",
                    confidence_score=confidence,
                    total_leaf_area=None,
                    lesion_area=None,
                    disease_class=label,
                    severity_level=severity_name,
                    pred_anthracnose=float(classification.get('probabilities', {}).get('Anthracnose', 0.0)),
                    pred_healthy=float(classification.get('probabilities', {}).get('Healthy', 0.0)),
                    pred_bacterial_canker=float(classification.get('probabilities', {}).get('Bacterial Canker', 0.0)),
                    pred_cutting_weevil=float(classification.get('probabilities', {}).get('Cutting Weevil', 0.0)),
                    pred_powdery_mildew=float(classification.get('probabilities', {}).get('Powdery Mildew', 0.0)),
                    pred_sooty_mould=float(classification.get('probabilities', {}).get('Sooty Mould', 0.0)),
                    source=source
                )

                # Keep source annotation in JSON if available
                external_json_path = img_path.with_suffix('.json')
                if external_json_path.exists():
                    try:
                        data = json.loads(external_json_path.read_text(encoding='utf-8'))
                        data['database_id'] = record_id
                        data['source'] = 'external_import'
                        external_json_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
                    except Exception:
                        pass

                added += 1
                if added % 20 == 0:
                    print(f"Added {added} external records...")

            except Exception as e:
                errors += 1
                print(f"Error processing {img_path_str}: {e}")

    conn.close()

    print(f"Import complete: added={added}, skipped={skipped}, errors={errors}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
