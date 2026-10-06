import pytest
from backend.services.voice_service import (
    validate_speech_segments,
    compute_vocabulary_diversity,
    compute_voice_metrics,
)
from backend.config import VOICE_PAUSE_THRESHOLD_SECONDS, MIN_WORDS_FOR_TTR, USE_VOICE_METRICS_IN_SCORE
from backend.services.scoring_engine import calculate_session_score


def test_validate_speech_segments():
    # Empty / None
    assert validate_speech_segments(None) == []
    assert validate_speech_segments([]) == []

    # Valid segments
    raw = [
        {"start": 0.5, "end": 2.0},
        {"start": 3.0, "end": 5.5},
    ]
    valid = validate_speech_segments(raw)
    assert len(valid) == 2
    assert valid[0]["start"] == 0.5
    assert valid[1]["end"] == 5.5

    # Malformed segments (negative start, end < start, overlaps)
    malformed = [
        {"start": -1.0, "end": 2.0},
        {"start": 3.0, "end": 2.5},
        {"start": 1.0, "end": 4.0},
        {"start": 3.5, "end": 6.0},  # Overlaps previous end of 4.0 -> corrected start=4.0
    ]
    cleaned = validate_speech_segments(malformed)
    assert len(cleaned) == 2
    assert cleaned[0]["start"] == 1.0
    assert cleaned[1]["start"] == 4.0


def test_compute_vocabulary_diversity_length_guard():
    # Less than MIN_WORDS_FOR_TTR (20 words)
    short_text = "I designed a scalable microservices architecture using FastAPI."
    result = compute_vocabulary_diversity(short_text)
    assert result["value"] is None
    assert "below the 20-word minimum" in result["interpretation"]

    # 25 words with high diversity
    long_diverse_text = (
        "We engineered distributed microservice pipelines using FastAPI, Redis caching, "
        "PostgreSQL indexing, Docker containers, Kubernetes orchestration, and Kafka streams "
        "to ensure high throughput resilience."
    )
    result_long = compute_vocabulary_diversity(long_diverse_text)
    assert result_long["value"] is not None
    assert result_long["value"] > 50.0
    assert "Vocabulary diversity score" in result_long["interpretation"]


def test_compute_voice_metrics_spoken_with_pauses():
    # Fixture with pause >= 0.8s:
    # 0.0 -> 1.0 (leading pause 1.0s >= 0.8s)
    # seg 1: 1.0 -> 3.0
    # gap: 3.0 -> 4.5 (gap 1.5s >= 0.8s)
    # seg 2: 4.5 -> 7.0
    segments = [
        {"start": 1.0, "end": 3.0},
        {"start": 4.5, "end": 7.0},
    ]
    transcript = (
        "In our previous project, um, we basically restructured the relational database "
        "schema to eliminate deadlocks and optimize slow query latency."
    )
    metrics = compute_voice_metrics(
        transcript=transcript,
        duration_seconds=10.0,
        speech_segments=segments,
        speech_source="speech",
    )

    assert metrics["speech_source"] == "speech"
    assert metrics["words_per_minute"]["value"] is not None
    assert metrics["filler_words"]["value"] >= 2  # 'um' and 'basically'
    pause_data = metrics["pause_metrics"]
    assert pause_data["pause_count"] == 2  # 1.0s leading pause + 1.5s gap
    assert pause_data["longest_pause"] == 1.5
    assert pause_data["avg_pause_duration"] == 1.25  # (1.0 + 1.5) / 2
    assert pause_data["silence_ratio"] == 0.25  # 2.5 / 10.0
    assert "Approximate, based on speech-recognition timing" in pause_data["interpretation"]


def test_compute_voice_metrics_typed_returns_null_cadence():
    transcript = "This is a typed answer that was entered manually via keyboard without microphone."
    metrics = compute_voice_metrics(
        transcript=transcript,
        duration_seconds=15.0,
        speech_segments=None,
        speech_source="typed",
    )

    assert metrics["speech_source"] == "typed"
    assert metrics["words_per_minute"]["value"] is None
    assert metrics["pause_metrics"]["pause_count"] is None
    assert metrics["pause_metrics"]["avg_pause_duration"] is None
    assert "Not measured" in metrics["words_per_minute"]["interpretation"]
    assert "Not measured" in metrics["pause_metrics"]["interpretation"]
    assert metrics["raw"]["words_per_minute"] is None
    assert metrics["raw"]["pause_count"] is None


def test_zero_duration_guard():
    metrics = compute_voice_metrics(
        transcript="Quick response",
        duration_seconds=0.0,
        speech_segments=[{"start": 0.0, "end": 0.0}],
        speech_source="speech",
    )
    assert metrics["words_per_minute"]["value"] is None
    assert "Duration too short" in metrics["words_per_minute"]["interpretation"]


def test_readiness_score_unaffected_by_voice_metrics():
    """
    Guarantees that USE_VOICE_METRICS_IN_SCORE = False ensures voice metrics
    do not alter the deterministic readiness score in Phase 2.
    """
    assert USE_VOICE_METRICS_IN_SCORE is False

    score1 = calculate_session_score(
        answer_scores=[80.0],
        technical_scores=[85.0],
        communication_scores=[80.0],
        consistency_scores=[90.0],
        delivery_score=85.6,
    )

    # Standard formula: 0.30 * Comm(80) + 0.30 * Tech(85) + 0.20 * Delivery(85.6) + 0.20 * Resume(90)
    # 24.0 + 25.5 + 17.12 + 18.0 = 84.62 -> 84.6
    assert round(score1["final_readiness_score"], 1) == 84.6


def test_voice_metrics_api_flow(client):
    # 1. Start interview
    start_resp = client.post(
        "/interview/start",
        json={"mode": "technical", "difficulty": "medium", "target_role": "Backend Engineer"},
    )
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]

    # 2. Submit spoken answer with segments
    ans_resp = client.post(
        f"/interview/{session_id}/answer",
        json={
            "session_id": session_id,
            "question_id": 1,
            "question_text": "Describe indexing strategies.",
            "transcript": (
                "We designed B-Tree indexing on primary user foreign keys and partial indexes "
                "on active tenant records to significantly cut database query execution time."
            ),
            "response_time": 12.0,
            "duration_seconds": 12.0,
            "wpm": 120.0,
            "filler_count": 0,
            "speech_source": "speech",
            "speech_segments": [
                {"start": 0.5, "end": 4.0},
                {"start": 5.5, "end": 11.5},
            ],
        },
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    assert "voice_metrics" in ans_data
    assert ans_data["voice_metrics"]["words_per_minute"]["value"] is not None
    assert ans_data["voice_metrics"]["pause_metrics"]["pause_count"] == 1  # 5.5 - 4.0 = 1.5s gap

    # 3. Complete interview
    client.post(
        f"/interview/{session_id}/complete",
        json={
            "eye_contact_percent": 82.0,
            "blink_rate": 18.0,
            "pause_rate": 1.5,
            "duration_seconds": 25.0,
        },
    )

    # 4. Check report includes voice_metrics in answer details
    rep_resp = client.get(f"/report/{session_id}")
    assert rep_resp.status_code == 200
    rep_data = rep_resp.json()
    assert len(rep_data["answers"]) >= 1
    assert rep_data["answers"][0]["voice_metrics"] is not None
    assert rep_data["answers"][0]["voice_metrics"]["speech_source"] == "speech"
    assert rep_data["answers"][0]["voice_metrics"]["words_per_minute"]["value"] is not None
