from typing import Optional
from backend.config import DELIVERY_THRESHOLDS, DELIVERY_WEIGHTS


def calculate_delivery_score(
    visual_centering: Optional[float],
    blink_rate: Optional[float],
    pause_rate: Optional[float]
) -> Optional[float]:
    """
    Computes Delivery & Visual Stability score from observable physical and cadence signals.
    Returns None if visual sensors were unmeasured (e.g. camera off or permissions denied).
    """
    if visual_centering is None or blink_rate is None:
        return None

    vc_cfg = DELIVERY_THRESHOLDS["visual_centering"]
    if vc_cfg["optimal_min"] <= visual_centering <= vc_cfg["optimal_max"]:
        eye_score = 100.0
    else:
        eye_score = max(vc_cfg["floor_score"], visual_centering)

    blink_cfg = DELIVERY_THRESHOLDS["blink_rate"]
    if blink_cfg["optimal_min"] <= blink_rate <= blink_cfg["optimal_max"]:
        blink_score = 100.0
    else:
        blink_score = max(
            blink_cfg["floor_score"],
            100.0 - abs(blink_rate - blink_cfg["target_baseline"]) * blink_cfg["penalty_multiplier"]
        )

    pause_val = pause_rate if pause_rate is not None else 2.0
    pause_cfg = DELIVERY_THRESHOLDS["pause_rate"]
    if pause_val <= pause_cfg["optimal_max"]:
        pause_score = 100.0
    else:
        pause_score = max(
            pause_cfg["floor_score"],
            100.0 - pause_val * pause_cfg["penalty_per_second"]
        )

    final = (
        eye_score * DELIVERY_WEIGHTS["visual_centering"] +
        blink_score * DELIVERY_WEIGHTS["blink_frequency"] +
        pause_score * DELIVERY_WEIGHTS["pause_cadence"]
    )
    return round(final, 2)


# Backward-compatible alias
def calculate_behavioral_score(eye, blink, pause):
    return calculate_delivery_score(eye, blink, pause)