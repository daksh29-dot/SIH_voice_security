"""
backend/models/opensmile_features.py

Physical prosodic feature extraction using OpenSMILE for Project VISOR.
Extracts targeted, low-latency prosody vectors from rolling audio buffers:
  - F0 (fundamental frequency) contour mean, variance, and delta
  - Jitter (local) and Shimmer (local)
  - Logarithmic energy / Loudness statistics
  - Voice quality / Harmonics-to-Noise Ratio (HNR)
Computes a normalized `prosody_anomaly_score` (0.0 to 1.0) flagging unnatural
pitch flatness or robotic micro-stability typical of synthetic speech.
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np
import opensmile


class OpenSMILEProsodyExtractor:
    """
    Targeted prosodic feature extractor for Project VISOR using OpenSMILE.
    Derives essential acoustic prosody features without the overhead of heavy 88-feature sets.
    """

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

        # Initialize lightweight GeMAPSv01b LowLevelDescriptors
        # This extracts F0, jitter, shimmer, loudness, and HNR directly
        self.smile = opensmile.Smile(
            feature_set=opensmile.FeatureSet.GeMAPSv01b,
            feature_level=opensmile.FeatureLevel.LowLevelDescriptors,
            sampling_rate=sample_rate,
        )

    def extract_features(
        self,
        audio_buffer: np.ndarray,
        sample_rate: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Extract physical prosodic feature vector from an audio buffer.

        Args:
            audio_buffer: 1D float32 numpy array (e.g. 3-second buffer at 16kHz)
            sample_rate: Optional sample rate override (defaults to self.sample_rate)

        Returns:
            Dict[str, Any]:
                - "features": dict of raw acoustic metrics (F0, Jitter, Shimmer, Loudness, HNR)
                - "prosody_anomaly_score": float in [0.0, 1.0]
                - "is_anomalous": bool
        """
        sr = sample_rate or self.sample_rate
        audio = np.asarray(audio_buffer, dtype=np.float32).flatten()

        if len(audio) == 0:
            return self._empty_result()

        try:
            lld_df = self.smile.process_signal(audio, sr)
        except Exception:
            # Fallback if signal is too short or all-zeros
            return self._empty_result()

        if lld_df is None or lld_df.empty:
            return self._empty_result()

        # ── 1. Fundamental Frequency (F0) Contour ──────────────────────────
        # OpenSMILE GeMAPS reports F0 in semitones relative to 27.5 Hz (0 for unvoiced)
        f0_st = lld_df["F0semitoneFrom27.5Hz_sma3nz"].values
        voiced_mask = f0_st > 0
        voiced_count = int(np.sum(voiced_mask))
        total_frames = len(f0_st)
        voiced_fraction = voiced_count / max(1, total_frames)

        if voiced_count > 2:
            # Convert semitones back to Hz: F0_hz = 27.5 * 2^(st / 12)
            f0_hz = 27.5 * (2.0 ** (f0_st[voiced_mask] / 12.0))
            f0_mean = float(np.mean(f0_hz))
            f0_variance = float(np.var(f0_hz))
            f0_std = float(np.std(f0_hz))

            f0_diff = np.diff(f0_hz)
            f0_delta_mean = float(np.mean(np.abs(f0_diff))) if len(f0_diff) > 0 else 0.0
            f0_delta_variance = float(np.var(f0_diff)) if len(f0_diff) > 0 else 0.0
        else:
            f0_mean = 0.0
            f0_variance = 0.0
            f0_std = 0.0
            f0_delta_mean = 0.0
            f0_delta_variance = 0.0

        # ── 2. Jitter and Shimmer ──────────────────────────────────────────
        if voiced_count > 2:
            jitter_vals = lld_df["jitterLocal_sma3nz"].values[voiced_mask]
            shimmer_vals = lld_df["shimmerLocaldB_sma3nz"].values[voiced_mask]

            jitter_local = float(np.mean(jitter_vals)) if len(jitter_vals) > 0 else 0.0
            shimmer_local = float(np.mean(shimmer_vals)) if len(shimmer_vals) > 0 else 0.0
        else:
            jitter_local = 0.0
            shimmer_local = 0.0

        # ── 3. Loudness / Log Energy Statistics ─────────────────────────────
        loudness_vals = lld_df["Loudness_sma3"].values
        loudness_mean = float(np.mean(loudness_vals)) if len(loudness_vals) > 0 else 0.0
        loudness_std = float(np.std(loudness_vals)) if len(loudness_vals) > 0 else 0.0
        loudness_max = float(np.max(loudness_vals)) if len(loudness_vals) > 0 else 0.0

        # Overall RMS log energy
        rms = float(np.sqrt(np.mean(np.square(audio))))
        log_energy = float(np.log(max(rms, 1e-7)))

        # ── 4. Voice Quality / Harmonics-to-Noise Ratio (HNR) ───────────────
        if voiced_count > 2:
            hnr_vals = lld_df["HNRdBACF_sma3nz"].values[voiced_mask]
            hnr_mean = float(np.mean(hnr_vals)) if len(hnr_vals) > 0 else 0.0
            hnr_std = float(np.std(hnr_vals)) if len(hnr_vals) > 0 else 0.0
        else:
            hnr_mean = 0.0
            hnr_std = 0.0

        raw_features = {
            "f0_mean": round(f0_mean, 2),
            "f0_variance": round(f0_variance, 2),
            "f0_std": round(f0_std, 2),
            "f0_delta_mean": round(f0_delta_mean, 2),
            "f0_delta_variance": round(f0_delta_variance, 2),
            "jitter_local": round(jitter_local, 5),
            "shimmer_local": round(shimmer_local, 4),
            "loudness_mean": round(loudness_mean, 4),
            "loudness_std": round(loudness_std, 4),
            "loudness_max": round(loudness_max, 4),
            "log_energy": round(log_energy, 4),
            "hnr_mean": round(hnr_mean, 2),
            "hnr_std": round(hnr_std, 2),
            "voiced_fraction": round(voiced_fraction, 3),
        }

        # ── 5. Prosody Anomaly Score ────────────────────────────────────────
        anomaly_score = self._compute_prosody_anomaly(
            f0_std=f0_std,
            f0_delta_mean=f0_delta_mean,
            jitter_local=jitter_local,
            shimmer_local=shimmer_local,
            voiced_fraction=voiced_fraction,
        )

        return {
            "features": raw_features,
            "prosody_anomaly_score": round(anomaly_score, 4),
            "is_anomalous": anomaly_score >= 0.60,
        }

    def _compute_prosody_anomaly(
        self,
        f0_std: float,
        f0_delta_mean: float,
        jitter_local: float,
        shimmer_local: float,
        voiced_fraction: float,
    ) -> float:
        """
        Flag unnatural pitch flatness or robotic micro-stability typical of synthetic speech.

        Human vocal characteristics:
          - Natural pitch variation (F0 std: 15Hz - 45Hz)
          - Natural micro-tremor (Jitter: 0.008 - 0.025)
          - Dynamic contour transitions (F0 delta mean > 1.5 Hz)

        Synthetic / Clone indicators:
          - Extremely flat pitch contour (F0 std < 8 Hz)
          - Robotic micro-stability (Jitter < 0.004)
          - Low contour dynamism (F0 delta mean < 0.8 Hz)
        """
        if voiced_fraction < 0.15:
            # Insufficient voiced content to evaluate prosody reliably
            return 0.10

        penalties = []

        # 1. Pitch Flatness Check:
        # Typical expressive speech has F0 std >= 16 Hz. F0 std < 8 Hz indicates monotonic TTS.
        if f0_std < 6.0:
            penalties.append(0.85)
        elif f0_std < 10.0:
            penalties.append(0.55 + (10.0 - f0_std) * 0.075)
        elif f0_std < 16.0:
            penalties.append(0.20 + (16.0 - f0_std) * 0.05)
        else:
            penalties.append(0.05)

        # 2. Robotic Micro-Stability (Jitter Flatline):
        # Pure synthetic vocoders often lack natural glottal jitter.
        if jitter_local < 0.003:
            penalties.append(0.80)
        elif jitter_local < 0.006:
            penalties.append(0.50 + (0.006 - jitter_local) * 100)
        elif jitter_local > 0.05:
            # Excessively high artificial glitch
            penalties.append(0.60)
        else:
            penalties.append(0.05)

        # 3. Contour Dynamism (F0 delta velocity):
        if f0_delta_mean < 0.6:
            penalties.append(0.75)
        elif f0_delta_mean < 1.2:
            penalties.append(0.40)
        else:
            penalties.append(0.05)

        # Weighted combination of prosody anomaly indicators
        raw_anomaly = float(np.average(penalties, weights=[0.45, 0.35, 0.20]))
        return max(0.0, min(1.0, raw_anomaly))

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "features": {
                "f0_mean": 0.0,
                "f0_variance": 0.0,
                "f0_std": 0.0,
                "f0_delta_mean": 0.0,
                "f0_delta_variance": 0.0,
                "jitter_local": 0.0,
                "shimmer_local": 0.0,
                "loudness_mean": 0.0,
                "loudness_std": 0.0,
                "loudness_max": 0.0,
                "log_energy": -16.0,
                "hnr_mean": 0.0,
                "hnr_std": 0.0,
                "voiced_fraction": 0.0,
            },
            "prosody_anomaly_score": 0.0,
            "is_anomalous": False,
        }


# Global shared instance
_global_prosody_extractor: Optional[OpenSMILEProsodyExtractor] = None


def get_prosody_extractor() -> OpenSMILEProsodyExtractor:
    """Retrieve or initialize the global shared OpenSMILE prosody extractor."""
    global _global_prosody_extractor
    if _global_prosody_extractor is None:
        _global_prosody_extractor = OpenSMILEProsodyExtractor()
    return _global_prosody_extractor
