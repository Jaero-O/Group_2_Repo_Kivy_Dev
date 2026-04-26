"""
ONNX-based Leaf Disease Classification
Pipeline-compatible version with consistent output format
"""

import sys
import numpy as np
from PIL import Image
import onnxruntime as ort
import json

# ============================================================
# GLOBAL MODEL SESSION (loads once)
# ============================================================
ORT_SESSION = None

def load_session(model_path):
    """Load ONNX model session (cached globally)"""
    global ORT_SESSION
    if ORT_SESSION is None:
        ORT_SESSION = ort.InferenceSession(model_path)
    return ORT_SESSION


# ============================================================
# IMAGE PREPROCESSING
# ============================================================
def preprocess_image(image_path):
    """
    Preprocess image for model inference without torchvision.
    
    Args:
        image_path: Path to input image
    
    Returns:
        Preprocessed tensor as numpy array [1, 3, 224, 224]
    """
    img = Image.open(image_path).convert('RGB')

    # resize shorter side to 256 preserving aspect ratio, then center crop 224
    w, h = img.size
    if w < h:
        new_w = 256
        new_h = int(round(h * 256 / w))
    else:
        new_h = 256
        new_w = int(round(w * 256 / h))
    img = img.resize((new_w, new_h), Image.BILINEAR)

    left = (new_w - 224) // 2
    top = (new_h - 224) // 2
    right = left + 224
    bottom = top + 224
    img = img.crop((left, top, right, bottom))

    arr = np.asarray(img, dtype=np.float32) / 255.0
    # reshape to CHW
    arr = np.transpose(arr, (2, 0, 1))

    # normalize
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)
    arr = (arr - mean) / std

    # add batch
    arr = np.expand_dims(arr, axis=0)
    return arr


# ============================================================
# CLASSIFICATION
# ============================================================
def classify_image(session, image_path):
    """
    Classify leaf disease from image.
    
    Args:
        session: ONNX runtime session
        image_path: Path to input image
    
    Returns:
        Dictionary with classification results
    """
    # Preprocess image
    input_tensor = preprocess_image(image_path)
    
    # Run inference
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: input_tensor})
    
    # Apply softmax to get probabilities
    logits = outputs[0][0]
    exp_logits = np.exp(logits - np.max(logits))  # Numerical stability
    probs = exp_logits / exp_logits.sum()
    
    # Get prediction
    predicted_class_idx = int(np.argmax(probs))
    confidence = float(probs[predicted_class_idx])
    
    # Class names (must match training order)
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
    
    # Build result dictionary
    result = {
        'class': class_names[predicted_class_idx],
        'class_index': predicted_class_idx,
        'confidence': confidence,
        'probabilities': {
            class_names[i]: float(probs[i]) for i in range(len(class_names))
        }
    }
    
    return result


# ============================================================
# BATCH CLASSIFICATION (Optional)
# ============================================================
def classify_batch(session, image_paths):
    """
    Classify multiple images.
    
    Args:
        session: ONNX runtime session
        image_paths: List of image paths
    
    Returns:
        List of classification results
    """
    results = []
    for img_path in image_paths:
        try:
            result = classify_image(session, img_path)
            result['image_path'] = img_path
            results.append(result)
        except Exception as e:
            results.append({
                'image_path': img_path,
                'error': str(e),
                'class': 'ERROR',
                'confidence': 0.0
            })
    return results


# ============================================================
# CLI ENTRY POINT (for subprocess calls from pipeline)
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(json.dumps({
            "error": "Usage: python classify_leaf.py <image_path> <model_path>"
        }))
        sys.exit(1)
    
    image_path = sys.argv[1]
    model_path = sys.argv[2]
    
    try:
        # Load model
        session = load_session(model_path)
        
        # Classify image
        output = classify_image(session, image_path)
        
        # Print JSON output (consumed by pipeline)
        print(json.dumps(output, indent=2))
        
    except FileNotFoundError as e:
        error_result = {
            "error": f"File not found: {str(e)}",
            "class": "ERROR",
            "confidence": 0.0
        }
        print(json.dumps(error_result))
        sys.exit(1)
        
    except Exception as e:
        error_result = {
            "error": str(e),
            "class": "ERROR",
            "confidence": 0.0
        }
        print(json.dumps(error_result))
        sys.exit(1)
