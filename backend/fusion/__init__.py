"""
Fusion subpackage for Project VISOR.
Includes score calibration and multi-signal acoustic score fusion.
"""

from backend.fusion.calibration import (
    temperature_scale,
    PlattScaler,
    ScoreCalibrator,
)
from backend.fusion.feature_fusion import (
    AcousticFusionResult,
    MultiSignalFusionHead,
    get_fusion_head,
)
from backend.fusion.risk_engine import (
    RiskState,
    RiskEngine,
    RiskEvaluationResult,
    get_risk_engine,
)

__all__ = [
    "temperature_scale",
    "PlattScaler",
    "ScoreCalibrator",
    "AcousticFusionResult",
    "MultiSignalFusionHead",
    "get_fusion_head",
    "RiskState",
    "RiskEngine",
    "RiskEvaluationResult",
    "get_risk_engine",
]

