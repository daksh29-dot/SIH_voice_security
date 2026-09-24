"""
Audit subpackage for Project VISOR.
Provides cryptographic hashing and tamper-evident append-only audit ledger.
"""

from backend.audit.hashing import (
    compute_chunk_hash,
    compute_ledger_entry_hash,
    get_default_model_versions,
    DEFAULT_MODEL_VERSIONS,
)
from backend.audit.ledger import (
    AuditLedger,
    get_audit_ledger,
    GENESIS_HASH,
)

__all__ = [
    "compute_chunk_hash",
    "compute_ledger_entry_hash",
    "get_default_model_versions",
    "DEFAULT_MODEL_VERSIONS",
    "AuditLedger",
    "get_audit_ledger",
    "GENESIS_HASH",
]
