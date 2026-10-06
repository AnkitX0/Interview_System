"""
backend/services/voice_service.py
Per-answer voice and speech metrics computation.
Computes speech cadence, pause duration approximations, silence ratio,
and length-guarded moving-average vocabulary diversity (MATTR).

HONESTY & PROBABILISTIC CONTRACT:
- The Web Speech API provides no word-level timestamps; pauses are approximated
  from client-side speech recognition event timing.
- For typed answers or missing audio timing, delivery/cadence metrics are NULL
  ("Not measured"), never zero or defaulted.
- In Phase 2, USE_VOICE_METRICS_IN_SCORE = False. Voice metrics are display-only
  and do not alter the final readiness score.
"""

import re
from typing import List, Dict, Any, Optional

from backend.config import (
    VOICE_PAUSE_THRESHOLD_SECONDS,
    MIN_WORDS_FOR_TTR,
    TTR_MOVING_WINDOW,
    FILLER_WORDS,
)

WORD_REGEX = re.compile(r"\b[a-zA-Z0-9']+\b")


def validate_speech_segments(segments: List[Dict[str, float]]) -> List[Dict[str, float]]:
    """
    Validates that speech segments are well-formed:
    - Non-negative start and end
    - end >= start
    - Monotonically increasing start timestamps
    - Bounded segment count
    """
    if not segments or not isinstance(segments, list):
        return []

    valid = []
    last_end = 0.0

    for seg in segments[:1000]:  # Bound maximum segments
        if not isinstance(seg, dict):
            continue
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", 0.0))

        if start < 0.0 or end < start:
            continue
        if start < last_end:
            # Enforce non-overlapping monotonicity
            start = last_end

        valid.append({"start": round(start, 3), "end": round(end, 3)})
        last_end = max(last_end, end)

    return valid


def compute_vocabulary_diversity(text: str) -> Dict[str, Any]:
    """
    Computes length-robust Moving-Average Type-Token Ratio (MATTR).
    Guarded against short answers where raw TTR artificially approaches 1.0.
    """
    tokens = [w.lower() for w in WORD_REGEX.findall(text)]
    total_tokens = len(tokens)

    if total_tokens < MIN_WORDS_FOR_TTR:
        return {
            "value": None,
            "interpretation": f"Not measured: response contains {total_tokens} words, below the {MIN_WORDS_FOR_TTR}-word minimum for reliable diversity evaluation.",
            "recommended_action": "Elaborate with specific technical context and implementation details to demonstrate broader domain vocabulary.",
        }

    if total_tokens <= TTR_MOVING_WINDOW:
        # Standard TTR for medium lengths
        unique_tokens = len(set(tokens))
        score = round((unique_tokens / total_tokens) * 100.0, 1)
    else:
        # Moving-average TTR across fixed window
        window_ttrs = []
        for i in range(total_tokens - TTR_MOVING_WINDOW + 1):
            window = tokens[i : i + TTR_MOVING_WINDOW]
            window_ttrs.append(len(set(window)) / TTR_MOVING_WINDOW)
        score = round((sum(window_ttrs) / len(window_ttrs)) * 100.0, 1)

    interpretation = (
        f"Vocabulary diversity score of {score}%. "
        f"Reflects word variety across {total_tokens} words."
    )
    action = (
        "Maintain current technical breadth."
        if score >= 60.0
        else "Consider using more varied domain-specific terminology instead of repeating general verbs and descriptors."
    )

    return {
        "value": score,
        "interpretation": interpretation,
        "recommended_action": action,
    }


def compute_voice_metrics(
    transcript: str,
    duration_seconds: float,
    speech_segments: Optional[List[Dict[str, float]]] = None,
    speech_source: str = "speech",
) -> Dict[str, Any]:
    """
    Computes per-answer voice and speech metrics.
    For typed answers, cadence and pauses are returned as None (Not measured).
    """
    clean_text = transcript.strip()
    words = clean_text.split()
    word_count = len(words)
    duration = max(0.0, duration_seconds)

    # 1. Vocabulary diversity (always computable from text)
    vocab_result = compute_vocabulary_diversity(clean_text)

    # If typed or no audio timing available: pause metrics are Not Measured
    if speech_source == "typed" or not speech_segments:
        return {
            "speech_source": speech_source,
            "words_per_minute": {
                "value": None,
                "interpretation": "Not measured (typed answer or audio timing unavailable).",
                "recommended_action": "Speak your answer using the microphone to capture speech pacing metrics.",
            },
            "filler_words": {
                "value": 0,
                "interpretation": "No audio filler words measured for typed response.",
                "recommended_action": "Practice speaking aloud to monitor verbal pause patterns.",
            },
            "pause_metrics": {
                "pause_count": None,
                "avg_pause_duration": None,
                "longest_pause": None,
                "silence_ratio": None,
                "interpretation": "Not measured (typed answer or speech timing unavailable).",
                "recommended_action": "Use speech input to capture cadence and pause metrics.",
            },
            "vocabulary_diversity": vocab_result,
            # Raw DB values
            "raw": {
                "words_per_minute": None,
                "filler_word_count": 0,
                "avg_pause_duration": None,
                "longest_pause": None,
                "pause_count": None,
                "silence_ratio": None,
                "vocabulary_diversity_score": vocab_result["value"],
                "speech_source": speech_source,
            },
        }

    # 2. Spoken metrics: Words Per Minute (WPM)
    if duration > 0.0:
        wpm = round((word_count / (duration / 60.0)), 1)
        wpm_interp = f"Pacing of {wpm} words per minute ({word_count} words over {round(duration, 1)} seconds)."
        if wpm < 110:
            wpm_action = "Your speaking rate was relatively deliberate. Consider pacing slightly faster to maintain engagement."
        elif wpm > 175:
            wpm_action = "Your speaking rate was elevated. Deliberately pausing between key points can enhance clarity."
        else:
            wpm_action = "Speaking rate is within standard conversational interview guidelines (120-160 WPM)."
    else:
        wpm = None
        wpm_interp = "Duration too short to compute speaking rate."
        wpm_action = "Ensure complete responses."

    # 3. Filler word count
    lower_text = clean_text.lower()
    filler_count = 0
    for filler in FILLER_WORDS:
        filler_count += len(re.findall(rf"\b{re.escape(filler)}\b", lower_text))

    filler_rate = round((filler_count / max(1, word_count)) * 100, 1)
    filler_interp = (
        f"{filler_count} filler words detected in {word_count} words "
        f"({filler_rate} per 100 words). Target benchmark: <= 4 per 100 words."
    )
    filler_action = (
        "Filler rate is within acceptable professional range."
        if filler_rate <= 4.0
        else "Replace verbal fillers with deliberate silent pauses to formulate thoughts."
    )

    # 4. Speech segments and pause calculations
    valid_segments = validate_speech_segments(speech_segments)
    pauses = []

    # Leading pause before first speech
    if valid_segments and valid_segments[0]["start"] >= VOICE_PAUSE_THRESHOLD_SECONDS:
        pauses.append(valid_segments[0]["start"])

    # Gaps between consecutive speech recognition results
    for i in range(len(valid_segments) - 1):
        gap = valid_segments[i + 1]["start"] - valid_segments[i]["end"]
        if gap >= VOICE_PAUSE_THRESHOLD_SECONDS:
            pauses.append(round(gap, 2))

    pause_count = len(pauses)
    longest_pause = round(max(pauses), 2) if pauses else 0.0
    avg_pause = round(sum(pauses) / pause_count, 2) if pause_count > 0 else 0.0
    total_pause_time = sum(pauses)
    silence_ratio = round(min(1.0, total_pause_time / duration), 3) if duration > 0.0 else 0.0

    pause_interp = (
        f"{pause_count} pauses exceeding {VOICE_PAUSE_THRESHOLD_SECONDS}s detected "
        f"(average {avg_pause}s, longest {longest_pause}s, silence ratio {round(silence_ratio * 100, 1)}%). "
        "Approximate, based on speech-recognition timing."
    )
    if pause_count == 0:
        pause_action = "Consistent continuous delivery without prolonged hesitation."
    elif avg_pause > 3.0:
        pause_action = "Several extended pauses observed. Structuring your answer beforehand can minimize mid-thought hesitations."
    else:
        pause_action = "Cadence shows natural conversational pauses."

    return {
        "speech_source": "speech",
        "words_per_minute": {
            "value": wpm,
            "interpretation": wpm_interp,
            "recommended_action": wpm_action,
        },
        "filler_words": {
            "value": filler_count,
            "rate_per_100_words": filler_rate,
            "interpretation": filler_interp,
            "recommended_action": filler_action,
        },
        "pause_metrics": {
            "pause_count": pause_count,
            "avg_pause_duration": avg_pause,
            "longest_pause": longest_pause,
            "silence_ratio": silence_ratio,
            "interpretation": pause_interp,
            "recommended_action": pause_action,
        },
        "vocabulary_diversity": vocab_result,
        # Raw values for database persistence
        "raw": {
            "words_per_minute": wpm,
            "filler_word_count": filler_count,
            "avg_pause_duration": avg_pause,
            "longest_pause": longest_pause,
            "pause_count": pause_count,
            "silence_ratio": silence_ratio,
            "vocabulary_diversity_score": vocab_result["value"],
            "speech_source": "speech",
        },
    }
