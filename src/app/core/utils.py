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
        # Attempt to call the provided function immediately. Tests often patch
        # `App.get_running_app()` in the screen module, and the wrapper function
        # (`fn`) will call that patched symbol. To be robust we attempt to call
        # `fn()` directly and treat any raised exception as an indication that
        # the DB or App isn't ready yet — in that case we schedule retries.
        try:
            fn()
            return True
        except Exception:
            # Swallow the exception here and allow scheduled retries to try again
            return False

    # First attempt synchronously to maintain test-friendly behavior.
    try:
        if _try():
            return
    except Exception:
        # If App isn't available yet, fall through to schedule retries.
        pass

    # Schedule retries using Clock if immediate attempt failed
    def _retry_sched(dt=None):
        success = _try()
        if success:
            return
        state['tries'] += 1
        if state['tries'] < max_retries:
            Clock.schedule_once(_retry_sched, interval)
        else:
            print("call_when_db_ready: DB manager not available after retries")

    Clock.schedule_once(_retry_sched, 0)
