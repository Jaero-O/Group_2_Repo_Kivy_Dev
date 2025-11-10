# Mangofy App

Mangofy is a Kivy-based mobile application designed to detect anthracnose disease in mangoes. The application provides a user-friendly interface to scan mango leaves, get predictions, and learn more about the disease.

## Features

*   **Scan Mango Leaves:** Use your device's camera or upload an image to scan for anthracnose disease.
*   **Prediction Results:** Get instant results on whether the mango is infected with anthracnose.
*   **Disease Information:** Access information about anthracnose, its symptoms, and prevention methods.
*   **Scan History:** Keep a record of your previous scans.
*   **User Guide:** A simple guide on how to use the application effectively.

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

To run the application, execute the `main.py` file:

```bash
python kivy-lcd-app/main.py
```

## Project Structure

The project is organized into the following directories and files:

```
Group_2_Repo_Kivy_Dev/
├── kivy-lcd-app/
│   ├── main.py               # Main entry point of the application
│   ├── app/
│   │   ├── assets/           # Images, icons, and other assets
│   │   ├── core/             # Core application logic
│   │   │   ├── __init__.py
│   │   │   ├── settings.py   # Window and screen settings
│   │   │   ├── utils.py      # Utility functions for scaling
│   │   │   └── widgets.py    # Custom Kivy widgets
│   │   ├── kv/               # Kivy language files for UI design
│   │   │   ├── WelcomeScreen.kv
│   │   │   ├── HomeScreen.kv
│   │   │   └── ...           # Other screen KV files
│   │   └── screens/          # Python files for each screen's logic
│   │       ├── __init__.py
│   │       ├── welcome_screen.py
│   │       ├── home_screen.py
│   │       └── ...           # Other screen Python files
├── requirements.txt          # Project dependencies
└── README.md                 # This file
```

### File and Directory Descriptions

*   **`kivy-lcd-app/main.py`**: The main script that initializes the Kivy application, loads the KV files, sets up the screen manager, and runs the app.

*   **`kivy-lcd-app/app/core/`**: This directory contains the core logic of the application.
    *   `settings.py`: Configures the application window size and behavior. It can switch between development and deployment modes.
    *   `utils.py`: Provides utility functions for responsive UI scaling based on the window size.
    *   `widgets.py`: (if present) would contain custom Kivy widgets used throughout the application.

*   **`kivy-lcd-app/app/kv/`**: This directory holds the Kivy language (`.kv`) files, which define the UI layout and widgets for each screen. Each `.kv` file corresponds to a screen in the `screens` directory.

*   **`kivy-lcd-app/app/screens/`**: This directory contains the Python classes for each screen of the application. Each file defines the behavior and logic associated with a specific screen.
    *   `welcome_screen.py`: The initial screen that welcomes the user.
    *   `home_screen.py`: The main screen with navigation to other features.
    *   `scan_screen.py`: The screen for capturing or selecting an image to be analyzed.
    *   `records_screen.py`: Displays the history of previous scans.
    *   And many more screens for different functionalities.

*   **`kivy-lcd-app/app/assets/`**: Contains all the static assets like images, icons, and fonts used in the application.

*   **`requirements.txt`**: A list of all the Python packages required to run the project.

## Dependencies

The application relies on the following Python libraries:

*   **Kivy:** For building the graphical user interface.
*   **NumPy:** For numerical operations, often used with image processing.
*   **Pillow:** For image manipulation.
*   **TensorFlow:** For running the machine learning model for disease prediction.

---
