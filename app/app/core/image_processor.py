import os
from typing import Optional

try:
    from ml.predictor import DiseasePredictor
    from ml.severity_calculator import calculate_severity_percentage
    ML_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    ML_AVAILABLE = False
    # Define a dummy class for fallback
    class DiseasePredictor:
        def __init__(self, model_path, labels_path):
            print("Warning: DiseasePredictor could not be imported. Using dummy class.")
        def predict(self, image_path):
            return "Anthracnose", 0.85
    
    def calculate_severity_percentage(image_path):
        return 25.0

# Define paths for the model and labels
MODEL_PATH = "ml/Plant_Disease_Prediction/tflite/mango_mobilenetv2.tflite"
LABELS_PATH = "ml/Plant_Disease_Prediction/tflite/labels.txt"

# Global instance of the classifier
_predictor: Optional[DiseasePredictor] = None

def _get_predictor() -> Optional[DiseasePredictor]:
    global _predictor
    if _predictor is None and ML_AVAILABLE:
        if os.path.exists(MODEL_PATH) and os.path.exists(LABELS_PATH):
            _predictor = DiseasePredictor(model_path=MODEL_PATH, labels_path=LABELS_PATH)
        else:
            print(f"Warning: Model or labels file not found. ML prediction will be disabled.")
            return None
    elif _predictor is None:
        _predictor = DiseasePredictor(model_path=None, labels_path=None) # Instantiate dummy class
    return _predictor

def analyze_image(image_path: str) -> dict:
    """
    Orchestrates the image analysis process, using the ML model if available,
    otherwise falling back to mock predictions.
    """
    print(f"Analyzing image: {os.path.basename(image_path)}")

    predictor = _get_predictor()

    if predictor and ML_AVAILABLE:
        # Perform ML prediction
        disease_name, confidence = predictor.predict(image_path)
        
        # Calculate severity percentage
        if disease_name == "Healthy":
            severity_percentage = 0.0
        else:
            severity_percentage = calculate_severity_percentage(image_path)
    else:
        # Fallback to mock data if ML is not available
        print("Warning: ML model not available. Using mock data.")
        disease_name, confidence = predictor.predict(image_path)
        severity_percentage = calculate_severity_percentage(image_path)


    # Determine severity name
    severity_name = "Healthy"
    if disease_name == "Anthracnose":
        if severity_percentage < 10.0:
            severity_name = "Early Stage"
        else:
            severity_name = "Advanced Stage"

    return {
        "image_path": image_path,
        "disease_name": disease_name,
        "confidence": confidence,
        "severity_percentage": severity_percentage,
        "severity_name": severity_name
    }