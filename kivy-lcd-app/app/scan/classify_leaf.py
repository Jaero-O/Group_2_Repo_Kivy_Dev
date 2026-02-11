import sys
import numpy as np
from PIL import Image
import onnxruntime as ort
import json
from torchvision import transforms


# ---- GLOBAL MODEL SESSION (loads once) ----
ORT_SESSION = None


def load_session(model_path):
    global ORT_SESSION
    if ORT_SESSION is None:
        ORT_SESSION = ort.InferenceSession(model_path)
    return ORT_SESSION


def classify_image(session, image_path):
    img = Image.open(image_path).convert('RGB')

    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225])
    ])

    input_tensor = preprocess(img).unsqueeze(0).numpy()

    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: input_tensor})

    # ---- Softmax ----
    logits = outputs[0][0]
    exp_logits = np.exp(logits - np.max(logits))
    probs = exp_logits / exp_logits.sum()

    predicted_class_idx = int(np.argmax(probs))
    confidence = float(probs[predicted_class_idx])

    class_names = [
        'Anthracnose',
        'Bacterial Canker',
        'Cutting Weevil',
        'Die Back',
        'Gall Midge',
        'Healthy',
        'Powdery Mildew',
        'Sooty Mould'
    ]

    result = {
        'class': class_names[predicted_class_idx],
        'class_index': predicted_class_idx,
        'confidence': confidence,
        'probabilities': {
            class_names[i]: float(probs[i]) for i in range(len(class_names))
        }
    }

    return result


# ---- CLI ENTRY POINT (for subprocess) ----
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(json.dumps({
            "error": "Usage: python classifier_onnx.py <image_path> <model_path>"
        }))
        sys.exit(1)

    image_path = sys.argv[1]
    model_path = sys.argv[2]

    try:
        session = load_session(model_path)
        output = classify_image(session, image_path)
        print(json.dumps(output, indent=2))
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "class": "ERROR",
            "confidence": 0.0
        }))
        sys.exit(1)
