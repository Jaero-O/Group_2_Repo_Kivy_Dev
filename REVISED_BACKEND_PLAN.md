# Revised Backend and Data Logic Plan for Mangofy App

This document provides a revised plan for how the Mangofy Kivy application will handle local data storage and logic. This plan is an evolution of the original `BACKEND_PLAN.md`, designed for better scalability and data organization.

## 1. Core Principle: Local-First

The application will continue to operate entirely on the user's device, requiring no remote server. This ensures offline capability, user privacy, and zero server-side costs.

---

## 2. Records and History

-   **Associated Screens:** `RecordsScreen`, `SaveScreen`, `ResultScreen`
-   **Functionality:** The app allows users to save their scan results and view a history of past scans.

### Revised Local Implementation:

-   **Database:** An **SQLite** database will be used. It will now contain two related tables: `ScanRecord` and `Disease`. This structure normalizes the data, making it more organized and scalable.
    -   `Disease` **Table:** This table stores detailed information about each detectable disease (e.g., name, description, symptoms, prevention methods).
        -   **Initial Population:** Must be populated with at least "Anthracnose" and "Healthy" entries. Other diseases can be added later.
        -   **Example Data:** `('Anthracnose', 'Fungal disease...', 'Dark spots...', 'Fungicides...')`, `('Healthy', 'No disease...', 'None', 'Good practices...')`
    -   `SeverityLevel` **Table:** This new table defines the different stages of infection the model can classify (e.g., "Healthy," "Early Stage," "Advanced Stage"). This separates the concept of a disease from its severity.
        -   **Initial Population:** Must be populated with the specific severity categories your ML model outputs.
        -   **Example Data:** `('Healthy', 'No visible signs of infection.')`, `('Early Stage', 'Minor lesions, less than 10% affected.')`, `('Advanced Stage', 'Significant lesions, 10% or more affected.')`
    -   `ScanRecord` **Table:** This table stores the history of each scan. It will now include foreign keys to both the `Disease` and `SeverityLevel` tables, along with the calculated severity percentage.
        -   **Foreign Key Constraints:** Ensure `ON DELETE RESTRICT` or `ON DELETE NO ACTION` to prevent accidental deletion of referenced disease or severity levels.

-   **Data Access Module (`database.py`):** This module will manage all database interactions.
    -   `init_db()`:
        -   **Purpose:** Creates the `Disease`, `SeverityLevel`, and `ScanRecord` tables if they don't already exist.
        -   **Population:** Populates the `Disease` and `SeverityLevel` tables with predefined initial data (e.g., "Anthracnose", "Healthy" for diseases; "Healthy", "Early Stage", "Advanced Stage" for severity levels). This ensures lookup data is always available.
    -   `save_record(image_path, disease_id, severity_level_id, severity_percentage, timestamp)`:
        -   **Purpose:** Inserts a new scan record into the `ScanRecord` table.
        -   **Parameters:** Requires the path to the saved image, the foreign key IDs for the detected disease and severity, the calculated severity percentage, and the timestamp of the scan.
        -   **Return:** Typically returns the `id` of the newly inserted record.
    -   `get_all_records()`:
        -   **Purpose:** Retrieves a comprehensive list of all scan records.
        -   **Details:** Performs `JOIN` operations with the `Disease` and `SeverityLevel` tables to fetch human-readable names and descriptions for display in the `RecordsScreen`.
        -   **Return:** A list of dictionaries or objects, each representing a scan with `id`, `image_path`, `timestamp`, `disease_name`, `severity_name`, `severity_percentage`, `disease_description`, etc.
    -   `get_disease_info(disease_id)`:
        -   **Purpose:** Fetches detailed information for a specific disease.
        -   **Parameters:** `disease_id` (integer).
        -   **Return:** A dictionary or object containing all attributes of the `Disease` table for the given ID.
    -   `get_lookup_ids(disease_name, severity_name)`:
        -   **Purpose:** A utility function to retrieve the primary keys (`id`) for a given disease name and severity level name. This is crucial for populating foreign keys in `ScanRecord`.
        -   **Parameters:** `disease_name` (string, e.g., "Anthracnose"), `severity_name` (string, e.g., "Advanced Stage").
        -   **Return:** A tuple `(disease_id, severity_level_id)`. Handles cases where names might not be found (e.g., returns `None` or raises an error).

### Quantitative Analysis (as per Methodology):
-   **Lesion Segmentation & Severity Calculation:** The application logic will perform image processing to segment lesions, calculate the total leaf area and lesion area, and compute a `severity_percentage` (`lesion_area / leaf_area`). This percentage will be stored in the `ScanRecord` table.
    -   **Implementation Note:** This logic will likely reside in a separate Python module (e.g., `image_processor.py`) that the `ScanScreen` or `ResultScreen` calls after image capture and before ML inference.

---

## 3. Image Analysis (Machine Learning Model)

-   **Associated Screens:** `ScanScreen`, `ResultScreen`
-   **Functionality:** Analyze a mango image to classify disease severity using a local TensorFlow Lite model.

### Local Implementation (Unchanged):

-   **On-Device Model:** A **TensorFlow Lite (`.tflite`)** model will be packaged with the application for classifying the severity stage.
-   **Inference Logic:** A Python module will load the `.tflite` model, preprocess the user's image, run inference, and interpret the output.
-   **Integration with Database:** After the model returns a prediction (e.g., the class "Advanced Stage"), the app will:
    1.  **Image Preprocessing:** Prepare the captured image for ML inference (resizing, normalization, etc.).
    2.  **ML Inference:** Run the `.tflite` model to get the predicted `severity_name` (e.g., "Healthy", "Early Stage", "Advanced Stage").
    3.  **Lesion Segmentation & Severity Percentage Calculation:** Call the `image_processor.py` module to calculate the `severity_percentage` based on the image.
    4.  **Database Lookup:** Use `database.get_lookup_ids("Anthracnose", predicted_severity_name)` to retrieve the `disease_id` and `severity_level_id`. (Assuming "Anthracnose" is the primary disease, or the model also predicts the disease type).
    5.  **Save Record:** Call `database.save_record()` with the `image_path`, retrieved `disease_id`, `severity_level_id`, calculated `severity_percentage`, and current `timestamp`.

---

## 4. Sharing Functionality

-   **Associated Screens:** `ShareScreen`, `ResultScreen`
-   **Functionality:** Allow users to share their scan results.

### Local Implementation (Unchanged):

-   **Native Sharing:** The app will use a library like `plyer` to trigger the device's native sharing dialog. The content to be shared (image and text) will be prepared by the app. This requires no backend.

## Summary of Revised Local Components

1.  **SQLite Database:** Three tables (`ScanRecord`, `Disease`, `SeverityLevel`) for normalized, severity-aware data storage.
2.  **Data Access Module (`database.py`):** Centralized Python functions for all CRUD operations and ID lookups.
3.  **On-Device ML Model:** A `.tflite` model for efficient local inference of severity stage.
4.  **Image Analysis Logic (`image_processor.py`):** Dedicated module for lesion segmentation and quantitative severity percentage calculation.
5.  **Native Sharing Integration:** Utilizes `plyer` or similar for standard mobile sharing.