"""
This module contains integration tests for the application.
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
    Tests the full image analysis pipeline.
    """
    sample_image_path = "ml/leaf-detection/scripts/20211231_123305 (Custom).jpg"
    
    print(f"--- Testing Image Analysis with: {sample_image_path} ---")
    
    if not os.path.exists(sample_image_path):
        print(f"Error: Sample image not found at {sample_image_path}")
        return

    # Run the analysis
    result = analyze_image(sample_image_path)

    # Print the results
    print("\n--- Analysis Result ---")
    pprint(result)
    print("-----------------------\n")

    # Basic assertions to verify the result structure
    assert "disease_name" in result
    assert "confidence" in result
    assert "severity_percentage" in result
    assert "severity_name" in result
    
    print("Integration test completed successfully.")

if __name__ == "__main__":
    test_image_analysis()
