from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.models import models
from backend.config import WEAKNESS_CONFIG


DEFAULT_WEAKNESS_CONFIG = {
    "filler_word_threshold_per_answer": 5,
    "filler_total_session_threshold": 8,
    "long_pause_threshold_seconds": 3.5,
    "min_pause_answers": 2,
    "speaking_speed_high_wpm": 165.0,
    "speaking_speed_low_wpm": 95.0,
    "shallow_technical_score_threshold": 60.0,
    "technical_drop_threshold": 15.0,
    "min_visual_frames": 30,
    "low_face_visibility_ratio": 0.60,
    "unstable_head_alignment_threshold": 55.0,
    "frequent_head_shifts_threshold": 8,
}


def get_performance_dimension_model(session_id: int, db: Session) -> Dict[str, Any]:
    """
    Formalizes the four primary performance dimensions:
    A. COMMUNICATION
    B. TECHNICAL DEPTH
    C. DELIVERY & VISUAL STABILITY
    D. RESUME CONSISTENCY

    Each dimension returns:
    - score: float or None
    - state: 'measured' or 'not_measured'
    - evidence: list of observable metrics and statements
    - explanation: objective interpretation
    - recommended_action: targeted practice recommendation
    """
    session = db.query(models.InterviewSession).filter_by(id=session_id).first()
    if not session:
        return {}

    score_rec = db.query(models.SessionScore).filter_by(session_id=session_id).first()
    answers = (
        db.query(models.InterviewAnswer)
        .filter_by(session_id=session_id)
        .order_by(models.InterviewAnswer.id.asc())
        .all()
    )

    # 1. Communication Dimension
    comm_score = score_rec.communication_score if score_rec else 70.0
    voice_metrics_list = (
        db.query(models.VoiceMetrics)
        .join(models.InterviewAnswer)
        .filter(models.InterviewAnswer.session_id == session_id)
        .all()
    )
    spoken_vms = [vm for vm in voice_metrics_list if vm.speech_source == "speech"]

    comm_evidence = []
    total_fillers = sum(vm.filler_word_count or 0 for vm in spoken_vms)
    wpms = [vm.words_per_minute for vm in spoken_vms if vm.words_per_minute is not None]
    avg_wpm = round(sum(wpms) / len(wpms), 1) if wpms else None
    long_pauses = [vm.longest_pause for vm in spoken_vms if vm.longest_pause is not None and vm.longest_pause >= 3.0]

    if spoken_vms:
        comm_evidence.append(f"{total_fillers} total verbal filler words across {len(spoken_vms)} spoken answers.")
        if avg_wpm:
            comm_evidence.append(f"Average cadence: {avg_wpm} WPM (standard conversational band: 120-160 WPM).")
        if long_pauses:
            comm_evidence.append(f"{len(long_pauses)} extended pauses measured (\u2265 3.0s).")
    else:
        comm_evidence.append("Answers submitted via text; audio cadence signals not recorded.")

    comm_action = "Practice 5 answers with deliberate 2-second structural pauses to eliminate fillers."
    if total_fillers >= 8:
        comm_action = "Practice 5 concise answers under 45s focusing on eliminating filler phrases."
    elif avg_wpm and avg_wpm > 165:
        comm_action = "Practice conversational cadence pacing around 130-150 WPM."

    communication_dimension = {
        "score": comm_score,
        "state": "measured",
        "evidence": comm_evidence,
        "explanation": f"Communication score of {comm_score}/100 based on structure, clarity, and pacing.",
        "recommended_action": comm_action,
    }

    # 2. Technical Depth Dimension
    tech_score = score_rec.technical_score if score_rec else 70.0
    evals = (
        db.query(models.AnswerEvaluation)
        .join(models.InterviewAnswer)
        .filter(models.InterviewAnswer.session_id == session_id)
        .all()
    )
    tech_scores = [ev.technical_score for ev in evals if ev.technical_score is not None]
    shallow_count = sum(1 for s in tech_scores if s < 60.0)

    tech_evidence = []
    if tech_scores:
        avg_tech = round(sum(tech_scores) / len(tech_scores), 1)
        tech_evidence.append(f"Average technical reasoning: {avg_tech}/100 across {len(tech_scores)} evaluated answers.")
        if shallow_count > 0:
            tech_evidence.append(f"{shallow_count} answers showed limited depth or missing technical trade-offs.")
    else:
        tech_evidence.append("No technical evaluations recorded.")

    technical_dimension = {
        "score": tech_score,
        "state": "measured",
        "evidence": tech_evidence,
        "explanation": f"Technical depth scored {tech_score}/100 reflecting architectural justification and concrete specifics.",
        "recommended_action": "Complete targeted technical depth drill focused on trade-offs and bottleneck analysis.",
    }

    # 3. Delivery & Visual Stability Dimension
    beh_score = score_rec.behavioral_score if score_rec else None
    delivery_measured = beh_score is not None
    deliv_evidence = []

    visual_metrics = (
        db.query(models.AnswerVisualMetrics)
        .join(models.InterviewAnswer)
        .filter(models.InterviewAnswer.session_id == session_id)
        .all()
    )
    valid_vis = [v for v in visual_metrics if v.frames_sampled and v.frames_sampled >= 30 and v.face_visibility_ratio is not None]

    if delivery_measured and valid_vis:
        avg_vis_ratio = round(sum(v.face_visibility_ratio for v in valid_vis) / len(valid_vis) * 100, 1)
        avg_align = round(sum(v.head_alignment_percent or 75.0 for v in valid_vis) / len(valid_vis), 1)
        deliv_evidence.append(f"Average head centering proxy: {avg_align}%.")
        deliv_evidence.append(f"Average face visibility ratio: {avg_vis_ratio}%.")
    else:
        deliv_evidence.append("Not measured: camera was off or frames did not meet quality gate.")

    delivery_dimension = {
        "score": beh_score,
        "state": "measured" if delivery_measured else "not_measured",
        "evidence": deliv_evidence,
        "explanation": "Head alignment (visual centering proxy) and frame stability during responses." if delivery_measured else "Camera was off or unmeasured; Delivery was excluded from readiness score.",
        "recommended_action": "Adjust webcam height to eye level and ensure even lighting." if delivery_measured else "Enable camera in setup to measure visual centering and delivery stability.",
    }

    # 4. Resume Consistency Dimension
    resume_score = score_rec.resume_consistency_score if score_rec else 75.0
    consistency_source = score_rec.consistency_source if score_rec and hasattr(score_rec, "consistency_source") else "heuristic"

    cc_records = db.query(models.ClaimConsistency).filter_by(session_id=session_id).all()
    resume_evidence = []
    if cc_records:
        supported_count = sum(1 for c in cc_records if c.label in ("consistent", "supported"))
        weak_count = sum(1 for c in cc_records if c.label in ("weak_support", "partially_supported"))
        resume_evidence.append(f"{len(cc_records)} claims probed ({supported_count} consistent, {weak_count} weak support).")
    else:
        resume_evidence.append(f"Consistency calculated via {consistency_source} keyword-overlap model.")

    resume_dimension = {
        "score": resume_score,
        "state": "measured",
        "evidence": resume_evidence,
        "explanation": "Evaluates correlation between claimed projects/metrics and spoken technical answers.",
        "recommended_action": "Practice project-defense drills with specific throughput numbers and architecture decisions.",
    }

    return {
        "communication": communication_dimension,
        "technical": technical_dimension,
        "delivery": delivery_dimension,
        "resume_consistency": resume_dimension,
    }


def diagnose_session_weaknesses(session_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Deterministic Diagnosis Engine.
    Distinguishes:
        SYMPTOM -> PATTERN -> ROOT WEAKNESS

    Each weakness item contains:
    - id: unique taxonomy code
    - dimension: 'communication' | 'technical' | 'delivery' | 'resume' | 'pressure'
    - symptom: observable metric or occurrence
    - pattern: cross-answer pattern
    - root_weakness: explanatory root weakness diagnosis
    - severity: 'low' | 'moderate' | 'high' | 'critical'
    - evidence: list of concrete facts/quotes
    - explanation: objective, non-psychological explanation
    - recommended_action: targeted practice type and details
    """
    session = db.query(models.InterviewSession).filter_by(id=session_id).first()
    if not session:
        return []

    answers = (
        db.query(models.InterviewAnswer)
        .filter_by(session_id=session_id)
        .order_by(models.InterviewAnswer.id.asc())
        .all()
    )
    if not answers:
        return []

    evals = (
        db.query(models.AnswerEvaluation)
        .join(models.InterviewAnswer)
        .filter(models.InterviewAnswer.session_id == session_id)
        .all()
    )
    eval_by_ans = {e.answer_id: e for e in evals}

    vms = (
        db.query(models.VoiceMetrics)
        .join(models.InterviewAnswer)
        .filter(models.InterviewAnswer.session_id == session_id)
        .all()
    )
    vm_by_ans = {v.answer_id: v for v in vms}

    vis = (
        db.query(models.AnswerVisualMetrics)
        .join(models.InterviewAnswer)
        .filter(models.InterviewAnswer.session_id == session_id)
        .all()
    )
    vis_by_ans = {v.answer_id: v for v in vis}

    decisions = db.query(models.InterviewDecision).filter_by(session_id=session_id).all()
    challenge_turns = {d.turn for d in decisions if d.decision == "TRIGGER_CHALLENGE"}

    weaknesses: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # 1. COMMUNICATION TAXONOMY
    # -------------------------------------------------------------------------
    # A. Excessive Filler Words
    total_fillers = sum(v.filler_word_count or 0 for v in vms if v.speech_source == "speech")
    answers_with_high_fillers = [
        ans for ans in answers
        if vm_by_ans.get(ans.id) and (vm_by_ans[ans.id].filler_word_count or 0) >= DEFAULT_WEAKNESS_CONFIG["filler_word_threshold_per_answer"]
    ]

    if len(answers_with_high_fillers) >= 2 or total_fillers >= DEFAULT_WEAKNESS_CONFIG["filler_total_session_threshold"]:
        sev = "moderate"
        if total_fillers >= 18 or len(answers_with_high_fillers) >= 3:
            sev = "high"
        weaknesses.append({
            "id": "comm_excessive_fillers",
            "dimension": "communication",
            "symptom": f"Recorded {total_fillers} verbal filler words across answers.",
            "pattern": f"Filler word frequency exceeded threshold in {len(answers_with_high_fillers)} answers.",
            "root_weakness": "Reliance on verbal placeholders when structuring complex thoughts.",
            "severity": sev,
            "evidence": [f"Answer {a.id}: {vm_by_ans[a.id].filler_word_count} fillers" for a in answers_with_high_fillers],
            "explanation": "Frequent verbal fillers interrupt answer cadence and reduce listener comprehension.",
            "recommended_action": {
                "practice_type": "COMMUNICATION",
                "target_count": 5,
                "focus": "Deliberate pauses instead of verbal placeholders",
                "time_limit": 60,
            }
        })

    # B. Extended Pauses / Cadence Hesitation
    long_pause_answers = [
        ans for ans in answers
        if vm_by_ans.get(ans.id) and (vm_by_ans[ans.id].longest_pause or 0) >= DEFAULT_WEAKNESS_CONFIG["long_pause_threshold_seconds"]
    ]
    if len(long_pause_answers) >= DEFAULT_WEAKNESS_CONFIG["min_pause_answers"]:
        weaknesses.append({
            "id": "comm_long_pauses",
            "dimension": "communication",
            "symptom": f"{len(long_pause_answers)} answers had pauses exceeding 3.5 seconds.",
            "pattern": "Mid-response silence duration interrupted answer flow.",
            "root_weakness": "Difficulty maintaining continuous structural progression under questioning.",
            "severity": "moderate",
            "evidence": [f"Answer {a.id}: longest pause {vm_by_ans[a.id].longest_pause}s" for a in long_pause_answers],
            "explanation": "Multiple pauses exceeding 3.5s were recorded mid-sentence during technical explanations.",
            "recommended_action": {
                "practice_type": "STRUCTURED_ANSWER",
                "target_count": 5,
                "focus": "3-point framework (Context, Implementation, Result)",
                "time_limit": 60,
            }
        })

    # -------------------------------------------------------------------------
    # 2. TECHNICAL DEPTH TAXONOMY
    # -------------------------------------------------------------------------
    # A. Shallow Technical Depth
    shallow_evals = [
        ev for ev in evals
        if ev.technical_score is not None and ev.technical_score < DEFAULT_WEAKNESS_CONFIG["shallow_technical_score_threshold"]
    ]
    if len(shallow_evals) >= 2:
        avg_shallow = sum(e.technical_score for e in shallow_evals) / len(shallow_evals)
        sev = "moderate" if avg_shallow >= 48 else "high"
        weaknesses.append({
            "id": "tech_shallow_depth",
            "dimension": "technical",
            "symptom": f"{len(shallow_evals)} answers scored below 60 in technical depth.",
            "pattern": "Explanations stayed at high-level overview without architectural details.",
            "root_weakness": "Insufficient concrete parameters, trade-offs, and system constraints.",
            "severity": sev,
            "evidence": [f"Technical score: {e.technical_score}/100 on answer {e.answer_id}" for e in shallow_evals],
            "explanation": "Technical depth dropped because answers lacked specific trade-offs, failure modes, or concrete metrics.",
            "recommended_action": {
                "practice_type": "TECHNICAL_DEPTH",
                "target_count": 5,
                "focus": "Architecture decisions, failure handling, and bottleneck metrics",
                "time_limit": 90,
            }
        })

    # B. Follow-up Performance Deterioration
    followup_drops = []
    for i in range(1, len(answers)):
        prev_ev = eval_by_ans.get(answers[i - 1].id)
        curr_ev = eval_by_ans.get(answers[i].id)
        if prev_ev and curr_ev and prev_ev.technical_score and curr_ev.technical_score:
            drop = prev_ev.technical_score - curr_ev.technical_score
            if drop >= DEFAULT_WEAKNESS_CONFIG["technical_drop_threshold"]:
                followup_drops.append((answers[i].id, drop, prev_ev.technical_score, curr_ev.technical_score))

    if followup_drops:
        weaknesses.append({
            "id": "tech_followup_defense",
            "dimension": "technical",
            "symptom": f"Technical score dropped by \u226515 points on {len(followup_drops)} probe turns.",
            "pattern": "Initial answers were acceptable, but follow-up probes exposed shallower depth.",
            "root_weakness": "Difficulty defending implementation choices when probed on edge cases.",
            "severity": "moderate" if len(followup_drops) == 1 else "high",
            "evidence": [f"Answer {ans_id}: dropped {drop:.1f} pts ({p_sc:.1f} -> {c_sc:.1f})" for ans_id, drop, p_sc, c_sc in followup_drops],
            "explanation": "When prompted to go deeper into edge cases or system incidents, technical reasoning degraded.",
            "recommended_action": {
                "practice_type": "FOLLOWUP_DEFENSE",
                "target_count": 5,
                "focus": "Probe ladder stages T2 (Trade-offs) and T3 (Incidents)",
                "time_limit": 60,
            }
        })

    # -------------------------------------------------------------------------
    # 3. RESUME & VERIFICATION TAXONOMY
    # -------------------------------------------------------------------------
    elevated_vr_evals = [
        e for e in evals
        if e.verification_risk_level in ("moderate", "elevated")
    ]
    if len(elevated_vr_evals) >= 2:
        sev = "moderate"
        if any(e.verification_risk_level == "elevated" for e in elevated_vr_evals):
            sev = "high"
        weaknesses.append({
            "id": "resume_unsupported_claims",
            "dimension": "resume",
            "symptom": f"{len(elevated_vr_evals)} answers flagged with elevated verification risk.",
            "pattern": "Answers contained buzzword density, vague ownership, and missing quantifiable metrics.",
            "root_weakness": "Candidate speaks in broad industry generalities rather than personal ownership.",
            "evidence": [f"Answer {e.answer_id}: {e.verification_risk_level} risk ({e.verification_risk_score}/100)" for e in elevated_vr_evals],
            "severity": sev,
            "explanation": "Observable signals indicate repeated generic phrasing ('we utilized scalable frameworks') instead of verifiable specifics.",
            "recommended_action": {
                "practice_type": "RESUME_CLAIM_DEFENSE",
                "target_count": 4,
                "focus": "First-person ownership ('I designed', 'I benchmarked') with exact throughput metrics",
                "time_limit": 60,
            }
        })

    # -------------------------------------------------------------------------
    # 4. PRESSURE TAXONOMY
    # -------------------------------------------------------------------------
    if challenge_turns:
        challenge_answers = [ans for idx, ans in enumerate(answers) if (idx + 1) in challenge_turns]
        challenge_evals = [eval_by_ans[a.id] for a in challenge_answers if a.id in eval_by_ans]
        low_challenge = [e for e in challenge_evals if (e.overall_score or 70.0) < 60.0]
        if len(low_challenge) >= 1:
            weaknesses.append({
                "id": "pressure_time_deterioration",
                "dimension": "pressure",
                "symptom": f"Answer quality dropped during {len(low_challenge)} challenge triggers.",
                "pattern": "Under 45s constraint and follow-up challenges, answers became brief and generic.",
                "root_weakness": "Difficulty synthesizing structured technical reasoning under tight time limits.",
                "severity": "moderate",
                "evidence": [f"Answer {e.answer_id}: overall score {e.overall_score}/100 under pressure challenge" for e in low_challenge],
                "explanation": "When challenged on specific numbers or given a 45s timer, answer substance dropped.",
                "recommended_action": {
                    "practice_type": "PRESSURE_RESPONSE",
                    "target_count": 5,
                    "focus": "45-second rapid technical synthesis drills",
                    "time_limit": 45,
                }
            })

    # -------------------------------------------------------------------------
    # 5. DELIVERY TAXONOMY (Only if camera was active and quality passed)
    # -------------------------------------------------------------------------
    valid_vis = [v for v in vis if v.frames_sampled and v.frames_sampled >= DEFAULT_WEAKNESS_CONFIG["min_visual_frames"] and v.face_visibility_ratio is not None]
    if valid_vis:
        low_alignment = [v for v in valid_vis if (v.head_alignment_percent or 100.0) < DEFAULT_WEAKNESS_CONFIG["unstable_head_alignment_threshold"]]
        if len(low_alignment) >= 2:
            weaknesses.append({
                "id": "delivery_unstable_alignment",
                "dimension": "delivery",
                "symptom": f"Head alignment proxy dropped below 55% in {len(low_alignment)} answers.",
                "pattern": "Significant visual centering deviation recorded during responses.",
                "root_weakness": "Camera framing or head position frequently drifting off center.",
                "severity": "low",
                "evidence": [f"Answer {v.answer_id}: alignment {v.head_alignment_percent}%" for v in low_alignment],
                "explanation": "Head alignment proxy indicates candidate was repeatedly positioned near the periphery of the frame.",
                "recommended_action": {
                    "practice_type": "COMMUNICATION",
                    "target_count": 3,
                    "focus": "Adjusting camera elevation and maintaining centered frame position",
                    "time_limit": 60,
                }
            })

    return weaknesses
