import json
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import get_db
import backend.models as models
from backend.services.auth_service import hash_password, create_access_token


def test_intelligence_layer_export_and_cascading_deletion(db_session: Session):
    """
    Validates that:
    1. /auth/export includes all 8 Phase 3 intelligence tables.
    2. User B cannot access User A's intelligence data (cross-user isolation).
    3. Permanent account deletion cascades and deletes all records across all 8 tables.
    """
    # 1. Create User A
    user_a = models.User(
        email="intel_user_a@example.com",
        password_hash=hash_password("passwordA1234"),
        full_name="User A Intelligence"
    )
    db_session.add(user_a)
    db_session.flush()

    # 2. Add Resume + 4 Resume Intelligence tables
    resume_a = models.Resume(
        user_id=user_a.id,
        filename="resume_a.txt",
        raw_text="Backend Engineer experienced in Kubernetes, Go, PostgreSQL",
        skills=json.dumps(["Kubernetes", "Go", "PostgreSQL"]),
        role_fit_scores={"backend_engineer": 88.0, "devops_engineer": 75.0},
        risk_areas=[{"area": "Scale", "reason": "No high-throughput metrics", "probe_priority": 0.8}]
    )
    db_session.add(resume_a)
    db_session.flush()

    # Table 1: resume_skills
    r_skill = models.ResumeSkill(
        resume_id=resume_a.id,
        name="Kubernetes",
        category="DevOps",
        confidence=0.95,
        evidenced=True
    )
    # Table 2: resume_projects
    r_proj = models.ResumeProject(
        resume_id=resume_a.id,
        title="Microservices Orchestrator",
        description="Managed deployments",
        technologies=["Kubernetes", "Go"],
        bullets=["Automated cluster scaling"]
    )
    db_session.add_all([r_skill, r_proj])
    db_session.flush()

    # Table 3: resume_claims
    r_claim = models.ResumeClaim(
        resume_id=resume_a.id,
        project_id=r_proj.id,
        claim_text="Automated scaling for 50 production clusters",
        claim_type="scale",
        technologies=["Kubernetes"],
        has_metric=True,
        probe_priority=0.85,
        reasons=["High operational impact claim"]
    )
    db_session.add(r_claim)
    db_session.flush()

    # Table 4: resume_flags
    r_flag = models.ResumeFlag(
        resume_id=resume_a.id,
        claim_id=r_claim.id,
        flag_type="buzzword_without_context",
        description="Mentions scaling without stating specific node limits",
        severity="info"
    )
    db_session.add(r_flag)

    # 3. Add Interview Session + 3 Session Intelligence tables
    session_a = models.InterviewSession(
        user_id=user_a.id,
        resume_id=resume_a.id,
        mode="technical",
        difficulty="hard",
        target_role="Backend Engineer",
        total_questions=3,
        current_question_index=1
    )
    db_session.add(session_a)
    db_session.flush()

    # Table 5: interview_questions
    iq = models.InterviewQuestion(
        session_id=session_a.id,
        sequence_order=1,
        question_text="How did you automate cluster scaling in Go?",
        question_type="probe",
        source="resume_claim",
        claim_id=r_claim.id,
        ladder_stage="T1_FOUNDATION",
        difficulty="hard",
        generated_reason="High priority scale claim probe"
    )
    # Table 6: interview_decisions
    idec = models.InterviewDecision(
        session_id=session_a.id,
        turn=1,
        decision="PROBE_CLAIM",
        reason="Claim probe ladder initiated",
        inputs={"claim_id": r_claim.id}
    )
    # Table 7: claim_consistency
    ccons = models.ClaimConsistency(
        session_id=session_a.id,
        claim_id=r_claim.id,
        label="consistent",
        evidence=["Candidate explained the controller loop in Go."],
        answers_considered=1
    )
    db_session.add_all([iq, idec, ccons])
    db_session.flush()

    # 4. Add Answer + Table 8: answer_visual_metrics
    ans = models.InterviewAnswer(
        session_id=session_a.id,
        question_id=iq.id,
        question_text=iq.question_text,
        transcript="I wrote custom controller loops using client-go.",
        duration_seconds=30.0,
        response_time=30.0,
        wpm=120.0
    )
    db_session.add(ans)
    db_session.flush()

    # Table 8: answer_visual_metrics
    avm = models.AnswerVisualMetrics(
        answer_id=ans.id,
        head_alignment_percent=85.0,
        blink_rate=16.5,
        head_movement_variance=0.0015,
        face_visibility_ratio=0.92,
        head_shift_count=2,
        frames_sampled=150
    )
    # Also add AnswerEvaluation
    aeval = models.AnswerEvaluation(
        answer_id=ans.id,
        overall_score=85.0,
        verification_risk_score=15.0,
        verification_risk_level="low",
        verification_risk_evidence=["Candidate provided specific controller loop details"],
        verification_risk_explanation="Grounded with specific technical details."
    )
    db_session.add_all([avm, aeval])
    db_session.commit()

    # Pre-condition check: verify rows exist in all 8 tables
    assert db_session.query(models.ResumeSkill).filter_by(resume_id=resume_a.id).count() == 1
    assert db_session.query(models.ResumeProject).filter_by(resume_id=resume_a.id).count() == 1
    assert db_session.query(models.ResumeClaim).filter_by(resume_id=resume_a.id).count() == 1
    assert db_session.query(models.ResumeFlag).filter_by(resume_id=resume_a.id).count() == 1
    assert db_session.query(models.InterviewQuestion).filter_by(session_id=session_a.id).count() == 1
    assert db_session.query(models.InterviewDecision).filter_by(session_id=session_a.id).count() == 1
    assert db_session.query(models.ClaimConsistency).filter_by(session_id=session_a.id).count() == 1
    assert db_session.query(models.AnswerVisualMetrics).filter_by(answer_id=ans.id).count() == 1

    # Create client authenticated as User A
    token_a = create_access_token(user_a.id)

    def override_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client_a:
        client_a.headers["Authorization"] = f"Bearer {token_a}"

        # 1. Verify GET /auth/export includes all 8 intelligence tables
        export_resp = client_a.get("/auth/export")
        assert export_resp.status_code == 200
        export_data = export_resp.json()

        # Check resume intelligence tables exported
        exported_resumes = export_data["resumes"]
        assert len(exported_resumes) == 1
        r_exp = exported_resumes[0]
        assert len(r_exp["skills_list"]) == 1
        assert r_exp["skills_list"][0]["name"] == "Kubernetes"
        assert len(r_exp["projects"]) == 1
        assert r_exp["projects"][0]["title"] == "Microservices Orchestrator"
        assert len(r_exp["claims"]) == 1
        assert r_exp["claims"][0]["claim_text"] == "Automated scaling for 50 production clusters"
        assert len(r_exp["flags"]) == 1
        assert r_exp["flags"][0]["flag_type"] == "buzzword_without_context"

        # Check session intelligence tables exported
        exported_sessions = export_data["interview_sessions"]
        assert len(exported_sessions) == 1
        s_exp = exported_sessions[0]
        assert len(s_exp["questions"]) == 1
        assert s_exp["questions"][0]["question_type"] == "probe"
        assert len(s_exp["decisions"]) == 1
        assert s_exp["decisions"][0]["decision"] == "PROBE_CLAIM"
        assert len(s_exp["claim_consistency"]) == 1
        assert s_exp["claim_consistency"][0]["label"] == "consistent"

        # Check visual metrics and verification risk in answers
        ans_exp = s_exp["answers"][0]
        assert ans_exp["visual_metrics"]["head_alignment_percent"] == 85.0
        assert ans_exp["visual_metrics"]["frames_sampled"] == 150
        assert ans_exp["evaluation"]["verification_risk_level"] == "low"

        # 2. Cross-user isolation: User B cannot access User A's intelligence data
        user_b = models.User(
            email="intel_user_b@example.com",
            password_hash=hash_password("passwordB1234"),
            full_name="User B"
        )
        db_session.add(user_b)
        db_session.commit()
        token_b = create_access_token(user_b.id)

        with TestClient(app) as client_b:
            client_b.headers["Authorization"] = f"Bearer {token_b}"
            # User B accessing User A's session -> 404
            assert client_b.get(f"/interview/{session_a.id}").status_code == 404
            # User B accessing User A's resume -> 404
            assert client_b.get(f"/resume/{resume_a.id}").status_code == 404
            # User B accessing User A's report -> 404
            assert client_b.get(f"/analytics/report/{session_a.id}").status_code == 404

        # 3. Cascading account deletion: Delete User A
        del_resp = client_a.request(
            "DELETE",
            "/auth/account",
            json={"password": "passwordA1234"}
        )
        assert del_resp.status_code == 200
        assert "permanently deleted" in del_resp.json()["message"]

        # 4. Assert row counts drop to 0 across all 8 Phase 3 intelligence tables
        assert db_session.query(models.User).filter_by(id=user_a.id).count() == 0
        assert db_session.query(models.Resume).filter_by(user_id=user_a.id).count() == 0
        assert db_session.query(models.InterviewSession).filter_by(user_id=user_a.id).count() == 0

        # All 8 tables must have 0 rows for User A's resources
        assert db_session.query(models.ResumeSkill).filter_by(resume_id=resume_a.id).count() == 0
        assert db_session.query(models.ResumeProject).filter_by(resume_id=resume_a.id).count() == 0
        assert db_session.query(models.ResumeClaim).filter_by(resume_id=resume_a.id).count() == 0
        assert db_session.query(models.ResumeFlag).filter_by(resume_id=resume_a.id).count() == 0
        assert db_session.query(models.InterviewQuestion).filter_by(session_id=session_a.id).count() == 0
        assert db_session.query(models.InterviewDecision).filter_by(session_id=session_a.id).count() == 0
        assert db_session.query(models.ClaimConsistency).filter_by(session_id=session_a.id).count() == 0
        assert db_session.query(models.AnswerVisualMetrics).filter_by(answer_id=ans.id).count() == 0

    app.dependency_overrides.clear()
