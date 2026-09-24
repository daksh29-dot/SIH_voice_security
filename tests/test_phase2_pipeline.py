"""
tests/test_phase2_pipeline.py

Automated test suite for Project VISOR Phase 2:
- backend/models/opensmile_features.py (OpenSMILE prosody extraction & anomaly scoring)
- backend/models/speaker_encoder.py (SpeechBrain ECAPA-TDNN speaker verification)
- backend/api/websocket.py (Updated WebSocket streaming with prosody & biometrics)
"""

import io
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from backend.models.opensmile_features import OpenSMILEProsodyExtractor, get_prosody_extractor
from backend.models.speaker_encoder import SpeakerEncoder, get_speaker_encoder
from backend.api.websocket import app


# ─────────────────────────────────────────────────────────────────────────────
# 1. OpenSMILE Prosodic Feature Extraction Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_opensmile_features_keys_and_values():
    extractor = get_prosody_extractor()
    # 3 seconds of synthetic audio
    audio = (np.sin(2 * np.pi * 220 * np.linspace(0, 3, 48000)) * 0.5).astype(np.float32)

    result = extractor.extract_features(audio)
    assert "features" in result
    assert "prosody_anomaly_score" in result
    assert "is_anomalous" in result

    features = result["features"]
    required_keys = [
        "f0_mean", "f0_variance", "f0_std", "f0_delta_mean",
        "jitter_local", "shimmer_local",
        "loudness_mean", "loudness_std", "log_energy",
        "hnr_mean", "voiced_fraction"
    ]
    for key in required_keys:
        assert key in features, f"Missing required feature key: {key}"

    assert 0.0 <= result["prosody_anomaly_score"] <= 1.0


def test_opensmile_empty_signal_handling():
    extractor = get_prosody_extractor()
    result = extractor.extract_features(np.empty(0, dtype=np.float32))
    assert result["prosody_anomaly_score"] == 0.0
    assert result["features"]["f0_mean"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Speaker Encoder (ECAPA-TDNN) Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_speaker_encoder_embedding_shape_and_unit_norm():
    encoder = get_speaker_encoder()
    audio = np.random.uniform(-0.1, 0.1, 16000).astype(np.float32)

    embedding = encoder.extract_embedding(audio)
    assert embedding.shape == (192,)
    assert abs(np.linalg.norm(embedding) - 1.0) < 1e-4


def test_speaker_enrollment_and_verification():
    encoder = get_speaker_encoder()
    audio = np.random.uniform(-0.2, 0.2, 16000).astype(np.float32)
    speaker_id = "test_unit_speaker_99"

    # Enroll
    ref_emb = encoder.enroll_speaker(speaker_id, audio)
    assert speaker_id in encoder.enrolled_speakers
    assert np.array_equal(encoder.enrolled_speakers[speaker_id], ref_emb)

    # Verify identical audio
    res = encoder.verify_speaker(speaker_id, audio)
    assert res["is_match"] is True
    assert res["similarity"] >= 0.99
    assert res["speaker_consistency_score"] >= 0.99


def test_speaker_verification_unregistered():
    encoder = get_speaker_encoder()
    audio = np.zeros(8000, dtype=np.float32)
    res = encoder.verify_speaker("non_existent_user_xyz", audio)
    assert res["is_match"] is False
    assert res["similarity"] == 0.0
    assert "error" in res


# ─────────────────────────────────────────────────────────────────────────────
# 3. WebSocket Phase 2 Streaming & Endpoints Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_websocket_phase2_payload():
    client = TestClient(app)

    with client.websocket_connect("/ws/audio") as ws:
        # Send silent frame
        ws.send_bytes(bytes(1600 * 2))
        r = ws.receive_json()

        assert "status" in r
        assert "w2v2_score" in r
        assert "prosody_anomaly_score" in r
        assert "speaker_similarity" in r
        assert "speaker_consistency_score" in r
        assert "speaker_match" in r
        assert "vad_active" in r
        assert r["vad_active"] is False


def test_api_speakers_endpoints():
    client = TestClient(app)

    # GET /api/speakers
    res = client.get("/api/speakers")
    assert res.status_code == 200
    assert "enrolled_speakers" in res.json()

    # POST /api/speakers/enroll
    wav_bytes = io.BytesIO()
    dummy_wav = np.random.uniform(-0.1, 0.1, 16000).astype(np.float32)
    sf.write(wav_bytes, dummy_wav, 16000, format="WAV")
    wav_bytes.seek(0)

    res_enroll = client.post(
        "/api/speakers/enroll",
        data={"speaker_id": "api_test_speaker"},
        files={"audio_file": ("test.wav", wav_bytes.getvalue(), "audio/wav")},
    )
    assert res_enroll.status_code == 200
    assert res_enroll.json()["success"] is True
    assert res_enroll.json()["embedding_dim"] == 192
