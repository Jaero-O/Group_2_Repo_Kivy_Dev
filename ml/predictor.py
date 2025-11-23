import os
import numpy as np
from typing import List, Tuple, Optional
from PIL import Image

# Attempt to import a lightweight TFLite runtime first; fall back to TensorFlow Lite
_INTERPRETER = None
try:  # tflite_runtime (preferred small footprint)
    from tflite_runtime.interpreter import Interpreter  # type: ignore
    _INTERPRETER = 'tflite_runtime'
except Exception:  # tensorflow lite fallback
    try:
        from tensorflow.lite.python.interpreter import Interpreter  # type: ignore
        _INTERPRETER = 'tensorflow.lite'
    except Exception:
        _INTERPRETER = None


class DiseasePredictor:
    """Loads a TFLite classification model and performs prediction on leaf images.

    Environment override:
        MANGOFY_MODEL_PATH can override supplied model_path.
        MANGOFY_LABELS_PATH can override labels_path.
    """

    def __init__(self, model_path: str, labels_path: Optional[str] = None):
        self.model_path = os.getenv("MANGOFY_MODEL_PATH", model_path)
        self.labels_path = os.getenv("MANGOFY_LABELS_PATH", labels_path or "")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        if _INTERPRETER is None:
            raise RuntimeError("No TFLite interpreter available. Install tflite-runtime or tensorflow.")

        self.interpreter = Interpreter(model_path=self.model_path)
        self.interpreter.allocate_tensors()

        input_details = self.interpreter.get_input_details()
        output_details = self.interpreter.get_output_details()
        self.input_index = input_details[0]['index']
        self.output_index = output_details[0]['index']
        self.input_shape = input_details[0]['shape']  # e.g. [1, 224, 224, 3]

        # Determine number of classes from output tensor shape
        output_shape = output_details[0]['shape']
        if len(output_shape) == 2:
            self.num_classes = int(output_shape[1])
        else:
            self.num_classes = int(np.prod(output_shape))

        self.labels: List[str] = self._load_labels(self.labels_path)
        if self.labels and len(self.labels) != self.num_classes:
            print(f"[Predictor Warning] Label count ({len(self.labels)}) does not match model classes ({self.num_classes}).")

    @staticmethod
    def _load_labels(path: str) -> List[str]:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return [ln.strip() for ln in f if ln.strip()]
        # Fallback minimal labels; should be replaced by real labels.txt
        return ["Anthracnose", "Healthy", "Other"]

    def _preprocess(self, image_path: str) -> np.ndarray:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        img = Image.open(image_path).convert("RGB")

        # Determine expected size from model (assume H=W for classification)
        if len(self.input_shape) != 4:
            raise ValueError(f"Unexpected input shape: {self.input_shape}")
        _, h, w, c = self.input_shape
        if c != 3:
            raise ValueError("Model expects 3-channel RGB input")

        img = img.resize((w, h))
        arr = np.asarray(img, dtype=np.float32) / 255.0  # normalize to [0,1]
        arr = np.expand_dims(arr, axis=0)  # batch dimension
        return arr

    def predict(self, image_path: str) -> Tuple[str, float]:
        """Return (label, confidence) for provided image_path."""
        input_tensor = self._preprocess(image_path)
        self.interpreter.set_tensor(self.input_index, input_tensor)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_index)

        # Assume output shape [1, N] probabilities
        if output.ndim == 2 and output.shape[0] == 1:
            probs = output[0]
        else:
            probs = output.flatten()

        best_idx = int(np.argmax(probs))
        confidence = float(probs[best_idx])
        label = self.labels[best_idx] if best_idx < len(self.labels) else f"class_{best_idx}"
        return label, confidence

    def predict_raw(self, image_path: str) -> np.ndarray:
        """Return raw probability vector for advanced consumers."""
        input_tensor = self._preprocess(image_path)
        self.interpreter.set_tensor(self.input_index, input_tensor)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_index)
        if output.ndim == 2 and output.shape[0] == 1:
            return output[0]
        return output.flatten()


__all__ = ["DiseasePredictor"]
