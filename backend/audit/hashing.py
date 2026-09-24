"""
backend/audit/hashing.py

Cryptographic hashing module for Project VISOR Audit Ledger (Phase 5).
Computes deterministic SHA-256 hashes of evaluated audio chunks concatenated
with UTC timestamp, active model versions, and raw subsystem scores.

Features:
  - Canonical serialization for deterministic, reproducible digests
  - Supports raw PCM bytes or float32/int16 NumPy audio arrays
  - Provides entry hash chaining for immutable audit ledgers
"""

import hashlib
import json
from typing import Dict, Any, Union, Optional
import numpy as np


DEFAULT_MODEL_VERSIONS: Dict[str, str] = {
    "w2v2_aasist": "1.0.0-onnx",
    "silero_vad": "v5.0-onnx",
    "opensmile": "gemaps_v01b",
    "wavlm": "base_plus_int8",
    "ecapa_tdnn": "speechbrain_192d",
    "whisper": "faster_whisper_tiny_int8",
    "scam_intent": "telecom_fraud_v1",
    "risk_engine": "5state_v1",
}


def get_default_model_versions() -> Dict[str, str]:
    """Return dictionary of current model versions used across VISOR."""
    return dict(DEFAULT_MODEL_VERSIONS)


def _serialize_audio_chunk(audio_chunk: Union[bytes, bytearray, np.ndarray, memoryview]) -> bytes:
    """Normalize incoming audio chunk to contiguous raw bytes."""
    if isinstance(audio_chunk, (bytes, bytearray)):
        return bytes(audio_chunk)
    elif isinstance(audio_chunk, memoryview):
        return audio_chunk.tobytes()
    elif isinstance(audio_chunk, np.ndarray):
        # Ensure float32 representation for consistent binary hashing
        if audio_chunk.dtype != np.float32:
            return audio_chunk.astype(np.float32).tobytes()
        return audio_chunk.tobytes()
    else:
        raise TypeError(f"Unsupported audio chunk type for hashing: {type(audio_chunk)}")


def compute_chunk_hash(
    audio_chunk: Union[bytes, bytearray, np.ndarray, memoryview],
    timestamp: str,
    model_versions: Optional[Dict[str, str]] = None,
    raw_scores: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Compute a deterministic SHA-256 hash of an evaluated audio chunk concatenated
    with UTC timestamp, model versions, and raw subsystem scores.

    Args:
        audio_chunk: Audio frame/window as raw bytes or NumPy array.
        timestamp: ISO-8601 UTC timestamp string.
        model_versions: Dictionary of model versions (e.g. w2v2, opensmile).
        raw_scores: Dictionary of raw inference scores.

    Returns:
        Hexadecimal SHA-256 digest string (64 characters).
    """
    # 1. Compute SHA-256 of raw audio bytes
    raw_audio_bytes = _serialize_audio_chunk(audio_chunk)
    audio_digest = hashlib.sha256(raw_audio_bytes).hexdigest()

    # 2. Canonical serialization of metadata (sorted keys, no extraneous whitespace)
    active_models = model_versions if model_versions is not None else get_default_model_versions()
    scores = raw_scores or {}

    metadata_payload = {
        "audio_sha256": audio_digest,
        "model_versions": active_models,
        "raw_scores": scores,
        "timestamp": timestamp,
    }
    canonical_json = json.dumps(metadata_payload, sort_keys=True, separators=(",", ":"))

    # 3. Compute final SHA-256 digest
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_ledger_entry_hash(
    prev_hash: str,
    entry_id: int,
    timestamp: str,
    session_id: str,
    chunk_hash: str,
    telemetry: Dict[str, Any],
) -> str:
    """
    Compute a tamper-evident SHA-256 block hash for an audit ledger entry.
    Binds the previous block hash to the current entry attributes, forming an immutable hash chain.

    Args:
        prev_hash: SHA-256 hash of preceding block (or 64 zeros for genesis).
        entry_id: Sequential 1-based integer index.
        timestamp: ISO-8601 UTC timestamp string.
        session_id: Unique session identifier string.
        chunk_hash: Evaluated audio chunk hash (from compute_chunk_hash).
        telemetry: Full telemetry dictionary (acoustic score, speaker score, semantic flags, risk state).

    Returns:
        Hexadecimal SHA-256 digest string (64 characters).
    """
    block_payload = {
        "chunk_hash": chunk_hash,
        "entry_id": entry_id,
        "prev_hash": prev_hash,
        "session_id": session_id,
        "telemetry": telemetry,
        "timestamp": timestamp,
    }
    canonical_block = json.dumps(block_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_block.encode("utf-8")).hexdigest()
