import pytest
from backend.services.scoring_engine import (
    evaluate_rubric_for_answer,
    calculate_session_score,
)
from backend.crud import calculate_behavioral_score


def test_rubric_determinism(golden_answers):
    """The same input must produce exactly the same score across runs."""
    sample = golden_answers["strong"]
    res1 = evaluate_rubric_for_answer(
        transcript=sample,
        question_text="Explain REST API architecture and caching.",
        category="Technical",
        resume_skills=["Python", "FastAPI", "PostgreSQL", "Redis"],
        response_time=30.0,
        wpm=130.0,
        filler_count=0
    )
    res2 = evaluate_rubric_for_answer(
        transcript=sample,
        question_text="Explain REST API architecture and caching.",
        category="Technical",
        resume_skills=["Python", "FastAPI", "PostgreSQL", "Redis"],
        response_time=30.0,
        wpm=130.0,
        filler_count=0
    )

    assert res1["overall_score"] == res2["overall_score"]
    assert res1["technical_score"] == res2["technical_score"]
    assert res1["structure_score"] == res2["structure_score"]
    assert res1["reasoning_score"] == res2["reasoning_score"]
    assert res1["star_score"] == res2["star_score"]
    assert res1["consistency_score"] == res2["consistency_score"]
    assert res1["strengths"] == res2["strengths"]
    assert res1["weaknesses"] == res2["weaknesses"]


def test_golden_answers_strictly_ordered_bands(golden_answers):
    """Weak < Average < Strong in strictly ordered score bands."""
    weak_res = evaluate_rubric_for_answer(
        transcript=golden_answers["weak"],
        category="Technical"
    )
    avg_res = evaluate_rubric_for_answer(
        transcript=golden_answers["average"],
        category="Technical"
    )
    strong_res = evaluate_rubric_for_answer(
        transcript=golden_answers["strong"],
        category="Technical"
    )

    weak_score = weak_res["overall_score"]
    avg_score = avg_res["overall_score"]
    strong_score = strong_res["overall_score"]

    # Strictly ordered
    assert weak_score < avg_score < strong_score, (
        f"Expected weak ({weak_score}) < avg ({avg_score}) < strong ({strong_score})"
    )

    # In appropriate bands
    assert weak_score < 55.0, f"Weak score {weak_score} should be < 55.0"
    assert 55.0 <= avg_score <= 78.0, f"Average score {avg_score} should be in 55-78 band"
    assert strong_score >= 80.0, f"Strong score {strong_score} should be >= 80.0"


def test_empty_or_trivial_answer_handled_gracefully():
    """Empty or very short answers must not crash and should receive floor baseline scores."""
    res_empty = evaluate_rubric_for_answer(transcript="")
    assert res_empty["overall_score"] <= 30.0
    assert len(res_empty["weaknesses"]) > 0

    res_short = evaluate_rubric_for_answer(transcript="Yes I did.")
    assert res_short["overall_score"] <= 35.0


def test_readiness_formula_weighted_combination():
    """Final Readiness = 0.30 Comm + 0.30 Tech + 0.20 Behavioral + 0.20 Resume Consistency."""
    res = calculate_session_score(
        answer_scores=[80.0],
        behavioral_score=90.0,
        technical_scores=[80.0],
        communication_scores=[70.0],
        consistency_scores=[60.0]
    )

    # 0.30*70 + 0.30*80 + 0.20*90 + 0.20*60 = 21 + 24 + 18 + 12 = 75.0
    expected = round(0.30 * 70.0 + 0.30 * 80.0 + 0.20 * 90.0 + 0.20 * 60.0, 1)
    assert res["final_readiness_score"] == expected
    assert res["communication_score"] == 70.0
    assert res["technical_score"] == 80.0
    assert res["behavioral_score"] == 90.0
    assert res["resume_consistency_score"] == 60.0


def test_readiness_formula_boundary_values():
    """Formula must handle boundaries (all 0 and all 100)."""
    zero_res = calculate_session_score(
        answer_scores=[0.0],
        behavioral_score=0.0,
        technical_scores=[0.0],
        communication_scores=[0.0],
        consistency_scores=[0.0]
    )
    assert zero_res["final_readiness_score"] >= 0.0

    max_res = calculate_session_score(
        answer_scores=[100.0],
        behavioral_score=100.0,
        technical_scores=[100.0],
        communication_scores=[100.0],
        consistency_scores=[100.0]
    )
    assert max_res["final_readiness_score"] == 100.0


def test_delivery_score_calculation():
    """Delivery / Behavioral score calculation from eye contact, blink rate, pause rate."""
    # Optimal metrics: eye=75%, blink=18/min, pause=1.5s
    score_opt = calculate_behavioral_score(eye=75, blink=18, pause=1.5)
    assert score_opt == 100.0

    # Poor metrics: eye=20%, blink=40/min, pause=6s
    score_poor = calculate_behavioral_score(eye=20, blink=40, pause=6)
    assert score_poor < 60.0


def test_dimension_evidence_contract(golden_answers):
    """Every dimension must return {score, evidence, explanation, recommended_action}."""
    res = evaluate_rubric_for_answer(
        transcript=golden_answers["strong"],
        category="Technical",
        resume_skills=["FastAPI", "Redis"]
    )

    assert "dimensions" in res
    required_dimensions = ["structure", "technical", "reasoning", "star", "consistency"]

    for dim_name in required_dimensions:
        dim = res["dimensions"][dim_name]
        assert "score" in dim, f"Missing 'score' in {dim_name}"
        assert isinstance(dim["score"], (int, float))
        assert 0.0 <= dim["score"] <= 100.0

        assert "evidence" in dim, f"Missing 'evidence' in {dim_name}"
        assert isinstance(dim["evidence"], list)
        assert len(dim["evidence"]) > 0
        for ev in dim["evidence"]:
            assert isinstance(ev, str) and len(ev) > 0

        assert "explanation" in dim, f"Missing 'explanation' in {dim_name}"
        assert isinstance(dim["explanation"], str) and len(dim["explanation"]) > 0

        assert "recommended_action" in dim, f"Missing 'recommended_action' in {dim_name}"
        assert isinstance(dim["recommended_action"], str) and len(dim["recommended_action"]) > 0


def test_empty_answer_evidence_contract():
    """Empty answer must also strictly satisfy the evidence contract."""
    res = evaluate_rubric_for_answer(transcript="", category="Technical")
    for dim_name in ["structure", "technical", "reasoning", "star", "consistency"]:
        dim = res["dimensions"][dim_name]
        assert "score" in dim
        assert "evidence" in dim and len(dim["evidence"]) > 0
        assert "explanation" in dim
        assert "recommended_action" in dim

