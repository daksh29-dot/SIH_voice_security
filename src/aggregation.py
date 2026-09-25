"""Aggregate equally over valid windows; overlap does not create independent evidence."""
import numpy as np

def aggregate(scores, strategy="mean"):
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or not values.size or not np.isfinite(values).all():
        raise ValueError("Expected non-empty finite scores")
    if strategy == "min":
        return float(np.min(values))
    if strategy == "mean":
        return float(values.mean())
    if strategy == "median":
        return float(np.median(values))
    raise ValueError("Only min/mean/median supported; evaluate changes before deployment")

def sigmoid(value):
    value = float(value)
    if not np.isfinite(value):
        raise ValueError("Non-finite score")
    if value >= 0:
        return float(1 / (1 + np.exp(-value)))
    e = np.exp(value)
    return float(e / (1 + e))
