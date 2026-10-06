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

# ---------------------------
# Authentication Configuration
# ---------------------------
import os
import secrets
import logging

_logger = logging.getLogger("interview_system.config")

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("AUTH_SECRET_KEY")

if not SECRET_KEY:
    if ENVIRONMENT == "production":
        raise RuntimeError("FATAL: SECRET_KEY environment variable is required in production mode.")
    else:
        SECRET_KEY = secrets.token_urlsafe(32)
        _logger.warning("No SECRET_KEY set. Generated ephemeral dev secret. Logins will invalidate on server restart.")

AUTH_COOKIE_NAME = "auth_token"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
ALGORITHM = "HS256"

# ---------------------------
# Voice Metrics Configuration
# ---------------------------
# In Phase 2, voice metrics are display-only and must not alter readiness score calculations.
# Will be integrated once golden-answer tests cover them.
USE_VOICE_METRICS_IN_SCORE = False
VOICE_PAUSE_THRESHOLD_SECONDS = 0.8  # Gap between speech-recognition segments to count as a pause (assumption)
MIN_WORDS_FOR_TTR = 20  # Minimum words required for vocabulary diversity calculation
TTR_MOVING_WINDOW = 50  # Moving-average TTR window

# ---------------------------
# Privacy & Consent Configuration
# ---------------------------
PRIVACY_POLICY_VERSION = "1.0"
DATA_RETENTION_STATEMENT = "Your data is kept until you delete it. You can export or delete your data at any time."

