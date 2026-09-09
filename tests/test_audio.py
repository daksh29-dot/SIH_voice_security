"""
tests/test_audio.py

Tests for audio_preprocessing.py and segment_audio.py using synthetic
audio, so these pass even before real test_audio/ files are collected.
"""

import numpy as np
import soundfile as sf
import pytest

import config
from audio_preprocessing import to_mono, resample, normalize, preprocess_audio
from segment_audio import pad_fixed, segment_waveform, segment_waveform_sliding


@pytest.fixture
def synthetic_wav(tmp_path):
    """Generate a 3-second, 22050 Hz stereo sine wave test file."""
    sr = 22050
    duration = 3.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
    stereo = np.stack([tone, tone])  # fake stereo

    path = tmp_path / "synthetic.wav"
    sf.write(str(path), stereo.T, sr)
    return path, sr, duration


def test_to_mono_collapses_channels():
    stereo = np.array([[1.0, 1.0], [-1.0, -1.0]], dtype=np.float32)  # 2 channels, 2 samples
    mono = to_mono(stereo)
    assert mono.shape == (2,)
    assert np.allclose(mono, [0.0, 0.0])


def test_to_mono_passthrough_for_mono_input():
    mono_in = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    assert np.array_equal(to_mono(mono_in), mono_in)


def test_resample_changes_length_proportionally():
    sr_in = 22050
    sr_out = 16000
    wav = np.random.uniform(-1, 1, sr_in).astype(np.float32)  # 1 second
    resampled = resample(wav, sr_in, sr_out)
    expected_len = sr_out
    assert abs(len(resampled) - expected_len) < 5  # allow small rounding difference


def test_resample_noop_when_rates_match():
    wav = np.random.uniform(-1, 1, 1000).astype(np.float32)
    assert np.array_equal(resample(wav, 16000, 16000), wav)


def test_normalize_peaks_at_one():
    wav = np.array([0.0, 2.0, -4.0, 1.0], dtype=np.float32)
    normed = normalize(wav)
    assert np.isclose(np.max(np.abs(normed)), 1.0)


def test_normalize_handles_silence():
    silence = np.zeros(100, dtype=np.float32)
    normed = normalize(silence)
    assert np.array_equal(normed, silence)  # should not raise / produce NaNs


def test_preprocess_audio_end_to_end(synthetic_wav):
    path, sr, duration = synthetic_wav
    wav = preprocess_audio(path)

    assert wav.ndim == 1
    expected_len = int(duration * config.TARGET_SAMPLE_RATE)
    assert abs(len(wav) - expected_len) < 10
    assert np.max(np.abs(wav)) <= 1.0 + 1e-6

def test_pad_fixed_truncates_long_audio():
    window = config.FIXED_WINDOW_SAMPLES
    wav = np.arange(window + 5000, dtype=np.float32)
    result = pad_fixed(wav, window)
    assert len(result) == window
    assert np.array_equal(result, wav[:window])

def test_pad_fixed_rejects_short_audio():
    """DIAGNOSTIC: short audio is now rejected rather than tile-repeated."""
    window = 1000
    wav = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    with pytest.raises(ValueError, match="too short"):
        pad_fixed(wav, window)


def test_pad_fixed_exact_length_passthrough():
    window = 500
    wav = np.random.uniform(-1, 1, window).astype(np.float32)
    result = pad_fixed(wav, window)
    assert np.array_equal(result, wav)


def test_pad_fixed_rejects_multi_dim_input():
    bad_wav = np.zeros((2, 1000), dtype=np.float32)
    with pytest.raises(ValueError):
        pad_fixed(bad_wav, 500)


def test_segment_waveform_baseline_returns_single_fixed_window(monkeypatch):
    monkeypatch.setattr(config, "USE_SLIDING_WINDOWS", False)
    wav = np.random.uniform(-1, 1, config.FIXED_WINDOW_SAMPLES * 3).astype(np.float32)
    segments = segment_waveform(wav)
    assert len(segments) == 1
    assert len(segments[0]) == config.FIXED_WINDOW_SAMPLES
    assert np.array_equal(segments[0], wav[:config.FIXED_WINDOW_SAMPLES])


def test_segment_waveform_sliding_multiple_windows(monkeypatch):
    monkeypatch.setattr(config, "USE_SLIDING_WINDOWS", True)
    window = config.FIXED_WINDOW_SAMPLES
    wav = np.random.uniform(-1, 1, window * 3).astype(np.float32)
    segments = segment_waveform_sliding(wav, window_samples=window, overlap_s=0.0)
    assert len(segments) == 3
    assert all(len(s) == window for s in segments)

def test_segment_waveform_sliding_short_audio_raises():
    """Sliding-window path falls back to pad_fixed() for short input, which now raises."""
    window = config.FIXED_WINDOW_SAMPLES
    wav = np.random.uniform(-1, 1, window // 2).astype(np.float32)
    with pytest.raises(ValueError, match="too short"):
        segment_waveform_sliding(wav, window_samples=window)