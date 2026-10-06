"""
backend/config.py
Centralized configuration for scoring parameters, thresholds, and verbal markers.

NOTE: The scoring weights and thresholds defined here represent baseline engineering
heuristics and assumptions; they are NOT empirically validated psychological or
psychometric measurements.
"""

from typing import Dict, List

# Session readiness weights (initial assumptions)
DEFAULT_SESSION_WEIGHTS: Dict[str, float] = {
    "communication": 0.30,
    "technical": 0.30,
    "delivery": 0.20,       # Delivery & Visual Stability (CV + pause pacing)
    "resume_consistency": 0.20,
}

# Delivery & Visual Stability component weights
DELIVERY_WEIGHTS: Dict[str, float] = {
    "visual_centering": 0.40,
    "blink_frequency": 0.30,
    "pause_cadence": 0.30,
}

# Target ranges for physical delivery signals
DELIVERY_THRESHOLDS = {
    "visual_centering": {
        "optimal_min": 60.0,
        "optimal_max": 85.0,
        "floor_score": 40.0,
    },
    "blink_rate": {
        "optimal_min": 15.0,
        "optimal_max": 20.0,
        "target_baseline": 18.0,
        "penalty_multiplier": 3.0,
        "floor_score": 50.0,
    },
    "pause_rate": {
        "optimal_max": 2.0,
        "penalty_per_second": 10.0,
        "floor_score": 40.0,
    },
}

# Answer length thresholds (word count)
WORD_COUNT_BANDS = {
    "floor_min": 5,        # Below this is considered empty/trivial
    "too_short": 25,       # Triggers follow-up probe for elaboration
    "minimal_detail": 40,   # Flagged as brief in critique
    "optimal_min": 70,     # Word count where full structure baseline is reached
    "optimal_max": 250,    # Ideal maximum for single response
}

# WPM (Words Per Minute) speech pacing bands
WPM_BANDS = {
    "slow_threshold": 100,
    "optimal_min": 120,
    "optimal_max": 160,
    "fast_threshold": 180,
}

# Verbal filler words to track
FILLER_WORDS: List[str] = [
    "um", "uh", "like", "basically", "actually", "literally",
    "you know", "sort of", "kind of", "i mean", "right"
]

# External LLM configuration
LLM_CONFIG = {
    "timeout_seconds": 5.0,
    "max_retries": 1,
    "temperature": 0.0,
    "prompt_version": "v1.0"
}

# Follow-up constraints
MAX_FOLLOWUPS_PER_QUESTION: int = 2

