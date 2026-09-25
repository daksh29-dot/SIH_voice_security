"""
tests/test_model.py

Step 2 of Phase 1: verify the ONNX model loads and inspect its true
input/output name, shape, and dtype. Run this BEFORE trusting any
assumptions baked into config.py.
"""

import numpy as np
import pytest

import src.config
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
def test_input_shape_matches_fixed_window_config():
    model = AasistOnnxModel()
    input_shape = model.input_info()["shape"]

    fixed_dims = [d for d in input_shape if isinstance(d, int) and d > 1]
    assert fixed_dims, f"Expected a fixed sample-count dimension in {input_shape}"
    assert fixed_dims[0] == config.FIXED_WINDOW_SAMPLES, (
        f"Model expects {fixed_dims[0]} samples but config.FIXED_WINDOW_SAMPLES "
        f"is {config.FIXED_WINDOW_SAMPLES} — update config.py"
    )


@pytest.mark.skipif(not MODEL_AVAILABLE, reason="aasist-l.onnx not present in models/")
def test_predict_segment_returns_float_in_range():
    model = AasistOnnxModel()
    dummy_segment = np.random.uniform(-1, 1, size=config.FIXED_WINDOW_SAMPLES).astype(np.float32)
    score = model.predict_segment(dummy_segment)

    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0, (
        f"Score {score} outside [0,1] — model output convention may need "
        f"adjustment in aasist_onnx.predict_segment()"
    )