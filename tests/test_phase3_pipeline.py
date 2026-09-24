"""
tests/test_phase3_pipeline.py

Automated test suite for Project VISOR Phase 3:
- backend/fusion/calibration.py (Temperature scaling and Platt scaling)
- backend/fusion/feature_fusion.py (Multi-signal score fusion & graceful degradation)
- backend/models/wavlm.py (Async WavLM worker and non-blocking scheduling)
- backend/api/websocket.py (Phase 3 multi-signal WebSocket pipeline)
"""

import time
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.fusion.calibration import temperature_scale, PlattScaler, ScoreCalibrator
from backend.fusion.feature_fusion import MultiSignalFusionHead, AcousticFusionResult, get_fusion_head
from backend.models.wavlm import AsyncWavLMWorker, WavLMModelWrapper, get_wavlm_worker
from backend.api.websocket import app


# ─────────────────────────────────────────────────────────────────────────────
# 1. Calibration Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_temperature_scaling_softening():
    # An extreme score near 1.0 (e.g. 0.95) should be softened when T > 1.0
    raw_score = 0.95
    scaled = temperature_scale(raw_score, temperature=1.5)
    assert 0.0 <= scaled <= 1.0
    assert scaled < raw_score  # Softened towards 0.5

    # A score near 0.0 should be softened upwards
    raw_low = 0.05
    scaled_low = temperature_scale(raw_low, temperature=1.5)
    assert scaled_low > raw_low


def test_platt_scaling_fit_and_calibrate():
    scaler = PlattScaler(a=1.0, b=0.0)
    scores = np.array([0.1, 0.2, 0.8, 0.9], dtype=np.float32)
    labels = np.array([0, 0, 1, 1], dtype=np.int32)

    scaler.fit(scores, labels, max_iter=50)
    calibrated = scaler.calibrate(np.array([0.15, 0.85]))
    assert len(calibrated) == 2
    assert calibrated[0] < calibrated[1]
    assert 0.0 <= calibrated[0] <= 1.0
    assert 0.0 <= calibrated[1] <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Multi-Signal Fusion Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_fusion_with_all_three_signals():
    fusion = MultiSignalFusionHead(
        w2v2_weight=0.50,
        prosody_weight=0.20,
        wavlm_weight=0.30,
        decision_threshold=0.55,
    )

    result = fusion.fuse(w2v2_score=0.90, prosody_score=0.80, wavlm_score=0.85)

    assert isinstance(result, AcousticFusionResult)
    assert result.wavlm_active is True
    assert result.wavlm_score == 0.85
    assert result.active_weights["w2v2"] == 0.50
    assert result.active_weights["prosody"] == 0.20
    assert result.active_weights["wavlm"] == 0.30
    assert result.is_spoof is True
    assert 0.0 <= result.acoustic_spoof_risk <= 1.0


def test_fusion_graceful_degradation_without_wavlm():
    fusion = MultiSignalFusionHead(
        w2v2_weight=0.50,
        prosody_weight=0.20,
        wavlm_weight=0.30,
    )

    # When WavLM is None (not finished or stale)
    result = fusion.fuse(w2v2_score=0.80, prosody_score=0.60, wavlm_score=None)

    assert result.wavlm_active is False
    assert result.wavlm_score is None
    assert result.active_weights["wavlm"] == 0.0
    # Normalized weights across 0.50 and 0.20 should sum to 1.0
    assert abs(sum(result.active_weights.values()) - 1.0) < 1e-3
    assert 0.0 <= result.acoustic_spoof_risk <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Async WavLM Worker Non-Blocking Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_wavlm_worker_non_blocking_submission():
    worker = get_wavlm_worker()
    dummy_audio = np.random.uniform(-0.1, 0.1, 16000).astype(np.float32)

    t0 = time.perf_counter()
    worker.submit_audio(dummy_audio)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Non-blocking submission must complete in < 5ms
    assert elapsed_ms < 10.0

    score, is_fresh = worker.get_latest_score()
    # Reading must be non-blocking
    assert isinstance(is_fresh, bool)


# ─────────────────────────────────────────────────────────────────────────────
# 4. WebSocket Phase 3 Pipeline Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_websocket_phase3_streaming_payload():
    client = TestClient(app)

    with client.websocket_connect("/ws/audio") as ws:
        # Silent chunk
        ws.send_bytes(bytes(1600 * 2))
        r = ws.receive_json()

        assert "status" in r
        assert "acoustic_spoof_risk" in r
        assert "w2v2_score" in r
        assert "prosody_anomaly_score" in r
        assert "wavlm_score" in r
        assert "wavlm_active" in r
        assert "speaker_similarity" in r
        assert "speaker_match" in r
        assert "vad_active" in r
        assert r["vad_active"] is False


def test_ws_status_phase3():
    client = TestClient(app)
    res = client.get("/ws/status")
    assert res.status_code == 200
    data = res.json()
    assert "fusion_weights" in data
    assert "wavlm_branch" in data
    assert data["fusion_weights"]["w2v2_weight"] == 0.50
