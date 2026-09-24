"""
Models subpackage for Project VISOR.
Includes:
  - W2V2-AASIST ONNX deepfake audio detector
  - OpenSMILE targeted physical prosody extractor
  - SpeechBrain ECAPA-TDNN speaker encoder & verification engine
"""

from backend.models.w2v2_aasist import (
    W2V2AASISTModel,
    W2V2AASISTPrediction,
    get_w2v2_aasist_model,
)
from backend.models.opensmile_features import (
    OpenSMILEProsodyExtractor,
    get_prosody_extractor,
)
from backend.models.speaker_encoder import (
    SpeakerEncoder,
    get_speaker_encoder,
)

__all__ = [
    "W2V2AASISTModel",
    "W2V2AASISTPrediction",
    "get_w2v2_aasist_model",
    "OpenSMILEProsodyExtractor",
    "get_prosody_extractor",
    "SpeakerEncoder",
    "get_speaker_encoder",
]
