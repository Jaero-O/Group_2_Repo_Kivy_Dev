#!/usr/bin/env python3
"""Retroactively sync scan_results.json from data/scans into kivy-lcd-app/mangofy.db."""
import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'kivy-lcd-app' / 'mangofy.db'
SCANS_DIR = BASE_DIR / 'data' / 'scans'


def quote_path(p):
    try:
        return str(p.resolve())
    except Exception:
        return str(p)


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


def get_or_create_tree(conn, tree_name: str):
    return get_or_create(conn, 'tbl_tree', tree_name)


def find_existing_record(conn, db_id, image_path, scan_timestamp):
    cur = conn.cursor()
    if db_id is not None:
        cur.execute("SELECT id FROM tbl_scan_record WHERE id=?", (db_id,))
        row = cur.fetchone()
        if row:
            return row[0]
    if image_path:
        cur.execute("SELECT id FROM tbl_scan_record WHERE image_path=?", (image_path,))
        row = cur.fetchone()
        if row:
            return row[0]
    if scan_timestamp:
        cur.execute("SELECT id FROM tbl_scan_record WHERE scan_timestamp=?", (scan_timestamp,))
        row = cur.fetchone()
        if row:
            return row[0]
    return None


def normalize_timestamp(ts):
    if not ts:
        return None
    try:
        # may be iso with Z or offset
        if ts.endswith('Z'):
            ts2 = ts.replace('Z', '+00:00')
            dt = datetime.fromisoformat(ts2)
        else:
            dt = datetime.fromisoformat(ts)
    except Exception:
        try:
            # fallback for compact
            dt = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S.%f')
        except Exception:
            try:
                dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
            except Exception:
                return None
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def run():
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found at {DB_PATH}")
    if not SCANS_DIR.exists():
        raise SystemExit(f"Scans folder not found at {SCANS_DIR}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute('PRAGMA foreign_keys=ON')
    migrated = 0
    updated = 0
    created = 0

    default_tree_name = os.getenv('RETROACTIVE_SCAN_TREE', 'Imported Scans')
    default_tree_id = get_or_create_tree(conn, default_tree_name)
    if default_tree_id is None:
        raise SystemExit(f"Cannot create/find default tree: {default_tree_name}")

    scan_json_files = sorted(SCANS_DIR.glob('scan_*/*scan_results.json'))
    for json_file in scan_json_files:
        try:
            payload = json.loads(json_file.read_text())
        except Exception as e:
            print(f"SKIP: {json_file} (invalid JSON: {e})")
            continue

        status = payload.get('status')
        classification = payload.get('classification') or {}
        analysis = payload.get('analysis') or {}
        db_id = payload.get('database_id')
        scan_dir = payload.get('scan_dir') or str(json_file.parent)
        reduced_image = payload.get('reduced_image') or str(Path(scan_dir) / 'output_image_reduced.jpg')
        if reduced_image:
            reduced_image = quote_path(Path(reduced_image) if isinstance(reduced_image, str) else reduced_image)
        timestamp = normalize_timestamp(payload.get('timestamp'))

        disease_class = classification.get('class')
        confidence_score = classification.get('confidence', 0.0)
        severity_percentage = analysis.get('severity_percentage', analysis.get('severity_percent', 0.0)) or 0.0
        severity_level = analysis.get('severity_level') or 'None'

        prob = classification.get('probabilities') or {}
        pred_anthracnose = prob.get('Anthracnose', 0.0)
        pred_healthy = prob.get('Healthy', 0.0)
        pred_bacterial_canker = prob.get('Bacterial Canker', 0.0)
        pred_cutting_weevil = prob.get('Cutting Weevil', 0.0)
        pred_powdery_mildew = prob.get('Powdery Mildew', 0.0)
        pred_sooty_mould = prob.get('Sooty Mould', 0.0)

        disease_id = get_or_create(conn, 'tbl_disease', disease_class if disease_class not in ['Unknown', None] else None)
        severity_id = get_or_create(conn, 'tbl_severity_level', severity_level if severity_level not in ['None', None, ''] else None)

        existing_id = find_existing_record(conn, db_id, reduced_image, timestamp)
        if existing_id is None:
            # Insert as new record
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO tbl_scan_record(tree_id, disease_id, severity_level_id, disease_class, severity_level,
                                           confidence_score, severity_percentage, pred_anthracnose, pred_healthy,
                                           pred_bacterial_canker, pred_cutting_weevil, pred_powdery_mildew, pred_sooty_mould,
                                           image_path, thumbnail_path, json_path, scan_timestamp, scan_status, notes, source, is_archived)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
                """,
                (default_tree_id, disease_id, severity_id, disease_class, severity_level,
                 confidence_score, severity_percentage, pred_anthracnose, pred_healthy,
                 pred_bacterial_canker, pred_cutting_weevil, pred_powdery_mildew, pred_sooty_mould,
                 reduced_image, None, quote_path(json_file),
                 timestamp or datetime.now().strftime('%Y-%m-%d %H:%M:%S'), status or 'unknown', None, 'scans')
            )
            conn.commit()
            existing_id = cur.lastrowid
            created += 1
            action = 'CREATED'
        else:
            # Update existing record; preserve assigned tree_id if present
            conn.execute(
                """
                UPDATE tbl_scan_record
                SET tree_id=COALESCE(tree_id, ?), disease_id=?, severity_level_id=?, disease_class=?, severity_level=?,
                    confidence_score=?, severity_percentage=?, pred_anthracnose=?, pred_healthy=?,
                    pred_bacterial_canker=?, pred_cutting_weevil=?, pred_powdery_mildew=?, pred_sooty_mould=?,
                    image_path=?, json_path=?, scan_timestamp=?, scan_status=?, source=?
                WHERE id=?
                """,
                (default_tree_id, disease_id, severity_id, disease_class, severity_level,
                 confidence_score, severity_percentage, pred_anthracnose, pred_healthy,
                 pred_bacterial_canker, pred_cutting_weevil, pred_powdery_mildew, pred_sooty_mould,
                 reduced_image, quote_path(json_file),
                 timestamp or datetime.now().strftime('%Y-%m-%d %H:%M:%S'), status or 'unknown', 'scans', existing_id)
            )
            conn.commit()
            updated += 1
            action = 'UPDATED'

        if payload.get('database_id') != existing_id:
            payload['database_id'] = existing_id
            json_file.write_text(json.dumps(payload, indent=2))

        migrated += 1
        print(f"{action}: scan_results={json_file} -> tbl_scan_record.id={existing_id}, status={status}")

    # ensure all imported or migrated scans get a concrete tree association
    conn.execute("UPDATE tbl_scan_record SET tree_id=? WHERE tree_id IS NULL", (default_tree_id,))
    conn.commit()
    conn.close()
    print(f"Done: {migrated} items processed (created={created}, updated={updated})")


if __name__ == '__main__':
    run()
