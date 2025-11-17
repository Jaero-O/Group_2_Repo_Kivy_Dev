import random
import os
from typing import Optional

# Import the actual classifier from models.py
from app.core.models import AnthracnoseClassifier

# Define mock disease and severity options
MOCK_DISEASES = ["Anthracnose", "Healthy"]

# Global instance of the classifier (or None if not loaded/available)
_classifier: Optional[AnthracnoseClassifier] = None

def _get_classifier() -> AnthracnoseClassifier:
    global _classifier
    if _classifier is None:
        _classifier = AnthracnoseClassifier(model_path=None, labels_path=None) # Use None to trigger mock if TF not available
    return _classifier

def calculate_severity(image_path: str, disease_name: str = None) -> float:
    """
    Mocks the calculation of the severity percentage of the disease in an image.
    As per the implementation plan, this is a placeholder returning mock data.

    Args:
        image_path: The path to the image file (not used in mock, but kept for signature).
        disease_name: The predicted disease name, to help with consistent mocking.

    Returns:
        A float representing the mock severity percentage.
    """
    print(f"MOCK: Calculating severity for image: {os.path.basename(image_path)}")
    
    if disease_name == "Healthy":
        return 0.0
    else:
        # Return a random mock severity percentage for non-healthy cases
        return round(random.uniform(5.0, 95.0), 1) # Ensure it's not 0 for diseased

def analyze_image(image_path: str) -> dict:
    """
    Orchestrates the image analysis process, using the ML model if available,
    otherwise falling back to mock predictions.

    Args:
        image_path: The path to the image file to be analyzed.

    Returns:
        A dictionary containing the analysis results:
        {
            "image_path": str,
            "disease_name": str,
            "confidence": float,
            "severity_percentage": float
        }
    """
    print(f"Analyzing image: {os.path.basename(image_path)}")

    classifier = _get_classifier()
    
    # Perform ML prediction (or mock if classifier is not ready)
    disease_name, confidence = classifier.predict(image_path) # AnthracnoseClassifier.predict handles its own mock fallback
    
    # Calculate severity percentage (currently always mocked)
    severity_percentage = calculate_severity(image_path, disease_name)

    # Determine severity name based on the same logic as the app's ResultScreen
    # This centralizes the logic and ensures consistency.
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
        "severity_name": severity_name  # Add this to the result
    }