from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.models import models
from backend.services.weakness_diagnosis_engine import diagnose_session_weaknesses
from backend.services.recurring_weakness_service import aggregate_user_weaknesses, SEVERITY_SCORE
from backend.services.velocity_service import calculate_improvement_velocity

VALID_PRACTICE_TYPES = {
    "STRUCTURED_ANSWER",
    "TECHNICAL_DEPTH",
    "PROJECT_DEFENSE",
    "FOLLOWUP_DEFENSE",
    "COMMUNICATION",
    "PRESSURE_RESPONSE",
    "RESUME_CLAIM_DEFENSE",
    "BEHAVIORAL_STAR",
    "TRADEOFF_REASONING"
}

WEAKNESS_TO_PRACTICE_MAP = {
    "comm_excessive_fillers": {
        "practice_type": "COMMUNICATION",
        "objective": "Eliminate verbal placeholders by practicing structural pauses before speaking.",
        "target_count": 5,
        "difficulty": "medium",
        "expected_skill": "Communication & Cadence Pacing"
    },
    "comm_long_pauses": {
        "practice_type": "STRUCTURED_ANSWER",
        "objective": "Structure answers using a 3-part framework (Context, Implementation, Result) to avoid mid-response hesitation.",
        "target_count": 5,
        "difficulty": "medium",
        "expected_skill": "Structured Delivery"
    },
    "tech_shallow_depth": {
        "practice_type": "TECHNICAL_DEPTH",
        "objective": "Deepen technical answers by citing architecture constraints, failure handling, and bottleneck metrics.",
        "target_count": 5,
        "difficulty": "hard",
        "expected_skill": "System Architecture & Deep Dive"
    },
    "tech_followup_defense": {
        "practice_type": "FOLLOWUP_DEFENSE",
        "objective": "Defend implementation decisions during multi-turn probe questions on trade-offs and edge cases.",
        "target_count": 5,
        "difficulty": "hard",
        "expected_skill": "Trade-off & Incident Defense"
    },
    "resume_unsupported_claims": {
        "practice_type": "RESUME_CLAIM_DEFENSE",
        "objective": "Defend resume claims with first-person ownership ('I built', 'I tuned') and specific throughput numbers.",
        "target_count": 4,
        "difficulty": "medium",
        "expected_skill": "Resume Verification Defense"
    },
    "pressure_time_deterioration": {
        "practice_type": "PRESSURE_RESPONSE",
        "objective": "Synthesize concise technical answers under strict 45-second response limits.",
        "target_count": 5,
        "difficulty": "hard",
        "expected_skill": "Rapid Technical Synthesis"
    },
    "delivery_unstable_alignment": {
        "practice_type": "COMMUNICATION",
        "objective": "Maintain visual centering and webcam alignment at eye level while speaking.",
        "target_count": 3,
        "difficulty": "easy",
        "expected_skill": "Delivery & Visual Stability"
    }
}


def select_next_practice(
    user_id: int,
    db: Session,
    source_session_id: Optional[int] = None,
    save_to_db: bool = True
) -> List[Dict[str, Any]]:
    """
    Next-Best-Practice Selection Algorithm.
    Deterministic function ranking candidate weaknesses and generating 1 primary
    and optional 1 secondary targeted practice recommendation.

    Decision Rules:
    1. High-impact recurring weakness (highest severity or frequency across sessions).
    2. Weaknesses worsening over time.
    3. Weakness directly related to target role.
    4. Avoid repeating recently completed practice if candidate is already improving.
    5. Fully deterministic tie-breaking.
    6. Logs full decision rationale with evidence contract.
    """
    user = db.query(models.User).filter_by(id=user_id).first()
    if not user:
        return []

    # 1. Gather all longitudinal user weaknesses
    agg_weaknesses = aggregate_user_weaknesses(user_id=user_id, db=db)

    # 2. Gather latest session weaknesses if source session provided or available
    target_session = None
    if source_session_id:
        target_session = db.query(models.InterviewSession).filter_by(id=source_session_id, user_id=user_id).first()
    if not target_session:
        target_session = (
            db.query(models.InterviewSession)
            .filter_by(user_id=user_id, status="completed")
            .order_by(models.InterviewSession.created_at.desc(), models.InterviewSession.id.desc())
            .first()
        )

    latest_session_weaknesses = []
    if target_session:
        latest_session_weaknesses = diagnose_session_weaknesses(target_session.id, db)

    # 3. Previous recommendations and completed practice
    past_recs = (
        db.query(models.PracticeRecommendation)
        .filter_by(user_id=user_id)
        .order_by(models.PracticeRecommendation.created_at.desc())
        .limit(10)
        .all()
    )
    recently_practiced_types = {r.practice_type for r in past_recs if r.status in ("completed", "in_progress")}

    # Combine weakness candidates
    candidate_map: Dict[str, Dict[str, Any]] = {}
    for w in agg_weaknesses:
        candidate_map[w["weakness_id"]] = {
            "source": "longitudinal",
            "data": w,
            "recurring": w["recurring"],
            "severity": w["latest_severity"],
            "trend": w["trend"]
        }

    for w in latest_session_weaknesses:
        w_id = w["id"]
        if w_id not in candidate_map:
            candidate_map[w_id] = {
                "source": "session",
                "data": w,
                "recurring": False,
                "severity": w["severity"],
                "trend": "new"
            }

    if not candidate_map:
        # Default fallback practice if candidate showed no detectable weaknesses
        fallback_target_role = target_session.target_role if target_session else "Software Engineer"
        fallback_practice = {
            "weakness": "Maintenance of balanced technical depth and communication pacing.",
            "weakness_type": "tech_shallow_depth",
            "dimension": "technical",
            "priority": 1,
            "practice_objective": "Advance into higher-difficulty architectural trade-off scenarios.",
            "practice_type": "TRADEOFF_REASONING",
            "target_count": 5,
            "expected_skill": "Advanced Trade-off Reasoning",
            "difficulty": "hard",
            "rationale": f"Candidate demonstrated baseline readiness for '{fallback_target_role}' with no active weakness indicators. Advanced trade-off drills recommended for mastery.",
            "decision_metadata": {
                "rule": "no_active_weakness_fallback",
                "source": "baseline_mastery"
            }
        }
        if save_to_db and target_session:
            rec_db = models.PracticeRecommendation(
                user_id=user_id,
                source_session_id=target_session.id,
                weakness_type=fallback_practice["weakness_type"],
                dimension=fallback_practice["dimension"],
                priority=1,
                rationale=fallback_practice["rationale"],
                practice_type=fallback_practice["practice_type"],
                target_count=fallback_practice["target_count"],
                difficulty=fallback_practice["difficulty"],
                status="pending",
                decision_metadata=fallback_practice["decision_metadata"]
            )
            db.add(rec_db)
            db.commit()
            fallback_practice["id"] = rec_db.id
        return [fallback_practice]

    # Score each candidate deterministically
    scored_candidates = []
    for w_id, item in candidate_map.items():
        base_priority_score = 0
        w_info = item["data"]
        sev_label = item["severity"]
        sev_num = SEVERITY_SCORE.get(sev_label, 2)

        # Rule 1: Severity weight
        base_priority_score += sev_num * 25  # 25, 50, 75, 100

        # Rule 2: Recurring weakness bonus
        if item["recurring"]:
            base_priority_score += 40
            base_priority_score += min(20, w_info.get("occurrence_count", 0) * 5)

        # Rule 3: Worsening trend bonus
        if item["trend"] == "worsening" or item["trend"] == "not_sustained":
            base_priority_score += 30
        elif item["trend"] == "improving":
            # Demote if already improving and recently practiced
            practice_cfg = WEAKNESS_TO_PRACTICE_MAP.get(w_id, {})
            if practice_cfg.get("practice_type") in recently_practiced_types:
                base_priority_score -= 25

        # Rule 4: Dimension weight (Technical & Communication prioritized)
        dim = w_info.get("dimension", "technical")
        if dim == "technical":
            base_priority_score += 20
        elif dim == "communication":
            base_priority_score += 15
        elif dim == "resume":
            base_priority_score += 10

        scored_candidates.append({
            "weakness_id": w_id,
            "priority_score": base_priority_score,
            "data": w_info,
            "dimension": dim,
            "severity": sev_label,
            "trend": item["trend"],
            "recurring": item["recurring"]
        })

    # Sort deterministically: highest priority score -> highest severity -> weakness_id alphabetical
    scored_candidates.sort(
        key=lambda x: (
            -x["priority_score"],
            -SEVERITY_SCORE.get(x["severity"], 0),
            x["weakness_id"]
        )
    )

    recommendations: List[Dict[str, Any]] = []
    top_candidates = scored_candidates[:2]  # primary and optional secondary

    for rank_idx, cand in enumerate(top_candidates):
        w_id = cand["weakness_id"]
        priority_num = rank_idx + 1
        cfg = WEAKNESS_TO_PRACTICE_MAP.get(w_id, {
            "practice_type": "TECHNICAL_DEPTH",
            "objective": "Targeted drill to improve depth and structure.",
            "target_count": 5,
            "difficulty": "medium",
            "expected_skill": "Technical Reasoning"
        })

        cand_data = cand["data"]
        root_weakness = cand_data.get("root_weakness") or cand_data.get("symptom", "Identified performance gap")
        evidence_list = cand_data.get("evidence", [])
        if isinstance(evidence_list, list):
            evidence_str = "; ".join(str(e) for e in evidence_list[:2])
        else:
            evidence_str = str(evidence_list)

        rec_dict = {
            "weakness": root_weakness,
            "weakness_type": w_id,
            "dimension": cand["dimension"],
            "priority": priority_num,
            "practice_objective": cfg["objective"],
            "practice_type": cfg["practice_type"],
            "target_count": cfg["target_count"],
            "expected_skill": cfg["expected_skill"],
            "difficulty": cfg["difficulty"],
            "rationale": f"{'Primary' if priority_num == 1 else 'Secondary'} focus: {root_weakness}. Observable evidence: {evidence_str or cand_data.get('symptom', 'Recorded gap')}.",
            "evidence": evidence_list,
            "decision_metadata": {
                "rank": priority_num,
                "priority_score": cand["priority_score"],
                "recurring": cand["recurring"],
                "severity": cand["severity"],
                "trend": cand["trend"],
                "source_session_id": target_session.id if target_session else None
            }
        }

        if save_to_db:
            rec_db = models.PracticeRecommendation(
                user_id=user_id,
                source_session_id=target_session.id if target_session else None,
                weakness_type=w_id,
                dimension=cand["dimension"],
                priority=priority_num,
                rationale=rec_dict["rationale"],
                practice_type=cfg["practice_type"],
                target_count=cfg["target_count"],
                difficulty=cfg["difficulty"],
                status="pending",
                decision_metadata=rec_dict["decision_metadata"]
            )
            db.add(rec_db)
            db.commit()
            rec_dict["id"] = rec_db.id

        recommendations.append(rec_dict)

    return recommendations
