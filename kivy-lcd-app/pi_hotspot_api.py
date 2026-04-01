import os
import json
import time
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, send_from_directory, abort

app = Flask(__name__)

DB_PATH = os.getenv('MANGOFY_DB_PATH', os.path.join(os.path.dirname(__file__), 'mangofy.db'))
IMAGE_DIR = os.getenv('MANGOFY_IMAGE_DIR', '/home/pi/captured_images')
PI_IP = '192.168.4.1'


def _normalize_timestamp(value: str) -> str:
    # Accept ISO8601 (with T) or space-separated.
    if 'T' in value:
        value = value.replace('T', ' ')
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass
    # maybe unix epoch
    try:
        ts = float(value)
        return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        raise ValueError('Unsupported timestamp format')


def _scan_metadata_from_row(row: sqlite3.Row) -> dict:
    image_path = row['image_path'] or ''
    image_file = os.path.basename(image_path) if image_path else f"scan_{row['id']}.jpg"
    image_uri = f'http://{PI_IP}:5000/api/image/{image_file}'

    description = []
    if row['disease_name']:
        description.append(row['disease_name'])
    if row['severity_name']:
        description.append(row['severity_name'])
    if row['notes']:
        description.append(row['notes'])
    if not description:
        description = [f'Scan from Pi (id={row["id"]})']

    metadata = {
        'id': str(row['id']),
        'title': row['tree_name'] if row['tree_name'] else f'Scan {row["id"]}',
        'description': ' | '.join(description),
        'timestamp': row['scan_timestamp'],
        'image_filename': image_file,
        'image_url': image_uri,
        'updated_at': row['scan_timestamp'],
        'metadata_hash': hashlib.sha256(json.dumps({
            'id': row['id'],
            'scan_timestamp': row['scan_timestamp'],
            'disease_class': row['disease_class'],
            'confidence_score': row['confidence_score'],
            'image_path': image_path,
        }, sort_keys=True).encode('utf-8')).hexdigest(),
    }
    return metadata


def _get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _get_scan(scan_id: str) -> dict:
    conn = _get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            '''
            SELECT r.*, t.name as tree_name, d.name as disease_name, s.name as severity_name
            FROM tbl_scan_record r
            LEFT JOIN tbl_tree t ON r.tree_id = t.id
            LEFT JOIN tbl_disease d ON r.disease_id = d.id
            LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
            WHERE r.id = ?
            ''', (scan_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return _scan_metadata_from_row(row)
    finally:
        conn.close()


def _get_all_scans() -> list:
    conn = _get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            '''
            SELECT r.*, t.name as tree_name, d.name as disease_name, s.name as severity_name
            FROM tbl_scan_record r
            LEFT JOIN tbl_tree t ON r.tree_id = t.id
            LEFT JOIN tbl_disease d ON r.disease_id = d.id
            LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
            ORDER BY r.scan_timestamp DESC
            '''
        )
        rows = cur.fetchall()
        return [_scan_metadata_from_row(row) for row in rows]
    finally:
        conn.close()


def _get_scans_since(timestamp: str) -> list:
    normalized = _normalize_timestamp(timestamp)
    conn = _get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            '''
            SELECT r.*, t.name as tree_name, d.name as disease_name, s.name as severity_name
            FROM tbl_scan_record r
            LEFT JOIN tbl_tree t ON r.tree_id = t.id
            LEFT JOIN tbl_disease d ON r.disease_id = d.id
            LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
            WHERE r.scan_timestamp > ?
            ORDER BY r.scan_timestamp ASC
            ''', (normalized,)
        )
        rows = cur.fetchall()
        return [_scan_metadata_from_row(row) for row in rows]
    finally:
        conn.close()


@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({'status': 'ready', 'pi_ip': PI_IP, 'db': os.path.basename(DB_PATH)})


@app.route('/api/scan/<scan_id>', methods=['GET'])
def get_scan_route(scan_id):
    data = _get_scan(scan_id)
    if data is None:
        abort(404, description='scan_id not found')
    return jsonify(data)


@app.route('/api/scan/all', methods=['GET'])
def get_all_scans_route():
    items = _get_all_scans()
    return jsonify(items)


@app.route('/api/scan/since/<timestamp>', methods=['GET'])
def get_scans_since_route(timestamp):
    try:
        items = _get_scans_since(timestamp)
        return jsonify(items)
    except ValueError as e:
        abort(400, description=f'Invalid timestamp: {e}')


@app.route('/api/image/<filename>', methods=['GET'])
def get_image(filename):
    search_path = os.path.join(IMAGE_DIR, filename)
    if os.path.exists(search_path):
        return send_from_directory(IMAGE_DIR, filename)

    # fallback: lookup in DB by basename
    conn = _get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT image_path FROM tbl_scan_record WHERE image_path LIKE ?', ('%' + filename,))
        row = cur.fetchone()
        if row and row['image_path'] and os.path.exists(row['image_path']):
            abs_path = os.path.abspath(row['image_path'])
            return send_from_directory(os.path.dirname(abs_path), os.path.basename(abs_path))
    finally:
        conn.close()

    abort(404, description='image file not found')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
