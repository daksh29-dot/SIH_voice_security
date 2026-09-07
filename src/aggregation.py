"""
aggregation.py

Combines per-segment spoof scores into a single recording-level score.

    Segment 1 -> 0.82
    Segment 2 -> 0.91
    Segment 3 -> 0.76
    Segment 4 -> 0.88
           |
       aggregation
           |
        0.8425

Multiple strategies are implemented so Step 5 can compare them empirically
rather than assuming mean is optimal.
"""

from typing import List

import numpy as np

import _pathfix  # noqa: F401
import config


def aggregate_mean(scores: List[float]) -> float:
    return float(np.mean(scores))


def aggregate_median(scores: List[float]) -> float:
    return float(np.median(scores))


def aggregate_weighted_mean(scores: List[float], weights: List[float] | None = None) -> float:
    """
    Weighted mean. If no weights are given, falls back to plain mean.
    Intended use: weight segments by e.g. voice-activity confidence or
    segment energy once that signal is available.
    """
    if weights is None:
        return aggregate_mean(scores)
    if len(weights) != len(scores):
        raise ValueError("weights and scores must be the same length")
    weights = np.asarray(weights, dtype=np.float64)
    if weights.sum() == 0:
        return aggregate_mean(scores)
    return float(np.average(scores, weights=weights))


def aggregate_top_k(scores: List[float], k: int = config.TOP_K) -> float:
    """
    Average of the top-k highest (most spoof-like) scores.
    Useful when spoofing artifacts may only appear in part of a recording —
    a single convincing fake segment shouldn't get diluted by many easy
    real-sounding segments.
    """
    k = min(k, len(scores))
    top_scores = sorted(scores, reverse=True)[:k]
    return float(np.mean(top_scores))


def aggregate_majority_vote(scores: List[float], threshold: float = config.SPOOF_THRESHOLD) -> float:
    """
    Fraction of segments classified as spoof at the given threshold.
    Returns a value in [0, 1] that can be compared against the same
    threshold downstream, or a separate vote threshold (e.g. 0.5).
    """
    votes = [1.0 if s >= threshold else 0.0 for s in scores]
    return float(np.mean(votes))


_STRATEGIES = {
    "mean": aggregate_mean,
    "median": aggregate_median,
    "weighted_mean": aggregate_weighted_mean,
    "top_k": aggregate_top_k,
    "majority_vote": aggregate_majority_vote,
}


def aggregate(scores: List[float], strategy: str = config.AGGREGATION_STRATEGY) -> float:
    """Dispatch to the configured aggregation strategy."""
    if not scores:
        raise ValueError("Cannot aggregate an empty list of scores")
    if strategy not in _STRATEGIES:
        raise ValueError(f"Unknown aggregation strategy: {strategy}. "
                          f"Choose from {list(_STRATEGIES)}")
    return _STRATEGIES[strategy](scores)


if __name__ == "__main__":
    example_scores = [0.82, 0.91, 0.76, 0.88]
    for name in _STRATEGIES:
        print(f"{name:15s} -> {aggregate(example_scores, name):.4f}")
