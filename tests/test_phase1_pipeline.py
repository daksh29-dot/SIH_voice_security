"""
tests/test_phase1_pipeline.py

Comprehensive unit and integration tests for Project VISOR Phase 1:
- backend/audio/preprocessing.py (validation, PCM conversion, energy checks)
- backend/audio/vad.py (Silero VAD ONNX speech detection)
- backend/audio/stream.py (thread-safe rolling FIFO buffer)
- backend/models/w2v2_aasist.py (W2V2-AASIST ONNX inference wrapper)
- backend/api/websocket.py (FastAPI WebSocket streaming endpoint)
"""

import threading
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.audio.preprocessing import (
    AudioPreprocessor,
    validate_and_convert_chunk,
    check_audio_energy,
)
from backend.audio.vad import SileroVAD
from backend.audio.stream import RollingAudioBuffer
from backend.models.w2v2_aasist import (
    W2V2AASISTModel,
    W2V2AASISTPrediction,
    get_w2v2_aasist_model,
)
from backend.api.websocket import app


# ─────────────────────────────────────────────────────────────────────────────
# 1. Preprocessing Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_preprocessing_pcm_conversion():
    preprocessor = AudioPreprocessor(target_sample_rate=16000)
    # Generate 1600 samples (0.1s at 16kHz) of int16 PCM
    original_floats = np.sin(np.linspace(0, 100, 1600)).astype(np.float32) * 0.8
    int16_pcm = (original_floats * 32767).astype(np.int16).tobytes()

    converted, is_valid, info = preprocessor.process_chunk(int16_pcm, input_sr=16000)
    assert is_valid is True
    assert converted.dtype == np.float32
    assert len(converted) == 1600
    assert np.max(np.abs(converted)) <= 1.0
    assert abs(info["rms"] - np.sqrt(np.mean(original_floats**2))) < 0.05


def test_preprocessing_empty_and_silence_detection():
    preprocessor = AudioPreprocessor(target_sample_rate=16000)

    # Empty chunk
    _, is_valid_empty, info_empty = preprocessor.process_chunk(b"")
    assert is_valid_empty is False
    assert info_empty["reason"] == "EMPTY_FRAME"

    # Silent chunk (zeros)
    silent_pcm = bytes(1600 * 2)
    _, is_valid_silent, info_silent = preprocessor.process_chunk(silent_pcm)
    assert is_valid_silent is False
    assert info_silent["reason"] == "SILENT_FRAME"


def test_preprocessing_stereo_to_mono():
    preprocessor = AudioPreprocessor(target_sample_rate=16000)
    # Stereo array: shape (2, 1000)
    left = np.full(1000, 0.4, dtype=np.float32)
    right = np.full(1000, 0.6, dtype=np.float32)
    stereo = np.stack([left, right], axis=0)

    mono = preprocessor.to_mono(stereo)
    assert mono.shape == (1000,)
    assert np.allclose(mono, 0.5, atol=1e-5)


def test_preprocessing_resampling():
    preprocessor = AudioPreprocessor(target_sample_rate=16000)
    # 44100Hz 1-second audio
    t = np.linspace(0, 1.0, 44100, endpoint=False)
    audio_44k = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)

    resampled, is_valid, info = preprocessor.process_chunk(audio_44k, input_sr=44100)
    assert is_valid is True
    assert len(resampled) == 16000
    assert resampled.dtype == np.float32


# ─────────────────────────────────────────────────────────────────────────────
# 2. Silero VAD Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_silero_vad_silence_suppression():
    vad = SileroVAD(threshold=0.5)
    # 0.5s of absolute silence (8000 samples)
    silence = np.zeros(8000, dtype=np.float32)
    is_sp, prob = vad.is_speech(silence)
    assert is_sp is False
    assert prob < 0.1


def test_silero_vad_resets_state():
    vad = SileroVAD()
    assert vad._state.shape == (2, 1, 128)
    assert vad._context.shape == (1, 64)

    # Modify state and verify reset
    vad._state.fill(1.0)
    vad.reset_states()
    assert np.all(vad._state == 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Rolling Buffer Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_rolling_buffer_accumulation_and_step():
    # 3-second window (48,000 samples), 500ms step (8,000 samples)
    buf = RollingAudioBuffer(
        sample_rate=16000,
        window_duration_sec=3.0,
        step_duration_sec=0.5,
    )
    assert buf.window_samples == 48000
    assert buf.step_samples == 8000

    chunk = np.ones(8000, dtype=np.float32)

    # Push 5 chunks (40,000 samples) -> not yet full (need 48,000)
    for _ in range(5):
        ready = buf.push(chunk)
        assert ready is False

    # Push 6th chunk -> 48,000 samples reached!
    ready = buf.push(chunk)
    assert ready is True
    assert buf.is_ready() is True

    window = buf.get_window()
    assert len(window) == 48000
    # After get_window(), accumulator is reset: not ready until another 8,000 samples arrive
    assert buf.is_ready() is False

    # Push another 8,000 samples -> ready again
    ready2 = buf.push(chunk)
    assert ready2 is True


def test_rolling_buffer_thread_safety():
    buf = RollingAudioBuffer(sample_rate=16000, window_duration_sec=1.0, step_duration_sec=0.2)
    chunk = np.ones(500, dtype=np.float32)

    def worker():
        for _ in range(50):
            buf.push(chunk)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Total samples ingested: 4 * 50 * 500 = 100,000 samples
    assert buf.stats()["total_samples_ingested"] == 100000
    # Buffer capacity caps at 16,000 samples
    assert buf.current_samples == 16000


# ─────────────────────────────────────────────────────────────────────────────
# 4. W2V2-AASIST Model Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_w2v2_aasist_prediction_output():
    model = get_w2v2_aasist_model()
    # Provide 3-second buffer (48,000 samples); wrapper should zero-pad to 64,600
    synthetic_buffer = np.random.uniform(-0.1, 0.1, 48000).astype(np.float32)
    pred = model.predict(synthetic_buffer)

    assert isinstance(pred, W2V2AASISTPrediction)
    assert isinstance(pred.raw_logits, tuple)
    assert len(pred.raw_logits) == 2
    assert 0.0 <= pred.spoof_score <= 1.0
    assert 0.0 <= pred.bona_fide_score <= 1.0
    assert abs((pred.spoof_score + pred.bona_fide_score) - 1.0) < 1e-4
    assert pred.inference_time_ms > 0.0

    d = pred.to_dict()
    assert "raw_logits" in d
    assert "spoof_score" in d
    assert "inference_time_ms" in d


# ─────────────────────────────────────────────────────────────────────────────
# 5. FastAPI WebSocket Endpoint Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_websocket_silent_frame_handling():
    client = TestClient(app)
    with client.websocket_connect("/ws/audio") as ws:
        # Send 0.1s of silence (1600 samples * 2 bytes = 3200 bytes)
        silent_chunk = bytes(1600 * 2)
        ws.send_bytes(silent_chunk)
        response = ws.receive_json()

        assert response["status"] in ("ANALYZING", "INSUFFICIENT AUDIO")
        assert response["vad_active"] is False
        assert isinstance(response["w2v2_score"], float)
        assert isinstance(response["latency_ms"], float)


def test_websocket_reset_command():
    client = TestClient(app)
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_text('{"command": "reset"}')
        response = ws.receive_json()
        assert response["status"] == "RESET_ACK"
        assert response["vad_active"] is False


def test_websocket_health_and_status():
    client = TestClient(app)
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "HEALTHY"

    res_status = client.get("/ws/status")
    assert res_status.status_code == 200
    assert res_status.json()["target_sample_rate"] == 16000
