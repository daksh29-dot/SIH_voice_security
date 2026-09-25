"""Explicit candidate contract. Confirm against YOUR checkpoint/export, not its filename."""
from dataclasses import dataclass, asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "models" / "w2v2-aasist.onnx"
CALIBRATION_PATH = PROJECT_ROOT / "calibration.json"

@dataclass(frozen=True)
class Settings:
    sample_rate: int = 16000
    window_samples: int = 64600
    hop_samples: int = 32000
    normalization: str = "peak"   # none / peak / zscore: verify with export
    output_name: str | None = None  # mandatory if graph has multiple outputs
    output_kind: str = "logits"   # logits / probabilities (two classes only)
    spoof_index: int = 0
    contract_verified: bool = False  # change only after provenance/parity checks
    # Defaults below are engineering quality gates, NOT calibrated accuracy claims.
    min_rms_dbfs: float = -60.0
    max_clipped_fraction: float = 0.01
    min_speech_seconds: float = 1.0
    min_speech_fraction: float = 0.30
    vad_mode: int = 1
    max_file_seconds: float = 120.0
    # Keep all waveform windows intact; VAD is used only for eligibility.
    short_audio: str = "abstain"  # abstain / repeat (reference diagnostic only)
    # List any ONNX external weight sidecars; they enter the calibration fingerprint.
    external_weights: tuple[str, ...] = ()

    def __post_init__(self):
        if self.sample_rate != 16000:
            raise ValueError("This adapter targets a verified 16 kHz checkpoint only")
        if self.window_samples <= 0 or not 0 < self.hop_samples <= self.window_samples:
            raise ValueError("Invalid window/hop")
        if self.normalization not in {"none", "peak", "zscore"}:
            raise ValueError("Unknown normalization")
        if self.output_kind not in {"logits", "probabilities"} or self.spoof_index not in (0, 1):
            raise ValueError("Unsupported two-class output contract")
        if self.short_audio not in {"abstain", "repeat"} or self.vad_mode not in range(4):
            raise ValueError("Invalid short-audio or VAD setting")
        if not 0 <= self.min_speech_fraction <= 1 or not 0 <= self.max_clipped_fraction <= 1:
            raise ValueError("Invalid quality fraction")
        if self.min_speech_seconds < 0 or self.max_file_seconds <= 0:
            raise ValueError("Invalid duration")

    def as_dict(self):
        return asdict(self)

DEFAULTS = Settings()
SPOOF_THRESHOLD = 0.6
