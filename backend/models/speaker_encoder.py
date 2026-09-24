"""
backend/models/speaker_encoder.py

Biometric speaker verification using SpeechBrain's ECAPA-TDNN (spkrec-ecapa-voxceleb).
Extracts 192-dimensional embeddings, manages speaker enrollment profiles, and
verifies speaker consistency against reference voiceprints via cosine similarity.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Union
import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models" / "spkrec-ecapa-voxceleb"
DEFAULT_ENROLLED_DIR = PROJECT_ROOT / "models" / "enrolled_speakers"


class SpeakerEncoder:
    """
    ECAPA-TDNN 192-dimensional speaker encoder and verification engine.
    Computes cosine similarity against enrolled speaker reference voiceprints.
    """

    SIMILARITY_THRESHOLD = 0.72  # Default threshold for ECAPA-TDNN speaker verification

    def __init__(
        self,
        model_dir: Optional[Union[str, Path]] = None,
        enrolled_dir: Optional[Union[str, Path]] = None,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        device: str = "cpu",
    ):
        self.model_dir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
        self.enrolled_dir = Path(enrolled_dir) if enrolled_dir else DEFAULT_ENROLLED_DIR
        self.enrolled_dir.mkdir(parents=True, exist_ok=True)
        self.similarity_threshold = similarity_threshold
        self.device = device

        self._load_encoder()
        self.enrolled_speakers: Dict[str, np.ndarray] = {}
        self._load_existing_enrollments()

    def _load_encoder(self) -> None:
        """Initialize the SpeechBrain ECAPA-TDNN EncoderClassifier."""
        from speechbrain.inference.speaker import EncoderClassifier
        from speechbrain.utils.fetching import LocalStrategy

        print(f"[*] Loading ECAPA-TDNN speaker encoder from {self.model_dir}...")
        self.classifier = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=str(self.model_dir),
            run_opts={"device": self.device},
            local_strategy=LocalStrategy.COPY,
        )
        print("[+] ECAPA-TDNN speaker encoder loaded successfully (192-dim embeddings).")

    def _load_existing_enrollments(self) -> None:
        """Load any previously saved reference embeddings from disk."""
        for npy_file in self.enrolled_dir.glob("*.npy"):
            speaker_id = npy_file.stem
            try:
                emb = np.load(str(npy_file))
                if emb.shape == (192,):
                    self.enrolled_speakers[speaker_id] = emb
                    print(f"  [+] Loaded enrolled voiceprint for speaker '{speaker_id}'")
            except Exception as e:
                print(f"  [!] Failed to load enrollment for {npy_file}: {e}")

    def extract_embedding(self, audio_array: np.ndarray) -> np.ndarray:
        """
        Extract and L2-normalize a 192-dimensional speaker embedding from 16kHz mono audio.

        Args:
            audio_array: 1D numpy array of 16kHz audio samples

        Returns:
            np.ndarray: 192-dimensional unit vector (float32)
        """
        audio = np.asarray(audio_array, dtype=np.float32).flatten()
        if len(audio) == 0:
            return np.zeros(192, dtype=np.float32)

        # Minimum recommended duration for ECAPA-TDNN is ~0.5s (8000 samples)
        if len(audio) < 8000:
            padded = np.zeros(8000, dtype=np.float32)
            padded[: len(audio)] = audio
            audio = padded

        wav_tensor = torch.from_numpy(audio).unsqueeze(0).to(self.device)

        with torch.no_grad():
            embeddings = self.classifier.encode_batch(wav_tensor)
            # embeddings shape is [1, 1, 192]
            emb = embeddings.squeeze().cpu().numpy().astype(np.float32)

        # L2 Normalization
        norm = np.linalg.norm(emb)
        if norm > 1e-9:
            emb = emb / norm
        return emb

    def enroll_speaker(
        self,
        speaker_id: str,
        audio_array: np.ndarray,
    ) -> np.ndarray:
        """
        Generate and save a normalized 192-dimensional reference embedding for speaker_id.

        Args:
            speaker_id: Unique identifier for the speaker (e.g. "caller_123", "alice")
            audio_array: 1D numpy array containing enrollment speech audio

        Returns:
            np.ndarray: Normalized 192-dimensional reference embedding
        """
        clean_id = str(speaker_id).strip()
        emb = self.extract_embedding(audio_array)

        # Store in memory
        self.enrolled_speakers[clean_id] = emb

        # Persist to disk
        save_path = self.enrolled_dir / f"{clean_id}.npy"
        np.save(str(save_path), emb)
        print(f"[+] Enrolled speaker '{clean_id}' saved to {save_path}")

        return emb

    def verify_speaker(
        self,
        speaker_id: str,
        current_audio: np.ndarray,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Verify live audio against an enrolled speaker reference embedding.

        Args:
            speaker_id: Identifier of the enrolled target speaker
            current_audio: 1D numpy array of current audio chunk/window
            threshold: Optional similarity threshold override (defaults to self.similarity_threshold)

        Returns:
            Dict[str, Any]:
                - "similarity": float (cosine similarity between -1.0 and 1.0)
                - "is_match": bool (similarity >= threshold)
                - "speaker_consistency_score": float (calibrated confidence score [0.0, 1.0])
        """
        clean_id = str(speaker_id).strip()
        active_thresh = self.similarity_threshold if threshold is None else threshold

        if clean_id not in self.enrolled_speakers:
            return {
                "similarity": 0.0,
                "is_match": False,
                "speaker_consistency_score": 0.0,
                "error": f"Speaker '{clean_id}' is not enrolled.",
            }

        ref_emb = self.enrolled_speakers[clean_id]
        live_emb = self.extract_embedding(current_audio)

        # Cosine similarity for unit vectors: dot product
        similarity = float(np.dot(live_emb, ref_emb))
        is_match = bool(similarity >= active_thresh)

        # Calibrate similarity to a 0.0 - 1.0 consistency score:
        # ECAPA-TDNN cosine similarities typically range from ~0.2 (different speakers)
        # to ~0.85+ (same speaker).
        if similarity <= 0.20:
            consistency = 0.0
        elif similarity >= 0.85:
            consistency = 1.0
        else:
            consistency = float((similarity - 0.20) / (0.85 - 0.20))

        return {
            "similarity": round(similarity, 4),
            "is_match": is_match,
            "speaker_consistency_score": round(consistency, 4),
        }

    def list_enrolled_speakers(self) -> list[str]:
        """Return list of currently enrolled speaker IDs."""
        return sorted(list(self.enrolled_speakers.keys()))


# Global shared instance
_global_speaker_encoder: Optional[SpeakerEncoder] = None


def get_speaker_encoder() -> SpeakerEncoder:
    """Retrieve or initialize the global shared ECAPA-TDNN speaker encoder."""
    global _global_speaker_encoder
    if _global_speaker_encoder is None:
        _global_speaker_encoder = SpeakerEncoder()
    return _global_speaker_encoder
