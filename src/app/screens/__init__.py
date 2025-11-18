# This file makes the 'screens' directory a Python package.

# By importing all screen classes here, they become accessible under the 'app.screens'
# namespace, which simplifies the import statements in main.py.
from .about_us_screen import AboutUsScreen
from .anthracnose_screen import AnthracnoseScreen
from .capture_result_screen import CaptureResultScreen
from .guide_screen import GuideScreen
from .help_screen import HelpScreen
from .home_screen import HomeScreen
from .image_selection_screen import ImageSelectionScreen
from .precaution_screen import PrecautionScreen
from .records_screen import RecordsScreen
from .result_screen import ResultScreen
from .save_screen import SaveScreen
from .scan_screen import ScanScreen
from .scanning_screen import ScanningScreen
from .share_screen import ShareScreen
from .system_spec_screen import SystemSpecScreen
from .welcome_screen import WelcomeScreen