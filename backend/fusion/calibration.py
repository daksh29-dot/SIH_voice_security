"""
backend/fusion/calibration.py

Probability calibration for multi-signal voice security scores in Project VISOR.
Implements Temperature Scaling and Platt Scaling (logistic calibration) to convert
raw acoustic logits and anomaly scores into well-calibrated, normalized probabilities.
"""

from typing import Union, Tuple, Optional
import numpy as np


def sigmoid(z: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Numerically stable sigmoid function."""
    z_arr = np.asarray(z, dtype=np.float64)
    # Clip z to prevent overflow in exp
    z_clipped = np.clip(z_arr, -50.0, 50.0)
    sig = 1.0 / (1.0 + np.exp(-z_clipped))
    if np.isscalar(z):
        return float(sig)
    return sig


def logit(p: Union[float, np.ndarray], eps: float = 1e-7) -> Union[float, np.ndarray]:
    """Inverse sigmoid function (transforms probability to logit)."""
    p_clipped = np.clip(np.asarray(p, dtype=np.float64), eps, 1.0 - eps)
    val = np.log(p_clipped / (1.0 - p_clipped))
    if np.isscalar(p):
        return float(val)
    return val


def temperature_scale(
    score: Union[float, np.ndarray],
    temperature: float = 1.2,
    is_logit: bool = False,
    eps: float = 1e-7,
) -> Union[float, np.ndarray]:
    """
    Calibrate a raw score using Temperature Scaling.

    Args:
        score: Raw probability in [0, 1] or raw unnormalized logit
        temperature: Temperature parameter T > 0.
                     T > 1 softens overconfident predictions.
                     T < 1 sharpens predictions.
        is_logit: Set to True if score is already a logit rather than a probability.
        eps: Small epsilon to avoid log(0) when is_logit is False.

    Returns:
        Calibrated probability in [0.0, 1.0]
    """
    if temperature <= 0:
        raise ValueError(f"Temperature must be positive, got {temperature}")

    if is_logit:
        z = np.asarray(score, dtype=np.float64)
    else:
        z = logit(score, eps=eps)

    scaled_z = z / float(temperature)
    return sigmoid(scaled_z)


class PlattScaler:
    """
    Platt Scaling (parametric logistic calibration):
        P(Y = 1 | s) = 1 / (1 + exp(-(A * s + B)))

    Fits scale parameter A and bias parameter B on validation scores and binary labels.
    """

    def __init__(self, a: float = 1.0, b: float = 0.0):
        self.a = float(a)
        self.b = float(b)
        self.is_fitted = True

    def calibrate(self, score: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Apply Platt scaling to a raw score."""
        s = np.asarray(score, dtype=np.float64)
        z = self.a * s + self.b
        return sigmoid(z)

    def fit(
        self,
        scores: np.ndarray,
        labels: np.ndarray,
        max_iter: int = 100,
        lr: float = 0.05,
    ) -> "PlattScaler":
        """
        Fit A and B using negative log-likelihood minimization via gradient descent.

        Args:
            scores: Array of uncalibrated model scores
            labels: Array of binary ground truth labels (0 = Real, 1 = Spoof)
        """
        s = np.asarray(scores, dtype=np.float64).flatten()
        y = np.asarray(labels, dtype=np.float64).flatten()
        n = len(s)

        if n == 0:
            return self

        # Initialize A and B
        a = 1.0
        b = 0.0

        for _ in range(max_iter):
            p = sigmoid(a * s + b)
            # Gradient of Binary Cross Entropy
            err = p - y
            grad_a = np.sum(err * s) / n
            grad_b = np.sum(err) / n

            a -= lr * grad_a
            b -= lr * grad_b

        self.a = float(a)
        self.b = float(b)
        self.is_fitted = True
        return self


class ScoreCalibrator:
    """
    Unified calibrator registry for all acoustic model branches in Project VISOR.
    Applies calibrated domain transformations to individual subsystem scores:
      - W2V2-AASIST
      - OpenSMILE Prosody Anomaly
      - WavLM Representation Score
    """

    def __init__(
        self,
        w2v2_temperature: float = 1.25,
        prosody_temperature: float = 1.10,
        wavlm_temperature: float = 1.20,
    ):
        self.w2v2_temp = w2v2_temperature
        self.prosody_temp = prosody_temperature
        self.wavlm_temp = wavlm_temperature

        # Default Platt scalers for fine-tuning
        self.w2v2_platt = PlattScaler(a=1.1, b=-0.05)
        self.prosody_platt = PlattScaler(a=1.0, b=-0.10)
        self.wavlm_platt = PlattScaler(a=1.05, b=-0.02)

    def calibrate_w2v2(self, raw_score: float) -> float:
        """Calibrate raw W2V2-AASIST spoof score."""
        return float(temperature_scale(raw_score, temperature=self.w2v2_temp))

    def calibrate_prosody(self, raw_score: float) -> float:
        """Calibrate raw OpenSMILE prosody anomaly score."""
        return float(temperature_scale(raw_score, temperature=self.prosody_temp))

    def calibrate_wavlm(self, raw_score: float) -> float:
        """Calibrate raw WavLM complementary spoof score."""
        return float(temperature_scale(raw_score, temperature=self.wavlm_temp))
