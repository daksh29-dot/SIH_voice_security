"""
tests/test_model.py

Step 2 of Phase 1: verify the ONNX model loads and inspect its true
input/output name, shape, and dtype. Run this BEFORE trusting any
assumptions baked into config.py.
"""

import numpy as np
import pytest

import config
from aasist_onnx import AasistOnnxModel


MODEL_AVAILABLE = config.MODEL_PATH.exists()


@pytest.mark.skipif(not MODEL_AVAILABLE, reason="aasist-l.onnx not present in models/")
def test_model_loads():
    model = AasistOnnxModel()
    assert model.session is not None


@pytest.mark.skipif(not MODEL_AVAILABLE, reason="aasist-l.onnx not present in models/")
def test_input_output_shapes_reported():
    model = AasistOnnxModel()
    input_info = model.input_info()
    output_info = model.output_info()

    print("\nInput: ", input_info)
    print("Output:", output_info)

    assert input_info["name"]
    assert output_info["name"]


@pytest.mark.skipif(not MODEL_AVAILABLE, reason="aasist-l.onnx not present in models/")
def test_predict_segment_returns_float_in_range():
    model = AasistOnnxModel()
    input_shape = model.input_info()["shape"]

    # Fall back to config's expected segment length if the model reports a
    # dynamic axis (commonly shown as a string like "batch" or -1).
    n_samples = int(config.SEGMENT_LENGTH_SECONDS * config.TARGET_SAMPLE_RATE)
    for dim in input_shape:
        if isinstance(dim, int) and dim > 1:
            n_samples = dim

    dummy_segment = np.random.uniform(-1, 1, size=n_samples).astype(np.float32)
    score = model.predict_segment(dummy_segment)

    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0, (
        f"Score {score} outside [0,1] — model output convention may need "
        f"adjustment in aasist_onnx.predict_segment()"
    )
