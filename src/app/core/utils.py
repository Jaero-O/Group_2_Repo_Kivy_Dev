# app/core/utils.py
from kivy.core.window import Window
from kivy.metrics import sp
from kivy.clock import Clock
from kivy.app import App
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


def call_when_db_ready(fn, max_retries=10, interval=0.1):
    """Schedule `fn()` to be called when `App.get_running_app().db_manager` exists.

    fn: callable with no args. Retries calling `fn` until db_manager is available
    or until `max_retries` have elapsed. Uses Kivy's Clock to schedule retries.
    """
    state = {'tries': 0}

    def _try(dt=None):
        app = None
        try:
            app = App.get_running_app()
        except Exception:
            app = None

        if app and getattr(app, 'db_manager', None):
            try:
                fn()
            except Exception as e:
                print(f"Error while executing DB callback: {e}")
        else:
            state['tries'] += 1
            if state['tries'] < max_retries:
                Clock.schedule_once(_try, interval)
            else:
                print("call_when_db_ready: DB manager not available after retries")

    # Start on next frame to ensure App may have been created
    Clock.schedule_once(_try, 0)
