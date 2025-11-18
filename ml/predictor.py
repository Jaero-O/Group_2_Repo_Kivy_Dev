"""
This module provides the predictor class for the ML model.
"""
import numpy as np
from PIL import Image
import tflite_runtime.interpreter as tflite
import os

class DiseasePredictor:
    def __init__(self, model_path, labels_path):
        self.interpreter = tflite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        with open(labels_path, 'r') as f:
            self.labels = [line.strip() for line in f.readlines()]

    def predict(self, image_path):
        """
        Predicts the disease from an image.
        """
        img = Image.open(image_path).resize((224, 224))
        img_array = np.array(img, dtype=np.float32)
        img_array = np.expand_dims(img_array, axis=0)
        img_array /= 255.0

        self.interpreter.set_tensor(self.input_details[0]['index'], img_array)
        self.interpreter.invoke()
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        
        prediction = output_data[0]
        predicted_label = self.labels[np.argmax(prediction)]
        confidence = np.max(prediction)

        return predicted_label, float(confidence)

