"""Configuration file for ML model paths and settings.

This centralizes hardcoded paths and enables version tracking.
"""

import os
from pathlib import Path

# Base directories
PROJECT_ROOT = Path(__file__).parent.parent
ML_DIR = PROJECT_ROOT / 'ml' / 'Plant_Disease_Prediction'

# Model configuration
MODEL_CONFIG = {
    'tflite': {
        'path': ML_DIR / 'tflite' / 'mango_mobilenetv2.tflite',
        'labels': ML_DIR / 'tflite' / 'labels.txt',
        'version': '1.0.0',
        'type': 'mobilenetv2',
        'input_size': (224, 224),
        'enabled': True,
    },
    'h5': {
        'dir': ML_DIR / 'h5',
        'fallback_enabled': False,  # Set True to enable H5 fallback
        'version': '1.0.0',
    }
}

# Severity thresholds
SEVERITY_THRESHOLDS = {
    'healthy': 0.0,
    'early_stage': 10.0,
    'advanced_stage': 30.0,
}

# Confidence thresholds
CONFIDENCE_THRESHOLDS = {
    'minimum': 0.6,  # Below this, consider result uncertain
    'high': 0.85,    # Above this, consider result reliable
}

def get_model_path(model_type='tflite'):
    """Get the configured model path.
    
    Args:
        model_type: 'tflite' or 'h5'
    
    Returns:
        Path object or None if not configured
    """
    if model_type == 'tflite':
        config = MODEL_CONFIG.get('tflite', {})
        if config.get('enabled'):
            return str(config.get('path', ''))
    elif model_type == 'h5':
        config = MODEL_CONFIG.get('h5', {})
        if config.get('fallback_enabled'):
            return str(config.get('dir', ''))
    return None

def get_labels_path(model_type='tflite'):
    """Get the labels file path.
    
    Args:
        model_type: 'tflite' or 'h5'
    
    Returns:
        Path string or None
    """
    if model_type == 'tflite':
        config = MODEL_CONFIG.get('tflite', {})
        return str(config.get('labels', ''))
    return None

def get_model_version(model_type='tflite'):
    """Get the model version.
    
    Args:
        model_type: 'tflite' or 'h5'
    
    Returns:
        Version string
    """
    config = MODEL_CONFIG.get(model_type, {})
    return config.get('version', 'unknown')

def is_h5_fallback_enabled():
    """Check if H5 fallback is enabled."""
    return MODEL_CONFIG.get('h5', {}).get('fallback_enabled', False)
