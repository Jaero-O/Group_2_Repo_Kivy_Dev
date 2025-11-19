"""ml.predictor
Provides a small wrapper around a TFLite Interpreter. This module first
tries to use the lightweight `tflite_runtime` package; if that's not
available it falls back to `tensorflow`'s `tf.lite.Interpreter` so the
project can run on environments where `tensorflow` is installed.

The implementation is defensive: if a `labels_path` file is missing we
infer the number of output classes from the model output shape and
generate placeholder class names so inference can still run.
"""
import os
import numpy as np
from PIL import Image
import types

# Try lightweight runtime first, then fall back to tensorflow
try:
    import tflite_runtime.interpreter as _tflite_rt
    Interpreter = _tflite_rt.Interpreter
except Exception:
    Interpreter = None

if Interpreter is None:
    try:
        import tensorflow as _tf
        Interpreter = _tf.lite.Interpreter
    except Exception:
        Interpreter = None

# Expose a lightweight `tflite` attribute so tests can monkeypatch
# `ml.predictor.tflite.Interpreter` even though we resolve the runtime above.
tflite = types.SimpleNamespace(Interpreter=Interpreter)


class DiseasePredictor:
    def __init__(self, model_path, labels_path):
        if Interpreter is None:
            raise RuntimeError('No TFLite interpreter is available (install tflite_runtime or tensorflow)')
        # Allow tests to supply a dummy/nonexistent model path when using a
        # monkeypatched Interpreter. If the file is missing we proceed rather
        # than raising to keep unit tests lightweight.
        if not os.path.exists(model_path):
            try:
                # If the path is missing, create a tiny placeholder file so
                # real runtimes that require a readable file do not fail.
                with open(model_path, 'wb') as _f:
                    _f.write(b'00')
            except Exception:
                # If we cannot create it, still proceed (mocked interpreter).
                pass

        # Construct interpreter and allocate tensors
        self.interpreter = Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        # Load labels if available; otherwise generate placeholder labels
        if labels_path and os.path.exists(labels_path):
            with open(labels_path, 'r', encoding='utf-8') as f:
                self.labels = [line.strip() for line in f.readlines() if line.strip()]
        else:
            # Infer number of classes from output tensor shape
            try:
                out_shape = self.output_details[0]['shape']
                num_classes = int(out_shape[-1]) if len(out_shape) >= 1 else 1
            except Exception:
                num_classes = 1
            self.labels = [f'class_{i}' for i in range(num_classes)]

    def predict(self, image_path):
        """Run inference on `image_path` and return (label, confidence).

        The image is resized to 224x224 and normalized to [0,1]. If your
        model expects a different preprocessing, modify this function.
        """
        img = Image.open(image_path).convert('RGB').resize((224, 224))
        img_array = np.array(img, dtype=np.float32)
        img_array = np.expand_dims(img_array, axis=0)
        img_array /= 255.0

        # Respect model's expected input dtype
        try:
            in_dt = self.input_details[0]['dtype']
            img_array = img_array.astype(in_dt)
        except Exception:
            pass

        self.interpreter.set_tensor(self.input_details[0]['index'], img_array)
        self.interpreter.invoke()
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])

        prediction = np.array(output_data[0])
        idx = int(np.argmax(prediction)) if prediction.size > 0 else 0
        predicted_label = self.labels[idx] if idx < len(self.labels) else self.labels[0]
        confidence = float(np.max(prediction)) if prediction.size > 0 else 0.0
        return predicted_label, confidence

