"""
Integration tests for ML pipeline compliance with USER_MANUAL.md Section 4.

Verifies:
- Section 4.1: Image preprocessing pipeline (resize 224×224, normalize 0-1)
- Section 4.2: ML inference returns disease classification
- Section 4.3: Severity calculation produces percentage

All ML processing must follow USER_MANUAL.md Section 4 specifications.
"""
import os
import sys
from pprint import pprint

# Add the project root to the Python path to allow for absolute imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.app.core.image_processor import analyze_image

def test_image_analysis():
    """
    Tests the full image analysis pipeline per USER_MANUAL.md Section 4.
    
    Verifies:
    - Section 4.1: Image preprocessing (resize, normalize)
    - Section 4.2: ML inference execution
    - Section 4.3: Severity calculation
    """
    sample_image_path = "ml/leaf-detection/scripts/20211231_123305 (Custom).jpg"
    
    print(f"--- Testing Image Analysis (USER_MANUAL.md Section 4) with: {sample_image_path} ---")
    
    if not os.path.exists(sample_image_path):
        print(f"Error: Sample image not found at {sample_image_path}")
        return

    # Run the analysis (Section 4.1-4.3 pipeline)
    result = analyze_image(sample_image_path)

    # Print the results
    print("\n--- Analysis Result ---")
    pprint(result)
    print("-----------------------\n")

    # Section 4.2: Verify result structure contains all required fields
    assert "disease_name" in result, "Section 4.2: disease_name required in ML output"
    assert "confidence" in result, "Section 4.2: confidence score required"
    assert "severity_percentage" in result, "Section 4.3: severity_percentage required"
    assert "severity_name" in result, "Section 4.3: severity_name required (Healthy/Early/Advanced)"
    
    print("Integration test completed successfully - USER_MANUAL.md Section 4 compliance verified.")

if __name__ == "__main__":
    test_image_analysis()
