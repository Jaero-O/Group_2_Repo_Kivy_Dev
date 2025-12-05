import os
import json
import subprocess
import sys
from typing import List, Tuple, Optional

# This module now acts as a wrapper that calls the actual TFLite predictor via subprocess


class DiseasePredictor:
    """Wrapper that calls TFLite prediction in a Python 3.10 subprocess.

    Environment variables:
        MANGOFY_MODEL_PATH: path to the .tflite model
        MANGOFY_LABELS_PATH: path to labels.txt
        MANGOFY_PYTHON310_PATH: path to Python 3.10 interpreter (required)
    """

    def __init__(self, model_path: str, labels_path: Optional[str] = None):
        self.model_path = os.getenv("MANGOFY_MODEL_PATH", model_path)
        self.labels_path = os.getenv("MANGOFY_LABELS_PATH", labels_path or "")
        
        # Get Python 3.10 interpreter path
        self.python310_path = os.getenv("MANGOFY_PYTHON310_PATH", "/home/kennethbinasa/tflite_venv/bin/python")
        if not self.python310_path:
            raise RuntimeError(
                "MANGOFY_PYTHON310_PATH environment variable must be set to your Python 3.10 interpreter path"
            )
        
        if not os.path.exists(self.python310_path):
            raise FileNotFoundError(f"Python 3.10 interpreter not found: {self.python310_path}")
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        # Path to the worker script (same directory as this file)
        self.worker_script = os.path.join(os.path.dirname(__file__), "predictor_worker.py")
        if not os.path.exists(self.worker_script):
            raise FileNotFoundError(f"Worker script not found: {self.worker_script}")

    def predict(self, image_path: str) -> Tuple[str, float]:
        """Return (label, confidence) for provided image_path."""
        result = self._run_worker("predict", image_path)
        return result["label"], result["confidence"]

    def predict_raw(self, image_path: str) -> list:
        """Return raw probability vector as a list."""
        result = self._run_worker("predict_raw", image_path)
        return result["probabilities"]

    def _run_worker(self, command: str, image_path: str) -> dict:
        """Execute the worker script in Python 3.10 subprocess."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Prepare arguments
        cmd = [
            self.python310_path,
            self.worker_script,
            command,
            self.model_path,
            image_path,
            self.labels_path
        ]
        
        try:
            # Run subprocess and capture output
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                check=True
            )
            
            # Parse JSON response
            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Prediction timed out after 30 seconds")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else "Unknown error"
            raise RuntimeError(f"Prediction failed: {error_msg}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid response from worker: {e}")


__all__ = ["DiseasePredictor"]
