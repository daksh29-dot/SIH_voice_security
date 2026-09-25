"""Diagnostic-first inference with auditable abstention and optional calibration."""
from dataclasses import dataclass, field, asdict
from pathlib import Path
import hashlib
import importlib.metadata
import json
import subprocess
import time
import numpy as np
from config import DEFAULTS, MODEL_PATH, CALIBRATION_PATH
from audio_preprocessing import preprocess_audio, resample, normalize, SpeechGate
from segment_audio import windows
from model import W2V2AASISTSpoofDetector, sha256_file
from aggregation import aggregate, sigmoid
from decision import Decision, decide

def pipeline_signature(settings, identity):
    root = Path(__file__).parent
    code = {name: sha256_file(root / name) for name in
            ("config.py", "audio_preprocessing.py", "segment_audio.py", "model.py", "aggregation.py", "decision.py", "inference.py", "aasist_onnx.py", "vad.py")}
    versions = {}
    for package in ("numpy", "scipy", "onnxruntime", "onnxruntime-gpu", "webrtcvad-wheels"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    try:
        versions["ffmpeg"] = subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True,
                                              text=True, timeout=5).stdout.splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        versions["ffmpeg"] = "not-available"
    data = {"settings": settings.as_dict(), "model": identity, "code": code, "versions": versions}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

@dataclass
class InferenceResult:
    file_path: str
    segment_scores: list[float] = field(default_factory=list)
    aggregated_score: float | None = None  # uncalibrated sigmoid(mean logit margin)
    aggregated_margin: float | None = None
    calibrated_score: float | None = None
    decision: Decision = Decision.UNCERTAIN
    status: str = "insufficient_evidence"
    reasons: list[str] = field(default_factory=list)
    windows: list[dict] = field(default_factory=list)
    pipeline_signature: str = ""
    elapsed_seconds: float = 0.0

    def to_dict(self):
        return asdict(self)

class VoiceSpoofDetector:
    def __init__(self, model_path=MODEL_PATH, settings=DEFAULTS, calibration_path=CALIBRATION_PATH,
                 model=None, gate=None):
        self.settings = settings
        self.model = model if model is not None else W2V2AASISTSpoofDetector(model_path, settings)
        self.gate = gate if gate is not None else SpeechGate(settings)
        self.signature = pipeline_signature(settings, self.model.identity)
        self.calibration = None
        if calibration_path is not None and Path(calibration_path).exists():
            c = json.loads(Path(calibration_path).read_text())
            if c["pipeline_signature"] != self.signature:
                raise ValueError("Calibration does not match model/code/config/dependencies; recalibrate")
            if not np.isfinite([c["slope"], c["intercept"], c["real_below"], c["spoof_above"]]).all() or c["slope"] <= 0:
                raise ValueError("Invalid calibration")
            decide(0.5, c["real_below"], c["spoof_above"])
            self.calibration = c

    def analyze(self, audio_path):
        t = time.perf_counter()
        result = self.analyze_array(preprocess_audio(audio_path, self.settings), self.settings.sample_rate, str(audio_path))
        result.elapsed_seconds = time.perf_counter() - t
        return result

    def analyze_array(self, waveform, sample_rate, source="pcm"):
        t = time.perf_counter()
        x = resample(waveform, sample_rate, self.settings.sample_rate)
        if len(x) > self.settings.max_file_seconds * self.settings.sample_rate:
            raise ValueError("Audio exceeds configured duration limit")
        result = InferenceResult(source, pipeline_signature=self.signature)
        candidates = windows(x, self.settings)
        if not candidates:
            result.reasons = ["need_full_window_of_audio"]
        margins = []
        for w in candidates:
            quality = self.gate.check(w.waveform[:w.valid_samples])
            row = {"start_seconds": w.start / self.settings.sample_rate,
                   "valid_seconds": w.valid_samples / self.settings.sample_rate,
                   "quality": asdict(quality), "score": None, "margin": None}
            if not quality.reasons:
                margin = self.model.predict_margin(normalize(w.waveform, self.settings.normalization))
                if not np.isfinite(margin):
                    raise ValueError("Model produced a non-finite margin")
                row.update(margin=margin, score=sigmoid(margin))
                margins.append(margin)
                result.segment_scores.append(row["score"])
            result.windows.append(row)
        if margins:
            result.aggregated_margin = aggregate(margins, self.settings.aggregation_strategy)
            result.aggregated_score = sigmoid(result.aggregated_margin)
            result.status = "uncalibrated"
            if not self.settings.contract_verified:
                result.reasons.append("checkpoint_contract_unverified")
            if self.calibration is None:
                result.reasons.append("calibration_required")
                # Softmax is a model score, not an empirical probability that
                # this microphone recording is fake. Never force a label here.
            elif not self.settings.contract_verified:
                result.status = "unverified_contract"
            else:
                c = self.calibration
                result.calibrated_score = sigmoid(c["slope"] * result.aggregated_margin + c["intercept"])
                result.decision = decide(result.calibrated_score, c["real_below"], c["spoof_above"])
                result.status = "ok" if result.decision != Decision.UNCERTAIN else "uncertain"
                if result.status == "uncertain":
                    result.reasons.append("between_calibrated_thresholds")
            # Do not pronounce a whole recording real when some windows were unassessed.
            if len(margins) != len(candidates):
                result.reasons.append("some_windows_unassessed")
                if result.decision == Decision.REAL:
                    result.decision, result.status = Decision.UNCERTAIN, "partial_coverage"
        elif candidates:
            result.reasons = sorted({r for w in result.windows for r in w["quality"]["reasons"]})
        result.elapsed_seconds = time.perf_counter() - t
        return result

def fit_calibration(margins, labels, pipeline_signature, real_below, spoof_above):
    """Return a calibration.json-compatible dict; label real=0, spoof=1.

    Supply recording-level aggregated_margin values from BOTH classes recorded
    through representative microphones/codecs. Verify the export contract first.
    Choose thresholds on a separate validation set; evaluate false rejection and
    spoof acceptance on a held-out test set split by speaker/session/generator.
    Do not fit on one user's real voice alone or treat a fit as accuracy evidence.
    Save the returned dict with json.dumps; no new project file/module is needed.
    """
    from scipy.optimize import minimize
    x = np.asarray(margins, dtype=np.float64)
    y = np.asarray(labels, dtype=np.float64)
    if (x.ndim != 1 or x.shape != y.shape or not np.isfinite(x).all()
            or not np.isfinite(y).all() or set(y.tolist()) != {0.0, 1.0}):
        raise ValueError("Finite paired margins and both labels (real=0, spoof=1) required")
    if min(np.sum(y == 0), np.sum(y == 1)) < 2 or np.std(x) < 1e-8:
        raise ValueError("Insufficient score variation or examples for calibration")
    decide(0.5, real_below, spoof_above)
    if not isinstance(pipeline_signature, str) or not pipeline_signature:
        raise ValueError("A pipeline signature is required")
    center, scale = float(x.mean()), float(x.std())
    z = (x - center) / scale
    def objective(theta):
        logits = theta[0] * z + theta[1]
        # Tiny regularizer prevents divergence on perfectly separable samples.
        return np.mean(np.logaddexp(0, logits) - y * logits) + 1e-6 * theta[0]**2
    fit = minimize(objective, [1.0, 0.0], method="L-BFGS-B",
                   bounds=[(0.0, None), (None, None)])
    if not fit.success or not np.isfinite(fit.x).all() or fit.x[0] <= 1e-6:
        raise ValueError("Calibration failed or score direction is unsupported; check class mapping/domain")
    slope = float(fit.x[0] / scale)
    return {"pipeline_signature": pipeline_signature, "slope": slope,
            "intercept": float(fit.x[1] - slope * center),
            "real_below": float(real_below), "spoof_above": float(spoof_above)}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("audio")
    p.add_argument("--model", default=str(MODEL_PATH))
    p.add_argument("--calibration", default=str(CALIBRATION_PATH))
    args = p.parse_args()
    d = VoiceSpoofDetector(args.model, calibration_path=args.calibration)
    print(json.dumps(d.analyze(args.audio).to_dict(), indent=2, allow_nan=False))
