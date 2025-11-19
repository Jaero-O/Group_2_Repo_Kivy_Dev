import os, shutil, pytest

FULL_UI = os.environ.get('FULL_UI_TEST') == '1'

if FULL_UI:
    # Explicit full UI mode: ensure headless flag is disabled.
    os.environ['HEADLESS_TEST'] = '0'
    # Remove mock backend overrides if previously set.
    for var in ('KIVY_WINDOW','KIVY_GL_BACKEND'):
        if var in os.environ and os.environ[var] == 'mock':
            os.environ.pop(var, None)
else:
    # Signal headless test mode.
    os.environ.setdefault('HEADLESS_TEST', '1')
    # Use mock backends to reduce reliance on real window/GL.
    os.environ.setdefault('KIVY_WINDOW', 'mock')
    os.environ.setdefault('KIVY_GL_BACKEND', 'mock')

# Patch EventLoop.ensure_window early so importing widgets in tests
# doesn't try to create a real window and abort the process.
if not FULL_UI:
    try:
        from kivy.base import EventLoop
        def _noop_ensure_window(*args, **kwargs):
            return None
        EventLoop.ensure_window = _noop_ensure_window
    except Exception:
        pass

# Selective skipping of UI-heavy tests that trigger canvas/texture creation
# which is unstable under the mock window backend.
UI_PATTERNS = [
    # scanning / capture flows
    'scanning_screen', 'scanning_flow', 'scan_capture', 'scan_fallback', 'scanning_thread_stress',
    # complex widget / canvas tests
    'fallback_error_indicator', 'kv_smoke', 'lcd_app_integration', 'multi_frame_capture', 'other_screens',
    'placeholder_banner', 'records_screen', 'result_screen', 'save_screen', 'image_selection_screen',
    'cancel_behavior', 'benchmark_raw_vs_normalized', 'performance_image_analysis', 'image_pipeline',
    'image_processor', 'main_app', 'app_db_file'
]

def pytest_collection_modifyitems(config, items):
    if FULL_UI or os.environ.get('HEADLESS_TEST') != '1':
        return
    skip_ui = pytest.mark.skip(reason='Skipped in headless mode (UI-heavy test).')
    for item in items:
        nodeid_lower = item.nodeid.lower()
        if any(pat in nodeid_lower for pat in UI_PATTERNS):
            item.add_marker(skip_ui)


# ---------------------------------------------------------------------------
# Test-only camera/image fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def deterministic_camera(monkeypatch):
    """Provide deterministic camera capture behavior for tests.

    Usage in a test:
        def test_flow(deterministic_camera):
            ...

    The fixture monkeypatches `capture_image_raspicam` and
    `capture_multi_frame_stitched` so they always return a stable
    placeholder image path. This keeps production code untouched while
    giving tests repeatable inputs.
    """
    placeholder = os.path.join(os.path.dirname(__file__), '..', 'src', 'app', 'assets', 'placeholder_bg1.png')
    placeholder = os.path.abspath(os.path.normpath(placeholder))

    # Ensure placeholder exists (copy from references if missing)
    if not os.path.exists(placeholder):
        # Attempt fallback to any existing figma reference welcome.png
        alt = os.path.join(os.path.dirname(__file__), '..', 'screenshots', 'references_figma', 'welcome.png')
        alt = os.path.abspath(os.path.normpath(alt))
        if os.path.exists(alt):
            os.makedirs(os.path.dirname(placeholder), exist_ok=True)
            try:
                shutil.copyfile(alt, placeholder)
            except Exception:
                pass

    def _fake_capture(path: str, *args, **kwargs):  # mimic signature subset
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # Copy placeholder so caller can rely on path existing
            if os.path.exists(placeholder):
                try:
                    shutil.copyfile(placeholder, path)
                except Exception:
                    pass
        except Exception:
            pass
        return path

    def _fake_multi(base_path: str, count: int = 4):
        return placeholder

    try:
        import app.core.camera as cam_mod  # type: ignore
        monkeypatch.setattr(cam_mod, 'capture_image_raspicam', _fake_capture, raising=False)
        monkeypatch.setattr(cam_mod, 'capture_multi_frame_stitched', _fake_multi, raising=False)
    except Exception:
        pass
    return {'placeholder': placeholder}

