import pytest
from unittest.mock import patch
import httpx
from backend.services.probe_rephraser import (
    rephrase_probe_question,
    verify_probe_grounding,
    clear_probe_cache,
)


@pytest.fixture(autouse=True)
def clean_cache():
    clear_probe_cache()
    yield
    clear_probe_cache()


def test_no_provider_fallback(monkeypatch):
    """When no API keys are present, returns the exact deterministic fallback template instantly."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    claim = "Architected a Kafka streaming pipeline handling 10k messages per second"
    template = "At scale, how did you maintain your Kafka streaming pipeline?"
    result = rephrase_probe_question(claim, "T1_FOUNDATION", template)

    assert result == template


def test_mocked_gemini_success(monkeypatch):
    """When Gemini returns a valid, grounded rephrasing, it is returned."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    claim = "Built a distributed cache with Redis cluster"
    template = "Walk me through how you deployed the Redis cluster."
    mock_rephrased = "Could you walk me through how your team configured the Redis cluster for high availability?"

    with patch("backend.services.probe_rephraser._call_gemini_rephrase", return_value=mock_rephrased) as mock_call:
        result = rephrase_probe_question(claim, "T1_FOUNDATION", template)
        assert result == mock_rephrased
        assert mock_call.call_count == 1


def test_probe_cache_hit(monkeypatch):
    """Repeated calls with identical parameters hit the cache without calling the LLM provider again."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    claim = "Optimized PostgreSQL indexes"
    template = "How did you benchmark PostgreSQL?"
    mock_q = "How did you verify query latency after tuning PostgreSQL indexes?"

    with patch("backend.services.probe_rephraser._call_gemini_rephrase", return_value=mock_q) as mock_call:
        res1 = rephrase_probe_question(claim, "T2_TRADE_OFFS", template)
        res2 = rephrase_probe_question(claim, "T2_TRADE_OFFS", template)

        assert res1 == mock_q
        assert res2 == mock_q
        assert mock_call.call_count == 1  # Only called once due to cache


def test_timeout_fallback(monkeypatch):
    """When the LLM call times out, it fails fast to the deterministic template without crashing."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    claim = "Managed Kubernetes multi-tenant clusters"
    template = "Describe your Kubernetes incident response."

    with patch("backend.services.probe_rephraser._call_gemini_rephrase", side_effect=httpx.TimeoutException("Read timed out")):
        result = rephrase_probe_question(claim, "T3_INCIDENT", template)
        assert result == template


def test_banned_words_rejection(monkeypatch):
    """Rephrasings containing hostile, derogatory, or banned words are rejected."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    claim = "Tuned DynamoDB partition keys"
    template = "What tradeoffs did you make with DynamoDB?"
    hostile_response = "Are you trying to bluff about your DynamoDB partition keys, or is this fake?"

    with patch("backend.services.probe_rephraser._call_gemini_rephrase", return_value=hostile_response):
        result = rephrase_probe_question(claim, "T2_TRADE_OFFS", template)
        # Banned words detected ("bluff", "fake"); must fall back to template
        assert result == template


def test_grounding_failure_rejection(monkeypatch):
    """Rephrasings that hallucinate unrelated topics and fail claim grounding are rejected."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    claim = "Engineered a GraphQL federated gateway"
    template = "Explain the architecture of your GraphQL gateway."
    # Hallucinated response that has nothing to do with GraphQL or gateway
    hallucinated_response = "What CSS framework do you prefer when building responsive layouts in React?"

    with patch("backend.services.probe_rephraser._call_gemini_rephrase", return_value=hallucinated_response):
        result = rephrase_probe_question(claim, "T1_FOUNDATION", template)
        assert result == template


def test_auto_append_question_mark(monkeypatch):
    """Rephrasing without a trailing question mark has one appended."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    claim = "Built a microservices auth proxy"
    template = "How does the auth proxy handle tokens?"
    clean_no_mark = "Tell me how your auth proxy handles token invalidation"

    with patch("backend.services.probe_rephraser._call_openai_rephrase", return_value=clean_no_mark):
        result = rephrase_probe_question(claim, "T1_FOUNDATION", template)
        assert result == clean_no_mark + "?"
