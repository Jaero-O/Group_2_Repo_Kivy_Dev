----
---- a/main.py
----
# Mangofy App: Full Implementation Plan

This document outlines the complete implementation plan for the Mangofy Kivy application, covering the backend architecture, database schema, frontend screen integration, and the data flow between them.

## Table of Contents
1.  Project Architecture Overview
2.  Phase 1: Backend and Database Setup
    -   Database Schema
    -   Core Module: `database.py`
    -   Core Module: `image_processor.py`
    -   Application Startup Integration
3.  Phase 2: Frontend and Backend Integration
    -   Data Flow: From Scan to Save
    -   Screen-by-Screen Integration Plan
        -   `ResultScreen`
        -   `RecordsScreen`
        -   `AnthracnoseScreen`
4.  Implementation Code
    -   A. `app/core/database.py` (Additions)
    -   B. `app/core/__init__.py` (Update)
    -   C. `main.py` (Verification)

---

## 1. Project Architecture Overview

The application is built on Kivy and follows a modular structure.

-   **Frontend (`app/screens/`, `app/kv/`)**: Consists of multiple `Screen` widgets, each with a corresponding `.kv` file for layout and styling. The `ScreenManager` in `main.py` handles navigation.
-   **Backend (`app/core/`)**: A local backend composed of Python modules responsible for business logic.
    -   `database.py`: Manages all interactions with the SQLite database. It is designed to be thread-safe and asynchronous to prevent UI freezes.
    -   `image_processor.py`: A placeholder module for image analysis logic (e.g., using OpenCV) to calculate disease severity.
    -   `ml_model.py` (Future): A module to encapsulate the TensorFlow Lite model loading and prediction logic.
-   **Database**: A single SQLite file (`mangofy.db`) stored in the user's data directory, ensuring data persistence across app updates.

## 2. Phase 1: Backend and Database Setup

This phase establishes the data storage and business logic foundation.

### Database Schema

The database consists of three tables:

1.  `tbl_disease` (Lookup Table)
    -   `id`: INTEGER, PRIMARY KEY
    -   `name`: TEXT, UNIQUE (e.g., 'Anthracnose', 'Healthy')
    -   `description`: TEXT
    -   `symptoms`: TEXT
    -   `prevention`: TEXT

2.  `tbl_severity_level` (Lookup Table)
    -   `id`: INTEGER, PRIMARY KEY
    -   `name`: TEXT, UNIQUE (e.g., 'Early Stage', 'Advanced Stage')
    -   `description`: TEXT

3.  `tbl_scan_record` (Main Data Table)
    -   `id`: INTEGER, PRIMARY KEY
    -   `scan_timestamp`: DATETIME
    -   `disease_id`: INTEGER (Foreign Key to `tbl_disease.id`)
    -   `severity_level_id`: INTEGER (Foreign Key to `tbl_severity_level.id`)
    -   `severity_percentage`: REAL (e.g., 15.7)
    -   `image_path`: TEXT (Path to the saved scan image)
    -   `is_archived`: INTEGER (0 for false, 1 for true)

### Core Module: `database.py`

This module, located at `app/core/database.py`, encapsulates all database logic using a `DatabaseManager` class.

-   **Initialization**: `initialize_database()` creates tables and populates the lookup tables (`tbl_disease`, `tbl_severity_level`) with default data if they are empty.
-   **Connections**: Uses optimized, thread-safe connections with WAL mode for performance on devices with SD cards (like Raspberry Pi).
-   **Asynchronous Operations**: Database writes (`save_record_async`) and reads (`get_all_records_async`) run in separate threads to keep the UI responsive. Callbacks are used to return data to the main Kivy thread.
-   **Data Retrieval**: Provides methods like `get_lookup_ids` to find foreign keys and `get_all_records_async` to fetch data for the history screen.

### Core Module: `image_processor.py`

Located at `app/core/image_processor.py`, this module contains the `calculate_severity` function.

-   **Purpose**: To analyze a given image and return the percentage of the area affected by disease.
-   **Current Status**: It's a placeholder that returns a mock value.
-   **Future Work**: This function will be implemented with actual image processing logic using a library like OpenCV.

### Application Startup Integration

In `main.py`, the database is initialized when the app starts. This ensures all tables are ready before any screen needs to access them.

```python
# main.py
from app.core import database

# ...

# INITIAL SETUP
# =========================================
setup_window()
# Initialize the database on startup
database.init_db() # This line is crucial

# ...
```

## 3. Phase 2: Frontend and Backend Integration

This phase connects the UI screens to the backend logic.

### Data Flow: From Scan to Save

1.  **Capture/Select Image**: The user uses the `ScanScreen` (camera) or `ImageSelection` screen to provide an image. The path to this image is stored.
2.  **Analyze**: The app navigates to `CaptureResultScreen` and then to `ResultScreen`.
3.  **ML Prediction**: On the `ResultScreen`, the ML model is run on the image to predict the `disease_name` and `severity_name`.
4.  **Calculate Severity %**: The `image_processor.calculate_severity(image_path)` function is called to get the `severity_percentage`.
5.  **Fetch IDs**: The app calls `database.get_lookup_ids(disease_name, severity_name)` to get the corresponding foreign keys from the database.
6.  **Save Record**: When the user clicks "Save", the `ResultScreen` calls `database.save_record_async()` with all the collected information (`disease_id`, `severity_level_id`, `severity_percentage`, `image_path`).
7.  **Confirmation**: A callback from `save_record_async` updates the UI to confirm the save (e.g., shows a popup or navigates to the `SaveScreen`).

### Screen-by-Screen Integration Plan

#### `ResultScreen`
-   **Objective**: Display the analysis result and provide an option to save it.
-   **Integration Steps**:
    1.  The screen will receive the `image_path`, `disease_name`, and `severity_name` when it's displayed.
    2.  In its `on_enter` method, it will call `image_processor.calculate_severity()` to get the severity percentage.
    3.  It will call `database.get_lookup_ids()` to fetch the necessary foreign keys.
    4.  The "Save" button's `on_press` event will trigger `database.save_record_async()` with the collected data.
    5.  It will define `on_save_success` and `on_save_error` callback methods to handle the result of the save operation (e.g., show a confirmation message).

#### `RecordsScreen`
-   **Objective**: Display a list of all previously saved scan records.
-   **Integration Steps**:
    1.  In its `on_enter` method, it will call `database.get_all_records_async(on_success_callback=self.populate_records)`.
    2.  It will have a method `populate_records(records)` that receives the list of records from the database.
    3.  Inside `populate_records`, it will clear any existing widgets in its list view (e.g., a `ScrollView` with a `GridLayout`).
    4.  It will then iterate through the `records` list and create a custom widget for each record (e.g., displaying the image thumbnail, disease name, and timestamp) and add it to the list view.

#### `AnthracnoseScreen`
-   **Objective**: Display detailed, static information about a specific disease.
-   **Integration Steps**:
    1.  This screen can be enhanced to pull its content dynamically from the database.
    2.  In its `on_enter` method, it could call a new database function, e.g., `database.get_disease_details_by_name('Anthracnose')`.
    3.  The returned data (description, symptoms, prevention) would then be used to populate the labels on the screen. This makes the content easily updatable via the database.

---

## 4. Implementation Code

The following code changes are required to complete the integration.

### A. `app/core/database.py` (Additions)

Add the following methods to the `DatabaseManager` class in `app/core/database.py` to support fetching records and lookup IDs.

```python
# Add these methods inside the DatabaseManager class in app/core/database.py

def get_lookup_ids(self, disease_name, severity_name):
    """
    Retrieves the IDs for a given disease and severity name.
    Returns (None, None) if not found.
    """
    disease_id = None
    severity_level_id = None
    try:
        with closing(self._create_connection()) as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM tbl_disease WHERE name = ?", (disease_name,))
            row = c.fetchone()
            if row:
                disease_id = row['id']

            c.execute("SELECT id FROM tbl_severity_level WHERE name = ?", (severity_name,))
            row = c.fetchone()
            if row:
                severity_level_id = row['id']

        return disease_id, severity_level_id
    except Exception as e:
        print(f"Error getting lookup IDs for '{disease_name}', '{severity_name}': {e}")
        return None, None

def get_all_records_async(self, on_success_callback, on_error_callback=None):
    """Asynchronously retrieves all scan records from the database."""
    threading.Thread(target=self._threaded_get_all_records,
                     args=(on_success_callback, on_error_callback)).start()

def _threaded_get_all_records(self, on_success_callback, on_error_callback):
    """Internal method to run the DB select operation in a separate thread."""
    try:
        with closing(self._create_connection()) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT
                    r.id,
                    r.scan_timestamp,
                    r.severity_percentage,
                    r.image_path,
                    d.name as disease_name,
                    s.name as severity_name
                FROM tbl_scan_record r
                LEFT JOIN tbl_disease d ON r.disease_id = d.id
                LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
                WHERE r.is_archived = 0
                ORDER BY r.scan_timestamp DESC
            """)
            records = [dict(row) for row in c.fetchall()]
        self._send_callback_to_main_thread(on_success_callback, records)
    except Exception as e:
        print(f"Error getting all records: {e}")
        if on_error_callback:
            self._send_callback_to_main_thread(on_error_callback, f"Error: {e}")

```

### B. `app/core/__init__.py` (Update)

Expose the `DatabaseManager` instance so it can be accessed globally and consistently throughout the app.

```python
# app/core/__init__.py
import os
from kivy.app import App
from .settings import setup_window, BASE_WIDTH, BASE_HEIGHT
from .utils import scale_x, scale_y, responsive_font
from .widgets import RoundedButton, ScanButton, GradientScanButton
from .database import DatabaseManager

# --- DATABASE SINGLETON ---
# Get the app's user data directory in a platform-independent way
user_data_dir = App.get_running_app().user_data_dir if App.get_running_app() else "."
db_path = os.path.join(user_data_dir, "mangofy.db")

# Create a single, globally accessible instance of the DatabaseManager
db_manager = DatabaseManager(db_path=db_path)

def init_db():
    """A proxy function to initialize the database via the singleton."""
    db_manager.initialize_database()

__all__ = [
    "setup_window",
    "BASE_WIDTH", "BASE_HEIGHT",
    "scale_x", "scale_y", "responsive_font",
    "RoundedButton", "ScanButton", "GradientScanButton",
    "db_manager", "init_db"
]
```

### C. `main.py` (Verification)

Your `main.py` already correctly calls `database.init_db()`. With the change in `app/core/__init__.py`, this will now correctly initialize the singleton `DatabaseManager` instance. No changes are needed in `main.py`, but its correctness is confirmed.

