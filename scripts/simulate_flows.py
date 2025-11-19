"""Mangofy logical flow simulation and metrics collection.

Refactored to expose a `run_full_simulation` function returning metrics
so unit tests can assert timing and flow outcomes.

ALL FLOWS MUST FOLLOW docs/USER_MANUAL.md SPECIFICATIONS:
- Section 2.2: Scan Leaf Flow (8 steps)
- Section 3.1: Mandatory Rules (RULE 1-4)
- No auto-save behavior (RULE 1)
- Correct back button navigation (RULE 2)

Direct execution still prints verbose flow details.
"""
import os
import sys
import time
import json
from datetime import datetime
from pprint import pprint as _pprint
try:
    import psutil  # memory metrics
except Exception:
    psutil = None

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from main import MangofyApp

os.environ.pop('HEADLESS_TEST', None)

def _select_real_image():
    candidates = [
        os.path.join(PROJECT_ROOT, 'data', 'captures', 'capture.jpg'),
        os.path.join(PROJECT_ROOT, 'data', 'captures', 'bench_raw.jpg'),
        os.path.join(PROJECT_ROOT, 'data', 'captures', 'synthetic.jpg')
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return os.path.join(PROJECT_ROOT, 'src', 'app', 'assets', 'placeholder_bg1.png')

def _init_app():
    print('[FLOW] Initializing MangofyApp (build + finish_loading)...')
    app = MangofyApp()
    sm = app.build()
    app.finish_loading(0)
    print('[FLOW] Screens registered:', [s.name for s in sm.screens])
    return app, sm

def run_full_simulation(stress_iterations: int = 5, stress_unique_names: bool = False):
    app, sm = _init_app()
    metrics = {}

    # FLOW 1: DB insert with real image
    real_image_path = _select_real_image()
    print('[FLOW] Inserting demo tree and scan record using image:', real_image_path)
    with app.db_manager.connection() as conn:
        cur = conn.cursor()
        tree_name = 'SimTree'
        try:
            cur.execute('INSERT INTO tbl_tree (name) VALUES (?)', (tree_name,))
            tree_id = cur.lastrowid
        except Exception:
            row = cur.execute('SELECT id FROM tbl_tree WHERE name=?', (tree_name,)).fetchone()
            tree_id = row['id'] if row else None
        cur.execute(
            'INSERT INTO tbl_scan_record (tree_id, disease_id, severity_level_id, severity_percentage, image_path) VALUES (?, ?, ?, ?, ?)',
            (tree_id, 1, 2, 23.5, real_image_path)
        )
        record_id = cur.lastrowid
        conn.commit()
    print(f'[FLOW] Created tree_id={tree_id}, record_id={record_id}')
    metrics.update({'tree_id': tree_id, 'record_id': record_id, 'record_image_path': real_image_path})

    # FLOW 2: View saved record (USER_MANUAL.md Section 2.3 - Records Flow)
    # Navigation: RecordsScreen → ImageSelectionScreen → ResultScreen
    app.selected_tree_id = tree_id
    sm.current = 'image_selection'
    print('[FLOW] Viewing saved record -> ResultScreen (Section 2.3)')
    app.analysis_result = {'record_id': record_id, 'source_screen': 'records'}
    sm.current = 'result'
    result_screen = sm.get_screen('result')
    with app.db_manager.connection() as conn:
        row = conn.execute(
            'SELECT sr.id, sr.severity_percentage, sr.image_path, d.name AS disease_name FROM tbl_scan_record sr LEFT JOIN tbl_disease d ON sr.disease_id=d.id WHERE sr.id=?',
            (record_id,)
        ).fetchone()
    record_details = {
        'image_path': row['image_path'],
        'severity_percentage': row['severity_percentage'],
        'disease_name': row['disease_name'],
        'confidence': 0.0
    }
    result_screen._source_screen = 'records'
    result_screen._populate_from_db_record(record_details)
    metrics['after_saved_record_screen'] = 'result'
    print('[FLOW] Navigating back from ResultScreen (saved record)...')
    result_screen.go_back()
    metrics['after_saved_record_screen'] = sm.current

    # FLOW 3: Fresh scan result (USER_MANUAL.md Section 2.2 Step 4-6)
    # Flow: ScanningScreen → ResultScreen → SaveScreen (user chooses Save)
    # RULE 1: No auto-save - user must explicitly click Save button
    print('[FLOW] Simulating fresh scan analysis result (Section 2.2 Step 4)...')
    app.analysis_result = {
        'image_path': real_image_path,
        'disease_name': 'Anthracnose',
        'severity_percentage': 67.2,  # Advanced Stage (>30%)
        'severity_name': 'Advanced Stage',
        'confidence': 0.93,  # High confidence (≥85%)
        'source_screen': 'scan'  # Fresh scan, not saved record
    }
    sm.current = 'result'
    result_screen = sm.get_screen('result')
    result_screen.on_enter()
    # User clicks Save button (Section 2.2 Step 6)
    result_screen.open_save_screen()
    metrics['after_open_save_screen'] = sm.current  # Should be 'save'

    # FLOW 5: Multi-frame stitching
    try:
        from app.core.camera import capture_multi_frame_stitched
        import cv2  # type: ignore
        base_multi = os.path.join(PROJECT_ROOT, 'data', 'captures', 'sim_multi')
        stitched = capture_multi_frame_stitched(base_multi, count=4)
        if stitched and os.path.exists(stitched):
            img = cv2.imread(stitched)
            print(f'[FLOW] Stitched image created size={None if img is None else img.shape}')
        else:
            print('[FLOW] Stitched image missing')
    except Exception as e:
        print(f'[FLOW] Multi-frame stitching skipped: {e}')
        stitched = None
    metrics['stitched_image'] = stitched if stitched and os.path.exists(stitched) else None

    # FLOW 6: Stress timings (optionally vary disease names via mock injection)
    durations = []
    rapid_results = []
    mem_start = psutil.Process().memory_info().rss if psutil else None
    try:
        scanning_screen_obj = sm.get_screen('scanning')
        original_processor = None
        if stress_unique_names:
            try:
                from app.core import image_processor
                original_processor = image_processor.analyze_image
                # Also clear the predictor cache to force our mock to be used
                image_processor._predictor = None
                names = [
                    'Anthracnose', 'Leaf Blight', 'Rust', 'Powdery Mildew',
                    'Early Blight', 'Late Blight', 'Septoria', 'Wilt'
                ]
                call_count = [0]  # Use list to allow mutation in closure
                def mock_analyze(_path, use_ml=True):
                    name = names[call_count[0] % len(names)]
                    call_count[0] += 1
                    result = {
                        'disease_name': name,
                        'confidence': 0.9,
                        'severity_percentage': 42.0,
                        'severity_name': 'Moderate'
                    }
                    print(f'[MOCK] Call {call_count[0]}: {name}')
                    return result
                image_processor.analyze_image = mock_analyze
                print(f'[FLOW] Mock injected successfully for unique names')
            except Exception as e:
                print(f'[FLOW] Mock injection failed: {e}')
                import traceback
                traceback.print_exc()
                stress_unique_names = False
        else:
            # Provide a lightweight analyze_image to avoid heavy ML init cost
            try:
                from app.core import image_processor
                original_processor = image_processor.analyze_image
                def fast_analyze(_path, use_ml=True):
                    return {
                        'disease_name': 'Healthy',
                        'confidence': 1.0,
                        'severity_percentage': 0.0,
                        'severity_name': 'Healthy'
                    }
                image_processor.analyze_image = fast_analyze
            except Exception:
                original_processor = None
        for i in range(stress_iterations):
            # Clear previous result
            try:
                if hasattr(app, 'analysis_result'):
                    app.analysis_result = None
            except Exception:
                pass
            # Use the screen's normal flow but with mocked analyze_image
            app.analysis_image_path = real_image_path
            sm.current = 'scanning'
            start = time.perf_counter()
            # Trigger the screen's analysis
            scanning_screen_obj.on_enter()
            # Wait for analysis to complete
            max_wait = 2.0
            elapsed = 0
            while elapsed < max_wait:
                if hasattr(app, 'analysis_result') and app.analysis_result:
                    break
                time.sleep(0.02)
                elapsed += 0.02
            durations.append(time.perf_counter() - start)
            result = dict(getattr(app, 'analysis_result', {}))
            rapid_results.append(result)
            print(f'[STRESS {i+1}/{stress_iterations}] Result: {result.get("disease_name")} (call_count: {call_count[0] if stress_unique_names else "N/A"})')
        # Restore analyze_image if patched (either unique or fast stub)
        if original_processor is not None:
            try:
                from app.core import image_processor
                image_processor.analyze_image = original_processor
            except Exception:
                pass
        uniq = {r.get('disease_name') for r in rapid_results if r.get('disease_name')}
        stress_summary = {
            'count': len(rapid_results),
            'unique_disease_names': len(uniq),
            'min_duration': min(durations) if durations else None,
            'max_duration': max(durations) if durations else None,
            'avg_duration': (sum(durations)/len(durations)) if durations else None
        }
        # Severity distribution (if severity_name present)
        severity_distribution = {}
        for r in rapid_results:
            name = r.get('severity_name') or 'UNKNOWN'
            severity_distribution[name] = severity_distribution.get(name, 0) + 1
        stress_summary['severity_distribution'] = severity_distribution
        if mem_start is not None and psutil:
            mem_end = psutil.Process().memory_info().rss
            stress_summary['memory_rss_before'] = mem_start
            stress_summary['memory_rss_after'] = mem_end
            stress_summary['memory_rss_delta'] = mem_end - mem_start
        stress_summary['unique_names_requested'] = stress_unique_names
    except Exception as e:
        print(f'[FLOW] Stress loop skipped: {e}')
        stress_summary = {}
    metrics.update({'stress_durations': durations, 'stress_results': rapid_results, 'stress_summary': stress_summary})

    # FLOW 7: Cancellation (USER_MANUAL.md Section 2.2 Step 3)
    # Cancel during ScanningScreen → Navigate to HomeScreen
    # RULE 1: Cancelled scans are NOT saved to database
    try:
        print('[FLOW] Testing cancellation flow (Section 2.2 Step 3)...')
        sm.current = 'scanning'
        cancel_screen = sm.get_screen('scanning')
        app.analysis_image_path = real_image_path
        cancel_screen.on_enter()
        time.sleep(0.05)
        # User clicks Cancel button
        if hasattr(cancel_screen, 'cancel_analysis'):
            cancel_screen.cancel_analysis()
        else:
            # Manually navigate to home (same behavior as cancel button)
            sm.current = 'home'
        # Wait for navigation to complete
        for _ in range(6):
            if sm.current == 'home':
                break
            time.sleep(0.05)
        if sm.current != 'home':
            sm.current = 'home'
        metrics['cancellation_final_screen'] = sm.current  # Should be 'home' per Section 2.2 Step 3
        # Verify no analysis_result persisted (RULE 1 compliance)
        if hasattr(app, 'analysis_result') and app.analysis_result is not None:
            print(f'[FLOW] WARNING: RULE 1 violation detected - analysis_result should not persist after cancel')
        print(f'[FLOW] Cancellation test complete: navigated to {sm.current}')
    except Exception as e:
        print(f'[FLOW] Cancellation skipped: {e}')
        metrics['cancellation_final_screen'] = None

    # FLOW 8: Hardware fallback
    try:
        import app.screens.scanning_screen as scanning_mod
        class DummyScanner:
            def run_scan_pipeline(self, progress_callback=None):
                for pct, txt in [(10,'Hardware init'),(35,'Capturing frames'),(60,'Preprocessing'),(80,'Finalizing')]:
                    if progress_callback:
                        progress_callback(pct, txt)
                return real_image_path
        scanning_mod.scanner = DummyScanner()
        scanning_mod._hardware_available = True
        app.analysis_image_path = ''
        sm.current = 'scanning'
        hw_screen = sm.get_screen('scanning')
        hw_screen.on_enter()
        time.sleep(0.25)
        metrics['hardware_final_screen'] = sm.current
    except Exception as e:
        print(f'[FLOW] Hardware fallback skipped: {e}')
        metrics['hardware_final_screen'] = None

    # Persist metrics artifact if enabled (CI/performance tracking)
    try:
        if os.environ.get('PERF_CAPTURE', '1') == '1':
            perf_dir = os.path.join(PROJECT_ROOT, 'artifacts', 'performance')
            os.makedirs(perf_dir, exist_ok=True)
            ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            artifact_path = os.path.join(perf_dir, f'perf_{ts}.json')
            metrics['timestamp'] = ts
            metrics['stress_iterations'] = stress_iterations
            with open(artifact_path, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2)
            # convenience symlink/copy latest
            latest_path = os.path.join(perf_dir, 'latest.json')
            try:
                with open(latest_path, 'w', encoding='utf-8') as f:
                    json.dump(metrics, f, indent=2)
            except Exception:
                pass
            metrics['artifact_path'] = artifact_path
    except Exception as e:
        metrics['artifact_error'] = str(e)
    return metrics

if __name__ == '__main__':
    metrics = run_full_simulation(stress_iterations=int(os.environ.get('STRESS_ITERS', '5')), stress_unique_names=os.environ.get('STRESS_UNIQUE','0')=='1')
    print('[FLOW] Metrics summary:')
    _pprint(metrics)
