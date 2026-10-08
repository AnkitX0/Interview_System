"""
backend/services/transcription_service.py

High-Accuracy Audio Transcription Service for Interview Intelligence.
Architecture:
1. Complete-Answer Recording via MediaRecorder in memory.
2. Official Google GenAI SDK (gemini-3.5-transcribe) with technical vocabulary grounding.
3. In-memory FFmpeg audio loudness normalization & duration extraction.
4. Seamless in-memory speech recognition fallback if Gemini API is unreachable.
5. Zero disk persistence: audio processed purely in memory and immediately discarded.
"""

import os
import re
import json
import base64
import logging
import io
import subprocess
from typing import Optional, Dict, Any, List

from backend.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TRANSCRIBE_MODEL

logger = logging.getLogger("interview_system.transcription")

DEFAULT_TECH_VOCABULARY = [
    "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes",
    "MediaPipe", "PyTorch", "React", "Vite", "WebRTC",
    "SQLAlchemy", "Gemini", "AWS", "Go", "Golang", "REST API",
    "WebSocket", "Microservices", "CNN", "MLP", "NLP", "XGBoost",
    "Random Forest", "OpenCV", "SQLite", "MongoDB", "gRPC", "Kafka",
    "CI/CD", "TypeScript", "JavaScript", "Python", "GraphQL", "OAuth",
    "JWT", "Argon2", "Next.js", "Tailwind", "CSS", "HTML5", "Redux",
    "TensorFlow", "Pandas", "NumPy", "Scikit-Learn", "BERT", "LLM"
]

SUPPORTED_AUDIO_MIMES = [
    "audio/webm", "audio/webm;codecs=opus", "audio/ogg", "audio/ogg;codecs=opus",
    "audio/mp4", "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/m4a"
]


def _align_technical_terms(text: str, vocabulary: Optional[List[str]] = None) -> str:
    """Aligns casing of recognized technical keywords without altering spoken words."""
    if not text:
        return ""
    vocab = list(set((vocabulary or []) + DEFAULT_TECH_VOCABULARY))
    # Match longer phrases first to prevent partial replacements
    vocab.sort(key=len, reverse=True)
    aligned = text
    for term in vocab:
        if not term or len(term) < 2:
            continue
        parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', term)
        if len(parts) > 1 and not any(" " in p for p in parts):
            spaced_pattern = r"\s+".join(re.escape(p) for p in parts)
            full_pattern = rf"\b(?:{re.escape(term)}|{spaced_pattern})\b"
        else:
            full_pattern = rf"\b{re.escape(term)}\b"
        aligned = re.sub(full_pattern, term, aligned, flags=re.IGNORECASE)
    return aligned


def extract_audio_duration_seconds(audio_bytes: bytes) -> Optional[float]:
    """
    Extracts the duration of the in-memory audio bytes using ffmpeg packet analysis.
    Returns duration in seconds (float) or None if unparseable.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        return None
    try:
        cmd = ["ffmpeg", "-loglevel", "info", "-i", "pipe:0", "-f", "null", "-"]
        proc = subprocess.run(cmd, input=audio_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=4.0)
        stderr = proc.stderr.decode("utf-8", errors="replace")
        match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', stderr)
        if match:
            h, m, s = match.groups()
            return round(int(h) * 3600 + int(m) * 60 + float(s), 2)
        match_dur = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', stderr)
        if match_dur:
            h, m, s = match_dur.groups()
            return round(int(h) * 3600 + int(m) * 60 + float(s), 2)
    except Exception as e:
        logger.debug("Could not extract audio duration: %s", e)
    return None


def normalize_audio_in_memory(audio_bytes: bytes, target_sample_rate: int = 16000) -> Optional[bytes]:
    """
    Applies EBU R128 loudness normalization and resamples to 16kHz mono WAV purely in memory.
    Ensures optimal acoustic quality and removes clipping / quiet microphone noise.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        return None
    try:
        cmd = [
            "ffmpeg", "-loglevel", "quiet",
            "-i", "pipe:0",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=16000",
            "-ac", "1",
            "-f", "wav",
            "pipe:1"
        ]
        proc = subprocess.run(cmd, input=audio_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=6.0)
        if proc.returncode == 0 and proc.stdout and len(proc.stdout) > 200:
            return proc.stdout
    except Exception as e:
        logger.warning("In-memory audio normalization warning: %s", e)
    return None


def _transcribe_via_gemini_sdk(
    audio_bytes: bytes,
    mime_type: str = "audio/webm",
    vocabulary: Optional[List[str]] = None,
    language: str = "en-IN",
    mode: str = "verbatim"
) -> Optional[Dict[str, Any]]:
    """
    Transcribes complete audio response using the official Google GenAI SDK.
    Primary model: GEMINI_TRANSCRIBE_MODEL (default: gemini-3.5-transcribe).
    Falls back to GEMINI_MODEL if dedicated transcribe model is not available.
    """
    api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.startswith("your_") or api_key.startswith("replace_") or len(api_key) < 20:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        clean_mime = mime_type.split(";")[0].strip() if mime_type else "audio/webm"
        if clean_mime not in ("audio/webm", "audio/wav", "audio/ogg", "audio/mp3", "audio/mp4", "audio/m4a"):
            clean_mime = "audio/webm"

        vocab_terms = list(set((vocabulary or []) + DEFAULT_TECH_VOCABULARY))
        vocab_str = ", ".join(vocab_terms[:60])

        if mode == "smart":
            prompt = (
                f"Transcribe this candidate's interview audio clearly and accurately in {language}. "
                f"Preserve all technical terminology, framework names, programming languages, and system architecture terms verbatim. "
                f"Format standard punctuation and capitalization cleanly. "
                f"Known technical vocabulary context: {vocab_str}. "
                f"Return JSON with key 'transcript': {{\"transcript\": \"...\"}}."
            )
        else:  # verbatim (default)
            prompt = (
                f"Transcribe this candidate's interview response STRICTLY VERBATIM in {language}. "
                f"Do not paraphrase, summarize, omit, or grammatically alter any words. "
                f"Preserve verbal markers (um, uh, like), repetitions, technical terminology, and exact numbers spoken. "
                f"Technical vocabulary grounding: {vocab_str}. "
                f"Return JSON with key 'transcript': {{\"transcript\": \"...\"}}."
            )

        models_to_try = [
            GEMINI_TRANSCRIBE_MODEL or "gemini-3.5-transcribe",
            GEMINI_MODEL or "gemini-2.5-flash",
            "gemini-2.0-flash"
        ]

        part = types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime)

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[part, prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json"
                    )
                )

                if response and response.text:
                    parsed = json.loads(response.text.strip())
                    raw_text = parsed.get("transcript", "").strip()
                    if raw_text:
                        aligned = _align_technical_terms(raw_text, vocabulary)
                        logger.info("[Speech] Successfully transcribed audio via Gemini model: %s", model_name)
                        return {
                            "transcript": aligned,
                            "raw_transcript": raw_text,
                            "engine": model_name,
                            "status": "success"
                        }
            except Exception as model_err:
                logger.debug("[Speech] Gemini model %s attempt: %s", model_name, model_err)
                continue

    except Exception as e:
        logger.warning("[Speech] Gemini SDK transcription failed: %s", e)

    return None


def _transcribe_via_google_speech(
    audio_bytes: bytes,
    mime_type: str = "audio/webm",
    vocabulary: Optional[List[str]] = None,
    language: str = "en-IN"
) -> Optional[str]:
    """
    Transcribes audio bytes in memory by piping into ffmpeg to produce 16kHz mono WAV,
    then running speech_recognition's Google recognizer with zero disk storage.
    """
    try:
        import speech_recognition as sr

        cmd = [
            "ffmpeg", "-loglevel", "quiet",
            "-i", "pipe:0",
            "-f", "wav",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "pipe:1"
        ]
        proc = subprocess.run(cmd, input=audio_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8.0)
        if proc.returncode != 0 or not proc.stdout:
            return None

        wav_io = io.BytesIO(proc.stdout)
        r = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            audio_data = r.record(source)
            try:
                sr_lang = "en-IN" if "IN" in language.upper() else ("hi-IN" if "HI" in language.upper() else "en-US")
                transcript = r.recognize_google(audio_data, language=sr_lang)
                if transcript:
                    aligned = _align_technical_terms(transcript.strip(), vocabulary)
                    logger.info("[Speech] Successfully transcribed audio via Google speech engine (lang: %s)", sr_lang)
                    return aligned
            except sr.UnknownValueError:
                return ""  # Silence or unvoiced audio
            except Exception as e:
                logger.debug("Google speech engine notice: %s", e)
                return None
    except Exception as e:
        logger.warning("In-memory speech fallback error: %s", e)
        return None
    return None


def transcribe_complete_answer(
    audio_bytes: bytes,
    mime_type: str = "audio/webm",
    vocabulary: Optional[List[str]] = None,
    language: str = "en-IN",
    mode: str = "verbatim",
    normalize: bool = False
) -> Dict[str, Any]:
    """
    Primary authoritative transcription pipeline for complete candidate interview answers.
    1. Validates audio bytes.
    2. Computes duration in seconds.
    3. Normalizes loudness if requested.
    4. Transcribes via Google GenAI SDK (gemini-3.5-transcribe).
    5. Falls back to in-memory Google Speech with FFmpeg.
    6. Returns structured response matching acceptance criteria.
    Zero disk persistence: processed strictly in memory.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        return {
            "success": False,
            "transcript": "",
            "raw_transcript": "",
            "clean_transcript": "",
            "engine": "none",
            "duration_seconds": 0.0,
            "confidence": None,
            "error": "EMPTY_AUDIO"
        }

    logger.info(
        "[TRANSCRIPTION_REQUEST] bytes=%d mime=%s lang=%s mode=%s",
        len(audio_bytes), mime_type, language, mode
    )

    duration = extract_audio_duration_seconds(audio_bytes) or 0.0

    target_bytes = audio_bytes
    if normalize:
        normalized = normalize_audio_in_memory(audio_bytes)
        if normalized:
            target_bytes = normalized
            mime_type = "audio/wav"

    # 1. Primary Engine: Official Google GenAI SDK
    gemini_res = _transcribe_via_gemini_sdk(
        audio_bytes=target_bytes,
        mime_type=mime_type,
        vocabulary=vocabulary,
        language=language,
        mode=mode
    )

    if gemini_res and gemini_res.get("transcript"):
        transcript = gemini_res["transcript"]
        model_name = gemini_res.get("engine", GEMINI_TRANSCRIBE_MODEL or "gemini-3.5-transcribe")
        words_count = len(transcript.split())
        logger.info(
            "[TRANSCRIPTION] provider=gemini model=%s duration=%.2f words=%d bytes=%d",
            model_name, duration, words_count, len(audio_bytes)
        )
        return {
            "success": True,
            "transcript": transcript,
            "raw_transcript": gemini_res.get("raw_transcript", transcript),
            "clean_transcript": transcript,
            "engine": "gemini",
            "model": model_name,
            "duration_seconds": duration,
            "confidence": None,
            "language": language,
            "mode": mode
        }

    # 2. Secondary Engine: In-memory Google Speech via FFmpeg
    fallback_transcript = _transcribe_via_google_speech(
        audio_bytes=target_bytes,
        mime_type=mime_type,
        vocabulary=vocabulary,
        language=language
    )

    if fallback_transcript is not None:
        words_count = len(fallback_transcript.split())
        logger.info(
            "[TRANSCRIPTION] provider=google_speech model=google_speech_v2 duration=%.2f words=%d bytes=%d",
            duration, words_count, len(audio_bytes)
        )
        return {
            "success": True,
            "transcript": fallback_transcript,
            "raw_transcript": fallback_transcript,
            "clean_transcript": fallback_transcript,
            "engine": "google_speech",
            "model": "google_speech_v2",
            "duration_seconds": duration,
            "confidence": None,
            "language": language,
            "mode": mode
        }

    logger.warning("[TRANSCRIPTION] provider=none model=none status=failed bytes=%d", len(audio_bytes))
    return {
        "success": False,
        "transcript": "",
        "raw_transcript": "",
        "clean_transcript": "",
        "engine": "none",
        "model": "none",
        "duration_seconds": duration,
        "confidence": None,
        "error": "NO_SPEECH_DETECTED"
    }


def transcribe_audio_bytes(
    audio_bytes: bytes,
    mime_type: str = "audio/webm",
    vocabulary: Optional[List[str]] = None,
    timeout: float = 6.0
) -> Dict[str, Any]:
    """
    Backwards-compatible wrapper delegating to transcribe_complete_answer.
    Used for rolling chunk streaming fallbacks and legacy endpoints.
    """
    res = transcribe_complete_answer(
        audio_bytes=audio_bytes,
        mime_type=mime_type,
        vocabulary=vocabulary,
        language="en-IN",
        mode="verbatim",
        normalize=False
    )
    return {
        "transcript": res.get("transcript", ""),
        "raw_transcript": res.get("raw_transcript", ""),
        "engine": res.get("engine", "none"),
        "status": "success" if res.get("success") else "no_speech_detected",
        "duration_seconds": res.get("duration_seconds", 0.0)
    }
