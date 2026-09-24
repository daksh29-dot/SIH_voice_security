"""
backend/fusion/feature_fusion.py

Multi-signal acoustic score fusion engine for Project VISOR.
Fuses heterogeneous deepfake detection signals:
  - W2V2-AASIST Acoustic Spoof Score (Weight: 0.50)
  - OpenSMILE Physical Prosody Anomaly Score (Weight: 0.20)
  - WavLM Masked Representation Score (Weight: 0.30)

Supports graceful degradation: if WavLM has not finished computing its representation,
dynamically normalizes weights across available signals (W2V2 + OpenSMILE) without latency penalty.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import numpy as np

from backend.fusion.calibration import ScoreCalibrator


@dataclass
class AcousticFusionResult:
    """Consolidated multi-signal acoustic assessment result."""
    acoustic_spoof_risk: float
    is_spoof: bool
    confidence: float
    w2v2_score: float
    calibrated_w2v2: float
    prosody_score: float
    calibrated_prosody: float
    wavlm_score: Optional[float]
    calibrated_wavlm: Optional[float]
    wavlm_active: bool
    active_weights: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "acoustic_spoof_risk": float(self.acoustic_spoof_risk),
            "is_spoof": bool(self.is_spoof),
            "confidence": float(self.confidence),
            "w2v2_score": float(self.w2v2_score),
            "calibrated_w2v2": float(self.calibrated_w2v2),
            "prosody_score": float(self.prosody_score),
            "calibrated_prosody": float(self.calibrated_prosody),
            "wavlm_score": float(self.wavlm_score) if self.wavlm_score is not None else None,
            "calibrated_wavlm": float(self.calibrated_wavlm) if self.calibrated_wavlm is not None else None,
            "wavlm_active": bool(self.wavlm_active),
            "active_weights": self.active_weights,
        }


class MultiSignalFusionHead:
    """
    Calibrated multi-signal score fusion head for Project VISOR.
    Combines calibrated acoustic probabilities with dynamic graceful degradation.
    """

    DEFAULT_W2V2_WEIGHT = 0.50
    DEFAULT_PROSODY_WEIGHT = 0.20
    DEFAULT_WAVLM_WEIGHT = 0.30
    DEFAULT_DECISION_THRESHOLD = 0.55

    def __init__(
        self,
        w2v2_weight: float = DEFAULT_W2V2_WEIGHT,
        prosody_weight: float = DEFAULT_PROSODY_WEIGHT,
        wavlm_weight: float = DEFAULT_WAVLM_WEIGHT,
        decision_threshold: float = DEFAULT_DECISION_THRESHOLD,
        calibrator: Optional[ScoreCalibrator] = None,
    ):
        self.w2v2_weight = w2v2_weight
        self.prosody_weight = prosody_weight
        self.wavlm_weight = wavlm_weight
        self.decision_threshold = decision_threshold
        self.calibrator = calibrator or ScoreCalibrator()

    def fuse(
        self,
        w2v2_score: float,
        prosody_score: float,
        wavlm_score: Optional[float] = None,
    ) -> AcousticFusionResult:
        """
        Fuse individual acoustic scores into a unified acoustic_spoof_risk.

        Args:
            w2v2_score: Raw W2V2-AASIST spoof probability [0.0, 1.0]
            prosody_score: Raw OpenSMILE prosody anomaly score [0.0, 1.0]
            wavlm_score: Optional secondary WavLM spoof score [0.0, 1.0].
                         If None (e.g. background worker hasn't finished), falls back
                         dynamically to calibrated W2V2 + OpenSMILE.

        Returns:
            AcousticFusionResult: Unified risk score, flags, and feature breakdown.
        """
        # 1. Calibrate raw subsystem probabilities
        cal_w2v2 = self.calibrator.calibrate_w2v2(w2v2_score)
        cal_prosody = self.calibrator.calibrate_prosody(prosody_score)

        # 2. Dynamic Weight Allocation & Graceful Degradation
        if wavlm_score is not None:
            cal_wavlm = self.calibrator.calibrate_wavlm(wavlm_score)
            active_weights = {
                "w2v2": self.w2v2_weight,
                "prosody": self.prosody_weight,
                "wavlm": self.wavlm_weight,
            }
            total_weight = sum(active_weights.values())
            fused_score = (
                self.w2v2_weight * cal_w2v2
                + self.prosody_weight * cal_prosody
                + self.wavlm_weight * cal_wavlm
            ) / total_weight
            wavlm_active = True
        else:
            # Graceful fallback: re-normalize across W2V2 and OpenSMILE
            cal_wavlm = None
            avail_sum = self.w2v2_weight + self.prosody_weight
            norm_w2v2 = round(self.w2v2_weight / avail_sum, 4)
            norm_prosody = round(self.prosody_weight / avail_sum, 4)
            active_weights = {
                "w2v2": norm_w2v2,
                "prosody": norm_prosody,
                "wavlm": 0.0,
            }
            fused_score = (norm_w2v2 * cal_w2v2) + (norm_prosody * cal_prosody)
            wavlm_active = False

        unified_risk = float(np.clip(fused_score, 0.0, 1.0))
        is_spoof = bool(unified_risk >= self.decision_threshold)
        confidence = float(abs(unified_risk - 0.5) * 2.0)  # Distance from decision boundary

        return AcousticFusionResult(
            acoustic_spoof_risk=round(unified_risk, 4),
            is_spoof=is_spoof,
            confidence=round(confidence, 4),
            w2v2_score=round(w2v2_score, 4),
            calibrated_w2v2=round(cal_w2v2, 4),
            prosody_score=round(prosody_score, 4),
            calibrated_prosody=round(cal_prosody, 4),
            wavlm_score=round(wavlm_score, 4) if wavlm_score is not None else None,
            calibrated_wavlm=round(cal_wavlm, 4) if cal_wavlm is not None else None,
            wavlm_active=wavlm_active,
            active_weights=active_weights,
        )


# Global shared fusion instance
_global_fusion_head: Optional[MultiSignalFusionHead] = None


def get_fusion_head() -> MultiSignalFusionHead:
    """Retrieve or initialize the global shared MultiSignalFusionHead singleton."""
    global _global_fusion_head
    if _global_fusion_head is None:
        _global_fusion_head = MultiSignalFusionHead()
    return _global_fusion_head
