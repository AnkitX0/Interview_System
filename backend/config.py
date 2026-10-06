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
PRIVACY_POLICY_VERSION = "2.0"
DATA_RETENTION_STATEMENT = "Your data is kept until you delete it. You can export or delete your data at any time."


# ---------------------------
# Role Profiles Configuration (Phase 3 Intelligence)
# ---------------------------
ROLE_PROFILES = {
    "Backend Engineer": {
        "core_skills": [
            "python", "java", "go", "golang", "c++", "c#", "rust",
            "fastapi", "django", "flask", "spring", "spring boot", "node.js", "express",
            "postgresql", "postgres", "mysql", "mongodb", "redis", "cassandra", "dynamodb",
            "rest api", "restful", "graphql", "microservices", "docker", "kubernetes", "k8s",
            "distributed systems", "concurrency", "kafka", "rabbitmq", "grpc", "sql"
        ],
        "keywords": ["api", "database", "query", "cache", "latency", "throughput", "concurrency", "distributed", "server", "endpoint"]
    },
    "Frontend Engineer": {
        "core_skills": [
            "javascript", "typescript", "react", "react.js", "vue", "vue.js", "angular",
            "next.js", "html", "css", "redux", "tailwind", "webpack", "vite", "responsive design",
            "accessibility", "browser apis", "state management", "ui", "ux", "jest", "cypress"
        ],
        "keywords": ["component", "interface", "dom", "rendering", "styling", "state", "user", "frontend", "client"]
    },
    "Full-Stack Engineer": {
        "core_skills": [
            "javascript", "typescript", "react", "node.js", "python", "fastapi", "django",
            "sql", "postgresql", "mongodb", "rest api", "html", "css", "docker", "git", "ci/cd"
        ],
        "keywords": ["full-stack", "frontend", "backend", "database", "deployment", "end-to-end"]
    },
    "ML Engineer": {
        "core_skills": [
            "python", "pytorch", "tensorflow", "keras", "scikit-learn", "numpy", "pandas",
            "transformers", "nlp", "computer vision", "mlops", "llm", "huggingface", "deep learning",
            "machine learning", "feature engineering", "model training", "fine-tuning", "onnx"
        ],
        "keywords": ["model", "training", "inference", "accuracy", "dataset", "neural", "weights", "loss", "pipeline", "prediction"]
    },
    "Data Scientist": {
        "core_skills": [
            "python", "sql", "r", "pandas", "numpy", "scikit-learn", "statistics",
            "tableau", "power bi", "data visualization", "a/b testing", "etl", "machine learning",
            "data analysis", "big data", "spark", "hadoop", "eda"
        ],
        "keywords": ["analysis", "dataset", "hypothesis", "metrics", "statistical", "regression", "insights", "dashboard"]
    },
    "DevOps Engineer": {
        "core_skills": [
            "linux", "docker", "kubernetes", "k8s", "terraform", "ansible", "ci/cd",
            "aws", "gcp", "azure", "prometheus", "grafana", "git", "bash", "shell",
            "nginx", "helm", "networking", "infrastructure", "security"
        ],
        "keywords": ["pipeline", "cluster", "deploy", "monitoring", "alerting", "infrastructure", "container", "automation"]
    },
    "Software Engineer": {
        "core_skills": [
            "python", "java", "c++", "javascript", "sql", "git", "data structures",
            "algorithms", "oop", "system design", "rest api", "docker", "testing", "linux"
        ],
        "keywords": ["software", "development", "code", "design", "refactor", "test", "implementation"]
    },
}


# ---------------------------
# Verification Risk Configuration (Phase 3 Intelligence)
# ---------------------------
VERIFICATION_RISK_CONFIG = {
    "min_word_count": 20,  # Fewer than 20 words -> not_computed (guard against penalizing short answers)
    "weights": {
        "generic_phrases": 0.25,
        "buzzwords_vs_specifics": 0.30,
        "lack_of_specifics": 0.20,
        "repetition": 0.40,
        "ownership_vagueness": 0.25,
    },
    "thresholds": {
        "low_max": 30.0,        # 0.0 - 30.0 -> low
        "moderate_max": 55.0,   # 30.1 - 55.0 -> moderate
        # > 55.0 -> elevated
    },

    "disclaimer": "Verification Risk is a heuristic based on wording patterns. It is not proof of anything and can be wrong, for example for concise speakers or non-native English.",
    "generic_phrases": [
        "best practices", "industry standard", "seamlessly integrated", "next level",
        "end to end solution", "state of the art", "cutting edge", "worked on various tasks",
        "handled different things", "did a lot of stuff", "helped out with everything",
        "various components", "multiple features", "many responsibilities", "general work",
        "synergistic", "paradigm shift", "streamlined the entire process", "modern stack",
        "all required technologies", "standard architecture", "typical setup", "did the needful",
        "highly scalable architecture", "worked on various aspects"
    ],
    "buzzwords": [
        "robust", "scalable", "synergy", "paradigm", "disruptive", "cutting-edge",
        "state-of-the-art", "game-changing", "revolutionary", "seamless", "holistic",
        "ecosystem", "hyper-scalable", "mission-critical", "enterprise-grade", "leverage",
        "streamline", "dynamic", "agile", "next-generation", "world-class"
    ],
    "concrete_verbs": [
        "implemented", "configured", "deployed", "profiled", "optimized", "migrated",
        "benchmarked", "refactored", "debugged", "indexed", "instrumented", "provisioned",
        "architected", "partitioned", "monitored", "scaled", "containerized", "automated",
        "reduced", "increased"
    ],
    "vague_ownership_phrases": [
        "we basically just", "we kind of did", "someone on the team", "the team mostly",
        "i was involved somewhat", "i assisted with some parts", "it was done for us",
        "they gave us the code", "not sure what happened behind the scenes", "i was just there",
        "the team did most of it"
    ],
}


