"""
backend/nlp/transcription.py

Automatic Speech Recognition (ASR) module for Project VISOR using faster-whisper.
Runs `tiny.en` (or `base.en`) on CPU with INT8 quantization for sub-second transcription.
Provides an asynchronous worker queue that transcribes completed speech utterances
triggered by VAD pause boundaries (> 600ms silence).
"""

import time
import queue
import threading
from typing import Dict, Any, Optional, List, Callable
import numpy as np
from faster_whisper import WhisperModel


class WhisperTranscriber:
    """
    Lightweight ASR inference wrapper using faster-whisper on CPU with INT8 quantization.
    """

    def __init__(
        self,
        model_size: str = "tiny.en",
        device: str = "cpu",
        compute_type: str = "int8",
        num_threads: int = 2,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

        print(f"[*] Initializing faster-whisper '{model_size}' (device={device}, compute_type={compute_type})...")
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=num_threads,
        )
        print(f"[+] faster-whisper '{model_size}' initialized successfully.")

    def transcribe(
        self,
        audio_buffer: np.ndarray,
        sample_rate: int = 16000,
    ) -> Dict[str, Any]:
        """
        Transcribe a 16kHz mono float32 audio buffer into text.

        Args:
            audio_buffer: 1D numpy array of audio samples
            sample_rate: Audio sampling frequency in Hz (default: 16000)

        Returns:
            Dict[str, Any]:
                - "transcript": str
                - "duration": float (in seconds)
                - "latency_ms": float (in milliseconds)
        """
        audio = np.asarray(audio_buffer, dtype=np.float32).flatten()
        duration_sec = len(audio) / float(sample_rate) if sample_rate > 0 else 0.0

        if len(audio) < 1600:
            # Under 100ms: return empty
            return {
                "transcript": "",
                "duration": duration_sec,
                "latency_ms": 0.0,
            }

        t0 = time.perf_counter()
        segments, info = self.model.transcribe(
            audio,
            beam_size=1,
            condition_on_previous_text=False,
            temperature=0.0,
            vad_filter=False,  # Audio has already been segmented by Silero VAD
        )

        texts = [s.text.strip() for s in segments if s.text and s.text.strip()]
        full_text = " ".join(texts).strip()
        latency_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "transcript": full_text,
            "duration": round(duration_sec, 2),
            "latency_ms": round(latency_ms, 2),
        }


class UtteranceAccumulator:
    """
    Monitors streaming audio chunks and VAD activity to isolate discrete utterances.
    Triggers an utterance completion when silence > silence_boundary_ms (default: 600ms)
    occurs after active speech.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        silence_boundary_ms: float = 600.0,
        min_speech_ms: float = 400.0,
    ):
        self.sample_rate = sample_rate
        self.silence_boundary_ms = silence_boundary_ms
        self.min_speech_ms = min_speech_ms

        self._in_speech = False
        self._speech_buffer: List[np.ndarray] = []
        self._current_silence_ms = 0.0
        self._total_speech_samples = 0

    def process_frame(
        self,
        audio_chunk: np.ndarray,
        is_speech: bool,
    ) -> Optional[np.ndarray]:
        """
        Ingest an audio frame. If an end-of-utterance boundary is reached,
        returns the completed utterance numpy array; otherwise returns None.
        """
        chunk = np.asarray(audio_chunk, dtype=np.float32).flatten()
        chunk_duration_ms = (len(chunk) / self.sample_rate) * 1000.0

        if is_speech:
            self._in_speech = True
            self._current_silence_ms = 0.0
            self._speech_buffer.append(chunk)
            self._total_speech_samples += len(chunk)
            return None
        else:
            if self._in_speech:
                self._current_silence_ms += chunk_duration_ms
                # Retain short trailing silence up to 250ms for natural audio envelope
                if self._current_silence_ms <= 250.0:
                    self._speech_buffer.append(chunk)

                if self._current_silence_ms >= self.silence_boundary_ms:
                    # Utterance boundary reached! Check minimum speech duration
                    speech_duration_ms = (self._total_speech_samples / self.sample_rate) * 1000.0
                    completed_audio = None
                    if speech_duration_ms >= self.min_speech_ms and self._speech_buffer:
                        completed_audio = np.concatenate(self._speech_buffer)

                    # Reset state for next utterance
                    self.reset()
                    return completed_audio
            return None

    def reset(self) -> None:
        """Reset internal accumulator buffers."""
        self._in_speech = False
        self._speech_buffer = []
        self._current_silence_ms = 0.0
        self._total_speech_samples = 0


class AsyncASRWorker:
    """
    Asynchronous ASR worker thread. Transcribes completed utterance buffers from a queue
    and triggers downstream NLP callbacks without blocking the real-time audio thread.
    """

    def __init__(
        self,
        transcriber: Optional[WhisperTranscriber] = None,
        on_utterance_transcribed: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.transcriber = transcriber or WhisperTranscriber()
        self.on_utterance_transcribed = on_utterance_transcribed

        self._queue: queue.Queue = queue.Queue()
        self._running = True
        self._lock = threading.Lock()
        self._utterances: List[Dict[str, Any]] = []

        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="AsyncASRWorker",
        )
        self._worker_thread.start()

    def submit_utterance(self, audio: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Non-blocking queue submission from the audio loop."""
        if audio is None or len(audio) == 0:
            return
        item = {
            "audio": audio.copy(),
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        self._queue.put_nowait(item)

    def _worker_loop(self) -> None:
        while self._running:
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                audio = item["audio"]
                res = self.transcriber.transcribe(audio)

                if res.get("transcript"):
                    payload = {
                        "transcript": res["transcript"],
                        "duration": res["duration"],
                        "latency_ms": res["latency_ms"],
                        "timestamp": item["timestamp"],
                        "metadata": item["metadata"],
                    }
                    with self._lock:
                        self._utterances.append(payload)

                    if self.on_utterance_transcribed:
                        try:
                            self.on_utterance_transcribed(payload)
                        except Exception as cb_err:
                            print(f"[!] ASR callback error: {cb_err}")
            except Exception as e:
                print(f"[!] ASR transcription error: {e}")
            finally:
                self._queue.task_done()

    def get_full_transcript(self) -> str:
        """Return the combined transcript of all transcribed utterances so far."""
        with self._lock:
            return " ".join(u["transcript"] for u in self._utterances).strip()

    def get_latest_utterance(self) -> Optional[Dict[str, Any]]:
        """Return the most recently transcribed utterance dict, if any."""
        with self._lock:
            if not self._utterances:
                return None
            return self._utterances[-1].copy()

    def get_all_utterances(self) -> List[Dict[str, Any]]:
        """Return a copy of all utterances."""
        with self._lock:
            return [u.copy() for u in self._utterances]

    def clear(self) -> None:
        """Clear session utterances and drain queue."""
        with self._lock:
            self._utterances = []
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Exception:
                break

    def stop(self) -> None:
        """Stop worker thread."""
        self._running = False


# Global singleton
_global_transcriber: Optional[WhisperTranscriber] = None


def get_whisper_transcriber() -> WhisperTranscriber:
    """Retrieve or initialize the global shared WhisperTranscriber singleton."""
    global _global_transcriber
    if _global_transcriber is None:
        _global_transcriber = WhisperTranscriber()
    return _global_transcriber
