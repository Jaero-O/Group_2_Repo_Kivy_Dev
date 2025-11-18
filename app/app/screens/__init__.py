from .welcome_screen import WelcomeScreen
from .home_screen import HomeScreen
from .scan_screen import ScanScreen
from .result_screen import ResultScreen
from .records_screen import RecordsScreen
from .share_screen import ShareScreen
from .help_screen import HelpScreen
from .guide_screen import GuideScreen
from .scanning_screen import ScanningScreen
from .capture_result_screen import CaptureResultScreen
from .result_screen import ResultScreen
from .save_screen import SaveScreen
from .image_selection_screen import ImageSelectionScreen
from .anthracnose_screen import AnthracnoseScreen
from .system_spec_screen import SystemSpecScreen
from .precaution_screen import PrecautionScreen
from .about_us_screen import AboutUsScreen
from .image_selection_screen import ImageSelectionScreen

# You can add other screens here as you create them

# This makes it possible to do `from app.screens import HomeScreen, ...`
__all__ = ["HomeScreen", "ScanScreen", "ResultScreen", "RecordsScreen", "ImageSelectionScreen"]
