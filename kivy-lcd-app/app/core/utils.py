# app/core/utils.py
from kivy.core.window import Window
from kivy.metrics import sp
from app.core.settings import BASE_WIDTH, BASE_HEIGHT

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
