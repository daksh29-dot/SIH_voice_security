"""Strict ONNX two-class adapter. Never infer output semantics from file names."""
import hashlib
import json
from pathlib import Path
import numpy as np
from config import DEFAULTS, MODEL_PATH
from aggregation import sigmoid

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def output_margin(output, kind="logits", spoof_index=0):
    a = np.asarray(output, dtype=np.float64)
    if a.shape != (1, 2) or not np.isfinite(a).all():
        raise ValueError(f"Expected finite classifier output [1,2], got {a.shape}")
    if spoof_index not in (0, 1):
        raise ValueError("Invalid spoof class index")
    if kind == "logits":
        return float(a[0, spoof_index] - a[0, 1-spoof_index])
    if kind != "probabilities" or np.any(a < 0) or np.any(a > 1) or not np.allclose(a.sum(), 1, atol=1e-4):
        raise ValueError("Output does not match configured probability contract")
    p = np.clip(a[0], 1e-12, 1-1e-12)
    return float(np.log(p[spoof_index]) - np.log(p[1-spoof_index]))

class W2V2AASISTSpoofDetector:
    def __init__(self, model_path=MODEL_PATH, settings=DEFAULTS, providers=None):
        import onnxruntime as ort
        self.settings = settings
        self.model_path = Path(model_path).resolve(strict=True)
        available = ort.get_available_providers()
        if providers is None:
            providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in available]
        if not providers or any(p not in available for p in providers):
            raise ValueError(f"Requested unavailable provider; installed: {available}")
        # Windows-only preload is optional and never required by CPU inference.
        import sys
        if sys.platform == "win32" and "CUDAExecutionProvider" in providers and hasattr(ort, "preload_dlls"):
            ort.preload_dlls()
        self.session = ort.InferenceSession(str(self.model_path), providers=providers)
        ins, outs = self.session.get_inputs(), self.session.get_outputs()
        if len(ins) != 1 or ins[0].type != "tensor(float)" or len(ins[0].shape) != 2:
            raise ValueError("Adapter requires one float32 [batch,samples] input; inspect your export")
        batch, length = ins[0].shape
        if isinstance(batch, int) and batch != 1:
            raise ValueError("Static model batch size is not 1")
        if isinstance(length, int) and length != settings.window_samples:
            raise ValueError(f"Graph requires {length} samples, config says {settings.window_samples}")
        self.input_name = ins[0].name
        candidates = [o for o in outs if o.type == "tensor(float)" and len(o.shape) == 2 and o.shape[-1] == 2]
        if settings.output_name is None and len(candidates) != 1:
            raise ValueError("Set classifier output_name explicitly; ONNX output is ambiguous")
        self.output_name = settings.output_name or candidates[0].name
        if self.output_name not in {o.name for o in outs}:
            raise ValueError("Classifier output_name not found")
        selected = next(o for o in outs if o.name == self.output_name)
        if (selected.type != "tensor(float)" or len(selected.shape) != 2
                or (isinstance(selected.shape[-1], int) and selected.shape[-1] != 2)):
            raise ValueError("Selected output must be float32 [batch,2] class scores")
        # Include external data files explicitly in the contract if your export uses them.
        assets = [(self.model_path.name, sha256_file(self.model_path))]
        for name in settings.external_weights:
            assets.append((name, sha256_file(self.model_path.parent / name)))
        self.identity = assets
        self.metadata = {"inputs": [(i.name, i.shape, i.type) for i in ins],
                         "outputs": [(o.name, o.shape, o.type) for o in outs],
                         "providers": self.session.get_providers(), "assets_sha256": assets,
                         "custom_metadata": self.session.get_modelmeta().custom_metadata_map}

    def predict_margin(self, waveform):
        x = np.asarray(waveform, dtype=np.float32)
        if x.shape != (self.settings.window_samples,) or not np.isfinite(x).all():
            raise ValueError("Supply exactly one complete finite window; no hidden padding/truncation")
        output = self.session.run([self.output_name], {self.input_name: np.ascontiguousarray(x[None])})[0]
        return output_margin(output, self.settings.output_kind, self.settings.spoof_index)

    def predict_segment(self, waveform):
        """Compatibility method: uncalibrated score, NOT a measured spoof probability."""
        return sigmoid(self.predict_margin(waveform))

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("model", nargs="?", default=str(MODEL_PATH))
    args = p.parse_args()
    # Inspection intentionally does not assume rank, classifier output, or class order.
    import onnxruntime as ort
    s = ort.InferenceSession(args.model, providers=["CPUExecutionProvider"])
    print(json.dumps({"sha256": sha256_file(args.model),
        "inputs": [(x.name, x.shape, x.type) for x in s.get_inputs()],
        "outputs": [(x.name, x.shape, x.type) for x in s.get_outputs()],
        "metadata": s.get_modelmeta().custom_metadata_map}, indent=2))
