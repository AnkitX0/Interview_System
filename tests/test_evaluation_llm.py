import os
import json
import pytest
from unittest.mock import patch, MagicMock

from backend.services.evaluation_engine import (
    evaluate_answer,
    _verify_evidence_grounding,
    _EVALUATION_CACHE
)


def test_offline_deterministic_fallback_no_keys(monkeypatch):
    """When no API keys are configured, fallback to rubric engine with engine_used='rubric'."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _EVALUATION_CACHE.clear()

    res = evaluate_answer(
        transcript="We deployed Redis cache cluster to optimize our SQL queries, reducing API latency by 45%.",
        question_text="How do you handle backend caching?",
        category="Technical"
    )

    assert res["engine_used"] == "rubric"
    assert "dimensions" in res
    assert res["technical_score"] >= 70.0


def test_input_hash_caching(monkeypatch):
    """Calling evaluate_answer twice with identical inputs should hit cache."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _EVALUATION_CACHE.clear()

    sample = "I designed and deployed a microservice using FastAPI and Docker."
    res1 = evaluate_answer(transcript=sample, question_text="Q1", category="Technical")
    res2 = evaluate_answer(transcript=sample, question_text="Q1", category="Technical")

    assert res1 is res2  # Exactly the same cached dict reference


def test_grounding_check_logic():
    """Grounding check: quotes in evidence must be substrings of the transcript."""
    transcript = "We reduced latency by 35% using indexing on MongoDB."

    # Valid quote
    valid_evidence = ["Candidate stated 'reduced latency by 35%' which is quantitative."]
    assert _verify_evidence_grounding(valid_evidence, transcript) is True

    # Hallucinated quote
    hallucinated_evidence = ["Candidate said 'we scaled to 100k requests per second' in production."]
    assert _verify_evidence_grounding(hallucinated_evidence, transcript) is False


def test_mocked_gemini_success_path(monkeypatch):
    """When GEMINI_API_KEY is present and Gemini returns valid JSON, format and return."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _EVALUATION_CACHE.clear()

    mock_llm_json = {
        "dimensions": {
            "structure": {
                "score": 85.0,
                "evidence": ["3 sentences with clear beginning and end"],
                "explanation": "Clear structural organization.",
                "recommended_action": "Keep using transitions."
            },
            "technical": {
                "score": 88.0,
                "evidence": ["Mentioned Redis and FastAPI"],
                "explanation": "Strong domain awareness.",
                "recommended_action": "Add concurrency details."
            },
            "reasoning": {
                "score": 82.0,
                "evidence": ["Compared against raw SQL"],
                "explanation": "Solid rationale.",
                "recommended_action": "Discuss cost trade-offs."
            },
            "star": {
                "score": 80.0,
                "evidence": ["Actions taken and outcome provided"],
                "explanation": "Good STAR flow.",
                "recommended_action": "Mention SLA specifics."
            },
            "consistency": {
                "score": 85.0,
                "evidence": ["Skills match backend track"],
                "explanation": "Consistent with profile.",
                "recommended_action": "Link to portfolio."
            }
        },
        "missing_concepts": ["Distributed locks"]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(mock_llm_json)}]
                }
            }
        ]
    }

    with patch("httpx.Client.post", return_value=mock_response):
        res = evaluate_answer(
            transcript="We deployed Redis cache cluster to optimize our SQL queries, reducing API latency by 45%.",
            question_text="How do you handle backend caching?",
            category="Technical"
        )

        assert res["engine_used"] == "llm_gemini"
        assert res["technical_score"] == 88.0
        assert res["structure_score"] == 85.0


def test_gemini_failure_openai_fallback(monkeypatch):
    """When Gemini fails, fallback to OpenAI if OPENAI_API_KEY is present."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "mock-openai-key")
    _EVALUATION_CACHE.clear()

    mock_openai_json = {
        "dimensions": {
            "structure": {
                "score": 75.0,
                "evidence": ["2 sentences"],
                "explanation": "Decent structure.",
                "recommended_action": "Elaborate more."
            },
            "technical": {
                "score": 80.0,
                "evidence": ["PostgreSQL indexing"],
                "explanation": "Solid.",
                "recommended_action": "Add cache details."
            },
            "reasoning": {
                "score": 75.0,
                "evidence": ["Evaluated B-tree"],
                "explanation": "Good.",
                "recommended_action": "Compare against hash index."
            },
            "star": {
                "score": 70.0,
                "evidence": ["Actions clear"],
                "explanation": "Fair.",
                "recommended_action": "Add metrics."
            },
            "consistency": {
                "score": 80.0,
                "evidence": ["Aligned"],
                "explanation": "Aligned.",
                "recommended_action": "Keep going."
            }
        }
    }

    # First call (Gemini) returns 500, second call (OpenAI) returns 200
    mock_gemini_resp = MagicMock()
    mock_gemini_resp.status_code = 500

    mock_openai_resp = MagicMock()
    mock_openai_resp.status_code = 200
    mock_openai_resp.json.return_value = {
        "choices": [
            {
                "message": {"content": json.dumps(mock_openai_json)}
            }
        ]
    }

    def mock_post_side_effect(url, **kwargs):
        if "googleapis.com" in url:
            return mock_gemini_resp
        elif "openai.com" in url:
            return mock_openai_resp
        return mock_gemini_resp

    with patch("httpx.Client.post", side_effect=mock_post_side_effect):
        res = evaluate_answer(
            transcript="We used PostgreSQL B-tree indexing to speed up queries.",
            question_text="How do you optimize databases?",
            category="Technical"
        )

        assert res["engine_used"] == "llm_openai"
        assert res["technical_score"] == 80.0


def test_hallucinated_llm_quotes_trigger_rubric_fallback(monkeypatch):
    """When LLM hallucinates quotes in evidence that candidate never said, reject and fallback to rubric."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key")
    _EVALUATION_CACHE.clear()

    mock_hallucinated_json = {
        "dimensions": {
            "structure": {
                "score": 90.0,
                "evidence": ["Candidate explicitly stated 'I am the chief architect of Google Search'."],
                "explanation": "Structure.",
                "recommended_action": "Action."
            },
            "technical": {"score": 90.0, "evidence": ["Tech"], "explanation": "Tech", "recommended_action": "Act"},
            "reasoning": {"score": 90.0, "evidence": ["Reas"], "explanation": "Reas", "recommended_action": "Act"},
            "star": {"score": 90.0, "evidence": ["Star"], "explanation": "Star", "recommended_action": "Act"},
            "consistency": {"score": 90.0, "evidence": ["Cons"], "explanation": "Cons", "recommended_action": "Act"}
        }
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(mock_hallucinated_json)}]
                }
            }
        ]
    }

    with patch("httpx.Client.post", return_value=mock_response):
        res = evaluate_answer(
            transcript="I worked on a small database migration project.",
            question_text="Tell me about a project.",
            category="Technical"
        )

        # Grounding check must fail and fall back to rubric
        assert res["engine_used"] == "rubric"

