import os
from kivy.app import App
from .settings import setup_window, BASE_WIDTH, BASE_HEIGHT
from .utils import scale_x, scale_y, responsive_font
from .models import AnthracnoseClassifier
from .image_processor import analyze_image
from .widgets import RoundedButton, ScanButton, GradientScanButton
from .database import DatabaseManager

user_data_dir = App.get_running_app().user_data_dir if App.get_running_app() else "."
db_path = os.path.join(user_data_dir, "mangofy.db")

db_manager = DatabaseManager(db_path=db_path)

def init_db():
    """A proxy function to initialize the database via the singleton."""
    db_manager.initialize_database()

__all__ = [
    "setup_window",
    "BASE_WIDTH", "BASE_HEIGHT",
    "scale_x", "scale_y", "responsive_font",
    "AnthracnoseClassifier",
    "analyze_image",
    "RoundedButton", "ScanButton", "GradientScanButton",
    "db_manager", "init_db"
]
