"""
backend/fusion/live_calibrator.py

Fits and applies calibration specifically for the LIVE, single-window
W2V2-AASIST score path used by backend/api/websocket.py.

WHY THIS EXISTS
The live path scores one ~4-second rolling window at a time
(backend/models/w2v2_aasist.py: W2V2AASISTModel.predict), while the file-upload
path (src/inference.py) averages many overlapping windows per recording. Those
are different statistics from the SAME model, so a calibration fitted on
file-based aggregated scores (src/inference.py's fit_calibration/calibration.json)
does not transfer to single live windows. This module fits a SEPARATE
calibration for that single-window case and plugs into the calibrator hook
already built into MultiSignalFusionHead (backend/fusion/feature_fusion.py),
which today runs with calibrator=None (pure pass-through of the raw score -
this is why calibrated_w2v2 has always equalled the raw, noisy w2v2_score).

COLLECTING DATA
Use the debug dump already added to backend/api/websocket.py (writes to
debug_windows/) to capture real windows from actual live sessions - this is
more representative than any separately-recorded file, because it IS the
exact input distribution production scores. Sort dumped files into:
  debug_windows/real/    <- windows captured while you were genuinely speaking
  debug_windows/spoof/   <- windows of spoofed/synthetic audio played through
                             the same live pipeline (mic replay or injected),
                             so channel conditions match the real ones
Aim for at least 5 (script minimum), ideally 15-30+, per class, across
different sessions/times of day.

FIT
    python -m backend.fusion.live_calibrator fit \\
        --real "debug_windows/real/*.wav" --spoof "debug_windows/spoof/*.wav"

Writes backend/fusion/live_calibration.json.

WIRE IT IN (one small edit to feature_fusion.py)
    from backend.fusion.live_calibrator import LiveScoreCalibrator

    def get_fusion_head() -> MultiSignalFusionHead:
        global _global_fusion_head
        if _global_fusion_head is None:
            _global_fusion_head = MultiSignalFusionHead(
                calibrator=LiveScoreCalibrator.load_if_available())
        return _global_fusion_head

Restart the app. calibrated_w2v2 / acoustic_spoof_risk in live responses will
then reflect this fit instead of passing the raw single-window score straight
through. Re-run `fit` whenever the model file changes.

This module intentionally does NOT touch calibration.json or src/inference.py
- those serve the file-upload path and have their own signature/consistency
checks against a different pipeline. Keep the two calibrations separate.
"""
import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.optimize import minimize

DEFAULT_PATH = Path(__file__).resolve().parent / "live_calibration.json"


def _margin_from_prediction(prediction, spoof_index):
    values = np.asarray(prediction.raw_logits, dtype=np.float64)
    if values.shape != (2,) or not np.isfinite(values).all():
        raise ValueError("Unexpected raw_logits shape from live model")
    return float(values[spoof_index] - values[1 - spoof_index])


def _load_wav_as_float(path):
    sr, data = wavfile.read(path)
    if np.issubdtype(data.dtype, np.integer):
        x = data.astype(np.float64) / float(np.iinfo(data.dtype).max)
    else:
        x = data.astype(np.float64)
    return sr, x.astype(np.float32)


def _score_files(model, paths, spoof_index):
    margins = []
    for path in paths:
        sr, x = _load_wav_as_float(path)
        try:
            pred = model.predict(x, sample_rate=sr)
        except ValueError as exc:
            print(f"  [SKIP] {path}: {exc}")
            continue
        margin = _margin_from_prediction(pred, spoof_index)
        margins.append(margin)
        print(f"  {path}: raw_score={pred.spoof_score:.4f} margin={margin:+.4f}")
    return margins


def expand(patterns):
    paths = []
    for pattern in patterns:
        matched = sorted(glob.glob(pattern))
        paths.extend(matched if matched else ([pattern] if Path(pattern).is_file() else []))
    if not paths:
        raise SystemExit(f"No files matched: {patterns}")
    return paths


def _sigmoid(z):
    return float(1 / (1 + np.exp(-z)) if z >= 0 else np.exp(z) / (1 + np.exp(z)))


def fit(real_paths, spoof_paths, out_path):
    from backend.models.w2v2_aasist import get_w2v2_aasist_model
    model = get_w2v2_aasist_model()

    print("Scoring REAL windows through the LIVE model wrapper:")
    real_margins = _score_files(model, real_paths, model.spoof_index)
    print("Scoring SPOOF windows through the LIVE model wrapper:")
    spoof_margins = _score_files(model, spoof_paths, model.spoof_index)

    if len(real_margins) < 5 or len(spoof_margins) < 5:
        raise SystemExit(
            "\nNeed at least 5 usable windows per class (15-30+ recommended for a "
            "trustworthy fit). Capture more via the debug dump and re-run."
        )

    x = np.array(real_margins + spoof_margins, dtype=np.float64)
    y = np.array([0.0] * len(real_margins) + [1.0] * len(spoof_margins), dtype=np.float64)
    if np.std(x) < 1e-8:
        raise SystemExit("No score variation across your samples; add more/varied clips.")

    center, scale = float(x.mean()), float(x.std())
    z = (x - center) / scale

    def objective(theta):
        logits = theta[0] * z + theta[1]
        return np.mean(np.logaddexp(0, logits) - y * logits) + 1e-6 * theta[0] ** 2

    result = minimize(objective, [1.0, 0.0], method="L-BFGS-B", bounds=[(0.0, None), (None, None)])
    if not result.success or result.x[0] <= 1e-6:
        raise SystemExit(
            "Calibration fit failed or direction unsupported. This usually means "
            "your real/spoof windows don't separate at all in this domain yet - "
            "double check labeling and try adding more varied samples."
        )

    slope = float(result.x[0] / scale)
    intercept = float(result.x[1] - slope * center)
    calibration = {
        "slope": slope, "intercept": intercept, "spoof_index": int(model.spoof_index),
        "n_real": len(real_margins), "n_spoof": len(spoof_margins),
    }
    out_path = Path(out_path)
    out_path.write_text(json.dumps(calibration, indent=2))
    print(f"\nWrote {out_path.resolve()}")
    print(json.dumps(calibration, indent=2))

    print("\nSanity check against the SAME data used to fit this "
          "(not held-out - get fresh clips for a real accuracy check):")
    for label, margins in (("REAL", real_margins), ("SPOOF", spoof_margins)):
        for m in margins:
            p = _sigmoid(slope * m + intercept)
            print(f"  {label:5s} calibrated={p:.3f}")


class LiveScoreCalibrator:
    """Duck-types MultiSignalFusionHead's calibrator interface for live, single-window scores.

    Only w2v2 is calibrated here (that's what live_calibration.json was fit for);
    prosody/wavlm are passed through unchanged so fusion doesn't silently invent
    calibration for signals this module never touched.
    """

    def __init__(self, slope, intercept):
        self.slope = float(slope)
        self.intercept = float(intercept)

    @classmethod
    def load_if_available(cls, path=DEFAULT_PATH):
        path = Path(path)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return cls(data["slope"], data["intercept"])

    def calibrate_w2v2(self, score):
        p = min(max(float(score), 1e-6), 1 - 1e-6)
        margin = float(np.log(p / (1 - p)))
        return _sigmoid(self.slope * margin + self.intercept)

    def calibrate_prosody(self, score):
        return float(score)

    def calibrate_wavlm(self, score):
        return float(score)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    pf = sub.add_parser("fit", help="Fit live_calibration.json from labeled debug-window wavs")
    pf.add_argument("--real", nargs="+", required=True)
    pf.add_argument("--spoof", nargs="+", required=True)
    pf.add_argument("--out", default=str(DEFAULT_PATH))
    args = parser.parse_args()
    if args.cmd == "fit":
        fit(expand(args.real), expand(args.spoof), args.out)


if __name__ == "__main__":
    main()