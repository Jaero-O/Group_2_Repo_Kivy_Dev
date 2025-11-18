# app/core/models.py
import numpy as np
from PIL import Image
from typing import Tuple, Optional

# --- TENSORFLOW SETUP (Lazy Loading) ---
# We import TensorFlow and other heavy libraries inside the functions
# to speed up initial app loading.
tf = None

def _load_dependencies():
    """Dynamically loads TensorFlow."""
    global tf
    if tf is None:
        try:
            import tensorflow
            tf = tensorflow
            print("TensorFlow loaded successfully.")
        except ImportError:
            print("Warning: TensorFlow is not installed. Model prediction will be mocked.")


class AnthracnoseClassifier:
    """
    A classifier to predict mango disease from an image using a TFLite model.
    """
    def __init__(self, model_path: Optional[str] = None, labels_path: Optional[str] = None):
        _load_dependencies()
        self.model_path = model_path
        self.labels_path = labels_path
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.labels = []

        self._load_model()
        self._load_labels()

    def _load_model(self):
        """Loads the TFLite model and allocates tensors."""
        if self.model_path and tf:
            try:
                self.interpreter = tf.lite.Interpreter(model_path=self.model_path)
                self.interpreter.allocate_tensors()
                self.input_details = self.interpreter.get_input_details()
                self.output_details = self.interpreter.get_output_details()
                print(f"TFLite model loaded successfully from {self.model_path}")
            except Exception as e:
                print(f"Error loading TFLite model: {e}")
                self.interpreter = None
        else:
            print("Using mock model (TensorFlow not available or no model path).")

    def _load_labels(self):
        """Loads labels from a text file."""
        if self.labels_path:
            try:
                with open(self.labels_path, 'r') as f:
                    self.labels = [line.strip().split(' ', 1)[1] for line in f.readlines()]
                print(f"Labels loaded: {self.labels}")
            except Exception as e:
                print(f"Error loading labels file: {e}")

    def predict(self, image_path: str) -> Tuple[str, float]:
        """
        Predicts the disease class and confidence for a given image.

        Returns:
            A tuple containing (disease_name, confidence_score).
        """
        if not self.interpreter or not self.labels:
            print("Prediction unavailable. Using mock data.")
            return ("Anthracnose", 0.92)  # Fallback mock prediction

        try:
            # Get model's expected input size
            _, height, width, _ = self.input_details[0]['shape']

            # Load and preprocess the image
            img = Image.open(image_path).convert('RGB').resize((width, height))
            input_data = np.expand_dims(img, axis=0)
            input_data = (input_data.astype(np.float32) / 255.0) # Normalize to [0,1]

            # Set the tensor and run inference
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()

            # Get the prediction result
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
            prediction = np.squeeze(output_data)

            # Get the class with the highest score
            predicted_class_index = np.argmax(prediction)
            confidence = float(prediction[predicted_class_index])
            disease_name = self.labels[predicted_class_index]

            return (disease_name, confidence)
        except Exception as e:
            print(f"Error during prediction: {e}")
            return ("Prediction Error", 0.0)