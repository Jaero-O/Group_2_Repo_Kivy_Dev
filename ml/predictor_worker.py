#!/usr/bin/env python
"""
Worker script that runs in Python 3.10 environment with TFLite.
Called by predictor.py via subprocess.

Usage:
    python predictor_worker.py <command> <model_path> <image_path> <labels_path>
    
Commands:
    predict: Returns {label, confidence}
    predict_raw: Returns {probabilities: [...]}
"""

import sys
import json
import os
import numpy as np
from PIL import Image

# Import TFLite interpreter
_INTERPRETER = None
try:
    from tflite_runtime.interpreter import Interpreter
    _INTERPRETER = 'tflite_runtime'
except Exception:
    try:
        from tensorflow.lite.python.interpreter import Interpreter
        _INTERPRETER = 'tensorflow.lite'
    except Exception:
        _INTERPRETER = None


def load_labels(path):
    """Load labels from file."""
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip()]
    return ["Anthracnose", "Healthy", "Other"]


def preprocess_image(image_path, input_shape):
    """Preprocess image for model input."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    img = Image.open(image_path).convert("RGB")
    
    if len(input_shape) != 4:
        raise ValueError(f"Unexpected input shape: {input_shape}")
    
    _, h, w, c = input_shape
    if c != 3:
        raise ValueError("Model expects 3-channel RGB input")
    
    img = img.resize((w, h))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    arr = np.expand_dims(arr, axis=0)
    return arr


def run_prediction(model_path, image_path, labels_path, command):
    """Run TFLite prediction and return result as JSON."""
    if _INTERPRETER is None:
        raise RuntimeError("No TFLite interpreter available")
    
    # Load model
    interpreter = Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    input_index = input_details[0]['index']
    output_index = output_details[0]['index']
    input_shape = input_details[0]['shape']
    
    # Load labels
    labels = load_labels(labels_path)
    
    # Preprocess and run inference
    input_tensor = preprocess_image(image_path, input_shape)
    interpreter.set_tensor(input_index, input_tensor)
    interpreter.invoke()
    output = interpreter.get_tensor(output_index)
    
    # Get probabilities
    if output.ndim == 2 and output.shape[0] == 1:
        probs = output[0]
    else:
        probs = output.flatten()
    
    if command == "predict":
        best_idx = int(np.argmax(probs))
        confidence = float(probs[best_idx])
        label = labels[best_idx] if best_idx < len(labels) else f"class_{best_idx}"
        return {"label": label, "confidence": confidence}
    
    elif command == "predict_raw":
        return {"probabilities": probs.tolist()}
    
    else:
        raise ValueError(f"Unknown command: {command}")


def main():
    if len(sys.argv) != 5:
        print(json.dumps({"error": "Invalid arguments"}), file=sys.stderr)
        sys.exit(1)
    
    command = sys.argv[1]
    model_path = sys.argv[2]
    image_path = sys.argv[3]
    labels_path = sys.argv[4]
    
    try:
        result = run_prediction(model_path, image_path, labels_path, command)
        print(json.dumps(result))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
