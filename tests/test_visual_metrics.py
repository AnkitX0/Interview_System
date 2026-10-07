import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import backend.models as models
from backend.config import USE_EXTENDED_VISUAL_METRICS_IN_SCORE, EXTENDED_VISUAL_QUALITY_GATE
from backend.services.visual_metrics_service import (
    evaluate_visual_quality_gate,
    extract_visual_metrics_dict,
    store_answer_visual_metrics,
)
from backend.services.scoring_engine import calculate_session_score


def test_visual_quality_gate_low_frames():
    """Frames sampled below 30 fails the quality gate and is marked low confidence."""
    res = evaluate_visual_quality_gate({
        "frames_sampled": 15,
        "face_visibility_ratio": 0.95,
        "head_alignment_percent": 85.0
    })
    assert res["quality_status"] == "low_confidence"
    assert res["is_usable"] is False
    assert "below minimum quality threshold" in res["reason"]


def test_visual_quality_gate_low_visibility_ratio():
    """Face visibility ratio below 0.60 fails the quality gate and is marked low confidence."""
    res = evaluate_visual_quality_gate({
        "frames_sampled": 120,
        "face_visibility_ratio": 0.45,
        "head_alignment_percent": 85.0
    })
    assert res["quality_status"] == "low_confidence"
    assert res["is_usable"] is False
    assert "below minimum threshold" in res["reason"]


def test_visual_quality_gate_acceptable():
    """Adequate frames and face visibility ratio passes quality gate."""
    res = evaluate_visual_quality_gate({
        "frames_sampled": 150,
        "face_visibility_ratio": 0.92,
        "head_alignment_percent": 80.0
    })
    assert res["quality_status"] == "acceptable"
    assert res["is_usable"] is True


def test_visual_quality_gate_empty_or_none():
    """Null or empty visual metrics are classified as unmeasured."""
    res_none = evaluate_visual_quality_gate(None)
    assert res_none["quality_status"] == "unmeasured"
    assert res_none["is_usable"] is False

    res_empty = evaluate_visual_quality_gate({})
    assert res_empty["quality_status"] == "unmeasured"
    assert res_empty["is_usable"] is False


def test_store_visual_metrics_in_database(db_session: Session):
    """Ensure AnswerVisualMetrics rows are properly created and linked to InterviewAnswer."""
    user = models.User(email="vis_test@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    session = models.InterviewSession(
        user_id=user.id,
        mode="technical",
        difficulty="medium",
        target_role="Software Engineer"
    )
    db_session.add(session)
    db_session.commit()

    answer = models.InterviewAnswer(
        session_id=session.id,
        question_id=1,
        question_text="Sample question",
        transcript="Sample answer text for testing visual metrics persistence."
    )
    db_session.add(answer)
    db_session.commit()

    data = {
        "visual_metrics": {
            "head_alignment_percent": 88.5,
            "blink_rate": 17.2,
            "head_movement_variance": 0.0025,
            "face_visibility_ratio": 0.94,
            "head_shift_count": 3,
            "frames_sampled": 140
        }
    }

    rec = store_answer_visual_metrics(answer.id, data, db_session)
    db_session.commit()

    assert rec is not None
    assert rec.answer_id == answer.id
    assert rec.head_alignment_percent == 88.5
    assert rec.blink_rate == 17.2
    assert rec.face_visibility_ratio == 0.94
    assert rec.frames_sampled == 140

    # Query back from DB
    queried = db_session.query(models.AnswerVisualMetrics).filter_by(answer_id=answer.id).first()
    assert queried is not None
    assert queried.head_shift_count == 3


def test_api_submit_answer_with_visual_metrics(client: TestClient, db_session: Session):
    """API endpoint stores visual metrics and returns quality status in response."""
    start_resp = client.post(
        "/interview/start",
        json={"mode": "technical", "difficulty": "medium", "target_role": "Backend Engineer", "question_count": 2}
    )
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]

    answer_payload = {
        "session_id": session_id,
        "question_id": 1,
        "question_text": "Explain REST API architecture.",
        "transcript": "REST stands for representational state transfer. We use standard HTTP verbs like GET, POST, PUT, DELETE.",
        "response_time": 25.0,
        "duration_seconds": 25.0,
        "wpm: liveWpm": 120.0,
        "visual_metrics": {
            "head_alignment_percent": 84.0,
            "blink_rate": 18.0,
            "head_movement_variance": 0.0018,
            "face_visibility_ratio": 0.95,
            "head_shift_count": 1,
            "frames_sampled": 100
        }
    }

    ans_resp = client.post(f"/interview/{session_id}/answer", json=answer_payload)
    assert ans_resp.status_code == 200
    res_data = ans_resp.json()

    assert "visual_metrics" in res_data
    vm = res_data["visual_metrics"]
    assert vm is not None
    assert vm["quality_status"] == "acceptable"
    assert vm["is_usable"] is True
    assert vm["face_visibility_ratio"] == 0.95

    # Check DB record exists
    answer_id = res_data["answer_id"]
    db_vm = db_session.query(models.AnswerVisualMetrics).filter_by(answer_id=answer_id).first()
    assert db_vm is not None
    assert db_vm.frames_sampled == 100


def test_api_submit_answer_low_confidence_quality_gate(client: TestClient):
    """When face visibility ratio is low, API return flags visual metrics as low confidence."""
    start_resp = client.post(
        "/interview/start",
        json={"mode": "technical", "difficulty": "medium", "target_role": "Backend Engineer", "question_count": 2}
    )
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]

    answer_payload = {
        "session_id": session_id,
        "question_id": 1,
        "question_text": "Explain REST API architecture.",
        "transcript": "REST APIs utilize stateless communication between client and server across standard HTTP methods.",
        "response_time": 20.0,
        "duration_seconds": 20.0,
        "visual_metrics": {
            "head_alignment_percent": 45.0,
            "blink_rate": 12.0,
            "head_movement_variance": 0.05,
            "face_visibility_ratio": 0.35,  # Below 0.60 threshold
            "head_shift_count": 8,
            "frames_sampled": 80
        }
    }

    ans_resp = client.post(f"/interview/{session_id}/answer", json=answer_payload)
    assert ans_resp.status_code == 200
    res_data = ans_resp.json()

    vm = res_data.get("visual_metrics")
    assert vm is not None
    assert vm["quality_status"] == "low_confidence"
    assert vm["is_usable"] is False


def test_readiness_score_invariance_with_flag_off():
    """Readiness score is 100% invariant whether extended visual metrics are present or not when flag is False."""
    assert USE_EXTENDED_VISUAL_METRICS_IN_SCORE is False

    answer_scores = [80.0, 85.0, 90.0]
    tech_scores = [85.0, 85.0, 85.0]
    comm_scores = [80.0, 80.0, 80.0]
    cons_scores = [90.0, 90.0, 90.0]

    # Baseline: camera off (delivery unmeasured)
    score_unmeasured = calculate_session_score(
        answer_scores=answer_scores,
        delivery_score=None,
        technical_scores=tech_scores,
        communication_scores=comm_scores,
        consistency_scores=cons_scores,
    )

    # With delivery measured
    score_measured = calculate_session_score(
        answer_scores=answer_scores,
        delivery_score=75.0,
        technical_scores=tech_scores,
        communication_scores=comm_scores,
        consistency_scores=cons_scores,
    )

    assert score_unmeasured["delivery_measured"] is False
    assert score_unmeasured["final_readiness_score"] == round(0.375 * 80.0 + 0.375 * 85.0 + 0.25 * 90.0, 1)

    assert score_measured["delivery_measured"] is True
    assert score_measured["final_readiness_score"] == round(0.30 * 80.0 + 0.30 * 85.0 + 0.20 * 75.0 + 0.20 * 90.0, 1)
