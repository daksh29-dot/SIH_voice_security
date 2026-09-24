"""
tests/test_phase4_pipeline.py

Automated test suite for Project VISOR Phase 4:
- backend/nlp/transcription.py (faster-whisper ASR, UtteranceAccumulator, AsyncASRWorker)
- backend/nlp/scam_intent.py (Rule-boosted telecom fraud & social engineering classifier)
- backend/api/websocket.py (Phase 4 WebSocket integration with ASR and NLP intent scoring)
"""

import time
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from backend.nlp.transcription import (
    WhisperTranscriber,
    UtteranceAccumulator,
    AsyncASRWorker,
    get_whisper_transcriber,
)
from backend.nlp.scam_intent import ScamIntentClassifier, get_scam_classifier
from backend.api.websocket import app


# ─────────────────────────────────────────────────────────────────────────────
# 1. ASR & Utterance Accumulator Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_whisper_transcription():
    transcriber = get_whisper_transcriber()
    # Load sample real speech
    audio, sr = sf.read("test_audio/real/LA_E_1027220.flac")
    result = transcriber.transcribe(audio, sample_rate=sr)

    assert "transcript" in result
    assert "duration" in result
    assert "latency_ms" in result
    assert len(result["transcript"]) > 0
    assert result["duration"] > 1.0


def test_utterance_accumulator_600ms_boundary_trigger():
    accumulator = UtteranceAccumulator(
        sample_rate=16000,
        silence_boundary_ms=600.0,
        min_speech_ms=400.0,
    )

    # 1. Feed 800ms of active speech in 100ms (1600-sample) chunks
    speech_chunk = np.ones(1600, dtype=np.float32)
    for _ in range(8):
        completed = accumulator.process_frame(speech_chunk, is_speech=True)
        assert completed is None

    # 2. Feed 500ms of silence (5 x 100ms) -> should NOT trigger yet (< 600ms)
    silence_chunk = np.zeros(1600, dtype=np.float32)
    for _ in range(5):
        completed = accumulator.process_frame(silence_chunk, is_speech=False)
        assert completed is None

    # 3. 6th chunk reaches 600ms boundary (500ms + 100ms = 600ms) -> boundary triggered!
    completed = accumulator.process_frame(silence_chunk, is_speech=False)
    assert completed is not None
    # Completed audio contains speech + short trailing padding
    assert len(completed) >= 8 * 1600


# ─────────────────────────────────────────────────────────────────────────────
# 2. Social Engineering Intent Classifier Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_intent_urgent_financial_transfer():
    classifier = get_scam_classifier()
    text = "Your account is frozen! You must make an urgent transfer to the safety account immediately."
    res = classifier.classify(text)

    assert res["is_threat"] is True
    assert res["semantic_threat_score"] >= 0.65
    assert "Urgent Financial Transfer Pressure" in res["triggered_intents"]
    assert any("frozen" in p or "urgent transfer" in p for p in res["flagged_phrases"])


def test_intent_credential_otp_harvesting():
    classifier = get_scam_classifier()
    text = "This is verification. Please read back the OTP sent to your mobile and confirm your passcode."
    res = classifier.classify(text)

    assert res["is_threat"] is True
    assert res["semantic_threat_score"] >= 0.70
    assert "Credential & OTP Harvesting" in res["triggered_intents"]
    assert any("otp" in p.lower() for p in res["flagged_phrases"])


def test_intent_authority_impersonation():
    classifier = get_scam_classifier()
    text = "I am the director of police department. Do not verify with anyone else under digital arrest."
    res = classifier.classify(text)

    assert res["is_threat"] is True
    assert res["semantic_threat_score"] >= 0.80
    assert "Authority & Executive Impersonation" in res["triggered_intents"]
    assert res["severity"] == "CRITICAL"


def test_intent_benign_conversation():
    classifier = get_scam_classifier()
    text = "Hey are we still meeting for lunch at 1pm? Let me know if you want pizza."
    res = classifier.classify(text)

    assert res["is_threat"] is False
    assert res["semantic_threat_score"] <= 0.15
    assert len(res["triggered_intents"]) == 0
    assert len(res["flagged_phrases"]) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Pipeline Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_websocket_phase4_nlp_streaming_payload():
    client = TestClient(app)

    with client.websocket_connect("/ws/audio") as ws:
        # Send silence chunk
        ws.send_bytes(bytes(1600 * 2))
        r = ws.receive_json()

        assert "status" in r
        assert "acoustic_spoof_risk" in r
        assert "semantic_threat_score" in r
        assert "transcript" in r
        assert "triggered_intents" in r
        assert "flagged_phrases" in r
        assert "vad_active" in r
        assert r["vad_active"] is False


def test_api_classify_intent_endpoint():
    client = TestClient(app)
    payload = {
        "text": "Wire the money right now, I am the inspector of CBI. Do not verify with anyone."
    }
    res = client.post("/api/nlp/classify-intent", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_threat"] is True
    assert data["semantic_threat_score"] >= 0.80
    assert len(data["triggered_intents"]) >= 2
