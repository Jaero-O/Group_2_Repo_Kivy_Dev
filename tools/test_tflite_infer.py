import os
import sys

# Ensure repo root is on sys.path so local `ml` package can be imported
sys.path.insert(0, os.getcwd())
from ml.predictor import DiseasePredictor
from ml.processing.severity import compute_severity

# Resolve model path via env override or default internal location
MODEL_ENV = os.getenv('MANGOFY_MODEL_PATH', '')
model_candidates = [
    MODEL_ENV,
    os.path.join('ml', 'models', 'mango_mobilenetv2.tflite'),
    os.path.join('ml','Plant_Disease_Prediction','tflite','mango_mobilenetv2.tflite'),
]
model_path = next((p for p in model_candidates if p and os.path.exists(p)), model_candidates[-1])

# Image path (test leaf image). Allow env override.
IMAGE_ENV = os.getenv('MANGOFY_TEST_IMAGE', '')
image_candidates = [
    IMAGE_ENV,
    os.path.join('samples', 'test_leaf.jpg'),
    os.path.join('leaf-detection','scripts','20211231_123305 (Custom).jpg'),
]
image_path = next((p for p in image_candidates if p and os.path.exists(p)), image_candidates[-1])

print('Using model path:', model_path)
print('Model exists:', os.path.exists(model_path))
print('Using image path:', image_path)
print('Image exists:', os.path.exists(image_path))

try:
    dp = DiseasePredictor(model_path, labels_path=os.getenv('MANGOFY_LABELS_PATH', ''))
    # Report loaded labels for verification
    if hasattr(dp, 'labels'):
        print('Loaded labels count:', len(dp.labels))
        if len(dp.labels) <= 10:
            print('Labels:', dp.labels)
        else:
            print('First 10 labels:', dp.labels[:10])
    if hasattr(dp, 'num_classes'):
        print('Model class count:', dp.num_classes)
    from PIL import Image
    try:
        Image.open(image_path).verify()
    except Exception:
        print('Provided image unreadable; creating dummy image')
        tmp = os.path.join('tools', 'tmp_test.jpg')
        img = Image.new('RGB', (224, 224), color=(128, 128, 128))
        img.save(tmp)
        image_path = tmp

    label, conf = dp.predict(image_path)
    raw = dp.predict_raw(image_path)
    severity = compute_severity(image_path)
    print('Prediction Label:', label)
    print('Confidence:', f"{conf:.4f}")
    print('Raw probs len:', len(raw))
    if len(raw) <= 10:
        print('Raw probs:', [float(f"{p:.4f}") for p in raw])
    print('Severity %:', severity)
except Exception as e:
    print('Inference error:', e)
