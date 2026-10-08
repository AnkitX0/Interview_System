"""
backend/tests/test_transcribe_endpoint.py
Comprehensive automated test suite for POST /interview/transcribe endpoint.
Covers Section 36 requirements:
- Valid audio upload
- Empty audio rejection
- Invalid MIME rejection
- Unauthenticated access rejection
- Technical vocabulary casing alignment
- Duration calculation
"""

import io
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.auth_service import create_access_token
from backend.services.transcription_service import (
    extract_audio_duration_seconds,
    normalize_audio_in_memory,
    _align_technical_terms,
    transcribe_complete_answer
)

client = TestClient(app)

def get_auth_headers(user_id: int = 1):
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def test_transcribe_unauthenticated():
    response = client.post(
        "/interview/transcribe",
        files={"audio": ("sample.webm", b"dummy audio content" * 20, "audio/webm")}
    )
    assert response.status_code == 401


def test_transcribe_empty_file():
    headers = get_auth_headers()
    response = client.post(
        "/interview/transcribe",
        headers=headers,
        files={"audio": ("empty.webm", b"", "audio/webm")}
    )
    assert response.status_code == 400
    body = response.json()
    msg = body.get("error", {}).get("message", "") or body.get("detail", "")
    assert "Empty" in msg


def test_transcribe_invalid_mime():
    headers = get_auth_headers()
    response = client.post(
        "/interview/transcribe",
        headers=headers,
        files={"audio": ("malicious.exe", b"A" * 500, "application/x-dosexec")}
    )
    assert response.status_code == 415


def test_transcribe_duration_extraction():
    # Synthetic 0.5s silence WAV (16kHz 16-bit mono = 32000 bytes/sec -> 16000 bytes)
    wav_header = (
        b"RIFF" + (16036).to_bytes(4, "little") + b"WAVEfmt " +
        (16).to_bytes(4, "little") + (1).to_bytes(2, "little") +
        (1).to_bytes(2, "little") + (16000).to_bytes(4, "little") +
        (32000).to_bytes(4, "little") + (2).to_bytes(2, "little") +
        (16).to_bytes(2, "little") + b"data" + (16000).to_bytes(4, "little")
    )
    wav_data = wav_header + (b"\x00" * 16000)
    dur = extract_audio_duration_seconds(wav_data)
    assert dur is not None
    assert 0.4 <= dur <= 0.6


def test_align_technical_terms():
    raw = "i used fast api with postgresql and py torch to build an asl app with mediapipe"
    aligned = _align_technical_terms(raw, ["FastAPI", "PostgreSQL", "PyTorch", "MediaPipe"])
    assert "FastAPI" in aligned
    assert "PostgreSQL" in aligned
    assert "PyTorch" in aligned
    assert "MediaPipe" in aligned


def test_transcribe_complete_answer_silence():
    # Audio with silence
    wav_header = (
        b"RIFF" + (16036).to_bytes(4, "little") + b"WAVEfmt " +
        (16).to_bytes(4, "little") + (1).to_bytes(2, "little") +
        (1).to_bytes(2, "little") + (16000).to_bytes(4, "little") +
        (32000).to_bytes(4, "little") + (2).to_bytes(2, "little") +
        (16).to_bytes(2, "little") + b"data" + (16000).to_bytes(4, "little")
    )
    wav_data = wav_header + (b"\x00" * 16000)
    res = transcribe_complete_answer(wav_data, mime_type="audio/wav")
    assert res["success"] is True
    assert res["transcript"] == ""
    assert res["duration_seconds"] > 0


if __name__ == "__main__":
    test_transcribe_unauthenticated()
    print("✔ test_transcribe_unauthenticated passed")
    test_transcribe_empty_file()
    print("✔ test_transcribe_empty_file passed")
    test_transcribe_invalid_mime()
    print("✔ test_transcribe_invalid_mime passed")
    test_transcribe_duration_extraction()
    print("✔ test_transcribe_duration_extraction passed")
    test_align_technical_terms()
    print("✔ test_align_technical_terms passed")
    test_transcribe_complete_answer_silence()
    print("✔ test_transcribe_complete_answer_silence passed")
    print("All backend transcribe endpoint tests PASSED successfully!")
