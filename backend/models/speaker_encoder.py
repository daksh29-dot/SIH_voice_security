"""ECAPA-TDNN enrollment/verification with identical PCM preparation.

encode_batch requires mono 16 kHz; it does NOT resample. Optional sample_rate
arguments describe the actual input rate. Existing calls still assume 16 kHz.
Cosine similarity and the compatibility consistency score are not probabilities.
Reference: https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb
"""
from pathlib import Path
from typing import Dict, Any, Optional, Union
import os
import re
import tempfile
import threading
import warnings
import numpy as np

if __package__:
    from .w2v2_aasist import prepare_pcm, audio_quality_reasons
else:
    from w2v2_aasist import prepare_pcm, audio_quality_reasons

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODEL_DIR = PROJECT_ROOT / 'models' / 'spkrec-ecapa-voxceleb'
DEFAULT_ENROLLED_DIR = PROJECT_ROOT / 'models' / 'enrolled_speakers'


class SpeakerEncoder:
    # Preserve the application's authentication policy. 0.72 was not calibrated
    # in the supplied code. Tune using held-out same/different-speaker pairs;
    # SpeechBrain's example 0.25 is also NOT a universal production threshold.
    SIMILARITY_THRESHOLD = 0.72

    def __init__(self, model_dir: Optional[Union[str, Path]] = None,
                 enrolled_dir: Optional[Union[str, Path]] = None,
                 similarity_threshold: float = SIMILARITY_THRESHOLD, device: str = 'cpu'):
        self.model_dir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
        self.enrolled_dir = Path(enrolled_dir) if enrolled_dir else DEFAULT_ENROLLED_DIR
        self.enrolled_dir.mkdir(parents=True, exist_ok=True)
        self.similarity_threshold = self._threshold(similarity_threshold)
        self.device = device
        self._lock = threading.RLock()
        self._load_encoder()
        self.enrolled_speakers: Dict[str, np.ndarray] = {}
        self._load_existing_enrollments()

    @staticmethod
    def _threshold(value):
        value = float(value)
        if not np.isfinite(value) or not -1 < value < 1:
            raise ValueError('Cosine threshold must be finite and between -1 and 1')
        return value

    @staticmethod
    def _speaker_id(value):
        value = str(value).strip()
        if not value or value in ('.', '..') or len(value) > 180 or re.search(r'[\\/\x00-\x1f<>:"|?*]', value):
            raise ValueError('Invalid speaker ID')
        return value

    @staticmethod
    def _unit_embedding(value):
        value = np.asarray(value, dtype=np.float32)
        if value.shape != (192,) or not np.isfinite(value).all():
            raise ValueError('Invalid 192-dimensional voiceprint')
        norm = float(np.linalg.norm(value.astype(np.float64)))
        if norm < 1e-8:
            raise ValueError('Zero voiceprint; enroll again using valid speech')
        return (value/norm).astype(np.float32)

    def _load_encoder(self):
        from speechbrain.inference.speaker import EncoderClassifier
        from speechbrain.utils.fetching import LocalStrategy
        self.classifier = EncoderClassifier.from_hparams(
            source='speechbrain/spkrec-ecapa-voxceleb', savedir=str(self.model_dir),
            run_opts={'device': self.device}, local_strategy=LocalStrategy.COPY)
        self.classifier.eval()

    def _load_existing_enrollments(self):
        for path in self.enrolled_dir.glob('*.npy'):
            try:
                speaker_id = self._speaker_id(path.stem)
                self.enrolled_speakers[speaker_id] = self._unit_embedding(np.load(path, allow_pickle=False))
            except (ValueError, OSError) as exc:
                warnings.warn(f'Ignoring invalid voiceprint {path.name}: {exc}', RuntimeWarning)

    def extract_embedding(self, audio_array: np.ndarray, sample_rate=16000, *, channel_axis=None) -> np.ndarray:
        import torch
        audio = prepare_pcm(audio_array, sample_rate, channel_axis)
        reasons = audio_quality_reasons(audio, min_seconds=1.0)
        if reasons:
            raise ValueError('Cannot extract voiceprint: ' + ', '.join(reasons))
        if len(audio) > 120*16000:
            raise ValueError('Use at most 120 seconds per voiceprint')
        # Use contiguous speech-containing windows for long enrollment recordings.
        # Mean unit embeddings, then renormalize; never include zero/silent vectors.
        size, hop = 6*16000, 3*16000
        starts = [0] if len(audio) <= size else list(range(0, len(audio)-size+1, hop))
        if len(audio) > size and starts[-1] != len(audio)-size:
            starts.append(len(audio)-size)
        embeddings = []
        with self._lock, torch.inference_mode():
            for start in starts:
                chunk = audio[start:start+size]
                if audio_quality_reasons(chunk):
                    continue
                tensor = torch.from_numpy(np.ascontiguousarray(chunk)).unsqueeze(0).to(self.device)
                value = self.classifier.encode_batch(tensor, normalize=False)
                embeddings.append(self._unit_embedding(value.detach().cpu().numpy().reshape(-1)))
        if not embeddings:
            raise ValueError('No usable audio window for speaker embedding')
        return self._unit_embedding(np.mean(embeddings, axis=0))

    def enroll_speaker(self, speaker_id: str, audio_array: np.ndarray, sample_rate=16000,
                       *, channel_axis=None) -> np.ndarray:
        clean_id = self._speaker_id(speaker_id)
        audio = prepare_pcm(audio_array, sample_rate, channel_axis)
        reasons = audio_quality_reasons(audio, min_seconds=2.0)
        if reasons:
            raise ValueError('Enrollment requires usable speech: ' + ', '.join(reasons))
        emb = self.extract_embedding(audio)
        # Atomic replacement prevents another worker reading a half-written file.
        with self._lock:
            fd, temp_path = tempfile.mkstemp(prefix='.enroll-', suffix='.tmp', dir=self.enrolled_dir)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    np.save(stream, emb, allow_pickle=False)
                os.replace(temp_path, self.enrolled_dir / f'{clean_id}.npy')
                self.enrolled_speakers[clean_id] = emb.copy()
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        return emb

    def verify_speaker(self, speaker_id: str, current_audio: np.ndarray,
                       threshold: Optional[float] = None, sample_rate=16000,
                       *, channel_axis=None) -> Dict[str, Any]:
        clean_id = self._speaker_id(speaker_id)
        active_thresh = self._threshold(self.similarity_threshold if threshold is None else threshold)
        unknown = {'similarity': 0.0, 'is_match': None, 'speaker_consistency_score': 0.0,
                   'status': 'unavailable', 'threshold': active_thresh, 'calibrated': False}
        try:
            # Refresh from disk: enrollment and live verification may run in
            # different backend workers. Never silently reuse a deleted profile.
            path = self.enrolled_dir / f'{clean_id}.npy'
            with self._lock:
                if not path.is_file():
                    self.enrolled_speakers.pop(clean_id, None)
                    return {**unknown, 'error': f"Speaker '{clean_id}' is not enrolled."}
                ref = self._unit_embedding(np.load(path, allow_pickle=False))
                self.enrolled_speakers[clean_id] = ref
            live = self.extract_embedding(current_audio, sample_rate, channel_axis=channel_axis)
        except (ValueError, OSError) as exc:
            return {**unknown, 'error': str(exc)}
        similarity = float(np.clip(np.dot(live, ref), -1, 1))
        match = bool(similarity >= active_thresh)
        # Preserve the old display scale for callers. It is only a heuristic;
        # RiskEngine must use is_match, not threshold this a second time.
        consistency = float(np.clip((similarity-.20)/.65, 0, 1))
        return {'similarity': round(similarity, 4), 'is_match': match,
                'speaker_consistency_score': round(consistency, 4),
                'status': 'match' if match else 'no_match', 'threshold': active_thresh,
                'calibrated': False, 'score_kind': 'cosine_similarity'}

    def list_enrolled_speakers(self) -> list[str]:
        with self._lock:
            self.enrolled_speakers.clear()
            self._load_existing_enrollments()
            return sorted(self.enrolled_speakers)


_global_speaker_encoder = None
_global_lock = threading.Lock()


def get_speaker_encoder() -> SpeakerEncoder:
    global _global_speaker_encoder
    with _global_lock:
        if _global_speaker_encoder is None:
            _global_speaker_encoder = SpeakerEncoder()
        return _global_speaker_encoder
