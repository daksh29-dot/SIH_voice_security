"""
Drop this into your project root (next to app.py / src / models).
It does the two things your pipeline is explicitly waiting on:

  1. verify   -> confirms which class index is actually "spoof" in your
                 .onnx export, using labeled files you provide.
  2. calibrate -> fits calibration.json against YOUR mic/app pipeline so
                 aggregated_score becomes a real probability instead of
                 a raw, uncalibrated sigmoid(logit-margin).

Nothing here guesses. If your data doesn't support a clean answer, it
tells you that instead of forcing one.

------------------------------------------------------------------
STEP 0 - get labeled audio, put it through YOUR pipeline
------------------------------------------------------------------
real/    : 15-30 short clips of YOUR actual voice, recorded the SAME way
           your app records it (same browser/mic path, saved to files
           you can point this script at). Different sentences each time.
real_replayed/ (optional but recommended): a few of those same real
           clips played out of a speaker and re-recorded through the
           mic, if your product needs to catch replay attacks too.
spoof/   : 15-30 clips that are NOT your voice: TTS output (any engine),
           voice-conversion output, or public ASVspoof2019 LA spoof
           samples. For the `verify` step, source doesn't matter much.
           For the `calibrate` step, prefer generating spoof clips that
           go through the SAME recording path a real attacker would use
           against your app (e.g. played through a speaker and captured
           by the mic, or injected via a virtual audio cable) - a spoof
           file that never touches your mic/codec path calibrates a
           different problem than the one you actually have.

Never calibrate on your voice alone. You need both classes.

------------------------------------------------------------------
STEP 1 - verify class orientation (run this FIRST)
------------------------------------------------------------------
python verify_and_calibrate.py verify --real real/*.wav --spoof spoof/*.wav

Reads the aggregated raw margin for every file (spoof_index as currently
set in src/config.py) and reports whether spoof files score higher than
real files, as they must if spoof_index is correct. If they don't:
flip `spoof_index` in src/config.py (0 <-> 1) and run verify again.
Only set `contract_verified = True` in config.py once this separates
sensibly AND you've cross-checked output semantics against whatever
export script / README produced your .onnx file.

------------------------------------------------------------------
STEP 2 - fit calibration (only after verify looks correct)
------------------------------------------------------------------
python verify_and_calibrate.py calibrate --real real/*.wav --spoof spoof/*.wav \\
    --real-below 0.3 --spoof-above 0.7 --out calibration.json

Writes calibration.json to your project root. Restart the app. From then
on `spoof_probability` in app.py's responses will be populated (it was
None before because calibrated_score was always None).

Re-run whenever you change the model file, config.py, or any file listed
in pipeline_signature() inside src/inference.py - old calibration is
rejected automatically if the signature no longer matches (this is a
safety check already built into your VoiceSpoofDetector, not new).
"""
import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from config import DEFAULTS, MODEL_PATH, CALIBRATION_PATH  # noqa: E402
from inference import VoiceSpoofDetector, fit_calibration  # noqa: E402


def expand(patterns):
    paths = []
    for pattern in patterns:
        matched = sorted(glob.glob(pattern))
        if not matched and Path(pattern).is_file():
            matched = [pattern]
        paths.extend(matched)
    if not paths:
        raise SystemExit(f"No files matched: {patterns}")
    return paths


def score_files(detector, paths, label):
    """Return list of (path, aggregated_margin). Skips files with no usable window."""
    rows = []
    for path in paths:
        result = detector.analyze(path)
        if result.aggregated_margin is None:
            print(f"  [SKIP] {path}: {result.status} reasons={result.reasons}")
            continue
        rows.append((path, result.aggregated_margin, result.aggregated_score))
        print(f"  [{label:5s}] {path}: raw_margin={result.aggregated_margin:+.4f} "
              f"raw_score={result.aggregated_score:.4f}")
    return rows


def cmd_verify(args):
    # calibration_path=None: we deliberately look at the RAW model output only,
    # orientation must be checked before calibration means anything.
    detector = VoiceSpoofDetector(args.model, calibration_path=None)
    print(f"contract_verified in config.py is currently: {DEFAULTS.contract_verified}")
    print(f"spoof_index in config.py is currently:        {DEFAULTS.spoof_index}\n")

    print("Scoring REAL files (should score LOW if spoof_index is correct):")
    real_rows = score_files(detector, expand(args.real), "REAL")
    print("\nScoring SPOOF files (should score HIGH if spoof_index is correct):")
    spoof_rows = score_files(detector, expand(args.spoof), "SPOOF")

    if len(real_rows) < 2 or len(spoof_rows) < 2:
        raise SystemExit("\nNeed at least 2 usable files per class to say anything meaningful.")

    real_mean = sum(r[1] for r in real_rows) / len(real_rows)
    spoof_mean = sum(r[1] for r in spoof_rows) / len(spoof_rows)
    print(f"\nMean raw margin  REAL:  {real_mean:+.4f}")
    print(f"Mean raw margin  SPOOF: {spoof_mean:+.4f}")

    if spoof_mean > real_mean:
        print("\nOK: spoof files score higher than real files, as expected.")
        print("spoof_index looks correctly oriented for THIS model export.")
        print("Do not set contract_verified=True from this alone - also confirm")
        print("output_kind (logits vs probabilities) and the export script/README")
        print("actually match this checkpoint. Then proceed to `calibrate`.")
    else:
        print("\nPROBLEM: real files score >= spoof files on average.")
        print("Your spoof_index is very likely inverted for this export.")
        print(f"Fix: in src/config.py, change spoof_index from {DEFAULTS.spoof_index} "
              f"to {1 - DEFAULTS.spoof_index}, then re-run verify.")
        print("If it's still not separating after flipping, the issue is not")
        print("orientation - re-check output_kind, normalization, and whether")
        print("this .onnx file is actually the checkpoint you think it is.")


def cmd_calibrate(args):
    if not 0 <= args.real_below < args.spoof_above <= 1:
        raise SystemExit("--real-below must be < --spoof-above, both in [0,1]")

    detector = VoiceSpoofDetector(args.model, calibration_path=None)

    print("Scoring REAL files:")
    real_rows = score_files(detector, expand(args.real), "REAL")
    print("\nScoring SPOOF files:")
    spoof_rows = score_files(detector, expand(args.spoof), "SPOOF")

    if len(real_rows) < 5 or len(spoof_rows) < 5:
        raise SystemExit(
            "\nNeed at least ~5 usable files per class to fit a calibration that "
            "means anything, and really you want more like 15-30. Add more clips."
        )

    margins = [r[1] for r in real_rows] + [r[1] for r in spoof_rows]
    labels = [0.0] * len(real_rows) + [1.0] * len(spoof_rows)

    calibration = fit_calibration(
        margins, labels, detector.signature, args.real_below, args.spoof_above
    )

    out_path = Path(args.out)
    out_path.write_text(json.dumps(calibration, indent=2))
    print(f"\nWrote {out_path.resolve()}")
    print(json.dumps(calibration, indent=2))

    # Sanity-check: show what each training file WOULD have decided under
    # this brand-new calibration, so you can see if it actually separates
    # your two classes before trusting it in production.
    from decision import decide
    print("\nSanity check against the same files used to fit this (not held-out - "
          "for a real accuracy claim you must test on DIFFERENT recordings):")
    import math
    def calibrated(margin):
        z = calibration["slope"] * margin + calibration["intercept"]
        return 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))
    for path, margin, _ in real_rows:
        c = calibrated(margin)
        print(f"  REAL  {path}: calibrated={c:.3f} -> {decide(c, args.real_below, args.spoof_above).value}")
    for path, margin, _ in spoof_rows:
        c = calibrated(margin)
        print(f"  SPOOF {path}: calibrated={c:.3f} -> {decide(c, args.real_below, args.spoof_above).value}")

    print("\nRestart your app. Re-run this whenever the model file or pipeline "
          "code changes - stale calibration.json is rejected automatically.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default=str(MODEL_PATH))
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("verify", help="Check whether spoof_index is oriented correctly")
    pv.add_argument("--real", nargs="+", required=True, help="Glob(s)/paths to real voice files")
    pv.add_argument("--spoof", nargs="+", required=True, help="Glob(s)/paths to spoof/synthetic files")
    pv.set_defaults(func=cmd_verify)

    pc = sub.add_parser("calibrate", help="Fit calibration.json against your pipeline")
    pc.add_argument("--real", nargs="+", required=True)
    pc.add_argument("--spoof", nargs="+", required=True)
    pc.add_argument("--real-below", type=float, default=0.3,
                     help="Calibrated scores below this are decided REAL (default 0.3)")
    pc.add_argument("--spoof-above", type=float, default=0.7,
                     help="Calibrated scores above this are decided SPOOF (default 0.7)")
    pc.add_argument("--out", default=str(CALIBRATION_PATH))
    pc.set_defaults(func=cmd_calibrate)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()