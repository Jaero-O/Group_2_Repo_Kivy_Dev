import os
import sys
import sqlite3
from glob import glob
import argparse
from kivy.app import App # Use App to derive the user_data_dir
from kivy.clock import Clock
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the project root to the Python path to allow imports from 'app'
# Assuming this script is run from the 'Group_2_Repo_Kivy_Dev' directory.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'kivy-lcd-app'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# This is a mock App class to get the user_data_dir without running the full app
class DummyApp(App):
    def build(self):
        # We need to schedule the stop event to allow the app context to initialize
        Clock.schedule_once(self.stop, 0.1)
        return None

# Run and stop a dummy app to get the user_data_dir correctly
dummy_app = DummyApp()
dummy_app.run()

from app.core.database import DatabaseManager

# --- Synchronous Add-on for DatabaseManager ---
# This is a helper to make scripting easier. We add a synchronous method
# to the class instance for use only within this script.
def add_tree_sync(self, tree_name: str) -> int:
    """Synchronously adds a tree and returns its ID."""
    try:
        with self._create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO tbl_tree (name) VALUES (?)', (tree_name,))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        # If tree exists, find and return its ID
        with self._create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM tbl_tree WHERE name = ?", (tree_name,))
            row = cursor.fetchone()
            return row['id'] if row else None
    except Exception as e:
        print(f"Error in add_tree_sync: {e}")
        return None

from app.core.image_processor import analyze_image # This will use the mock classifier

def process_single_image(image_path: str) -> dict:
    """Analyzes a single image and returns a record dictionary."""
    print(f"Processing {os.path.basename(image_path)}...")
    analysis_result = analyze_image(image_path)
    
    return {
        "image_path": image_path,
        "disease_name": analysis_result.get("disease_name", "Unknown"),
        "severity_percentage": analysis_result.get("severity_percentage", 0.0),
        "severity_name": analysis_result.get("severity_name", "Healthy")
    }


def populate_database_with_dataset(dataset_root: str, clear_existing: bool = False):
    print(f"Starting database population from dataset: {dataset_root}")

    if not os.path.isdir(dataset_root):
        print(f"Error: Dataset directory '{dataset_root}' not found or is not a directory.")
        return

    # --- Database Setup ---
    # We get the user_data_dir from the dummy_app instance that was run earlier.
    # This ensures we're using the same database path as the main application.
    if not dummy_app.user_data_dir:
        print("Error: Could not determine the app's user data directory. Aborting.")
        return

    main_db_path = r"C:\Users\kenne\Group_2_Repo_Kivy_Dev\mangofy.db"
    print(f"Targeting main app database at: {main_db_path}")

    db_manager = DatabaseManager(db_path=main_db_path)
    db_manager.initialize_database()

    # --- Add a synchronous method to the instance for this script's use ---
    DatabaseManager.add_tree_sync = add_tree_sync
    
    # Create a tree for this dataset and get its ID
    dataset_tree_name = "Imported Dataset"
    print(f"Ensuring tree '{dataset_tree_name}' exists...")
    tree_id = db_manager.add_tree_sync(dataset_tree_name)
    print(f"All records will be associated with tree ID: {tree_id}")

    image_files = []

    if clear_existing:
        print("Clearing all existing scan records from the database...")
        db_manager.clear_all_scan_records()

    # Look for common image extensions recursively
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
        image_files.extend(glob(os.path.join(dataset_root, '**', ext), recursive=True))
    
    if not image_files:
        print(f"No image files found in '{dataset_root}' or its subdirectories.")
        return

    # --- MODIFICATION: Limit to 30 images ---
    total_found = len(image_files)
    if total_found > 30:
        print(f"Found {total_found} total images. Limiting to first 30 for processing.")
        image_files = image_files[:30] # Slice the list to the first 30 items
    # --- END OF MODIFICATION ---

    print(f"Found {len(image_files)} image files. Processing...")
    total_images = len(image_files)

    records_to_insert = []
    # Use a ThreadPoolExecutor to process images in parallel, improving speed
    # and demonstrating a non-blocking pattern.
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        # Create a future for each image processing task
        future_to_image = {executor.submit(process_single_image, path): path for path in image_files}

        for i, future in enumerate(as_completed(future_to_image)):
            try:
                record = future.result()
                records_to_insert.append(record)
                # Simple progress indicator
                progress = (i + 1) / total_images * 100
                print(f"Progress: {i + 1}/{total_images} ({progress:.1f}%)", end='\r')
            except Exception as exc:
                image_path = future_to_image[future]
                print(f"'{os.path.basename(image_path)}' generated an exception: {exc}")
    
    if records_to_insert:
        print(f"\nAll images processed. Handing off {len(records_to_insert)} records to the database manager for bulk insertion.")
        # Use the existing bulk insert method from the DatabaseManager
        # This is safer and reuses the optimized connection logic.
        db_manager.bulk_insert_records(records_to_insert, tree_id=tree_id)
    else:
        print("No records prepared for insertion.")

    print("Database population complete.")

if __name__ == "__main__":
    # --- Command-Line Argument Parsing ---
    parser = argparse.ArgumentParser(description="Populate the Mangofy database with a sample dataset.")
    parser.add_argument(
        "dataset_path", 
        type=str, 
        help="The full path to the root directory of the dataset."
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="If set, clears all existing scan records before populating."
    )
    args = parser.parse_args()

    populate_database_with_dataset(args.dataset_path, clear_existing=args.clear)