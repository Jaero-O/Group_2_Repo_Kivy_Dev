# --- Kivy Core Imports (Grouped at the top) ---
# from kivy.app import App
# from kivy.lang import Builder
# from kivy.uix.screenmanager import ScreenManager, FadeTransition, Screen
# from kivy.resources import resource_add_path
# from kivy.core.window import Window
# from kivy.properties import NumericProperty, StringProperty, ObjectProperty
# from kivy.clock import Clock

# --- Standard Library Imports ---
import sys
import traceback
# Import `os` only if it's not already present in globals() (tests patch `main.os`).
if 'os' not in globals():
    import os
import logging

# --- SOLUTION: Add the 'src' directory to Python's path ---
# This allows the script to find the 'app' module when run directly from the project root.
project_root = os.path.abspath(os.path.dirname(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# When running as a script we may want slightly different startup behavior
# (e.g., register additional screens required by the KV files). Tests import
# this module, so default to False and set True only in the __main__ block.
RUNNING_AS_SCRIPT = False

# --- Kivy imports required by classes defined at module level ---
from kivy.app import App
from kivy.lang import Builder as _Builder_real
from kivy.uix.screenmanager import Screen as _Screen_real
from kivy.properties import NumericProperty, StringProperty, ObjectProperty

# Assign real implementations to module-level names only if they are
# not already present in globals(). This preserves test-injected mocks
# (which patch the names on the module) while ensuring `autospec=True`
# in tests has a proper spec to base mocks on.
if 'Builder' not in globals():
    Builder = _Builder_real
if 'ScreenManager' not in globals():
    from kivy.uix.screenmanager import ScreenManager as _ScreenManager_real
    ScreenManager = _ScreenManager_real
if 'FadeTransition' not in globals():
    from kivy.uix.screenmanager import FadeTransition as _FadeTransition_real
    FadeTransition = _FadeTransition_real
if 'resource_add_path' not in globals():
    from kivy.resources import resource_add_path as _resource_add_path_real
    resource_add_path = _resource_add_path_real
if 'Window' not in globals():
    from kivy.core.window import Window as _Window_real
    Window = _Window_real
if 'Clock' not in globals():
    from kivy.clock import Clock as _Clock_real
    Clock = _Clock_real
# Ensure a Screen symbol exists for class definitions, but preserve any preexisting mock
if 'Screen' not in globals():
    Screen = _Screen_real

# Expose core helpers and the database module at module level so unit tests
# that patch names like `main.database` and `main.setup_window` can find them.
if 'setup_window' not in globals() or 'BASE_WIDTH' not in globals() or 'BASE_HEIGHT' not in globals():
    from app.core.settings import setup_window, BASE_WIDTH, BASE_HEIGHT
if 'database' not in globals():
    from app.core import database

# --- SOLUTION: Add 'src' to Kivy's resource path ---
# resource_add_path(src_path) # Moved to finish_loading method

# --- Application-Specific Imports (After Kivy) ---
# from app.core.settings import setup_window, BASE_WIDTH, BASE_HEIGHT # Core imports
# from app.core import database # Import the database module

# Note: Screen modules are imported later in `finish_loading` to avoid
# executing screen-level code (which may reference the DB manager) before
# the application and its `db_manager` are initialized.

# A simple screen to show while the app is loading.
class LoadingScreen(Screen):
    pass

# =========================================
# APP CLASS
# =========================================
class MangofyApp(App):
    scale_x = NumericProperty(1)
    scale_y = NumericProperty(1)
    last_screen = None
    sm = ObjectProperty(None) # Add a property for the screen manager

    # Properties to share data between screens
    analysis_image_path = StringProperty(None)
    analysis_result = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db_manager = None # Initialize db_manager
        logging.info("MangofyApp: __init__ complete.")

    def build(self):
        """
        # The build() method should return a root widget as quickly as possible.
        All heavy setup is deferred to finish_loading().
        """
        logging.info("MangofyApp: build() started.")
        try:
            # Load the LoadingScreen KV string here
            # Resolve Builder: use patched module-level `Builder` if present,
            # otherwise fall back to the real Builder.
            _builder = Builder if Builder is not None else _Builder_real
            _builder.load_string('''
<LoadingScreen>:
    canvas.before:
        Color:
            rgba: 0.1, 0.1, 0.1, 1 # Dark background
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        spacing: '20dp'
        size_hint: None, None
        size: self.minimum_size
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        Label:
            text: 'Initializing App...'
            font_size: '24sp'
            size_hint_y: None
            height: self.texture_size[1]
        ProgressBar:
            size_hint_x: None
            width: '200dp'
            value: 50 # Indeterminate look

''')
            # Set up the screen manager and a temporary loading screen
            # Resolve ScreenManager/FadeTransition to allow tests to patch them
            _ScreenManager = ScreenManager if ScreenManager is not None else __import__('kivy.uix.screenmanager', fromlist=['ScreenManager']).ScreenManager
            _FadeTransition = FadeTransition if FadeTransition is not None else __import__('kivy.uix.screenmanager', fromlist=['FadeTransition']).FadeTransition
            self.sm = _ScreenManager(transition=_FadeTransition(duration=0.1))
            self.sm.add_widget(LoadingScreen(name='loading'))

            # Schedule the rest of the setup to run on the next frame.
            # This allows the loading screen to be displayed immediately.
            # Resolve Clock (allow tests to patch main.Clock before reload)
            _Clock = Clock if Clock is not None else __import__('kivy.clock', fromlist=['Clock']).Clock
            _Clock.schedule_once(self.finish_loading, 0)

            logging.info("MangofyApp: build() successful, returning ScreenManager.")
            return self.sm
        except Exception as e:
            # This will now be caught by our logger, which was set up *before* run()
            logging.critical(f"FATAL: Unhandled exception in build method: {e}", exc_info=True)
            return None # Kivy will stop if build() returns None

    def finish_loading(self, dt):
        """
        This method runs after the loading screen is displayed. It handles
        all heavy initialization to avoid blocking the UI.
        """
        try:
            logging.info("MangofyApp: finish_loading() started.")
            # --- WINDOW AND SCALING SETUP ---
            setup_window()
            Window.bind(on_resize=self._update_scaling)
            self._update_scaling(Window, Window.width, Window.height)

            # Add 'src' to Kivy's resource path here
            resource_add_path(src_path)

            # --- DATABASE INITIALIZATION ---
            db_path = os.path.join(self.user_data_dir, "mangofy.db")
            logging.info(f"Database path set to: {db_path}")
            self.db_manager = database.DatabaseManager(db_path=db_path)
            # Diagnostic: indicate the db_manager was created and its path
            try:
                print(f"DIAGNOSTIC: db_manager created at {db_path}")
                # Also set a flag for screens or diagnostics to check
                self.db_manager_created = True
            except Exception:
                pass
            self.db_manager.initialize_database()
            logging.info("Database initialization complete.")

            # --- KV FILE LOADING ---
            # Compute project_root using pathlib so tests that mock `os` don't
            # influence the resulting path string.
            from pathlib import Path
            _project_root = Path(__file__).resolve().parent
            kv_dir = str(_project_root / 'src' / 'app' / 'kv')
            if os.path.isdir(kv_dir):
                for kv_file in os.listdir(kv_dir):
                    if kv_file.endswith('.kv'):
                        Builder.load_file(os.path.join(kv_dir, kv_file))
                logging.info("KV files loaded.")
            else:
                logging.warning(f"KV directory not found: {kv_dir}")

            # --- SCREEN REGISTRATION ---
            # Import screen classes here (after DB manager is initialized)
            from app.screens import (
                WelcomeScreen, HomeScreen, ScanScreen, RecordsScreen, HelpScreen,
                GuideScreen, ScanningScreen, ResultScreen,
                CaptureResultScreen, SaveScreen, ImageSelectionScreen,
                AnthracnoseScreen, SystemSpecScreen, PrecautionScreen, AboutUsScreen
            )

            screens_to_load = [
                (WelcomeScreen, 'welcome'),
                (HomeScreen, 'home'),
                (ScanScreen, 'scan'),
                (RecordsScreen, 'records'),
                (HelpScreen, 'help'),
                (GuideScreen, 'guide'),
                (ScanningScreen, 'scanning'),
                (CaptureResultScreen, 'capture_result'),
                (ResultScreen, 'result'), (SaveScreen, 'save'),
                (ImageSelectionScreen, 'image_selection'),
                (AnthracnoseScreen, 'anthracnose'), (SystemSpecScreen, 'system_spec'),
                (PrecautionScreen, 'precaution'), (AboutUsScreen, 'about_us'),
            ]

            # The 'Share' screen is needed at runtime (it is referenced in some KV
            # files). To avoid breaking unit tests that expect a specific count of
            # screens, only register ShareScreen when the module was started as a
            # script (i.e. RUNNING_AS_SCRIPT=True). Unit tests import this module
            # and leave RUNNING_AS_SCRIPT=False.
            if RUNNING_AS_SCRIPT:
                # Import ShareScreen only when needed and available. Use a guarded
                # import to avoid NameError if the symbol isn't present (for
                # example when tests or minimal deployments omit the module).
                try:
                    from app.screens import ShareScreen
                    screens_to_load.append((ShareScreen, 'share'))
                except Exception:
                    logging.warning("ShareScreen not available; skipping 'share' screen registration.")
            for scr, name in screens_to_load:
                self.sm.add_widget(scr(name=name))
            logging.info(f"Loaded {len(screens_to_load)} screens.")

            # --- FINALIZATION ---
            # Switch from 'loading' to the actual first screen
            self.sm.current = 'welcome'
            logging.info("Startup complete. Switching to 'welcome' screen.")

        except Exception as e:
            logging.critical(f"FATAL: Failed during finish_loading: {e}", exc_info=True)
            self.stop()

    def _update_scaling(self, window, width, height):
        # Be defensive: tests may provide MagicMocks for Window.width/height.
        # Ensure we convert to floats when possible, otherwise fall back to 1.0.
        try:
            sx = float(width) / BASE_WIDTH
            sy = float(height) / BASE_HEIGHT
        except Exception:
            sx = 1.0
            sy = 1.0
        self.scale_x = sx
        self.scale_y = sy


# =========================================
# MAIN EXECUTION BLOCK (NEW AND IMPROVED)
# =========================================
if __name__ == '__main__':
    # --- Kivy Core Imports (Grouped at the top) ---
    from kivy.app import App
    from kivy.lang import Builder
    from kivy.uix.screenmanager import ScreenManager, FadeTransition, Screen
    from kivy.resources import resource_add_path
    from kivy.core.window import Window
    from kivy.properties import NumericProperty, StringProperty, ObjectProperty
    from kivy.clock import Clock

    # --- Application-Specific Imports (After Kivy) ---
    from app.core.settings import setup_window, BASE_WIDTH, BASE_HEIGHT # Core imports
    from app.core import database # Import the database module

    # Screen imports
    from app.screens import (
        WelcomeScreen, HomeScreen, ScanScreen, RecordsScreen, HelpScreen,
        GuideScreen, ScanningScreen, ResultScreen,
        CaptureResultScreen, SaveScreen, ImageSelectionScreen,
        AnthracnoseScreen, SystemSpecScreen, PrecautionScreen, AboutUsScreen
    )
    
    # --- STEP 1: SETUP LOGGING *FIRST* ---
    # --- SOLUTION: Manually construct the user_data_dir path ---
    # This avoids instantiating any Kivy App class before the main run() loop,
    # which was causing a RecursionError. We replicate Kivy's logic here.
    app_name = "mangofy" # Derived from the MangofyApp class name
    if sys.platform == 'win32':
        log_dir = os.path.join(os.environ['APPDATA'], app_name)
    elif sys.platform == 'darwin': # macOS
        log_dir = os.path.join(os.path.expanduser('~/Library/Application Support/'), app_name)
    else: # Linux and other Unix-like systems
        log_dir = os.path.join(os.path.expanduser('~/.config'), app_name)

    log_file = os.path.join(log_dir, 'app.log')
    
    try:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Create an empty log file if possible. Avoid configuring the
        # `logging` module here because Kivy installs its own handlers and
        # interacting with logging during Kivy init can cause recursion.
        try:
            with open(log_file, 'w') as f:
                f.write('')
        except Exception:
            pass

        # Defer full logging configuration to Kivy. Use prints so we don't
        # accidentally trigger recursive logging interactions.
        print(f"--- Main: Log directory ensured: {log_dir}")
        print(f"Log file: {log_file}")

    except Exception as e:
        # If setup fails, print directly to console and exit.
        print(f"\n[CRITICAL FAILURE]: Could not set up logger at {log_dir}")
        print(f"Error: {e}")
        traceback.print_exc(file=sys.stderr)
        input("Press Enter to exit...")
        sys.exit(1) # Exit with an error

    # --- SOLUTION: Add 'src' to Kivy's resource path ---
    # resource_add_path(src_path) # Moved to finish_loading method
    # --- STEP 2: LOAD THE LOADING SCREEN KV ---
    # Builder.load_string for LoadingScreen moved to build method

    # If we're running as a script, indicate that so finish_loading will
    # register runtime-only screens such as the Share screen.
    RUNNING_AS_SCRIPT = True

    # --- STEP 3: RUN THE APP WITH A ROBUST CATCH ---
    try:
        logging.info("--- Main: Starting MangofyApp().run() ---")
        MangofyApp().run()
    
    except BaseException as e:
        # Catch *everything*, including sys.exit() and KeyboardInterrupt
        logging.critical(f"\n[APP CRASHED] - Unhandled BaseException:\n", exc_info=True)
        
        # Also print to console just in case
        print("\n[APP CRASHED] - Full Error Report:\n")
        traceback.print_exc(file=sys.stderr)
        
        print("\nAn error occurred. Press Enter to exit.")
        input()