"""
tests/test_phase5_pipeline.py

Comprehensive test suite for Project VISOR Phase 5:
  1. Explainable 5-State Risk Engine (`backend/fusion/risk_engine.py`)
  2. Cryptographic SHA-256 Audio Chunk & Block Hashing (`backend/audit/hashing.py`)
  3. Tamper-Evident Append-Only Audit Ledger (`backend/audit/ledger.py`)
  4. Structured Forensic Incident Report Generator (`backend/reports/generator.py`)
"""

import json
import tempfile
import pytest
import numpy as np
from pathlib import Path

from backend.fusion.risk_engine import (
    RiskEngine,
    RiskState,
    RiskEvaluationResult,
    get_risk_engine,
)
from backend.audit.hashing import (
    compute_chunk_hash,
    compute_ledger_entry_hash,
    get_default_model_versions,
    DEFAULT_MODEL_VERSIONS,
)
from backend.audit.ledger import (
    AuditLedger,
    GENESIS_HASH,
)
from backend.reports.generator import (
    IncidentReportGenerator,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Risk Engine State Machine & Explainability Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_risk_engine_insufficient_audio_state():
    engine = RiskEngine()

    # Case A: Energy check failed (empty / silent frame)
    res_silent = engine.evaluate(
        is_valid_audio=False,
        vad_active=False,
        window_ready=False,
    )
    assert res_silent.state == RiskState.INSUFFICIENT_AUDIO
    assert "insufficient" in res_silent.explanation.lower()
    assert res_silent.composite_risk == 0.0
    assert res_silent.contributing_factors["audio_stream"]["energy_valid"] is False

    # Case B: Energy valid, but VAD classified as non-speech
    res_nonspeech = engine.evaluate(
        is_valid_audio=True,
        vad_active=False,
        window_ready=False,
    )
    assert res_nonspeech.state == RiskState.INSUFFICIENT_AUDIO
    assert res_nonspeech.contributing_factors["audio_stream"]["vad_active"] is False


def test_risk_engine_analyzing_state():
    engine = RiskEngine()

    # Valid speech detected, but circular FIFO buffer not full (window_ready=False)
    res_analyzing = engine.evaluate(
        is_valid_audio=True,
        vad_active=True,
        window_ready=False,
    )
    assert res_analyzing.state == RiskState.ANALYZING
    assert "buffering" in res_analyzing.explanation.lower()
    assert res_analyzing.composite_risk == 0.0
    assert res_analyzing.contributing_factors["audio_stream"]["window_ready"] is False


def test_risk_engine_low_risk_state():
    engine = RiskEngine()

    # Rule: High speaker consistency (>0.75), low acoustic spoof risk (<0.35), zero scam flags
    res_low = engine.evaluate(
        is_valid_audio=True,
        vad_active=True,
        window_ready=True,
        acoustic_spoof_risk=0.12,
        speaker_consistency=0.88,
        speaker_match=True,
        speaker_enrolled=True,
        semantic_threat_score=0.05,
        triggered_intents=[],
        flagged_phrases=[],
    )
    assert res_low.state == RiskState.LOW_RISK
    assert res_low.composite_risk < 0.35
    assert "low risk" in res_low.explanation.lower()
    assert res_low.contributing_factors["acoustic_spoof"]["status"] == "NORMAL"
    assert res_low.contributing_factors["speaker_verification"]["status"] == "MATCH"
    assert res_low.contributing_factors["semantic_intent"]["status"] == "CLEAN"


def test_risk_engine_review_state():
    engine = RiskEngine()

    # Sub-case A: Borderline acoustic spoof score (0.35 - 0.65)
    res_borderline = engine.evaluate(
        is_valid_audio=True,
        vad_active=True,
        window_ready=True,
        acoustic_spoof_risk=0.48,
        speaker_consistency=0.82,
        speaker_match=True,
        speaker_enrolled=True,
        semantic_threat_score=0.05,
    )
    assert res_borderline.state == RiskState.REVIEW
    assert "borderline" in res_borderline.explanation.lower()
    assert res_borderline.contributing_factors["acoustic_spoof"]["status"] == "BORDERLINE"

    # Sub-case B: Unverified speaker identity with neutral intent
    res_unverified = engine.evaluate(
        is_valid_audio=True,
        vad_active=True,
        window_ready=True,
        acoustic_spoof_risk=0.15,
        speaker_consistency=0.0,
        speaker_match=None,
        speaker_enrolled=False,
        semantic_threat_score=0.05,
        triggered_intents=[],
    )
    assert res_unverified.state == RiskState.REVIEW
    assert "unverified speaker" in res_unverified.explanation.lower()
    assert res_unverified.contributing_factors["speaker_verification"]["status"] == "UNVERIFIED"


def test_risk_engine_high_risk_spoof():
    engine = RiskEngine()

    # Rule: Spoof score >= 0.70
    res_high_spoof = engine.evaluate(
        is_valid_audio=True,
        vad_active=True,
        window_ready=True,
        acoustic_spoof_risk=0.78,
        speaker_consistency=0.90,
        speaker_match=True,
        speaker_enrolled=True,
        semantic_threat_score=0.05,
        w2v2_score=0.82,
        prosody_anomaly_score=0.74,
    )
    assert res_high_spoof.state == RiskState.HIGH_RISK
    assert res_high_spoof.composite_risk >= 0.70
    assert "elevated" in res_high_spoof.explanation.lower()
    assert res_high_spoof.contributing_factors["acoustic_spoof"]["status"] == "CRITICAL"


def test_risk_engine_high_risk_imposter_and_scam():
    engine = RiskEngine()

    # Rule: Speaker Imposter Detected + Scam Intent Detected
    res_compound = engine.evaluate(
        is_valid_audio=True,
        vad_active=True,
        window_ready=True,
        acoustic_spoof_risk=0.25,  # Low acoustic spoof alone
        speaker_consistency=0.32,  # Low consistency -> Imposter
        speaker_match=False,
        speaker_enrolled=True,
        semantic_threat_score=0.88,  # Critical scam intent
        triggered_intents=["Credential & OTP Harvesting"],
        flagged_phrases=["read back the otp"],
    )
    assert res_compound.state == RiskState.HIGH_RISK
    assert res_compound.composite_risk >= 0.75
    assert "imposter" in res_compound.explanation.lower()
    assert "scam intent" in res_compound.explanation.lower()
    assert res_compound.contributing_factors["speaker_verification"]["status"] == "IMPOSTER"
    assert res_compound.contributing_factors["semantic_intent"]["status"] == "FLAGGED"


def test_risk_engine_explainable_breakdowns_format():
    engine = get_risk_engine()
    res = engine.evaluate(
        is_valid_audio=True,
        vad_active=True,
        window_ready=True,
        acoustic_spoof_risk=0.85,
        speaker_consistency=0.20,
        speaker_match=False,
        speaker_enrolled=True,
        semantic_threat_score=0.92,
        triggered_intents=["Authority & Executive Impersonation"],
        flagged_phrases=["digital arrest", "cbi"],
    )
    d = res.to_dict()
    assert d["state"] == "HIGH RISK"
    assert "explanation" in d
    assert "composite_risk" in d
    assert "contributing_factors" in d

    factors = d["contributing_factors"]
    assert "acoustic_spoof" in factors
    assert "speaker_verification" in factors
    assert "semantic_intent" in factors
    assert "audio_stream" in factors
    assert "explanation" in factors["acoustic_spoof"]
    assert "explanation" in factors["speaker_verification"]
    assert "explanation" in factors["semantic_intent"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Cryptographic Hashing Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_compute_chunk_hash_deterministic():
    audio = np.random.uniform(-0.5, 0.5, 16000).astype(np.float32)
    ts = "2026-09-24T15:00:00.000000Z"
    scores = {"acoustic_score": 0.45, "speaker_score": 0.80}

    hash1 = compute_chunk_hash(audio, ts, raw_scores=scores)
    hash2 = compute_chunk_hash(audio, ts, raw_scores=scores)

    assert isinstance(hash1, str)
    assert len(hash1) == 64
    assert hash1 == hash2


def test_compute_chunk_hash_avalanche_effect():
    audio = np.ones(1600, dtype=np.float32)
    ts = "2026-09-24T15:00:00.000000Z"

    base_hash = compute_chunk_hash(audio, ts, raw_scores={"score": 0.5})

    # Modifying timestamp changes hash
    ts_hash = compute_chunk_hash(audio, "2026-09-24T15:00:01.000000Z", raw_scores={"score": 0.5})
    assert base_hash != ts_hash

    # Modifying score changes hash
    score_hash = compute_chunk_hash(audio, ts, raw_scores={"score": 0.6})
    assert base_hash != score_hash

    # Modifying audio data changes hash
    audio_mod = audio.copy()
    audio_mod[0] = 0.5
    audio_hash = compute_chunk_hash(audio_mod, ts, raw_scores={"score": 0.5})
    assert base_hash != audio_hash


def test_compute_chunk_hash_supports_bytes():
    raw_bytes = bytes([1, 2, 3, 4] * 400)
    ts = "2026-09-24T15:00:00.000000Z"
    digest = compute_chunk_hash(raw_bytes, ts)
    assert len(digest) == 64


# ─────────────────────────────────────────────────────────────────────────────
# 3. Tamper-Evident Audit Ledger Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_audit_ledger_hash_chaining(tmp_path):
    ledger_file = tmp_path / "test_ledger.jsonl"
    ledger = AuditLedger(ledger_path=ledger_file)

    # 1. Record Block 1 (Genesis parent)
    audio1 = np.zeros(8000, dtype=np.float32)
    e1 = ledger.record_event(
        session_id="session_alpha",
        audio_chunk=audio1,
        telemetry={"acoustic_spoof_risk": 0.10, "speaker_consistency_score": 0.85},
        risk_state="LOW RISK",
        explanation="Genesis clean call",
    )
    assert e1["entry_id"] == 1
    assert e1["prev_hash"] == GENESIS_HASH
    assert len(e1["current_hash"]) == 64

    # 2. Record Block 2 (Chained to Block 1)
    audio2 = np.ones(8000, dtype=np.float32) * 0.1
    e2 = ledger.record_event(
        session_id="session_alpha",
        audio_chunk=audio2,
        telemetry={"acoustic_spoof_risk": 0.42, "speaker_consistency_score": 0.78},
        risk_state="REVIEW",
        explanation="Borderline acoustic review",
    )
    assert e2["entry_id"] == 2
    assert e2["prev_hash"] == e1["current_hash"]

    # 3. Record Block 3 (Chained to Block 2)
    audio3 = np.random.uniform(-0.8, 0.8, 8000).astype(np.float32)
    e3 = ledger.record_event(
        session_id="session_alpha",
        audio_chunk=audio3,
        telemetry={"acoustic_spoof_risk": 0.88, "speaker_consistency_score": 0.25},
        risk_state="HIGH RISK",
        explanation="Critical spoof spike",
    )
    assert e3["entry_id"] == 3
    assert e3["prev_hash"] == e2["current_hash"]

    # 4. Verify chain integrity
    is_valid, count, err = ledger.verify_chain()
    assert is_valid is True
    assert count == 3
    assert err is None


def test_audit_ledger_tamper_detection(tmp_path):
    ledger_file = tmp_path / "tamper_ledger.jsonl"
    ledger = AuditLedger(ledger_path=ledger_file)

    # Write 3 valid blocks
    for i in range(1, 4):
        ledger.record_event(
            session_id="sess_tamper",
            audio_chunk=np.zeros(1000, dtype=np.float32),
            telemetry={"acoustic_spoof_risk": 0.1 * i},
            risk_state="LOW RISK",
        )

    # Verify initially valid
    valid_initial, _, _ = ledger.verify_chain()
    assert valid_initial is True

    # Tamper with block 2 in the file directly (modify risk score)
    lines = ledger_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3

    b2 = json.loads(lines[1])
    b2["telemetry"]["acoustic_score"] = 0.9999  # Unauthorized modification
    lines[1] = json.dumps(b2)
    ledger_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Cryptographic verification MUST detect tampering
    is_valid, count, err = ledger.verify_chain()
    assert is_valid is False
    assert "tampered" in err.lower() or "mismatch" in err.lower()


def test_audit_ledger_session_filtering(tmp_path):
    ledger_file = tmp_path / "multi_session.jsonl"
    ledger = AuditLedger(ledger_path=ledger_file)

    ledger.record_event("sess_A", np.zeros(500, dtype=np.float32), telemetry={}, risk_state="LOW RISK")
    ledger.record_event("sess_B", np.zeros(500, dtype=np.float32), telemetry={}, risk_state="REVIEW")
    ledger.record_event("sess_A", np.zeros(500, dtype=np.float32), telemetry={}, risk_state="LOW RISK")

    entries_a = ledger.get_session_entries("sess_A")
    entries_b = ledger.get_session_entries("sess_B")
    assert len(entries_a) == 2
    assert len(entries_b) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 4. Forensic Incident Report Generator Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_incident_report_generation(tmp_path):
    ledger_file = tmp_path / "report_ledger.jsonl"
    reports_dir = tmp_path / "reports"
    ledger = AuditLedger(ledger_path=ledger_file)
    generator = IncidentReportGenerator(ledger=ledger, reports_dir=reports_dir)

    session_id = "sess_incident_001"

    # Simulate realistic 3-block incident progression:
    # 1. Clean speech
    ledger.record_event(
        session_id=session_id,
        audio_chunk=np.zeros(16000, dtype=np.float32),
        telemetry={
            "acoustic_spoof_risk": 0.12,
            "speaker_consistency_score": 0.85,
            "speaker_match": True,
            "semantic_threat_score": 0.05,
            "triggered_intents": [],
            "flagged_phrases": [],
        },
        risk_state="LOW RISK",
        explanation="Baseline enrolled speaker",
        timestamp="2026-09-24T15:10:00.000000Z",
    )

    # 2. Borderline / Scam phrase detection
    ledger.record_event(
        session_id=session_id,
        audio_chunk=np.ones(16000, dtype=np.float32) * 0.1,
        telemetry={
            "acoustic_spoof_risk": 0.55,
            "speaker_consistency_score": 0.65,
            "speaker_match": True,
            "semantic_threat_score": 0.75,
            "triggered_intents": ["Urgent Financial Transfer Pressure"],
            "flagged_phrases": ["wire the money immediately"],
        },
        risk_state="REVIEW",
        explanation="Urgent wire transfer detected",
        timestamp="2026-09-24T15:10:05.500000Z",
    )

    # 3. High Risk synthetic voice clone + imposter
    ledger.record_event(
        session_id=session_id,
        audio_chunk=np.random.uniform(-0.5, 0.5, 16000).astype(np.float32),
        telemetry={
            "acoustic_spoof_risk": 0.88,
            "speaker_consistency_score": 0.22,
            "speaker_match": False,
            "semantic_threat_score": 0.95,
            "triggered_intents": ["Credential & OTP Harvesting", "Authority & Executive Impersonation"],
            "flagged_phrases": ["digital arrest", "read back the otp"],
        },
        risk_state="HIGH RISK",
        explanation="Synthetic voice clone imposter",
        timestamp="2026-09-24T15:10:12.000000Z",
    )

    # Test JSON Report
    json_rep = generator.generate_json_report(session_id)
    assert json_rep["status"] == "SUCCESS"
    assert json_rep["session_id"] == session_id

    summary = json_rep["summary"]
    assert summary["session_duration_sec"] == 12.0
    assert summary["total_frames_evaluated"] == 3
    assert summary["final_decision_state"] == "HIGH RISK"
    assert summary["maximum_risk_observed"] == 0.88
    assert summary["maximum_risk_state"] == "HIGH RISK"
    assert summary["session_verdict"] == "MALICIOUS_THREAT_CONFIRMED"
    assert len(summary["all_flagged_phrases"]) >= 3

    # Cryptographic check
    crypto = json_rep["cryptographic_verification"]
    assert crypto["is_verified"] is True
    assert crypto["chain_intact"] is True
    assert crypto["blocks_checked"] == 3
    assert crypto["tamper_detected"] is False

    # Forensic Timeline check
    factors = json_rep["timeline_contributing_factors"]
    assert len(factors) >= 2
    # Verify exact second timestamps / offsets
    offsets = [f["offset_sec"] for f in factors]
    assert any(o > 0.0 for o in offsets)

    # Test Markdown Report
    md_rep = generator.generate_markdown_report(session_id)
    assert "# Project VISOR - Incident Security Audit Report" in md_rep
    assert "CRITICAL ALERT: MALICIOUS THREAT DETECTED" in md_rep
    assert "[VERIFIED: CRYPTOGRAPHIC HASH CHAIN INTACT]" in md_rep
    assert "wire the money immediately" in md_rep
    assert "digital arrest" in md_rep

    # Test File Persistence
    saved_files = generator.save_report(session_id, output_dir=reports_dir)
    assert "json" in saved_files
    assert "md" in saved_files
    assert saved_files["json"].exists()
    assert saved_files["md"].exists()
    assert saved_files["json"].stat().st_size > 0
    assert saved_files["md"].stat().st_size > 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. FastAPI Endpoints & WebSocket Integration Tests (Phase 5)
# ─────────────────────────────────────────────────────────────────────────────

def test_websocket_streaming_phase5_telemetry():
    from fastapi.testclient import TestClient
    from backend.api.websocket import app

    client = TestClient(app)
    with client.websocket_connect("/ws/audio") as ws:
        # Send 0.1s of silence (1600 samples * 2 bytes = 3200 bytes)
        silent_chunk = bytes(1600 * 2)
        ws.send_bytes(silent_chunk)
        res = ws.receive_json()

        assert res["status"] == "INSUFFICIENT AUDIO"
        assert res["risk_state"] == "INSUFFICIENT AUDIO"
        assert "explanation" in res
        assert "contributing_factors" in res
        assert "session_id" in res
        assert res["session_id"].startswith("sess_")
        assert res["vad_active"] is False


def test_websocket_get_report_command():
    from fastapi.testclient import TestClient
    from backend.api.websocket import app

    client = TestClient(app)
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_text('{"command": "get_report"}')
        res = ws.receive_json()

        assert res["status"] == "REPORT_ACK"
        assert "session_id" in res
        assert "report" in res
        assert res["report"]["status"] in ("SUCCESS", "EMPTY_SESSION")


def test_api_ledger_and_report_endpoints():
    from fastapi.testclient import TestClient
    from backend.api.websocket import app

    client = TestClient(app)

    # 1. Health check includes new endpoints
    res_health = client.get("/health")
    assert res_health.status_code == 200
    endpoints = res_health.json()["endpoints"]
    assert "/api/reports/{session_id}" in endpoints
    assert "/api/ledger/verify" in endpoints

    # 2. Ledger verification endpoint
    res_verify = client.get("/api/ledger/verify")
    assert res_verify.status_code == 200
    v_data = res_verify.json()
    assert "is_valid" in v_data
    assert "verified_blocks" in v_data
    assert v_data["is_valid"] is True

    # 3. Recent ledger entries endpoint
    res_recent = client.get("/api/ledger/recent?limit=10")
    assert res_recent.status_code == 200
    r_data = res_recent.json()
    assert "entries" in r_data
    assert "count" in r_data
    assert isinstance(r_data["entries"], list)

    # 4. Report JSON endpoint
    test_session = "sess_api_test_001"
    res_rep = client.get(f"/api/reports/{test_session}")
    assert res_rep.status_code == 200
    rep_json = res_rep.json()
    assert rep_json["session_id"] == test_session
    assert "summary" in rep_json

    # 5. Report Markdown endpoint
    res_md = client.get(f"/api/reports/{test_session}/markdown")
    assert res_md.status_code == 200
    assert "text/markdown" in res_md.headers["content-type"]
    assert "# Project VISOR - Incident Security Audit Report" in res_md.text

