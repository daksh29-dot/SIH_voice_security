"""
backend/models/wavlm.py

Complementary WavLM acoustic representation and secondary spoof estimation branch for Project VISOR.
Wraps WavLM (microsoft/wavlm-base-plus) with INT8 ONNX Runtime acceleration and provides
an asynchronous background worker running at lower frequency (~1.5s cadence) to avoid
blocking the real-time audio pipeline.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union
import time
import threading
import numpy as np
import onnxruntime as ort

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_ONNX_PATH = PROJECT_ROOT / "models" / "wavlm-base-plus-int8.onnx"
DEFAULT_FP32_ONNX_PATH = PROJECT_ROOT / "models" / "wavlm-base-plus.onnx"


def export_wavlm_to_onnx(
    output_path: Union[str, Path] = DEFAULT_ONNX_PATH,
    quantize_int8: bool = True,
    sample_rate: int = 16000,
) -> Path:
    """
    Automated export utility to convert `microsoft/wavlm-base-plus` to ONNX
    and optionally apply INT8 dynamic quantization for low-latency CPU inference.
    """
    import torch
    from transformers import WavLMModel

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_fp32_path = output_path.parent / "wavlm-temp-fp32.onnx"

    print(f"[*] Exporting WavLM (microsoft/wavlm-base-plus) to ONNX...")
    model = WavLMModel.from_pretrained("microsoft/wavlm-base-plus")
    model.eval()

    # Dummy 1-second audio input at 16kHz
    dummy_input = torch.randn(1, 16000, dtype=torch.float32)

    torch.onnx.export(
        model,
        dummy_input,
        str(temp_fp32_path),
        input_names=["input_values"],
        output_names=["last_hidden_state"],
        dynamic_axes={
            "input_values": {0: "batch_size", 1: "sequence_length"},
            "last_hidden_state": {0: "batch_size", 1: "time_steps"},
        },
        opset_version=14,
        do_constant_folding=True,
    )
    print(f"[+] FP32 ONNX model exported to {temp_fp32_path}")

    if quantize_int8:
        print(f"[*] Applying INT8 dynamic quantization to WavLM ONNX model...")
        from onnxruntime.quantization import quantize_dynamic, QuantType

        quantize_dynamic(
            model_input=str(temp_fp32_path),
            model_output=str(output_path),
            weight_type=QuantType.QInt8,
        )
        if temp_fp32_path.exists():
            temp_fp32_path.unlink()
        print(f"[+] INT8 Quantized WavLM saved to {output_path} ({output_path.stat().st_size // (1024*1024)} MB)")
    else:
        if temp_fp32_path != output_path:
            temp_fp32_path.rename(output_path)

    return output_path


class WavLMModelWrapper:
    """
    Inference wrapper for WavLM.
    Uses ONNX Runtime CPU if available, otherwise falls back smoothly to PyTorch WavLMModel.
    Extracts 768-dimensional acoustic embeddings and computes a complementary spoof score.
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        use_onnx: bool = True,
        num_threads: int = 2,
    ):
        self.model_path = Path(model_path) if model_path else DEFAULT_ONNX_PATH
        self.session: Optional[ort.InferenceSession] = None
        self.torch_model = None

        if use_onnx and (self.model_path.exists() or DEFAULT_FP32_ONNX_PATH.exists()):
            active_path = self.model_path if self.model_path.exists() else DEFAULT_FP32_ONNX_PATH
            print(f"[*] Loading WavLM ONNX model from {active_path}...")
            sess_opts = ort.SessionOptions()
            sess_opts.intra_op_num_threads = num_threads
            sess_opts.inter_op_num_threads = 1
            sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self.session = ort.InferenceSession(
                str(active_path),
                sess_options=sess_opts,
                providers=["CPUExecutionProvider"],
            )
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            print(f"[+] WavLM ONNX loaded. Input: '{self.input_name}', Output: '{self.output_name}'")
        else:
            # Fallback to PyTorch transformers WavLMModel in eval mode
            print("[*] ONNX model not found on disk. Initializing PyTorch WavLMModel fallback...")
            import torch
            try:
                from transformers import WavLMModel
            except ImportError:
                import importlib
                import transformers
                importlib.reload(transformers)
                from transformers import WavLMModel

            self.torch_model = WavLMModel.from_pretrained("microsoft/wavlm-base-plus")
            self.torch_model.eval()
            print("[+] PyTorch WavLMModel initialized successfully.")

    def compute_representation(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract pooled representation and compute secondary spoof score.

        Args:
            audio: 1D numpy array of 16kHz mono audio

        Returns:
            Dict[str, Any]:
                - "embedding": 768-dim float32 numpy array
                - "wavlm_score": float in [0.0, 1.0] (secondary spoof estimation)
                - "latency_ms": float
        """
        wav = np.asarray(audio, dtype=np.float32).flatten()
        if len(wav) < 1600:
            # Minimum ~0.1s for WavLM
            padded = np.zeros(1600, dtype=np.float32)
            padded[: len(wav)] = wav
            wav = padded

        t0 = time.perf_counter()

        if self.session is not None:
            input_tensor = wav[np.newaxis, :].astype(np.float32)
            out = self.session.run([self.output_name], {self.input_name: input_tensor})[0]
            # out shape: [1, time_steps, 768]
            hidden_states = out[0]
        else:
            import torch
            with torch.no_grad():
                tensor = torch.from_numpy(wav).unsqueeze(0).float()
                out = self.torch_model(tensor).last_hidden_state
                hidden_states = out[0].cpu().numpy()

        latency_ms = (time.perf_counter() - t0) * 1000.0

        # Mean pooling across time frames -> 768-dimensional embedding
        embedding = np.mean(hidden_states, axis=0).astype(np.float32)
        norm = np.linalg.norm(embedding)
        if norm > 1e-9:
            embedding = embedding / norm

        # Masked speech representation dispersion metric:
        # Cloned voices (neural vocoders) produce compressed inter-frame variance
        # in higher transformer layers compared to organic human acoustic dynamics.
        temporal_variance = float(np.mean(np.var(hidden_states, axis=0)))
        feature_dispersion = float(np.std(embedding))

        # Calibrate dispersion into secondary spoof likelihood [0.0, 1.0]
        # Low variance / flat feature dispersion -> higher synthetic score
        if temporal_variance < 0.08:
            spoof_est = 0.75 + (0.08 - temporal_variance) * 2.5
        elif temporal_variance < 0.20:
            spoof_est = 0.35 + (0.20 - temporal_variance) * 2.0
        else:
            spoof_est = max(0.05, 0.30 - (temporal_variance - 0.20) * 0.5)

        spoof_score = max(0.0, min(1.0, float(spoof_est)))

        return {
            "embedding": embedding,
            "wavlm_score": round(spoof_score, 4),
            "latency_ms": round(latency_ms, 2),
            "temporal_variance": round(temporal_variance, 4),
        }


class AsyncWavLMWorker:
    """
    Asynchronous background worker that runs WavLM inference at a lower cadence (~1.5s).
    Guarantees the primary real-time WebSocket audio processing loop is NEVER blocked.
    """

    def __init__(
        self,
        model: Optional[WavLMModelWrapper] = None,
        cadence_sec: float = 1.5,
    ):
        self.model = model or WavLMModelWrapper()
        self.cadence_sec = cadence_sec

        self._lock = threading.Lock()
        self._latest_audio: Optional[np.ndarray] = None
        self._latest_result: Optional[Dict[str, Any]] = None
        self._last_run_time: float = 0.0
        self._running: bool = True
        self._wake_event = threading.Event()

        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="WavLMAsyncWorker",
        )
        self._worker_thread.start()
        print(f"[+] AsyncWavLMWorker running in background (cadence: {cadence_sec}s).")

    def submit_audio(self, audio: np.ndarray) -> None:
        """Non-blocking audio update called from the real-time audio loop."""
        if audio is None or len(audio) == 0:
            return
        with self._lock:
            self._latest_audio = audio.copy()
        self._wake_event.set()

    def get_latest_score(self, max_stale_sec: float = 3.5) -> Tuple[Optional[float], bool]:
        """
        Non-blocking read of the latest computed WavLM spoof score.

        Returns:
            Tuple[Optional[float], bool]:
                - score: float in [0.0, 1.0] or None if not yet computed
                - is_fresh: True if score was computed within max_stale_sec
        """
        with self._lock:
            if self._latest_result is None:
                return None, False

            score = self._latest_result.get("wavlm_score")
            age = time.time() - self._last_run_time
            is_fresh = age <= max_stale_sec
            return score, is_fresh

    def _worker_loop(self) -> None:
        """Background thread executing WavLM at relaxed frequency."""
        while self._running:
            self._wake_event.wait(timeout=self.cadence_sec)
            self._wake_event.clear()

            if not self._running:
                break

            now = time.time()
            if now - self._last_run_time < self.cadence_sec:
                continue

            audio_to_process = None
            with self._lock:
                if self._latest_audio is not None and len(self._latest_audio) > 0:
                    audio_to_process = self._latest_audio.copy()
                    self._latest_audio = None

            if audio_to_process is not None:
                try:
                    result = self.model.compute_representation(audio_to_process)
                    with self._lock:
                        self._latest_result = result
                        self._last_run_time = time.time()
                except Exception as e:
                    print(f"[!] AsyncWavLMWorker computation error: {e}")

    def stop(self) -> None:
        """Signal thread shutdown."""
        self._running = False
        self._wake_event.set()


# Global shared instance with thread lock
_global_wavlm_worker: Optional[AsyncWavLMWorker] = None
_wavlm_init_lock = threading.Lock()


def get_wavlm_worker() -> AsyncWavLMWorker:
    """Retrieve or initialize the global shared AsyncWavLMWorker singleton thread-safely."""
    global _global_wavlm_worker
    if _global_wavlm_worker is None:
        with _wavlm_init_lock:
            if _global_wavlm_worker is None:
                _global_wavlm_worker = AsyncWavLMWorker()
    return _global_wavlm_worker

