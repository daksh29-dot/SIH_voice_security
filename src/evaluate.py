"""
evaluate.py

Step 6/7 of Phase 1: batch-run the pipeline over a labeled evaluation
dataset (test_audio/real, test_audio/spoof) and compute metrics.

    Dataset -> Batch inference -> Metrics -> Results

Writes:
    results/predictions.csv  — per-file scores and decisions
    results/metrics.json     — aggregate metrics (accuracy, F1, EER, etc.)
    results/evaluation_results.xlsx — Excel version of predictions
"""

import csv
import json
import time
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd

import _pathfix  # noqa: F401
import config
from inference import VoiceSpoofDetector
from decision import Decision


def _collect_files(directory: Path) -> List[Path]:
    if not directory.exists():
        return []
    exts = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
    return sorted(p for p in directory.iterdir() if p.suffix.lower() in exts)


def compute_eer(y_true: List[int], y_scores: List[float]) -> float:
    """
    Compute Equal Error Rate: the point where False Positive Rate (real
    classified as spoof) equals False Negative Rate (spoof classified as
    real). y_true: 1 = spoof, 0 = real. y_scores: higher = more spoof-like.
    """
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)

    thresholds = np.unique(y_scores)
    fprs, fnrs = [], []

    n_pos = np.sum(y_true == 1)  # spoof
    n_neg = np.sum(y_true == 0)  # real

    if n_pos == 0 or n_neg == 0:
        return float("nan")

    for t in thresholds:
        preds = (y_scores >= t).astype(int)
        fp = np.sum((preds == 1) & (y_true == 0))
        fn = np.sum((preds == 0) & (y_true == 1))
        fprs.append(fp / n_neg)
        fnrs.append(fn / n_pos)

    fprs = np.array(fprs)
    fnrs = np.array(fnrs)
    idx = np.argmin(np.abs(fprs - fnrs))
    eer = (fprs[idx] + fnrs[idx]) / 2.0
    return float(eer)


def run_evaluation() -> dict:
    detector = VoiceSpoofDetector()

    real_files = _collect_files(config.REAL_AUDIO_DIR)
    spoof_files = _collect_files(config.SPOOF_AUDIO_DIR)

    if not real_files and not spoof_files:
        raise RuntimeError(
            f"No audio found in {config.REAL_AUDIO_DIR} or {config.SPOOF_AUDIO_DIR}. "
            f"Populate the evaluation dataset before running evaluate.py."
        )

    rows = []
    y_true, y_scores = [], []
    total_time = 0.0

    for label, files, true_label in (
        ("real", real_files, 0),
        ("spoof", spoof_files, 1),
    ):
        for f in files:
            start = time.perf_counter()
            try:
                result = detector.analyze(f)
            except Exception as e:
                print(f"[WARN] Skipping {f} due to error: {e}")
                continue
            elapsed = time.perf_counter() - start
            total_time += elapsed

            rows.append({
                "file": str(f),
                "true_label": label,
                "aggregated_score": result.aggregated_score,
                "decision": result.decision.value,
                "inference_time_s": round(elapsed, 4),
            })
            y_true.append(true_label)
            y_scores.append(result.aggregated_score)

    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(config.PREDICTIONS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Save predictions to Excel
    excel_path = config.RESULTS_DIR / "evaluation_results.xlsx"
    pd.DataFrame(rows).to_excel(excel_path, index=False)

    metrics = compute_metrics(y_true, y_scores)
    metrics["avg_inference_time_s"] = round(total_time / max(len(rows), 1), 4)
    metrics["num_files"] = len(rows)

    with open(config.METRICS_JSON, "w") as f:
        json.dump(metrics, f, indent=2)

    return metrics


def compute_metrics(y_true: List[int], y_scores: List[float]) -> dict:
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    y_pred = (y_scores >= config.SPOOF_THRESHOLD).astype(int)

    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))

    accuracy = (tp + tn) / max(len(y_true), 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    fpr = fp / max(fp + tn, 1)
    fnr = fn / max(fn + tp, 1)
    eer = compute_eer(y_true.tolist(), y_scores.tolist())

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "eer": round(eer, 4) if not np.isnan(eer) else None,
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "threshold_used": config.SPOOF_THRESHOLD,
        "aggregation_strategy": config.AGGREGATION_STRATEGY,
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }


if __name__ == "__main__":
    metrics = run_evaluation()
    print(json.dumps(metrics, indent=2))