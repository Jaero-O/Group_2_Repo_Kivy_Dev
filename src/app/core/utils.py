# app/core/utils.py
from kivy.core.window import Window
from kivy.metrics import sp
from src.app.core.settings import BASE_WIDTH, BASE_HEIGHT

# =========================================
# ✅ RESPONSIVE UTILS
# =========================================
def scale_x(px: float) -> float:
    """Scale X value based on window width."""
    return px * (Window.width / BASE_WIDTH)

def scale_y(py: float) -> float:
    """Scale Y value based on window height."""
    return py * (Window.height / BASE_HEIGHT)

def responsive_font(size: float) -> float:
    """Responsive font scaling based on width."""
    return sp(size * (Window.width / BASE_WIDTH))


def call_when_db_ready(fn):
    """Compatibility shim: in tests we often call DB helpers immediately.

    In the real app this might wait for background initialization; for
    unit tests and fast-path behavior we call the function immediately.
    """
    try:
        fn()
    except Exception:
        # Swallow exceptions here so callers can decide how to handle errors
        return
