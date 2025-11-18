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
project_root = os.path.abspath(os.path.dirname(__file__))
src_path = os.path.join(project_root, 'src')
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.core.image_processor import analyze_image # This will use the mock classifier
from src.core.database import DatabaseManager

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
    # Explicitly define the database path to match the main application.
    # The app name 'mangofy' is derived from the MangofyApp class name.
    app_name = 'mangofy'
    if sys.platform == 'win32':
        db_folder = os.path.join(os.environ['APPDATA'], app_name)
    else: # macOS and Linux
        db_folder = os.path.join(os.path.expanduser('~'), '.config', app_name)
    
    os.makedirs(db_folder, exist_ok=True)
    main_db_path = os.path.join(db_folder, "mangofy.db")
    print(f"Targeting main app database at: {main_db_path}")

    db_manager = DatabaseManager(db_path=main_db_path)
    db_manager.initialize_database()
    
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