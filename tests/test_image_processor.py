import unittest
from unittest.mock import patch, MagicMock
import os
import io
import sys

# Add project and src directories to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.app.core import image_processor

class TestImageProcessor(unittest.TestCase):

    def setUp(self):
        """
        Reset the global predictor instance before each test to ensure isolation.
        This prevents mocks from one test from leaking into another.
        """
        image_processor._predictor = None

    def test_analyze_image_healthy_ml_on(self):
        """Test the analysis pipeline when the prediction is 'Healthy'."""
        with patch('src.app.core.image_processor.DiseasePredictor') as mock_DiseasePredictor, \
             patch('src.app.core.image_processor.calculate_severity_percentage') as mock_calculate_severity, \
             patch('src.app.core.image_processor.ML_AVAILABLE', True):

            # --- Setup Mocks ---
            mock_predictor_instance = MagicMock()
            mock_predictor_instance.predict.return_value = ('Healthy', 0.99)
            mock_DiseasePredictor.return_value = mock_predictor_instance

            # --- Action ---
            result = image_processor.analyze_image('/fake/healthy_leaf.jpg')

            # --- Assertions ---
            self.assertEqual(result['disease_name'], 'Healthy')
            self.assertEqual(result['confidence'], 0.99)
            # Crucially, severity calculation should be skipped for healthy leaves.
            mock_calculate_severity.assert_not_called()
            self.assertEqual(result['severity_percentage'], 0.0)
            self.assertEqual(result['severity_name'], 'Healthy')

    def test_analyze_image_anthracnose_early_stage_ml_on(self):
        """Test the analysis pipeline for an 'Early Stage' anthracnose prediction."""
        with patch('src.app.core.image_processor.DiseasePredictor') as mock_DiseasePredictor, \
             patch('src.app.core.image_processor.calculate_severity_percentage') as mock_calculate_severity, \
             patch('src.app.core.image_processor.ML_AVAILABLE', True):

            # --- Setup Mocks ---
            mock_predictor_instance = MagicMock()
            mock_predictor_instance.predict.return_value = ('Anthracnose', 0.95)
            mock_DiseasePredictor.return_value = mock_predictor_instance
            mock_calculate_severity.return_value = 5.0

            # --- Action ---
            result = image_processor.analyze_image('/fake/early_stage.jpg')

            # --- Assertions ---
            self.assertEqual(result['disease_name'], 'Anthracnose')
            self.assertEqual(result['confidence'], 0.95)
            mock_calculate_severity.assert_called_once_with('/fake/early_stage.jpg')
            self.assertEqual(result['severity_percentage'], 5.0)
            self.assertEqual(result['severity_name'], 'Early Stage')

    def test_analyze_image_anthracnose_advanced_stage_ml_on(self):
        """Test the analysis pipeline for an 'Advanced Stage' anthracnose prediction."""
        with patch('src.app.core.image_processor.DiseasePredictor') as mock_DiseasePredictor, \
             patch('src.app.core.image_processor.calculate_severity_percentage') as mock_calculate_severity, \
             patch('src.app.core.image_processor.ML_AVAILABLE', True):

            # --- Setup Mocks ---
            mock_predictor_instance = MagicMock()
            mock_predictor_instance.predict.return_value = ('Anthracnose', 0.98)
            mock_DiseasePredictor.return_value = mock_predictor_instance
            mock_calculate_severity.return_value = 25.0

            # --- Action ---
            result = image_processor.analyze_image('/fake/advanced_stage.jpg')

            # --- Assertions ---
            self.assertEqual(result['disease_name'], 'Anthracnose')
            self.assertEqual(result['confidence'], 0.98)
            mock_calculate_severity.assert_called_once_with('/fake/advanced_stage.jpg')
            self.assertEqual(result['severity_percentage'], 25.0)
            self.assertEqual(result['severity_name'], 'Advanced Stage')

    def test_analyze_image_fallback_mode_ml_off(self):
        """Test the fallback behavior when ML components are not available."""
        with patch('src.app.core.image_processor.DiseasePredictor') as mock_DiseasePredictor, \
             patch('src.app.core.image_processor.calculate_severity_percentage') as mock_calculate_severity, \
             patch('src.app.core.image_processor.ML_AVAILABLE', False):

            # --- Setup Mocks ---
            mock_predictor_instance = MagicMock()
            mock_predictor_instance.predict.return_value = ('Anthracnose', 0.85)
            mock_DiseasePredictor.return_value = mock_predictor_instance
            mock_calculate_severity.return_value = 25.0

            # --- Action ---
            result = image_processor.analyze_image('/fake/any_image.jpg')

            # --- Assertions ---
            self.assertEqual(result['disease_name'], 'Anthracnose')
            self.assertEqual(result['confidence'], 0.85)
            self.assertEqual(result['severity_percentage'], 25.0)
            self.assertEqual(result['severity_name'], 'Advanced Stage')

    def test_analyze_image_healthy_fallback_mode_ml_off(self):
        """Test the fallback behavior for a 'Healthy' prediction when ML is off."""
        with patch('src.app.core.image_processor.DiseasePredictor') as mock_DiseasePredictor, \
             patch('src.app.core.image_processor.calculate_severity_percentage') as mock_calculate_severity, \
             patch('src.app.core.image_processor.ML_AVAILABLE', False):

            # --- Setup Mocks ---
            mock_predictor_instance = MagicMock()
            mock_predictor_instance.predict.return_value = ('Healthy', 0.99)
            mock_DiseasePredictor.return_value = mock_predictor_instance

            # --- Action ---
            result = image_processor.analyze_image('/fake/healthy_leaf.jpg')

            # --- Assertions ---
            self.assertEqual(result['disease_name'], 'Healthy')
            self.assertEqual(result['confidence'], 0.99)
            mock_calculate_severity.assert_not_called()
            self.assertEqual(result['severity_percentage'], 0.0)
            self.assertEqual(result['severity_name'], 'Healthy')

    def test_get_predictor_model_file_not_found(self):
        """Test _get_predictor returns None and warns when the model file is missing."""
        with patch('src.app.core.image_processor.os.path.exists') as mock_exists, \
             patch('src.app.core.image_processor.ML_AVAILABLE', True):

            # Simulate model file missing, but labels file present.
            # The `and` condition in _get_predictor will short-circuit.
            mock_exists.return_value = False

            predictor = image_processor._get_predictor()

            # Assert that the function returns None because the file check failed
            self.assertIsNone(predictor)
            # Assert that it checked for the model path (logger may also call exists)
            # Check if MODEL_PATH appears in any of the call arguments
            model_path_checked = any(
                image_processor.MODEL_PATH in str(call[0][0]) if call[0] else False
                for call in mock_exists.call_args_list
            )
            self.assertTrue(model_path_checked, 
                f"Expected MODEL_PATH '{image_processor.MODEL_PATH}' in calls: {mock_exists.call_args_list}")

if __name__ == '__main__':
    unittest.main()