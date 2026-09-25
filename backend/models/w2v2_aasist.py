"""VISOR W2V2-AASIST adapter. Scores are uncalibrated, not probabilities.

Existing predict(waveform) calls continue to mean 16 kHz mono PCM. If the
browser sends 44.1/48 kHz, the caller MUST supply its actual sample_rate (or
already resample). A waveform alone contains no sample-rate metadata.
Reference: TakHemlata/SSL_Anti-spoofing/data_utils_SSL.py (16k, repeat padding).
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, Tuple, Dict, Any
import math
import time
import threading
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def prepare_pcm(waveform, sample_rate=16000, channel_axis=None):
    """PCM to float32 mono 16 kHz, shared by enrollment and both live models.

    Supports signed int16/int32, unsigned uint8, float PCM and unambiguous
    [samples,channels]/[channels,samples]. Never flatten/interleave channels.
    Encoded WebM/Opus bytes must be decoded upstream; float integer-scale PCM
    is rejected instead of guessing its scale. No peak normalization/denoising.
    """
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, (int, np.integer)) or not 8000 <= sample_rate <= 192000:
        raise ValueError("Supply the actual integer sample rate (8000..192000 Hz)")
    x = np.asarray(waveform)
    if x.ndim not in (1, 2) or x.size == 0:
        raise ValueError("Expected non-empty mono or stereo PCM, not encoded media")
    if x.dtype.kind == 'i' and x.dtype.itemsize in (2, 4):
        x = x.astype(np.float64) / float(2 ** (8*x.dtype.itemsize-1))
    elif x.dtype == np.uint8:
        x = (x.astype(np.float64)-128.0)/128.0
    elif x.dtype.kind != 'f':
        raise ValueError("Expected float PCM, int16/int32 PCM or uint8 PCM")
    if not np.isfinite(x).all() or np.max(np.abs(x)) > 1.5:
        raise ValueError("Invalid PCM amplitude; convert integer-scale floats correctly upstream")
    if x.ndim == 2:
        if channel_axis is None:
            possible = [i for i, n in enumerate(x.shape) if n in (1, 2)]
            if len(possible) != 1:
                raise ValueError("Ambiguous audio shape; pass channel_axis explicitly")
            channel_axis = possible[0]
        if channel_axis not in (0, 1, -1, -2) or x.shape[channel_axis] not in (1, 2):
            raise ValueError("Expected one or two channels")
        x = x.mean(axis=channel_axis)
    x = np.ascontiguousarray(x, dtype=np.float32)
    if sample_rate != 16000:
        from scipy.signal import resample_poly
        divisor = math.gcd(int(sample_rate), 16000)
        x = resample_poly(x, 16000//divisor, int(sample_rate)//divisor).astype(np.float32)
    return x


def audio_quality_reasons(x, min_seconds=1.0):
    """Basic PCM gates, not a VAD or proof of genuine speech."""
    reasons = []
    if len(x) < int(min_seconds*16000):
        reasons.append('insufficient_audio_duration')
    centered = x.astype(np.float64) - float(x.mean())
    if np.sqrt(np.mean(centered**2)) < 1e-3:
        reasons.append('silent_or_too_quiet')
    if float(np.mean(np.abs(x) >= .999)) > .01:
        reasons.append('excessive_clipping')
    return reasons


def find_w2v2_aasist_model() -> Path:
    for path in (PROJECT_ROOT/'models'/'w2v2-aasist.onnx', PROJECT_ROOT/'models'/'w2v2_aasist.onnx'):
        if path.is_file():
            return path
    try:
        import config
        path = Path(config.MODEL_PATH)
        if path.is_file():
            return path
    except (ImportError, AttributeError):
        pass
    raise FileNotFoundError('W2V2-AASIST model missing from models/w2v2-aasist.onnx')


@dataclass
class W2V2AASISTPrediction:
    raw_logits: Tuple[float, ...]
    spoof_score: float
    inference_time_ms: float
    bona_fide_score: float
    score_kind: str = 'uncalibrated_softmax'
    input_seconds: float = 0.0
    valid_audio: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {'raw_logits': list(self.raw_logits), 'spoof_score': float(self.spoof_score),
                'bona_fide_score': float(self.bona_fide_score),
                'inference_time_ms': float(self.inference_time_ms),
                'score_kind': self.score_kind, 'input_seconds': self.input_seconds,
                'valid_audio': self.valid_audio}


class W2V2AASISTModel:
    WINDOW_SAMPLES = 64600

    def __init__(self, model_path: Optional[Union[str, Path]] = None, num_threads: int = 4,
                 *, output_name=None, output_kind='logits', spoof_index=0):
        import onnxruntime as ort
        self.model_path = Path(model_path) if model_path is not None else find_w2v2_aasist_model()
        if not self.model_path.is_file():
            raise FileNotFoundError(self.model_path)
        if output_kind not in ('logits', 'probabilities') or spoof_index not in (0, 1):
            raise ValueError('Explicit two-class output contract required')
        if not isinstance(num_threads, int) or num_threads < 1:
            raise ValueError('num_threads must be positive')
        options = ort.SessionOptions()
        options.intra_op_num_threads = num_threads
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(str(self.model_path), sess_options=options,
                                           providers=['CPUExecutionProvider'])
        ins, outs = self.session.get_inputs(), self.session.get_outputs()
        if len(ins) != 1 or ins[0].type != 'tensor(float)' or len(ins[0].shape) != 2:
            raise ValueError('Expected one float32 [batch,samples] ONNX input')
        batch, length = ins[0].shape
        if isinstance(batch, int) and batch != 1:
            raise ValueError('Model batch must be 1')
        if isinstance(length, int) and length != self.WINDOW_SAMPLES:
            raise ValueError(f'Graph window {length} differs from 64600; check checkpoint/export')
        if output_name is None:
            candidates = [o for o in outs if o.type == 'tensor(float)' and len(o.shape) == 2 and o.shape[-1] == 2]
            if len(candidates) != 1:
                raise ValueError('Set output_name to the classifier output; graph is ambiguous')
            output_name = candidates[0].name
        if output_name not in {o.name for o in outs}:
            raise ValueError('Classifier output not found')
        self.input_name, self.output_name = ins[0].name, output_name
        self.output_kind, self.spoof_index = output_kind, spoof_index

    def predict(self, waveform: np.ndarray, sample_rate=16000, *, channel_axis=None) -> W2V2AASISTPrediction:
        x = prepare_pcm(waveform, sample_rate, channel_axis)
        # Rolling streams must score the newest window, not stale audio at the front.
        wav = x[-self.WINDOW_SAMPLES:]
        reasons = audio_quality_reasons(wav)
        if reasons:
            # Returning 0 would falsely mark silence as genuine; fail explicitly.
            raise ValueError('Cannot score audio: ' + ', '.join(reasons))
        duration = len(wav)/16000
        if len(wav) < self.WINDOW_SAMPLES:
            wav = np.tile(wav, (self.WINDOW_SAMPLES+len(wav)-1)//len(wav))[:self.WINDOW_SAMPLES]
        start = time.perf_counter()
        output = self.session.run([self.output_name], {self.input_name: np.ascontiguousarray(wav[None])})[0]
        elapsed = (time.perf_counter()-start)*1000
        logits = np.asarray(output, dtype=np.float64)
        if logits.shape != (1, 2) or not np.isfinite(logits).all():
            raise ValueError(f'Expected finite classifier [1,2], got {logits.shape}')
        values = logits[0]
        if self.output_kind == 'logits':
            probabilities = np.exp(values-values.max())
            probabilities /= probabilities.sum()
        else:
            if np.any(values < 0) or np.any(values > 1) or not np.isclose(values.sum(), 1, atol=1e-4):
                raise ValueError('Model does not return configured class probabilities')
            probabilities = values
        return W2V2AASISTPrediction(tuple(map(float, values)), float(probabilities[self.spoof_index]),
                                  elapsed, float(probabilities[1-self.spoof_index]),
                                  'uncalibrated_softmax' if self.output_kind == 'logits' else 'uncalibrated_model_score',
                                  duration)


_global_w2v2_aasist = None
_global_lock = threading.Lock()


def get_w2v2_aasist_model() -> W2V2AASISTModel:
    global _global_w2v2_aasist
    with _global_lock:
        if _global_w2v2_aasist is None:
            _global_w2v2_aasist = W2V2AASISTModel()
        return _global_w2v2_aasist
