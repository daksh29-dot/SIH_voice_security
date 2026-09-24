"""
backend/audit/ledger.py

Lightweight, tamper-evident append-only Audit Ledger for Project VISOR (Phase 5).
Maintains an immutable cryptographic SHA-256 hash chain stored in JSON Lines format (.jsonl).

Each ledger entry contains:
  - entry_id: Sequential integer index
  - timestamp: ISO-8601 UTC timestamp
  - session_id: Streaming call session identifier
  - current_hash: SHA-256 digest of (prev_hash + chunk_hash + telemetry + session_id + timestamp)
  - prev_hash: Cryptographic link to previous block (genesis = 64 zeros)
  - chunk_hash: SHA-256 hash of evaluated audio chunk concatenated with model versions & raw scores
  - telemetry: Acoustic spoof score, speaker consistency score, semantic flags, risk state, explanation
"""

import os
import json
import threading
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np

from backend.audit.hashing import (
    compute_chunk_hash,
    compute_ledger_entry_hash,
    get_default_model_versions,
)

DEFAULT_LEDGER_PATH = Path(__file__).resolve().parent.parent.parent / "results" / "audit_ledger.jsonl"
GENESIS_HASH = "0" * 64


class AuditLedger:
    """
    Append-only, tamper-evident audit ledger using SHA-256 cryptographic hash chaining.
    Thread-safe and optimized for real-time streaming audio ingestion.
    """

    def __init__(self, ledger_path: Union[str, Path] = DEFAULT_LEDGER_PATH):
        self.path = Path(ledger_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._last_hash: str = GENESIS_HASH
        self._entry_count: int = 0
        self._init_from_disk()

    def _init_from_disk(self):
        """Read existing ledger on startup to recover last entry ID and block hash."""
        if not self.path.exists() or os.path.getsize(self.path) == 0:
            self._last_hash = GENESIS_HASH
            self._entry_count = 0
            return

        last_valid_hash = GENESIS_HASH
        count = 0
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        last_valid_hash = record.get("current_hash", last_valid_hash)
                        count = record.get("entry_id", count + 1)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

        self._last_hash = last_valid_hash
        self._entry_count = count

    @property
    def last_hash(self) -> str:
        with self._lock:
            return self._last_hash

    @property
    def entry_count(self) -> int:
        with self._lock:
            return self._entry_count

    def record_event(
        self,
        session_id: str,
        audio_chunk: Union[bytes, bytearray, np.ndarray, memoryview],
        telemetry: Dict[str, Any],
        risk_state: str,
        explanation: str = "",
        model_versions: Optional[Dict[str, str]] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Append a tamper-evident event block to the ledger.

        Args:
            session_id: Session identifier string.
            audio_chunk: Audio frame/window as raw bytes or NumPy array.
            telemetry: Dictionary containing raw scores and detection flags.
            risk_state: Evaluated risk state ("LOW RISK", "HIGH RISK", "REVIEW", etc.).
            explanation: Explainable reason for state assignment.
            model_versions: Subsystem model versions dictionary.
            timestamp: ISO-8601 UTC timestamp string (defaults to current time).

        Returns:
            Dict[str, Any]: Complete ledger entry including current_hash and prev_hash.
        """
        now_ts = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        active_models = model_versions or get_default_model_versions()

        # Telemetry payload
        full_telemetry = {
            "acoustic_score": round(float(telemetry.get("acoustic_spoof_risk", 0.0)), 4),
            "speaker_score": round(float(telemetry.get("speaker_consistency_score", 0.0)), 4),
            "speaker_match": telemetry.get("speaker_match"),
            "speaker_similarity": round(float(telemetry.get("speaker_similarity", 0.0)), 4),
            "semantic_threat_score": round(float(telemetry.get("semantic_threat_score", 0.0)), 4),
            "semantic_flags": telemetry.get("triggered_intents", []),
            "flagged_phrases": telemetry.get("flagged_phrases", []),
            "risk_state": str(risk_state),
            "w2v2_score": round(float(telemetry.get("w2v2_score", 0.0)), 4),
            "prosody_anomaly_score": round(float(telemetry.get("prosody_anomaly_score", 0.0)), 4),
            "wavlm_score": round(float(telemetry.get("wavlm_score", 0.0)), 4) if telemetry.get("wavlm_score") is not None else None,
            "vad_active": bool(telemetry.get("vad_active", False)),
        }

        # 1. Compute SHA-256 chunk hash
        chunk_hash = compute_chunk_hash(
            audio_chunk=audio_chunk,
            timestamp=now_ts,
            model_versions=active_models,
            raw_scores=full_telemetry,
        )

        with self._lock:
            entry_id = self._entry_count + 1
            prev_hash = self._last_hash

            # 2. Compute tamper-evident current block hash
            current_hash = compute_ledger_entry_hash(
                prev_hash=prev_hash,
                entry_id=entry_id,
                timestamp=now_ts,
                session_id=session_id,
                chunk_hash=chunk_hash,
                telemetry=full_telemetry,
            )

            entry: Dict[str, Any] = {
                "entry_id": entry_id,
                "timestamp": now_ts,
                "session_id": session_id,
                "prev_hash": prev_hash,
                "current_hash": current_hash,
                "chunk_hash": chunk_hash,
                "telemetry": full_telemetry,
                "explanation": explanation,
                "model_versions": active_models,
            }

            # 3. Append-only write to disk with flush
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())

            self._last_hash = current_hash
            self._entry_count = entry_id

        return entry

    def verify_chain(self, session_id: Optional[str] = None) -> Tuple[bool, int, Optional[str]]:
        """
        Cryptographically verify the integrity of the audit ledger hash chain.

        Args:
            session_id: Optional session ID to filter validation. If None, validates all entries.

        Returns:
            Tuple[bool, int, Optional[str]]:
              - is_valid: True if every hash matches and chain is unbroken.
              - verified_count: Total blocks validated.
              - error_reason: None if valid, or description of tampering / mismatch.
        """
        with self._lock:
            if not self.path.exists() or os.path.getsize(self.path) == 0:
                return True, 0, None

            expected_prev_hash: Optional[str] = None
            verified_count = 0

            with open(self.path, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as err:
                        return False, verified_count, f"Corrupted JSON at line {line_idx}: {err}"

                    if session_id and record.get("session_id") != session_id:
                        continue

                    entry_id = record.get("entry_id")
                    rec_prev_hash = record.get("prev_hash")
                    rec_current_hash = record.get("current_hash")
                    rec_chunk_hash = record.get("chunk_hash")
                    rec_session_id = record.get("session_id")
                    rec_timestamp = record.get("timestamp")
                    rec_telemetry = record.get("telemetry", {})

                    # Check unbroken chain link
                    if expected_prev_hash is not None and rec_prev_hash != expected_prev_hash:
                        return (
                            False,
                            verified_count,
                            f"Broken chain link at entry_id={entry_id}: expected prev_hash '{expected_prev_hash}', got '{rec_prev_hash}'",
                        )

                    # Recompute and verify current block hash
                    recomputed_hash = compute_ledger_entry_hash(
                        prev_hash=rec_prev_hash,
                        entry_id=entry_id,
                        timestamp=rec_timestamp,
                        session_id=rec_session_id,
                        chunk_hash=rec_chunk_hash,
                        telemetry=rec_telemetry,
                    )

                    if recomputed_hash != rec_current_hash:
                        return (
                            False,
                            verified_count,
                            f"Tampered block detected at entry_id={entry_id}: stored hash '{rec_current_hash}' != recomputed '{recomputed_hash}'",
                        )

                    expected_prev_hash = rec_current_hash
                    verified_count += 1

            return True, verified_count, None

    def get_session_entries(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all ledger entries recorded for a specific session."""
        with self._lock:
            if not self.path.exists():
                return []

            results = []
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if record.get("session_id") == session_id:
                            results.append(record)
                    except json.JSONDecodeError:
                        continue
            return results

    def get_recent_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve the latest N ledger entries."""
        with self._lock:
            if not self.path.exists():
                return []

            entries = []
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            return entries[-limit:]

    def clear(self):
        """Reset ledger file (for testing purposes)."""
        with self._lock:
            if self.path.exists():
                self.path.unlink()
            self._last_hash = GENESIS_HASH
            self._entry_count = 0


# Global shared singleton
_global_audit_ledger: Optional[AuditLedger] = None


def get_audit_ledger(ledger_path: Optional[Union[str, Path]] = None) -> AuditLedger:
    """Retrieve or initialize the global shared AuditLedger singleton."""
    global _global_audit_ledger
    if _global_audit_ledger is None or (ledger_path is not None and _global_audit_ledger.path != Path(ledger_path)):
        _global_audit_ledger = AuditLedger(ledger_path or DEFAULT_LEDGER_PATH)
    return _global_audit_ledger
