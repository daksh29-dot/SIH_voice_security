"""Decode actual media; no denoising, VAD splicing, or unconditional gain change."""
import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly
try:
    from .config import DEFAULTS
except ImportError:
    from config import DEFAULTS

class AudioLoadError(ValueError):
    pass

def _run(args):
    try:
        return subprocess.run(args, check=True, capture_output=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise AudioLoadError("Audio decoding failed; install FFmpeg/ffprobe and supply a complete recording") from exc

def load_audio(path, max_seconds=DEFAULTS.max_file_seconds):
    if not np.isfinite(max_seconds) or max_seconds <= 0:
        raise AudioLoadError("max_seconds must be positive and finite")
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise AudioLoadError("Expected a local audio file")
    info = json.loads(_run(["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe",
                           "-select_streams", "a:0", "-show_entries", "stream=sample_rate",
                           "-of", "json", str(path)]))
    try:
        sr = int(info["streams"][0]["sample_rate"])
    except (KeyError, IndexError, ValueError) as exc:
        raise AudioLoadError("No valid audio stream") from exc
    if not 8000 <= sr <= 192000:
        raise AudioLoadError(f"Unsupported source rate: {sr}")
    # Decode at the real native rate. -ac 1 uses FFmpeg's defined mono downmix.
    raw = _run(["ffmpeg", "-nostdin", "-v", "error", "-protocol_whitelist", "file,pipe",
                "-i", str(path), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", str(sr),
                "-t", str(max_seconds + 1), "-f", "f32le", "pipe:1"])
    x = np.frombuffer(raw, dtype="<f4").copy()
    if len(x) > max_seconds * sr:
        raise AudioLoadError(f"Recording exceeds {max_seconds}s limit; process it in bounded sessions")
    return validate_waveform(x), sr

def validate_waveform(x):
    x = np.asarray(x)
    if x.ndim != 1 or x.size == 0:
        raise AudioLoadError("Expected non-empty mono waveform")
    if x.dtype.kind != "f":
        raise AudioLoadError("Expected floating PCM; convert int16 using /32768.0 first")
    if not np.isfinite(x).all():
        raise AudioLoadError("Waveform contains NaN/Inf")
    if np.max(np.abs(x)) > 1.5:
        raise AudioLoadError("Unexpected amplitude; check integer-to-float scaling")
    return np.ascontiguousarray(x, dtype=np.float32)

def resample(x, orig_sr, target_sr=16000):
    x = validate_waveform(x)
    if not isinstance(orig_sr, (int, np.integer)) or not 8000 <= orig_sr <= 192000:
        raise AudioLoadError("Supply the actual integer source sample rate")
    if not isinstance(target_sr, (int, np.integer)) or not 8000 <= target_sr <= 192000:
        raise AudioLoadError("Invalid target sample rate")
    if orig_sr == target_sr:
        return x
    g = math.gcd(orig_sr, target_sr)
    return resample_poly(x, target_sr // g, orig_sr // g).astype(np.float32)

def normalize(x, mode="none"):
    x = validate_waveform(x)
    if mode == "none":
        return x
    if mode == "peak":
        return (x / max(float(np.max(np.abs(x))), 1e-8)).astype(np.float32)
    if mode == "zscore":
        return ((x - x.mean()) / np.sqrt(x.var() + 1e-7)).astype(np.float32)
    raise ValueError("Unknown normalization")

def preprocess_audio(path, settings=DEFAULTS):
    x, sr = load_audio(path, settings.max_file_seconds)
    # Normalization is intentionally per model window, after quality measurement.
    x = resample(x, sr, settings.sample_rate)
    return x

@dataclass
class Quality:
    rms_dbfs: float
    clipped_fraction: float
    speech_seconds: float
    speech_fraction: float
    reasons: list[str]

class SpeechGate:
    def __init__(self, settings=DEFAULTS):
        try:
            import webrtcvad
        except ImportError as exc:
            raise RuntimeError("Install webrtcvad-wheels; there is no silent energy-only fallback") from exc
        self.vad_factory = webrtcvad.Vad
        self.settings = settings

    def check(self, waveform):
        x = validate_waveform(waveform)
        cfg = self.settings
        # Stateful VAD must start fresh for each independently scored window.
        vad = self.vad_factory(cfg.vad_mode)
        rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
        db = float(20 * np.log10(max(rms, 1e-12)))
        clip = float(np.mean(np.abs(x) >= 0.999))
        # VAD sees a separate int16 copy. Detector receives the original waveform.
        pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
        frame_n = int(0.02 * cfg.sample_rate)
        frames = [pcm[i:i + frame_n] for i in range(0, len(pcm) - frame_n + 1, frame_n)]
        flags = [vad.is_speech(f.tobytes(), cfg.sample_rate) for f in frames]
        speech_s = sum(flags) * 0.02
        fraction = sum(flags) / max(len(flags), 1)
        reasons = []
        if db < cfg.min_rms_dbfs:
            reasons.append("too_quiet")
        if clip > cfg.max_clipped_fraction:
            reasons.append("excessive_clipping")
        if speech_s < cfg.min_speech_seconds or fraction < cfg.min_speech_fraction:
            reasons.append("insufficient_speech")
        return Quality(db, clip, speech_s, fraction, reasons)
