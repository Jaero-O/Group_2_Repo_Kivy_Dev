# Centralized severity threshold constants per manuscript
HEALTHY_MAX = 10.0        # <10% considered Healthy (or negligible)
EARLY_MAX = 30.0          # 10% - <30% Early Stage
# >=30% Advanced Stage

STAGE_NAMES = {
    'healthy': 'Healthy',
    'early': 'Early Stage',
    'advanced': 'Advanced Stage',
}

def severity_stage(severity_pct: float, predicted_label: str) -> str:
    """Map numeric severity + predicted label to stage name.
    - If model predicts Healthy OR severity < HEALTHY_MAX -> Healthy
    - Early Stage for [HEALTHY_MAX, EARLY_MAX)
    - Advanced Stage for >= EARLY_MAX
    """
    if predicted_label.lower() == 'healthy' or severity_pct < HEALTHY_MAX:
        return STAGE_NAMES['healthy']
    if severity_pct < EARLY_MAX:
        return STAGE_NAMES['early']
    return STAGE_NAMES['advanced']
