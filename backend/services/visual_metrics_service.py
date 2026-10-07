"""
backend/services/visual_metrics_service.py
Service for client-side FaceMesh aggregate validation, quality gating,
and persistent per-answer storage.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import backend.models as models
from backend.config import (
    USE_EXTENDED_VISUAL_METRICS_IN_SCORE,
    EXTENDED_VISUAL_QUALITY_GATE,
)


def evaluate_visual_quality_gate(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Quality Gate for physical/visual metrics.
    If face_visibility_ratio < 0.60 or frames_sampled < 30:
    Metrics are classified as low_confidence and excluded from scoring or reporting.
    """
    if not metrics:
        return {
            "quality_status": "unmeasured",
            "is_usable": False,
            "reason": "No camera frames recorded",
        }

    frames = metrics.get("frames_sampled")
    min_frames = EXTENDED_VISUAL_QUALITY_GATE.get("min_frames_sampled", 30)
    if frames is None or frames < min_frames:
        return {
            "quality_status": "low_confidence",
            "is_usable": False,
            "reason": f"Sampled frames ({frames or 0}) below minimum quality threshold ({min_frames})",
        }

    vis_ratio = metrics.get("face_visibility_ratio")
    min_ratio = EXTENDED_VISUAL_QUALITY_GATE.get("min_face_visibility_ratio", 0.60)
    if vis_ratio is None or vis_ratio < min_ratio:
        return {
            "quality_status": "low_confidence",
            "is_usable": False,
            "reason": f"Face visibility ratio ({vis_ratio or 0.0}) below minimum threshold ({min_ratio})",
        }

    return {
        "quality_status": "acceptable",
        "is_usable": True,
        "reason": "Face visibility and frame sampling satisfy quality threshold",
    }


def extract_visual_metrics_dict(data: Any) -> Optional[Dict[str, Any]]:
    """Helper to extract visual metrics dictionary from request object or dictionary."""
    if not data:
        return None

    vm_dict = getattr(data, "visual_metrics", None) if not isinstance(data, dict) else data.get("visual_metrics")
    if not isinstance(vm_dict, dict):
        vm_dict = {}

    def _val(key: str):
        if not isinstance(data, dict):
            val = getattr(data, key, None)
            if val is not None:
                return val
        else:
            if key in data and data[key] is not None:
                return data[key]
        return vm_dict.get(key)

    head_align = _val("head_alignment_percent")
    blink = _val("blink_rate")
    variance = _val("head_movement_variance")
    vis_ratio = _val("face_visibility_ratio")
    shifts = _val("head_shift_count")
    frames = _val("frames_sampled")

    if all(v is None for v in [head_align, blink, variance, vis_ratio, shifts, frames]):
        return None

    return {
        "head_alignment_percent": float(head_align) if head_align is not None else None,
        "blink_rate": float(blink) if blink is not None else None,
        "head_movement_variance": float(variance) if variance is not None else None,
        "face_visibility_ratio": float(vis_ratio) if vis_ratio is not None else None,
        "head_shift_count": int(shifts) if shifts is not None else None,
        "frames_sampled": int(frames) if frames is not None else None,
    }


def store_answer_visual_metrics(
    answer_id: int,
    data: Any,
    db: Session,
) -> Optional[models.AnswerVisualMetrics]:
    """
    Validates, extracts, and stores per-answer visual metrics in answer_visual_metrics.
    Returns the created AnswerVisualMetrics record, or None if no visual data was provided.
    """
    metrics = extract_visual_metrics_dict(data)
    if not metrics:
        return None

    rec = models.AnswerVisualMetrics(
        answer_id=answer_id,
        head_alignment_percent=metrics.get("head_alignment_percent"),
        blink_rate=metrics.get("blink_rate"),
        head_movement_variance=metrics.get("head_movement_variance"),
        face_visibility_ratio=metrics.get("face_visibility_ratio"),
        head_shift_count=metrics.get("head_shift_count"),
        frames_sampled=metrics.get("frames_sampled"),
    )
    db.add(rec)
    db.flush()
    return rec
