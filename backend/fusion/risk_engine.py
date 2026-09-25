"""
backend/fusion/risk_engine.py

Project VISOR Explainable Risk Engine State Machine (Phase 5).
Implements a 5-state decision machine with granular, explainable signal breakdowns:
  1. ANALYZING: Waiting for sufficient valid speech frames (buffer filling).
  2. INSUFFICIENT AUDIO: VAD or audio energy below minimum thresholds (silence / non-speech).
  3. LOW RISK: Explicit speaker match, low acoustic spoof risk (<0.35), zero scam flags.
  4. REVIEW: Borderline spoof score (0.35–0.65) OR unverified speaker identity with neutral intent.
  5. HIGH RISK: Spoof score >= 0.70 OR (Speaker Imposter Detected + Scam Intent Detected).

Every evaluation returns an explainable breakdown of contributing signals:
  - Uncalibrated acoustic score & status
  - Speaker biometric consistency, similarity, and match result
  - Semantic fraud intent score, triggered categories, and flagged phrases
  - Energy & VAD stream telemetry
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import datetime
import numpy as np


class RiskState(str, Enum):
    """5-State Risk Engine Classification."""
    ANALYZING = "ANALYZING"
    INSUFFICIENT_AUDIO = "INSUFFICIENT AUDIO"
    LOW_RISK = "LOW RISK"
    REVIEW = "REVIEW"
    HIGH_RISK = "HIGH RISK"


@dataclass
class SignalBreakdown:
    """Explainable breakdown of a single telemetry pillar."""
    status: str
    score: float
    explanation: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskEvaluationResult:
    """
    Explainable decision machine evaluation result with contributing signal breakdowns.
    """
    state: RiskState
    explanation: str
    composite_risk: float
    contributing_factors: Dict[str, Any]
    timestamp: str  # ISO-8601 UTC
    frame_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to JSON-serializable dictionary."""
        return {
            "state": self.state.value if isinstance(self.state, RiskState) else str(self.state),
            "explanation": self.explanation,
            "composite_risk": round(float(self.composite_risk), 4),
            "contributing_factors": self.contributing_factors,
            "timestamp": self.timestamp,
            "frame_index": self.frame_index,
        }


class RiskEngine:
    """
    Explainable 5-state Risk Engine for Project VISOR.
    Evaluates multi-modal signals to detect synthetic voice, biometric impersonation,
    and social engineering scam intent in real-time.
    """

    # Risk Engine decision thresholds
    LOW_SPOOF_THRESHOLD: float = 0.35
    HIGH_SPOOF_THRESHOLD: float = 0.70
    HIGH_SPEAKER_CONSISTENCY: float = 0.75
    IMPOSTER_SPEAKER_CONSISTENCY: float = 0.50
    SCAM_THREAT_THRESHOLD: float = 0.50
    CLEAN_SCAM_THRESHOLD: float = 0.20

    def __init__(
        self,
        low_spoof_thresh: float = LOW_SPOOF_THRESHOLD,
        high_spoof_thresh: float = HIGH_SPOOF_THRESHOLD,
        high_speaker_consistency: float = HIGH_SPEAKER_CONSISTENCY,
        imposter_speaker_consistency: float = IMPOSTER_SPEAKER_CONSISTENCY,
        scam_threat_thresh: float = SCAM_THREAT_THRESHOLD,
    ):
        vals = (low_spoof_thresh, high_spoof_thresh, high_speaker_consistency,
                imposter_speaker_consistency, scam_threat_thresh)
        if not all(np.isfinite(v) and 0 <= v <= 1 for v in vals) or low_spoof_thresh >= high_spoof_thresh:
            raise ValueError("Invalid risk thresholds")
        self.low_spoof_thresh = low_spoof_thresh
        self.high_spoof_thresh = high_spoof_thresh
        self.high_speaker_consistency = high_speaker_consistency
        self.imposter_speaker_consistency = imposter_speaker_consistency
        self.scam_threat_thresh = scam_threat_thresh

    def evaluate(
        self,
        is_valid_audio: bool,
        vad_active: bool,
        window_ready: bool,
        acoustic_spoof_risk: float = 0.0,
        speaker_consistency: float = 0.0,
        speaker_similarity: float = 0.0,
        speaker_match: Optional[bool] = None,
        speaker_enrolled: bool = False,
        semantic_threat_score: float = 0.0,
        triggered_intents: Optional[List[str]] = None,
        flagged_phrases: Optional[List[str]] = None,
        w2v2_score: float = 0.0,
        prosody_anomaly_score: float = 0.0,
        wavlm_score: Optional[float] = None,
        frame_index: int = 0,
        timestamp: Optional[str] = None,
    ) -> RiskEvaluationResult:
        """
        Evaluate real-time signals against the 5-state decision machine.

        Args:
            is_valid_audio: Amplitude/energy check passed.
            vad_active: Speech detected by Silero VAD.
            window_ready: Circular FIFO buffer has filled minimum evaluation window (e.g. 3.0s).
            acoustic_spoof_risk: Multi-signal fused acoustic spoof score [0.0, 1.0].
            speaker_consistency: Biometric speaker consistency score [0.0, 1.0].
            speaker_similarity: Raw cosine similarity against enrolled profile [-1.0, 1.0].
            speaker_match: True if match, False if comparison did not match, None if unverified/no enrolled speaker.
            speaker_enrolled: True if an enrolled profile exists for comparison.
            semantic_threat_score: NLP scam intent threat score [0.0, 1.0].
            triggered_intents: List of detected scam intent categories.
            flagged_phrases: List of matched suspicious phrases.
            w2v2_score: Raw W2V2-AASIST spoof score.
            prosody_anomaly_score: Raw OpenSMILE prosody anomaly score.
            wavlm_score: Secondary WavLM representation spoof score (if active).
            frame_index: Sequential index of audio frame or window.
            timestamp: ISO-8601 UTC timestamp string.

        Returns:
            RiskEvaluationResult: Evaluated state, explanation, composite risk, and signal breakdowns.
        """
        # Never turn missing/NaN outputs into apparently clean results.
        for name, value in (("acoustic_spoof_risk", acoustic_spoof_risk),
                            ("speaker_consistency", speaker_consistency),
                            ("semantic_threat_score", semantic_threat_score),
                            ("w2v2_score", w2v2_score), ("prosody_anomaly_score", prosody_anomaly_score)):
            if not isinstance(value, (int, float, np.number)) or not np.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be a finite score in [0,1]")
        if not np.isfinite(speaker_similarity) or not -1 <= speaker_similarity <= 1:
            raise ValueError("Invalid cosine similarity")
        if wavlm_score is not None and (not np.isfinite(wavlm_score) or not 0 <= wavlm_score <= 1):
            raise ValueError("Invalid WavLM score")
        if speaker_match is not None:
            if not isinstance(speaker_match, (bool, np.bool_)):
                raise ValueError("speaker_match must be bool or None")
            speaker_match = bool(speaker_match)
        now_ts = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        triggered_intents = triggered_intents or []
        flagged_phrases = flagged_phrases or []

        # 1. State: INSUFFICIENT AUDIO
        # Triggered when audio energy check fails or Silero VAD classifies frame as non-speech / silence.
        if not is_valid_audio or not vad_active:
            sub_reason = "Energy below amplitude threshold (silence/empty frame)" if not is_valid_audio else "VAD classified audio as non-speech"
            factors = self._build_breakdowns(
                acoustic_risk=acoustic_spoof_risk,
                speaker_consistency=speaker_consistency,
                speaker_similarity=speaker_similarity,
                speaker_match=speaker_match,
                speaker_enrolled=speaker_enrolled,
                semantic_threat=semantic_threat_score,
                triggered_intents=triggered_intents,
                flagged_phrases=flagged_phrases,
                w2v2_score=w2v2_score,
                prosody_score=prosody_anomaly_score,
                wavlm_score=wavlm_score,
                is_valid_audio=is_valid_audio,
                vad_active=vad_active,
                window_ready=window_ready,
            )
            return RiskEvaluationResult(
                state=RiskState.INSUFFICIENT_AUDIO,
                explanation=f"Audio signal insufficient for deepfake analysis: {sub_reason}.",
                composite_risk=0.0,
                contributing_factors=factors,
                timestamp=now_ts,
                frame_index=frame_index,
            )

        # 2. State: ANALYZING
        # Triggered when active speech is detected, but circular FIFO buffer has not yet
        # accumulated sufficient frames to form a full analysis window (e.g. 3.0 seconds).
        if not window_ready:
            factors = self._build_breakdowns(
                acoustic_risk=acoustic_spoof_risk,
                speaker_consistency=speaker_consistency,
                speaker_similarity=speaker_similarity,
                speaker_match=speaker_match,
                speaker_enrolled=speaker_enrolled,
                semantic_threat=semantic_threat_score,
                triggered_intents=triggered_intents,
                flagged_phrases=flagged_phrases,
                w2v2_score=w2v2_score,
                prosody_score=prosody_anomaly_score,
                wavlm_score=wavlm_score,
                is_valid_audio=is_valid_audio,
                vad_active=vad_active,
                window_ready=window_ready,
            )
            return RiskEvaluationResult(
                state=RiskState.ANALYZING,
                explanation="Valid speech detected. Buffering audio window for multi-signal acoustic analysis.",
                composite_risk=0.0,
                contributing_factors=factors,
                timestamp=now_ts,
                frame_index=frame_index,
            )

        # 3. Window Ready: Evaluate 3 operational states (HIGH RISK, LOW RISK, REVIEW)
        # Identify key conditions:
        is_spoof_high = acoustic_spoof_risk >= self.high_spoof_thresh
        is_spoof_borderline = (self.low_spoof_thresh <= acoustic_spoof_risk < self.high_spoof_thresh)
        is_spoof_low = acoustic_spoof_risk < self.low_spoof_thresh

        # Speaker imposter detection
        # A non-match is a comparison result, not proof of an impostor.
        # The speaker encoder owns its threshold. Never contradict its decision
        # using a second threshold on an arbitrary display-score transformation.
        # None means unavailable/insufficient evidence, NOT a mismatch.
        is_speaker_imposter = speaker_enrolled and speaker_match is False
        is_speaker_verified_high = speaker_enrolled and speaker_match is True
        is_speaker_unverified = not speaker_enrolled or speaker_match is None

        # Scam intent detection
        is_scam_detected = (semantic_threat_score >= self.scam_threat_thresh) or (len(triggered_intents) > 0)
        has_zero_scam_flags = (len(triggered_intents) == 0) and not flagged_phrases and (semantic_threat_score < self.CLEAN_SCAM_THRESHOLD)

        # Evaluate HIGH RISK:
        # Rule: Spoof score >= 0.70 OR (Speaker Imposter Detected + Scam Intent Detected)
        if is_spoof_high or (is_speaker_imposter and is_scam_detected):
            explanations = []
            if is_spoof_high:
                explanations.append(f"Acoustic spoof score elevated ({acoustic_spoof_risk:.2f} >= {self.high_spoof_thresh:.2f})")
            if is_speaker_imposter and is_scam_detected:
                intents_str = ", ".join(triggered_intents) if triggered_intents else "telecom fraud intent"
                explanations.append(
                    f"Speaker did not match the enrolled profile (cosine {speaker_similarity:.2f}) "
                    f"with concurrent scam intent ({intents_str})"
                )

            # Composite score blends acoustic and semantic threat
            composite = max(acoustic_spoof_risk, 0.75 if (is_speaker_imposter and is_scam_detected) else acoustic_spoof_risk)
            factors = self._build_breakdowns(
                acoustic_risk=acoustic_spoof_risk,
                speaker_consistency=speaker_consistency,
                speaker_similarity=speaker_similarity,
                speaker_match=speaker_match,
                speaker_enrolled=speaker_enrolled,
                semantic_threat=semantic_threat_score,
                triggered_intents=triggered_intents,
                flagged_phrases=flagged_phrases,
                w2v2_score=w2v2_score,
                prosody_score=prosody_anomaly_score,
                wavlm_score=wavlm_score,
                is_valid_audio=is_valid_audio,
                vad_active=vad_active,
                window_ready=window_ready,
            )
            return RiskEvaluationResult(
                state=RiskState.HIGH_RISK,
                explanation="HIGH RISK: " + "; ".join(explanations) + ".",
                composite_risk=round(float(composite), 4),
                contributing_factors=factors,
                timestamp=now_ts,
                frame_index=frame_index,
            )

        # Evaluate LOW RISK:
        # Rule: Explicit speaker match, low acoustic spoof risk (<0.35), zero scam flags.
        if is_speaker_verified_high and is_spoof_low and has_zero_scam_flags:
            factors = self._build_breakdowns(
                acoustic_risk=acoustic_spoof_risk,
                speaker_consistency=speaker_consistency,
                speaker_similarity=speaker_similarity,
                speaker_match=speaker_match,
                speaker_enrolled=speaker_enrolled,
                semantic_threat=semantic_threat_score,
                triggered_intents=triggered_intents,
                flagged_phrases=flagged_phrases,
                w2v2_score=w2v2_score,
                prosody_score=prosody_anomaly_score,
                wavlm_score=wavlm_score,
                is_valid_audio=is_valid_audio,
                vad_active=vad_active,
                window_ready=window_ready,
            )
            composite = max(acoustic_spoof_risk, semantic_threat_score * 0.5)
            return RiskEvaluationResult(
                state=RiskState.LOW_RISK,
                explanation=(
                    f"LOW RISK: Speaker matched the enrolled profile (cosine {speaker_similarity:.2f}), "
                    f"low acoustic spoof risk ({acoustic_spoof_risk:.2f} < {self.low_spoof_thresh:.2f}), zero scam flags."
                ),
                composite_risk=round(float(composite), 4),
                contributing_factors=factors,
                timestamp=now_ts,
                frame_index=frame_index,
            )

        # Evaluate REVIEW:
        # Rule: Borderline spoof score (0.35–0.65) OR unverified speaker identity with neutral intent.
        # Also handles intermediate / non-matching states.
        review_reasons = []
        if is_spoof_borderline:
            review_reasons.append(
                f"Borderline acoustic spoof score ({acoustic_spoof_risk:.2f} in [{self.low_spoof_thresh:.2f}, {self.high_spoof_thresh:.2f}))"
            )
        if is_speaker_unverified:
            if has_zero_scam_flags:
                review_reasons.append("Unverified speaker identity with neutral intent")
            else:
                review_reasons.append("Unverified speaker identity with flagged semantic patterns")
        elif not is_speaker_verified_high and not is_speaker_imposter:
            review_reasons.append(f"Moderate speaker consistency ({speaker_consistency:.2f})")
        elif is_speaker_imposter and not is_scam_detected:
            review_reasons.append(f"Speaker inconsistency detected ({speaker_consistency:.2f}) without active scam flags")
        elif is_scam_detected and not is_speaker_imposter:
            review_reasons.append(f"Suspicious semantic intent detected without acoustic spoof anomalies")

        if not review_reasons:
            review_reasons.append("Signals inconclusive; marked for manual or supervisor review")

        factors = self._build_breakdowns(
            acoustic_risk=acoustic_spoof_risk,
            speaker_consistency=speaker_consistency,
            speaker_similarity=speaker_similarity,
            speaker_match=speaker_match,
            speaker_enrolled=speaker_enrolled,
            semantic_threat=semantic_threat_score,
            triggered_intents=triggered_intents,
            flagged_phrases=flagged_phrases,
            w2v2_score=w2v2_score,
            prosody_score=prosody_anomaly_score,
            wavlm_score=wavlm_score,
            is_valid_audio=is_valid_audio,
            vad_active=vad_active,
            window_ready=window_ready,
        )

        composite = max(acoustic_spoof_risk, 0.40)
        return RiskEvaluationResult(
            state=RiskState.REVIEW,
            explanation="REVIEW REQUIRED: " + "; ".join(review_reasons) + ".",
            composite_risk=round(float(composite), 4),
            contributing_factors=factors,
            timestamp=now_ts,
            frame_index=frame_index,
        )

    def _build_breakdowns(
        self,
        acoustic_risk: float,
        speaker_consistency: float,
        speaker_similarity: float,
        speaker_match: Optional[bool],
        speaker_enrolled: bool,
        semantic_threat: float,
        triggered_intents: List[str],
        flagged_phrases: List[str],
        w2v2_score: float,
        prosody_score: float,
        wavlm_score: Optional[float],
        is_valid_audio: bool,
        vad_active: bool,
        window_ready: bool,
    ) -> Dict[str, Any]:
        """Generate structured, explainable contributing factor breakdowns."""
        # Acoustic status
        if acoustic_risk >= self.high_spoof_thresh:
            ac_status = "CRITICAL"
            ac_exp = f"Acoustic spoof risk {acoustic_risk:.2f} >= {self.high_spoof_thresh:.2f}: elevated model score, not proof of synthetic speech."
        elif acoustic_risk >= self.low_spoof_thresh:
            ac_status = "BORDERLINE"
            ac_exp = f"Acoustic spoof risk {acoustic_risk:.2f} is in borderline range [{self.low_spoof_thresh:.2f}, {self.high_spoof_thresh:.2f})."
        else:
            ac_status = "NORMAL"
            ac_exp = f"Acoustic spoof risk {acoustic_risk:.2f} is below the configured review threshold (< {self.low_spoof_thresh:.2f})."

        # Speaker status
        if not speaker_enrolled:
            spk_status = "UNVERIFIED"
            spk_exp = "No enrolled speaker profile provided; identity unverified."
        elif speaker_match is None:
            spk_status = "UNVERIFIED"
            spk_exp = "Speaker comparison unavailable; insufficient audio or invalid enrollment is not an impostor."
        elif speaker_match is False:
            spk_status = "NO_MATCH"
            spk_exp = f"Voice did not pass the encoder matching threshold (cosine {speaker_similarity:.2f}); this alone does not establish impersonation."
        elif speaker_match is True:
            spk_status = "MATCH"
            spk_exp = f"Voice passed the encoder matching threshold (cosine {speaker_similarity:.2f}); speaker identity is separate from spoof detection."
        else:
            spk_status = "BORDERLINE"
            spk_exp = f"Voice similarity inconclusive (consistency {speaker_consistency:.2f})."

        # Semantic status
        if semantic_threat >= self.scam_threat_thresh or len(triggered_intents) > 0 or flagged_phrases:
            sem_status = "FLAGGED"
            sem_exp = f"Detected scam intent patterns: {', '.join(triggered_intents) if triggered_intents else 'Suspicious phrases'}"
        else:
            sem_status = "CLEAN"
            sem_exp = "Zero telecom fraud or social engineering patterns detected."

        if not is_valid_audio or not vad_active or not window_ready:
            ac_status = "NOT_EVALUATED"
            ac_exp = "Current audio has not passed the readiness gates; displayed scores may be stale."
            spk_status = "UNVERIFIED"
            spk_exp = "Wait for a valid audio window before interpreting identity."
        return {
            "acoustic_spoof": {
                "status": ac_status,
                "fused_risk": round(float(acoustic_risk), 4),
                "score_kind": "heuristic_risk_not_calibrated_probability",
                "w2v2_score": round(float(w2v2_score), 4),
                "prosody_anomaly_score": round(float(prosody_score), 4),
                "wavlm_score": round(float(wavlm_score), 4) if wavlm_score is not None else None,
                "explanation": ac_exp,
            },
            "speaker_verification": {
                "status": spk_status,
                "enrolled": speaker_enrolled,
                "consistency_score": round(float(speaker_consistency), 4),
                "score_kind": "heuristic_display_score",
                "similarity": round(float(speaker_similarity), 4),
                "is_match": speaker_match if (is_valid_audio and vad_active and window_ready) else None,
                "explanation": spk_exp,
            },
            "semantic_intent": {
                "status": sem_status,
                "threat_score": round(float(semantic_threat), 4),
                "triggered_intents": triggered_intents,
                "flagged_phrases": flagged_phrases,
                "explanation": sem_exp,
            },
            "audio_stream": {
                "energy_valid": bool(is_valid_audio),
                "vad_active": bool(vad_active),
                "window_ready": bool(window_ready),
            },
        }


# Global shared singleton
_global_risk_engine: Optional[RiskEngine] = None


def get_risk_engine() -> RiskEngine:
    """Retrieve or initialize the global shared RiskEngine singleton."""
    global _global_risk_engine
    if _global_risk_engine is None:
        _global_risk_engine = RiskEngine()
    return _global_risk_engine
