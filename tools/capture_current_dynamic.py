import importlib.util, os, time
import argparse

# Prevent Kivy from consuming our CLI args
os.environ['KIVY_NO_ARGS'] = '1'

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window

"""Dynamic capture script.
Builds the app, simulates minimal data population (records + analysis image),
then triggers automated multi-screen capture to an alternate directory.
Usage:
  python tools/capture_current_dynamic.py [--out screenshots/current_alt]
Environment overrides:
  ALL_SCREENS_OUTPUT_DIR, EXIT_AFTER_CAPTURE=1, AUTO_CAPTURE_ALL_SCREENS=1 are set automatically.
"""

def main():
    ap = argparse.ArgumentParser(description='Dynamic multi-screen capture with data population.')
    ap.add_argument('--out', default='screenshots/current_alt')
    ap.add_argument('--analysis-image', default='ml/leaf-detection/scripts/20211231_123305 (Custom).jpg')
    ap.add_argument('--wait-seconds', type=float, default=float(os.environ.get('CAPTURE_WAIT_SECS', '6.0')), help='Maximum seconds to wait after app.run() for screenshots to appear.')
    args = ap.parse_args()

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    main_path = os.path.join(project_root, 'main.py')
    spec = importlib.util.spec_from_file_location('main_mod_dyn', main_path)
    main_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_mod)
    MangofyApp = main_mod.MangofyApp

    # Enable automated capture. Defer EXIT_AFTER_CAPTURE until after we populate
    # dynamic data to avoid premature shutdown if finish_loading schedules capture
    # before we inject records.
    os.environ['AUTO_CAPTURE_ALL_SCREENS'] = '1'
    os.environ['ALL_SCREENS_OUTPUT_DIR'] = args.out
    # EXIT_AFTER_CAPTURE will be set later once population is done.

    app = MangofyApp()
    App._running_app = app  # allow other modules to access running app if needed
    # IMPORTANT: Do not call build() manually; app.run() will invoke build().
    # DO NOT call finish_loading manually; build() already scheduled it. Calling
    # it again leads to duplicate initialization and potential failures.

    # Populate dynamic data before capture begins (capture starts after 0.2s per main.py)
    # We need to populate AFTER finish_loading completes. Poll sm for expected screens.
    from kivy.clock import Clock

    def _populate_and_enable_exit(dt):
        try:
            # Ensure finish_loading executed: presence of non-loading screens and db_manager set
            if not getattr(app, 'db_manager', None):
                # Reschedule quickly until ready
                Clock.schedule_once(_populate_and_enable_exit, 0.05)
                return
            # Fallback analysis image if provided path missing
            analysis_image = args.analysis_image
            if not os.path.isfile(analysis_image):
                placeholder = os.path.join(project_root, 'src', 'app', 'assets', 'placeholder_bg1.png')
                if os.path.isfile(placeholder):
                    analysis_image = placeholder
            # Select image if scan screen is available
            if 'scan' in [s.name for s in app.sm.screens]:
                try:
                    scan_screen = app.sm.get_screen('scan')
                    scan_screen.select_image(analysis_image)
                except Exception as e:
                    print('WARN: select_image failed:', e)
            # Insert sample tree & record
            try:
                db = app.db_manager
                tree_id = db.add_tree_sync('Dynamic Capture Tree')
                recs = [{'disease_name': 'Healthy', 'severity_name': 'Healthy', 'severity_percentage': 0.0, 'image_path': analysis_image}]
                db.bulk_insert_records(recs, tree_id=tree_id)
            except Exception as e:
                print('WARN: record insertion failed:', e)
            # Now allow app to exit after capture sequence completes
            os.environ['EXIT_AFTER_CAPTURE'] = '1'
        except Exception as e:
            print('WARN: populate sequence error:', e)

    # Schedule population slightly after startup but before first capture (capture starts at ~0.2s)
    Clock.schedule_once(_populate_and_enable_exit, 0.05)

    # Run the app main loop long enough for captures to finish
    # We rely on EXIT_AFTER_CAPTURE=1 for shutdown.
    try:
        app.run()
    except BaseException as e:
        print('ERROR: capture run crashed:', e)
    # Post-run verification of screenshots
    import sys
    # Blocking wait: poll directory until minimum screenshots present or timeout
    required_min = 8  # heuristic: core + several secondary screens
    deadline = time.time() + args.wait_seconds
    last_count = 0
    while time.time() < deadline:
        png_files = [f for f in os.listdir(args.out) if f.lower().endswith('.png')]
        count = len(png_files)
        if count >= required_min:
            break
        last_count = count
        time.sleep(0.25)
    else:
        png_files = [f for f in os.listdir(args.out) if f.lower().endswith('.png')]
    if len(png_files) < required_min:
        print(f'WARN: capture timeout ({args.wait_seconds}s); only {len(png_files)} screenshots: {png_files}')
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    main()
