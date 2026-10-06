import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.models import models


def format_seconds_to_mmss(seconds: float) -> str:
    """Formats float seconds into MM:SS string."""
    total_sec = max(0, int(round(seconds)))
    mins = total_sec // 60
    secs = total_sec % 60
    return f"{mins:02d}:{secs:02d}"


def build_time_range(start_sec: float, end_sec: float) -> str:
    """Returns a formatted time interval string e.g. '00:00 - 01:15'."""
    return f"{format_seconds_to_mmss(start_sec)} - {format_seconds_to_mmss(end_sec)}"


def generate_session_timeline(session_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Transforms stored answer evaluations, voice metrics, visual metrics,
    and adaptive decisions into a deterministic, chronological timeline of observable events.

    Guarantees:
    - Pure derivation from stored data (no redundant tables required).
    - Fully deterministic: identical inputs produce identical timelines.
    - No psychological or deception inferences (strictly observable descriptions).
    - Camera-off / unmeasured visual signals produce zero visual events.
    - Text-only answers produce zero audio cadence events.
    """
    session = db.query(models.InterviewSession).filter_by(id=session_id).first()
    if not session:
        return []

    # Query answers in chronological order
    answers = (
        db.query(models.InterviewAnswer)
        .filter_by(session_id=session_id)
        .order_by(models.InterviewAnswer.id.asc())
        .all()
    )

    # Query all decisions for this session
    decisions = (
        db.query(models.InterviewDecision)
        .filter_by(session_id=session_id)
        .order_by(models.InterviewDecision.turn.asc(), models.InterviewDecision.id.asc())
        .all()
    )
    decisions_by_turn: Dict[int, List[models.InterviewDecision]] = {}
    for d in decisions:
        decisions_by_turn.setdefault(d.turn, []).append(d)

    timeline_events: List[Dict[str, Any]] = []
    cumulative_seconds = 0.0
    prev_technical_score: Optional[float] = None
    prev_verification_level: Optional[str] = None

    for idx, ans in enumerate(answers):
        turn_num = idx + 1
        duration = float(ans.duration_seconds or 0.0)
        if duration <= 0.0 and ans.response_time and ans.response_time > 0.0:
            duration = float(ans.response_time)
        if duration <= 0.0:
            duration = 45.0  # sensible default duration for timeline spacing

        start_sec = cumulative_seconds
        end_sec = start_sec + duration
        range_str = build_time_range(start_sec, end_sec)

        # Linked question metadata if exists
        iq = (
            db.query(models.InterviewQuestion)
            .filter_by(session_id=session_id, id=ans.question_id)
            .first()
        )
        if not iq:
            iq = (
                db.query(models.InterviewQuestion)
                .filter_by(session_id=session_id, question_text=ans.question_text)
                .first()
            )

        ladder_stage = iq.ladder_stage if iq else None
        q_type = iq.question_type if iq else "technical"
        difficulty = iq.difficulty if iq else session.difficulty or "medium"

        # 1. Question Started Event
        q_summary = (ans.question_text or "Question").strip()
        if len(q_summary) > 70:
            q_summary = q_summary[:67] + "..."

        timeline_events.append({
            "event_id": f"q_start_{turn_num}",
            "timestamp_offset": round(start_sec, 1),
            "time_range": build_time_range(start_sec, start_sec + min(5.0, duration)),
            "event_type": "question_started",
            "dimension": "session",
            "title": f"Question {turn_num} Started",
            "description": f"{q_summary} ({ladder_stage or q_type}, difficulty: {difficulty})",
            "evidence": {
                "question_id": ans.question_id,
                "turn": turn_num,
                "ladder_stage": ladder_stage,
                "difficulty": difficulty
            },
            "severity": "info"
        })

        # 2. Check for Decisions on this turn (e.g. pressure challenge or mode switch)
        turn_decisions = decisions_by_turn.get(turn_num, [])
        for d in turn_decisions:
            if d.decision == "TRIGGER_CHALLENGE":
                timeline_events.append({
                    "event_id": f"pressure_challenge_{d.id}",
                    "timestamp_offset": round(start_sec + 2.0, 1),
                    "time_range": build_time_range(start_sec, start_sec + min(15.0, duration)),
                    "event_type": "pressure_challenge",
                    "dimension": "pressure",
                    "title": "Pressure Challenge Triggered",
                    "description": d.reason,
                    "evidence": {"turn": turn_num, "decision": d.decision, "inputs": d.inputs},
                    "severity": "warning"
                })
            elif d.decision == "SWITCH_TO_PRACTICE":
                timeline_events.append({
                    "event_id": f"mode_switch_{d.id}",
                    "timestamp_offset": round(start_sec, 1),
                    "time_range": build_time_range(start_sec, start_sec + 5.0),
                    "event_type": "mode_switch",
                    "dimension": "session",
                    "title": "De-escalated to Standard Mode",
                    "description": d.reason,
                    "evidence": {"turn": turn_num, "decision": d.decision},
                    "severity": "info"
                })

        # Query AnswerEvaluation, VoiceMetrics, VisualMetrics
        ev = (
            db.query(models.AnswerEvaluation)
            .filter_by(answer_id=ans.id)
            .first()
        )
        vm = (
            db.query(models.VoiceMetrics)
            .filter_by(answer_id=ans.id)
            .first()
        )
        vis = (
            db.query(models.AnswerVisualMetrics)
            .filter_by(answer_id=ans.id)
            .first()
        )

        # 3. Audio & Cadence Events (Only if spoken and voice_metrics is available)
        if vm and vm.speech_source == "speech":
            # Speaking speed change
            wpm = vm.words_per_minute
            if wpm is not None:
                if wpm > 165.0:
                    timeline_events.append({
                        "event_id": f"wpm_high_{turn_num}",
                        "timestamp_offset": round(start_sec + (duration * 0.4), 1),
                        "time_range": range_str,
                        "event_type": "speaking_speed_change",
                        "dimension": "communication",
                        "title": "Speaking Speed Rose Above Baseline",
                        "description": f"Cadence rose to {round(wpm, 1)} WPM (standard conversational band: 120-160 WPM).",
                        "evidence": {"words_per_minute": wpm, "baseline": "120-160 WPM"},
                        "severity": "info"
                    })
                elif wpm < 95.0:
                    timeline_events.append({
                        "event_id": f"wpm_low_{turn_num}",
                        "timestamp_offset": round(start_sec + (duration * 0.4), 1),
                        "time_range": range_str,
                        "event_type": "speaking_speed_change",
                        "dimension": "communication",
                        "title": "Speaking Speed Slowed Below Baseline",
                        "description": f"Cadence slowed to {round(wpm, 1)} WPM (standard conversational band: 120-160 WPM).",
                        "evidence": {"words_per_minute": wpm, "baseline": "120-160 WPM"},
                        "severity": "info"
                    })

            # Filler word spike
            filler_count = vm.filler_word_count
            word_count = len((ans.transcript or "").split())
            if filler_count is not None and filler_count >= 5:
                timeline_events.append({
                    "event_id": f"filler_spike_{turn_num}",
                    "timestamp_offset": round(start_sec + (duration * 0.5), 1),
                    "time_range": range_str,
                    "event_type": "filler_spike",
                    "dimension": "communication",
                    "title": "Verbal Filler Count Rose",
                    "description": f"Recorded {filler_count} verbal filler words during response ({round((filler_count / max(1, word_count)) * 100, 1)}% of spoken words).",
                    "evidence": {"filler_count": filler_count, "word_count": word_count},
                    "severity": "warning"
                })

            # Long pause
            longest_pause = vm.longest_pause
            if longest_pause is not None and longest_pause >= 3.0:
                timeline_events.append({
                    "event_id": f"long_pause_{turn_num}",
                    "timestamp_offset": round(start_sec + (duration * 0.2), 1),
                    "time_range": range_str,
                    "event_type": "long_pause",
                    "dimension": "communication",
                    "title": "Extended Pause Recorded",
                    "description": f"Longest mid-answer pause measured at {round(longest_pause, 1)}s (average pause: {round(vm.avg_pause_duration or 0.0, 1)}s).",
                    "evidence": {"longest_pause": longest_pause, "avg_pause_duration": vm.avg_pause_duration},
                    "severity": "info"
                })

        # 4. Evaluation & Score Events
        if ev:
            tech_score = ev.technical_score
            if tech_score is not None:
                if prev_technical_score is not None and (prev_technical_score - tech_score) >= 15.0:
                    timeline_events.append({
                        "event_id": f"tech_drop_{turn_num}",
                        "timestamp_offset": round(start_sec + (duration * 0.6), 1),
                        "time_range": range_str,
                        "event_type": "answer_score_change",
                        "dimension": "technical",
                        "title": "Technical Depth Score Dropped",
                        "description": f"Technical score decreased from {round(prev_technical_score, 1)} to {round(tech_score, 1)}/100 on follow-up question.",
                        "evidence": {"previous_score": prev_technical_score, "current_score": tech_score, "delta": round(tech_score - prev_technical_score, 1)},
                        "severity": "warning"
                    })
                elif tech_score < 55.0:
                    timeline_events.append({
                        "event_id": f"tech_low_{turn_num}",
                        "timestamp_offset": round(start_sec + (duration * 0.6), 1),
                        "time_range": range_str,
                        "event_type": "answer_score_change",
                        "dimension": "technical",
                        "title": "Technical Depth Evaluated Low",
                        "description": f"Answer technical reasoning evaluated at {round(tech_score, 1)}/100.",
                        "evidence": {"current_score": tech_score},
                        "severity": "warning"
                    })
                elif tech_score >= 85.0:
                    timeline_events.append({
                        "event_id": f"tech_high_{turn_num}",
                        "timestamp_offset": round(start_sec + (duration * 0.6), 1),
                        "time_range": range_str,
                        "event_type": "answer_score_change",
                        "dimension": "technical",
                        "title": "Strong Technical Depth Evaluated",
                        "description": f"Answer technical reasoning evaluated at {round(tech_score, 1)}/100.",
                        "evidence": {"current_score": tech_score},
                        "severity": "positive"
                    })
                prev_technical_score = tech_score

            # Verification risk change
            vr_level = ev.verification_risk_level
            if vr_level in ("moderate", "elevated"):
                ev_items = ev.verification_risk_evidence or []
                ev_str = "; ".join(ev_items[:2]) if isinstance(ev_items, list) else str(ev_items)
                timeline_events.append({
                    "event_id": f"vr_flag_{turn_num}",
                    "timestamp_offset": round(start_sec + (duration * 0.7), 1),
                    "time_range": range_str,
                    "event_type": "verification_risk_change",
                    "dimension": "resume",
                    "title": f"Verification Risk: {vr_level.capitalize()}",
                    "description": f"Observable risk indicators: {ev_str or 'Lower specific detail density recorded'}.",
                    "evidence": {
                        "level": vr_level,
                        "risk_score": ev.verification_risk_score,
                        "observable_signals": ev.verification_risk_evidence
                    },
                    "severity": "warning"
                })
            prev_verification_level = vr_level

        # 5. Visual Events (Only if visual metrics are measured with sufficient frames)
        if vis and vis.frames_sampled and vis.frames_sampled >= 30 and vis.face_visibility_ratio is not None:
            # Low face visibility
            if vis.face_visibility_ratio < 0.60:
                timeline_events.append({
                    "event_id": f"vis_visib_drop_{turn_num}",
                    "timestamp_offset": round(start_sec + (duration * 0.5), 1),
                    "time_range": range_str,
                    "event_type": "visual_quality_drop",
                    "dimension": "delivery",
                    "title": "Low Face Visibility Ratio",
                    "description": f"Face was detected in {round(vis.face_visibility_ratio * 100, 1)}% of sampled frames (below 60% quality gate).",
                    "evidence": {"face_visibility_ratio": vis.face_visibility_ratio, "frames_sampled": vis.frames_sampled},
                    "severity": "warning"
                })
            # Frequent head shifts
            elif vis.head_shift_count is not None and vis.head_shift_count >= 8:
                timeline_events.append({
                    "event_id": f"vis_shifts_{turn_num}",
                    "timestamp_offset": round(start_sec + (duration * 0.5), 1),
                    "time_range": range_str,
                    "event_type": "visual_quality_drop",
                    "dimension": "delivery",
                    "title": "Frequent Head Position Shifts",
                    "description": f"Recorded {vis.head_shift_count} significant head shifts during response.",
                    "evidence": {"head_shift_count": vis.head_shift_count},
                    "severity": "info"
                })

        # 6. Answer Completed Event
        timeline_events.append({
            "event_id": f"ans_complete_{turn_num}",
            "timestamp_offset": round(end_sec, 1),
            "time_range": range_str,
            "event_type": "answer_completed",
            "dimension": "session",
            "title": f"Answer {turn_num} Completed",
            "description": f"Response submitted ({round(duration, 1)}s duration, {len((ans.transcript or '').split())} words).",
            "evidence": {
                "turn": turn_num,
                "duration_seconds": duration,
                "word_count": len((ans.transcript or '').split()),
                "overall_score": ev.overall_score if ev else None
            },
            "severity": "info"
        })

        cumulative_seconds = end_sec

    # Sort deterministically by timestamp_offset, then event_id
    timeline_events.sort(key=lambda e: (e["timestamp_offset"], e["event_id"]))
    return timeline_events
