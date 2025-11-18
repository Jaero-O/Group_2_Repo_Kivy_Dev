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
    tbl_tree {
        INTEGER id PK "Auto-incrementing primary key"
        TEXT name UQ "Unique name of the tree (e.g., 'Backyard Mango')"
        DATETIME created_at "Timestamp of creation"
    }
    tbl_disease {
        INTEGER id PK "Auto-incrementing primary key"
        TEXT name UQ "Unique name of the disease (e.g., 'Anthracnose')"
        TEXT description "Detailed description of the disease"
        TEXT symptoms "Common symptoms"
        TEXT prevention "Prevention and treatment methods"
    }
    tbl_severity_level {
        INTEGER id PK "Auto-incrementing primary key"
        TEXT name UQ "e.g., Healthy, Early Stage, Advanced Stage"
        TEXT description "Description of the severity stage"
    }
    tbl_scan_record {
        INTEGER id PK "Auto-incrementing primary key"
        INTEGER tree_id FK "Foreign key to tbl_tree"
        INTEGER disease_id FK "Foreign key to tbl_disease"
        INTEGER severity_level_id FK "Foreign key to tbl_severity_level"
        REAL severity_percentage "Calculated as (lesion_area / leaf_area)"
        TEXT image_path "File path to the saved scan image"
        # Mangofy — Mango Leaf Disease Scanner (Project README)

        This repository contains the Mangofy Kivy application and supporting tools for dataset handling, model hosting, and CI automation.

        This README documents everything a new developer or maintainer needs to run, test, and extend the system, including how we handle large ML artifacts and how to recover or re-sync after the repository history was cleaned.

        --

        **Quick links**

        - App entry: `main.py` (app bootstrap in `src/`)
        - App code: `src/app/` (core, screens, kv files)
        - Tests: `tests/`
        - Model helpers: `scripts/publish_models_github.ps1`, `scripts/download_models.py`
        - CI workflow: `.github/workflows/download-models.yml`
        - Models Release (uploaded): `v1.0-models` (GitHub Release)

        --

        **Table of contents**

        - Project overview
        - Repo layout
        - Environment & setup (Windows-focused + cross-platform notes)
        - Running the app (dev mode)
        - Tests and test utilities
        - Database details (`mangofy.db`)
        - ML models & hosting (GitHub Releases + download/upload scripts)
        - CI: workflow for downloading models
        - Post-history-rewrite collaborator instructions
        - Developer workflow & common commands
        - Troubleshooting

        --

        **Project overview**

        Mangofy is a Kivy-based application for detecting leaf disease (anthracnose) in mango leaves. It includes:

        - A Kivy UI (screens, KV files) under `src/app/`.
        - A small SQLite-backed local database used for persisting scans and lookups (`mangofy.db`).
        - ML inference code that uses TFLite models for on-device prediction.
        - Image-processing helpers to compute a severity percentage from segmented lesions.

        The repository also contains test coverage and utilities to host large model files outside of Git history (we use a GitHub Release for binary model hosting).

        --

        **Repository layout (important paths)**

        - `src/` — application source (Kivy app under `src/app/`).
        - `ml/` — ML utilities and scripts (predictor, severity calculator, leftover utils)
        - `ml/Plant_Disease_Prediction/` — model metadata, notebooks, scripts (NOT the canonical place for large binaries)
        - `scripts/` — helpers for model upload/download and other utilities
        - `tests/` — unit and integration tests
        - `.github/workflows/` — CI workflows (download-models.yml added)
        - `README.md` — this file

        --

        **Environment & setup**

        Prerequisites (Windows recommended flow):

        - Python 3.10+ installed and accessible in PATH
        - Git CLI
        - PowerShell (Windows) or bash (Linux/macOS)
        - For model publishing: GitHub CLI (`gh`) installed and authenticated

        Setup steps (Windows PowerShell)

        1) Create and activate a virtual environment:

        ```powershell
        python -m venv .venv
        .\.venv\Scripts\Activate.ps1
        ```

        2) Upgrade pip and install dependencies:

        ```powershell
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        ```

        Notes for Linux/macOS:

        ```bash
        python -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        ```

        --

        **Running the app (development)**

        - From repo root, with venv active:

        PowerShell:
        ```powershell
        python main.py
        ```

        Or if your entry was moved/structured under `src/` you may run via:
        ```powershell
        python -m src.main
        ```

        Notes:
        - The Kivy app requires a display (on headless CI use a virtual framebuffer or run on a desktop environment).
        - The app defers heavy initialization (KV loading and screen imports) until DB setup finishes — this helps unit tests run without starting the full UI.

        --

        **Testing**

        - Run the full test suite (unit tests):

        PowerShell / bash:
        ```powershell
        python -m unittest discover tests
        ```

        - Individual test file:

        ```powershell
        python -m unittest tests.test_database
        ```

        Test design notes:
        - Tests are written to be deterministic and avoid requiring native-only packages (we inject fake `tflite_runtime` where needed and skip cv2 tests when OpenCV is not available).

        --

        **Database (`mangofy.db`)**

        - The app stores data in a SQLite DB named `mangofy.db` located under the user data directory (or `populated_mangofy.db` in dev/test scenarios). The schema includes `tbl_disease`, `tbl_severity_level`, `tbl_tree`, and `tbl_scan_record`.
        - There are utilities in `src/app/core/database.py` to initialize and populate lookup tables. Use the provided tests to validate DB creation.

        --

        **ML models & hosting (how we handle large files)**

        Rationale:
        - Large artifacts (models, videos, datasets) were removed from Git history to keep the repository small and fast. The canonical location for binary models is a GitHub Release named `v1.0-models`.

        What we added to help:
        - `scripts/publish_models_github.ps1` — PowerShell script that uses `gh` to create a release and upload assets. It supports absolute paths and glob-style patterns.
        - `scripts/download_models.py` — Python script that downloads release assets by tag; supports `GITHUB_TOKEN` from the environment for private releases.
        - `.github/workflows/download-models.yml` — CI job that downloads models into `models/` for workflows.

        Uploading models (manual, using `gh` locally)

        1. Ensure `gh` is installed and logged in:

        ```powershell
        gh auth login
        gh auth status
        ```

        2. From the repo root (PowerShell), run:

        ```powershell
        .\scripts\publish_models_github.ps1 -Tag 'v1.0-models' -Title 'ML models v1' -Notes 'Models removed from repo'
        ```

        Or specify absolute paths if files live elsewhere:

        ```powershell
        .\scripts\publish_models_github.ps1 -Tag 'v1.0-models' -Pattern 'C:\path\to\h5\*,C:\path\to\tflite\*'
        ```

        Downloading models (local or CI):

        ```powershell
        python scripts/download_models.py --repo Jaero-O/Group_2_Repo_Kivy_Dev --tag v1.0-models --dest models/
        ```

        CI (GitHub Actions): The workflow `.github/workflows/download-models.yml` will run the same downloader using `GITHUB_TOKEN`.

        Alternatives to GitHub Releases

        - Google Drive: free, but requires managing share links; I can extend `download_models.py` to fetch from Drive if you prefer.
        - Self-hosting (S3 or similar): works but may incur costs.

        --

        **Post-history-rewrite collaborator instructions (important)**

        Because the repo had large binary files removed from history, the `integration` branch was rewritten and force-pushed. Collaborators must not pull normally — they should re-clone or reset.

        Safest (recommended): re-clone:

        ```powershell
        git clone https://github.com/Jaero-O/Group_2_Repo_Kivy_Dev.git
        cd Group_2_Repo_Kivy_Dev
        git checkout integration
        ```

        If a contributor must preserve local work, they should:

        ```powershell
        git fetch origin
        git checkout -b my-local-backup
        git rebase --onto origin/integration <old-integration-commit> my-local-backup
        # or create patches with `git format-patch` and reapply after re-cloning
        ```

        If you need a short message to send to the team, use the collaborator note in `docs/MODEL_HOSTING.md`.

        --

        **Developer workflow & common commands**

        - Run tests:

        ```powershell
        python -m unittest discover tests
        ```

        - Start app (dev):

        ```powershell
        python main.py
        ```

        - Create a release and upload models (local):

        ```powershell
        gh auth login
        .\scripts\publish_models_github.ps1 -Tag 'v1.0-models' -Title 'ML models v1'
        ```

        - Download models locally:

        ```powershell
        python scripts/download_models.py --repo Jaero-O/Group_2_Repo_Kivy_Dev --tag v1.0-models --dest models/
        ```

        --

        **Troubleshooting**

        - Push fails due to large files or remote timeouts: we removed large files and force-pushed a cleaned branch. If you encounter push failures, ensure you re-cloned the cleaned repo.
        - `gh` CLI not found: install from https://cli.github.com/ and authenticate with `gh auth login`.
        - Running Kivy on headless CI: use a headful runner or xvfb on Linux.

        --

        **Contributing**

        - Open issues and PRs are welcome. For large model changes, use Releases or external storage rather than committing binaries.

        --

        If you'd like, I can also:

        - Add a release-upload GitHub Actions workflow (automates uploads from a CI artifact or from a secret-uploaded artifact).
        - Remove the binary model files currently copied into `ml/Plant_Disease_Prediction/h5` and `tflite` (recommended to avoid duplicating the Release contents in git history).

        Thank you — if anything in this README should be expanded or made more specific to your environment, tell me which section to change and I'll update it.