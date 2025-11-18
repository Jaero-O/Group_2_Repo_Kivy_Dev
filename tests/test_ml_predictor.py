import os
import sys
import tempfile
import numpy as np
import types
from unittest.mock import patch, MagicMock

# Ensure src is importable
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# The real module `tflite_runtime` may not be available in CI or developer
# environments. Provide a lightweight fake in `sys.modules` so importing
# `ml.predictor` succeeds and we can control the Interpreter used for tests.
import sys

def _ensure_fake_tflite(DummyInterpreter):
    # Create a minimal fake package and submodule
    fake_pkg = types.ModuleType('tflite_runtime')
    fake_interp_mod = types.ModuleType('tflite_runtime.interpreter')
    fake_interp_mod.Interpreter = DummyInterpreter
    sys.modules['tflite_runtime'] = fake_pkg
    sys.modules['tflite_runtime.interpreter'] = fake_interp_mod

class DummyInterpreter:
    def __init__(self, model_path=None):
        self._tensors = {}
        self._output = np.array([[0.1, 0.9]], dtype=np.float32)

    def allocate_tensors(self):
        pass

    def get_input_details(self):
        return [{'index': 0}]

    def get_output_details(self):
        return [{'index': 0}]

    def set_tensor(self, idx, value):
        self._tensors[idx] = value

    def invoke(self):
        # pretend to run inference
        pass

    def get_tensor(self, idx):
        return self._output


_ensure_fake_tflite(DummyInterpreter)

from ml.predictor import DiseasePredictor


def test_predictor_with_mocked_interpreter_and_labels(tmp_path, monkeypatch):
    # Create a fake labels file
    labels_file = tmp_path / "labels.txt"
    labels_file.write_text("Healthy\nAnthracnose\n")

    # Create a tiny dummy image file
    img_file = tmp_path / "img.jpg"
    from PIL import Image
    Image.new('RGB', (224, 224), color=(255, 255, 255)).save(img_file)

    # Patch the tflite Interpreter used inside ml.predictor
    monkeypatch.setattr('ml.predictor.tflite.Interpreter', lambda model_path=None: DummyInterpreter(model_path))

    pred = DiseasePredictor(model_path=str(tmp_path / 'dummy.tflite'), labels_path=str(labels_file))
    label, confidence = pred.predict(str(img_file))

    assert label == 'Anthracnose'
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0
