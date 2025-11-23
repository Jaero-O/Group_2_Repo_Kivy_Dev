#!/usr/bin/env python3
"""Capture current app screens after simulating backend-driven flow.

This script builds the Kivy app without starting the full event loop,
executes a minimal workflow to populate backend state (DB init, image
selection to feed analysis), then iterates over all registered screens
and saves screenshots to `screenshots/current`.

It uses the sample image at `ml/leaf-detection/scripts/20211231_123305 (Custom).jpg`.
"""
import os
import importlib.util
from kivy.app import App
from kivy.core.window import Window

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MAIN_PATH = os.path.join(PROJECT_ROOT, 'main.py')
OUT_DIR = os.path.join(PROJECT_ROOT, 'screenshots', 'current')
SAMPLE_IMAGE = os.path.join(PROJECT_ROOT, 'ml', 'leaf-detection', 'scripts', '20211231_123305 (Custom).jpg')


def load_app():
    spec = importlib.util.spec_from_file_location('main_mod', MAIN_PATH)
    main_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_mod)
    MangofyApp = main_mod.MangofyApp
    app = MangofyApp()
    # Make App.get_running_app() return our instance
    App._running_app = app
    root = app.build()
    app.finish_loading(0)
    return app


def ensure_output_dir():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR, exist_ok=True)


def simulate_flow(app):
    try:
        # Navigate to scan and select image to populate backend analysis_result
        app.sm.current = 'scan'
        scan_screen = app.sm.get_screen('scan')
        if os.path.exists(SAMPLE_IMAGE):
            scan_screen.select_image(SAMPLE_IMAGE)
        # Trigger scanning on_enter if available to compute results
        try:
            scanning = app.sm.get_screen('scanning')
            scanning.on_enter()
        except Exception:
            pass
    except Exception:
        # Flow is best-effort; continue to capture regardless
        pass


def capture_all(app):
    ensure_output_dir()
    # Iterate in the order they are registered
    for s in app.sm.screens:
        try:
            app.sm.current = s.name
            # Allow layout to settle minimally by forcing a frame flip via size update
            Window.size = (Window.width, Window.height)
            out = os.path.join(OUT_DIR, f"{s.name}0001.png")
            Window.screenshot(out)
        except Exception:
            pass


def main():
    app = load_app()
    simulate_flow(app)
    capture_all(app)


if __name__ == '__main__':
    main()
