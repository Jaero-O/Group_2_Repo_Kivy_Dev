# Mangofy App

Mangofy is a Kivy-based mobile application designed to detect anthracnose disease in mangoes. The application provides a user-friendly interface to scan mango leaves, get predictions, save the results, and learn more about the disease.

## Features

*   **Scan Mango Leaves:** Use your device's camera or upload an image to scan for anthracnose disease.
*   **Prediction Results:** Get instant results on whether the mango is infected with anthracnose and at what severity stage.
*   **Quantitative Analysis:** Calculates the severity percentage based on the leaf area affected by lesions.
*   **Disease Information:** Access detailed information about anthracnose, its symptoms, and prevention methods.
*   **Scan History:** Keep a persistent record of your previous scans, including images and analysis data.
*   **User Guide:** A simple guide on how to use the application effectively.
*   **Offline First:** The application works entirely offline, with all data stored locally on the device.

## Project Structure

The project is organized into the following directories and files:

```
Group_2_Repo_Kivy_Dev/
├── kivy-lcd-app/
│   ├── main.py               # Main entry point of the Kivy application
│   └── app/
│       ├── assets/           # Images, icons, and other assets
│       ├── core/             # Core application logic (database, image processing)
│       ├── kv/               # Kivy language files for UI design
│       └── screens/          # Python files for each screen's logic
├── populate_dataset.py     # Script to populate the database with sample data
├── requirements.txt          # Project dependencies
└── README.md                 # This file
```

### File and Directory Descriptions

*   **`kivy-lcd-app/`**: This directory contains the main Kivy application.
    *   **`main.py`**: The main script that initializes and runs the Kivy application.
    *   **`app/core/`**: Contains the core logic, including database management (`database.py`) and image processing (`image_processor.py`).
    *   **`app/kv/`**: Holds the Kivy language (`.kv`) files that define the UI layout for each screen.
    *   **`app/screens/`**: Contains the Python classes for each screen, defining their behavior and logic.
    *   **`app/assets/`**: Contains all static assets like images and icons.
*   **`populate_dataset.py`**: A utility script to populate the application's database with a sample dataset of images. This is useful for development and testing.
*   **`requirements.txt`**: A list of all Python packages required to run the project.


## Backend and Database

The backend is designed to be robust and self-contained, with a normalized database schema to ensure data integrity and scalability.

### Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    Disease {
        INTEGER id PK "Auto-incrementing primary key"
        TEXT name UQ "Unique name of the disease (e.g., 'Anthracnose')"
        TEXT description "Detailed description of the disease"
        TEXT symptoms "Common symptoms"
        TEXT prevention "Prevention and treatment methods"
    }
    SeverityLevel {
        INTEGER id PK "Auto-incrementing primary key"
        TEXT name UQ "e.g., Healthy, Early Stage, Advanced Stage"
        TEXT description "Description of the severity stage"
    }
    ScanRecord {
        INTEGER id PK "Auto-incrementing primary key"
        INTEGER disease_id FK "Foreign key to Disease table"
        INTEGER severity_level_id FK "Foreign key to SeverityLevel table"
        REAL severity_percentage "Calculated as (lesion_area / leaf_area)"
        TEXT image_path "File path to the saved scan image"
        DATETIME timestamp "The date and time of the scan"
    }

    ScanRecord ||--o{ Disease : "has"
    ScanRecord ||--o{ SeverityLevel : "is at"
```

### Database Tables

1.  **`Disease`** (Lookup Table)
    *   Stores static, detailed information about each detectable condition.
    *   **Columns**: `id`, `name` (e.g., 'Anthracnose', 'Healthy'), `description`, `symptoms`, `prevention`.

2.  **`SeverityLevel`** (Lookup Table)
    *   Defines the different stages of infection that the model can classify.
    *   **Columns**: `id`, `name` (e.g., 'Early Stage', 'Advanced Stage'), `description`.

3.  **`ScanRecord`** (Main Data Table)
    *   Stores the results of every scan performed by the user.
    *   **Columns**: `id`, `scan_timestamp`, `disease_id` (FK to `Disease`), `severity_level_id` (FK to `SeverityLevel`), `severity_percentage` (REAL), `image_path`, `is_archived`.

## Data Flow: From Scan to Save

1.  **Capture/Select Image**: The user provides an image via the camera (`ScanScreen`) or file system (`ImageSelection` screen).
2.  **Analyze**: The application navigates to the `ResultScreen`.
3.  **ML Prediction**: A TensorFlow Lite model runs on the image to predict the `disease_name` (e.g., "Anthracnose") and `severity_name` (e.g., "Advanced Stage").
4.  **Calculate Severity %**: The `image_processor.calculate_severity(image_path)` function is called to get the quantitative `severity_percentage`.
5.  **Fetch Foreign Keys**: The app calls `database.get_lookup_ids(disease_name, severity_name)` to get the corresponding IDs from the `Disease` and `SeverityLevel` tables.
6.  **Save Record**: When the user clicks "Save", the `ResultScreen` calls `database.save_record_async()` with all the collected information (`disease_id`, `severity_level_id`, `severity_percentage`, `image_path`).
7.  **Confirmation**: A callback from the asynchronous save operation updates the UI to confirm that the record has been saved successfully.

## Installation

To run this application, you need to have Python and Kivy installed.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/Group_2_Repo_Kivy_Dev.git
    cd Group_2_Repo_Kivy_Dev
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To run the application, execute the `main.py` file located inside the `kivy-lcd-app` directory:

```bash
python kivy-lcd-app/main.py
```

## Dependencies

The application relies on the following key Python libraries:

*   **Kivy:** For building the cross-platform graphical user interface.
*   **NumPy:** For numerical operations, especially in image processing.
*   **Pillow:** For image manipulation tasks.
*   **TensorFlow:** For running the machine learning model for disease prediction.