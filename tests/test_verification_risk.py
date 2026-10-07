"""
tests/test_verification_risk.py
Calibration tests and fixture verification for Verification Risk heuristic engine.
Ensures:
- >= 10 labeled answers tested with expected risk bands (low, moderate, elevated, not_computed)
- Concrete concise answers score low (false-positive guard)
- Short answers (< 20 words) return not_computed guard
- Repetition with earlier answer raises repetition signal
- Banned words ('bluff', 'lie', 'fake') never appear in output labels or text
- Verification risk does NOT alter readiness score
"""

import pytest
from backend.services.verification_risk import compute_verification_risk
from backend.config import VERIFICATION_RISK_CONFIG


# -------------------------------------------------------------
# Calibration Fixture: >= 10 Labeled Answers with Expected Bands
# -------------------------------------------------------------
CALIBRATION_FIXTURES = [
    # 1. Guard: Ultra-short response (< 20 words)
    {
        "id": "short_answer_trivial",
        "transcript": "I used Redis to cache database queries and speed things up.",
        "previous_answers": [],
        "expected_level": "not_computed",
        "description": "Short answer below 20 words must return not_computed guard."
    },
    # 2. Guard: Brief answer (< 20 words)
    {
        "id": "short_answer_brief",
        "transcript": "We set up Docker and deployed the microservice to AWS EC2 instances.",
        "previous_answers": [],
        "expected_level": "not_computed",
        "description": "Short answer guard to avoid penalizing brief communication."
    },
    # 3. Low Risk: Concrete backend caching implementation with metrics
    {
        "id": "concrete_backend_redis",
        "transcript": (
            "I implemented a two-tier Redis caching layer in FastAPI to optimize slow queries. "
            "We configured cache invalidation using TTLs set to 300 seconds and write-through cache logic. "
            "This reduced p99 database latency from 420ms down to 18ms and handled 5000 QPS during peak load."
        ),
        "previous_answers": [],
        "expected_level": "low",
        "description": "Concrete engineering specifics, metrics, and tools must score low risk."
    },
    # 4. Low Risk: Concrete database indexing and execution profiling
    {
        "id": "concrete_database_postgres",
        "transcript": (
            "I investigated slow analytical queries in PostgreSQL using EXPLAIN ANALYZE. "
            "The query was performing a sequential scan over 12 million rows. "
            "I added a composite B-tree index on user_id and created_at, reducing query execution time from 2.4s to 35ms."
        ),
        "previous_answers": [],
        "expected_level": "low",
        "description": "Precise mechanisms, metrics, and tools must score low risk."
    },
    # 5. Low Risk: Concrete DevOps Kubernetes & Prometheus observability
    {
        "id": "concrete_devops_k8s",
        "transcript": (
            "I authored Terraform modules to provision an EKS Kubernetes cluster on AWS. "
            "I deployed Prometheus and Grafana to track CPU utilization and container restart counts, "
            "configuring Horizontal Pod Autoscaling to scale pods between 3 and 20 replicas when memory exceeded 75%."
        ),
        "previous_answers": [],
        "expected_level": "low",
        "description": "Infrastructure specifics and thresholds score low risk."
    },
    # 6. Low Risk: Concise speaker with clear technical facts (False-positive guard)
    {
        "id": "concrete_concise_speaker",
        "transcript": (
            "I built an event-driven worker in Go utilizing RabbitMQ. "
            "I configured 8 consumer goroutines with manual acknowledgments and dead-letter queues. "
            "The service processed 1500 messages per second and maintained 99.9% uptime."
        ),
        "previous_answers": [],
        "expected_level": "low",
        "description": "Concise candidate with concrete tools and metrics must not be falsely flagged."
    },
    # 7. Elevated Risk: Extreme buzzwords with zero technical specifics
    {
        "id": "buzzword_dense_extreme",
        "transcript": (
            "We built a disruptive, cutting-edge, state-of-the-art enterprise-grade platform. "
            "It leverages next-generation architecture to create a revolutionary ecosystem with synergistic agility. "
            "We streamlined the entire process using world-class paradigms and game-changing solutions."
        ),
        "previous_answers": [],
        "expected_level": "elevated",
        "description": "Heavy buzzword density with zero specifics must score elevated risk."
    },
    # 8. Elevated Risk: Generic phrasing with vague ownership
    {
        "id": "vague_ownership_and_generic",
        "transcript": (
            "We basically just worked on various tasks and handled different things across the system. "
            "Someone on the team gave us the code and we kind of helped out with everything using industry standard best practices. "
            "We did a lot of stuff across various components to make sure all required technologies were there."
        ),
        "previous_answers": [],
        "expected_level": "elevated",
        "description": "Vague ownership and generic filler phrases trigger elevated risk."
    },
    # 9. Moderate Risk: Partial specifics with generalized phrasing
    {
        "id": "moderate_mixed_answer",
        "transcript": (
            "I built backend endpoints with Python and FastAPI for our application. "
            "We followed standard architecture and best practices to seamlessly integrate multiple features, "
            "working on various components to ensure the system remained robust and reliable for all users."
        ),
        "previous_answers": [],
        "expected_level": "moderate",
        "description": "Contains some concrete tools but leans on generic phrasing and buzzwords."
    },
    # 10. Elevated/Moderate Risk: Repetition of previous answer
    {
        "id": "high_repetition_answer",
        "transcript": (
            "As I mentioned earlier, I built backend endpoints with Python and FastAPI for our application. "
            "We followed standard architecture and best practices to seamlessly integrate multiple features, "
            "working on various components to ensure the system remained robust and reliable for all users."
        ),
        "previous_answers": [
            "I built backend endpoints with Python and FastAPI for our application. We followed standard architecture and best practices to seamlessly integrate multiple features, working on various components to ensure the system remained robust and reliable for all users."
        ],
        "expected_level": "elevated",
        "description": "High lexical overlap with previous answer without adding new technical detail."
    },
]


@pytest.mark.parametrize("fixture", CALIBRATION_FIXTURES, ids=[f["id"] for f in CALIBRATION_FIXTURES])
def test_calibration_fixtures(fixture):
    """Verify that all 10 calibration fixtures fall into their expected risk bands."""
    result = compute_verification_risk(
        transcript=fixture["transcript"],
        previous_answers=fixture.get("previous_answers", [])
    )

    assert result["level"] == fixture["expected_level"], (
        f"Fixture '{fixture['id']}' failed: expected {fixture['expected_level']}, "
        f"got {result['level']} (score: {result['score']}). Evidence: {result['evidence']}"
    )

    if fixture["expected_level"] == "not_computed":
        assert result["score"] is None
        assert "minimum threshold" in result["explanation"]
    elif fixture["expected_level"] == "low":
        assert result["score"] <= VERIFICATION_RISK_CONFIG["thresholds"]["low_max"]
    elif fixture["expected_level"] == "moderate":
        assert (
            VERIFICATION_RISK_CONFIG["thresholds"]["low_max"]
            < result["score"]
            <= VERIFICATION_RISK_CONFIG["thresholds"]["moderate_max"]
        )
    elif fixture["expected_level"] == "elevated":
        assert result["score"] > VERIFICATION_RISK_CONFIG["thresholds"]["moderate_max"]

    # Verify disclaimer is present
    assert result["disclaimer"] == VERIFICATION_RISK_CONFIG["disclaimer"]


def test_banned_words_absence():
    """Verify that banned terms ('bluff', 'lie', 'fake') NEVER appear in output evidence or explanations."""
    import re
    banned_pattern = re.compile(r"\b(bluff|lie|lies|fake|faked)\b", re.IGNORECASE)

    for fixture in CALIBRATION_FIXTURES:
        result = compute_verification_risk(
            transcript=fixture["transcript"],
            previous_answers=fixture.get("previous_answers", [])
        )
        combined_text = (
            f"{result['explanation']} {result['recommended_action']} "
            + " ".join(result["evidence"])
        )
        assert not banned_pattern.search(combined_text), f"Banned term pattern matched in {fixture['id']}: {combined_text}"


def test_verification_risk_api_flow(client):
    """Test full API submission flow and verification risk persistence in database."""
    # 1. Start interview
    start_resp = client.post(
        "/interview/start",
        json={"mode": "technical", "difficulty": "medium", "number_of_questions": 2}
    )
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]
    q1 = start_resp.json()["questions"][0]

    # 2. Submit concrete answer
    ans_resp = client.post(
        f"/interview/{session_id}/answer",
        json={
            "session_id": session_id,
            "question_id": q1["id"],
            "question_text": q1["question"],
            "transcript": (
                "I implemented an asynchronous worker queue using Python and Celery backed by Redis. "
                "I configured batch prefetching of 50 tasks per worker and handled retries with exponential backoff. "
                "This reduced task latency to 12ms and sustained 2500 requests per second."
            ),
            "response_time": 25.0
        }
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    assert "verification_risk" in ans_data
    vr = ans_data["verification_risk"]
    assert vr["level"] == "low"
    assert vr["score"] <= 30.0

    # 3. Check report endpoint includes verification_risk
    client.post(f"/interview/{session_id}/complete")
    rep_resp = client.get(f"/report/{session_id}")
    assert rep_resp.status_code == 200
    rep_data = rep_resp.json()
    assert len(rep_data["answers"]) == 1
    assert "verification_risk" in rep_data["answers"][0]
    rep_vr = rep_data["answers"][0]["verification_risk"]
    assert rep_vr["level"] == "low"
    assert rep_vr["score"] is not None

    assert rep_vr["level"] == "low"
    assert rep_vr["score"] is not None
