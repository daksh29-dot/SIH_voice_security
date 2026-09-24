"""
NLP subpackage for Project VISOR.
Includes faster-whisper ASR and social engineering intent classification.
"""

from backend.nlp.transcription import (
    WhisperTranscriber,
    UtteranceAccumulator,
    AsyncASRWorker,
    get_whisper_transcriber,
)
from backend.nlp.scam_intent import (
    ScamIntentClassifier,
    get_scam_classifier,
    TELECOM_FRAUD_PATTERNS,
)

__all__ = [
    "WhisperTranscriber",
    "UtteranceAccumulator",
    "AsyncASRWorker",
    "get_whisper_transcriber",
    "ScamIntentClassifier",
    "get_scam_classifier",
    "TELECOM_FRAUD_PATTERNS",
]
