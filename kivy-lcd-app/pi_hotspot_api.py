import os
import json
import time
from flask import Flask, jsonify, send_from_directory, abort

app = Flask(__name__)

# These should be adjusted to your system path
IMAGE_DIR = os.getenv('MANGOFY_IMAGE_DIR', '/home/pi/captured_images')
PI_IP = '192.168.4.1'

# --- Utility ---

def _scan_metadata(scan_id: str) -> dict:
    # Replace this stub with real DB lookups / actual metadata find.
    # For rapid integration, we mimic a sample record.
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    return {
        'id': scan_id,
        'title': f'Leaf Scan #{scan_id}',
        'description': 'Auto-sync from Pi prototype',
        'timestamp': now,
        'image_filename': f'{scan_id}.jpg',
        'updated_at': now,
        'metadata_hash': '',
        'image_url': f'http://{PI_IP}:5000/api/image/{scan_id}.jpg',
    }


@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({'status': 'ready', 'pi_ip': PI_IP})


@app.route('/api/scan/<scan_id>', methods=['GET'])
def get_scan(scan_id):
    # Replace this sample with a real lookup using scan_id.
    # If missing, return 404.
    data = _scan_metadata(scan_id)
    if data is None:
        abort(404, description='scan_id not found')
    return jsonify(data)


@app.route('/api/scan/all', methods=['GET'])
def get_all_scans():
    # TODO: replace with real collection from Pi database.
    return jsonify([_scan_metadata('001'), _scan_metadata('002')])


@app.route('/api/scan/since/<timestamp>', methods=['GET'])
def get_scans_since(timestamp):
    # Simple stub: return all scans if timestamp is older; this can be improved.
    try:
        # if timestamp is formatted as ISO or epoch
        pass
    except Exception:
        pass
    return jsonify([_scan_metadata('001'), _scan_metadata('002')])


@app.route('/api/image/<filename>', methods=['GET'])
def get_image(filename):
    if not os.path.exists(os.path.join(IMAGE_DIR, filename)):
        abort(404, description='image file not found')
    return send_from_directory(IMAGE_DIR, filename)


if __name__ == '__main__':
    # 0.0.0.0 so devices on hotspot can reach it
    app.run(host='0.0.0.0', port=5000, debug=False)
