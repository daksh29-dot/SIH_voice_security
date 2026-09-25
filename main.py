"""
main.py

CLI entry point for the voice-security Phase 1 pipeline.

Usage:
    python main.py analyze <path_to_audio_file>
    python main.py evaluate
    python main.py inspect-model
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import src.config  # noqa: E402


def cmd_analyze(args):
    from inference import VoiceSpoofDetector

    detector = VoiceSpoofDetector()
    result = detector.analyze(args.audio_path)

    print(f"\nFile:             {result.file_path}")
    print(f"Segments:         {len(result.segment_scores)}")
    print(f"Segment scores:   {[f'{s:.4f}' for s in result.segment_scores]}")
    print(f"Aggregated score: {result.aggregated_score:.4f}  "
          f"(strategy={config.AGGREGATION_STRATEGY})")
    print(f"Decision:         {result.decision.value}  "
          f"(threshold={config.SPOOF_THRESHOLD})\n")


def cmd_evaluate(args):
    from evaluate import run_evaluation

    metrics = run_evaluation()
    print("\n=== Evaluation Results ===")
    print(json.dumps(metrics, indent=2))
    print(f"\nFull predictions written to: {config.PREDICTIONS_CSV}")
    print(f"Metrics written to:          {config.METRICS_JSON}\n")


def cmd_inspect_model(args):
    from aasist_onnx import AasistOnnxModel

    model = AasistOnnxModel()
    print("\n=== AASIST-L ONNX Model Info ===")
    print("Input: ", model.input_info())
    print("Output:", model.output_info())
    print(
        "\nConfirm config.TARGET_SAMPLE_RATE and segment length match this "
        "input shape before trusting pipeline results.\n"
    )


def main():
    parser = argparse.ArgumentParser(description="Voice deepfake/spoof detector (Phase 1)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_analyze = subparsers.add_parser("analyze", help="Analyze a single audio file")
    p_analyze.add_argument("audio_path", type=str)
    p_analyze.set_defaults(func=cmd_analyze)

    p_eval = subparsers.add_parser("evaluate", help="Run batch evaluation on test_audio/")
    p_eval.set_defaults(func=cmd_evaluate)

    p_inspect = subparsers.add_parser("inspect-model", help="Print ONNX model input/output shapes")
    p_inspect.set_defaults(func=cmd_inspect_model)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
