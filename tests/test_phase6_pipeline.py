"""
tests/test_phase6_pipeline.py

Comprehensive test suite for Project VISOR Phase 6:
  1. Frontend Audio Streaming Recorder (`static/js/recorder.js` & `frontend/js/recorder.js`)
  2. Operational Security Dashboard DOM Components (`frontend/index.html`)
  3. Dashboard Styling & Explanatory State Classes (`frontend/styles.css`)
  4. Real-Time Telemetry Handling & Oscilloscope Logic (`frontend/app.js`)
  5. FastAPI Static Asset Mounting & Single-Port Server Integration
"""

import json
import pytest
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient

from backend.api.websocket import app
from backend.audit.ledger import get_audit_ledger
from backend.reports.generator import get_report_generator

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = WORKSPACE_ROOT / "frontend"
STATIC_DIR = WORKSPACE_ROOT / "static"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Frontend Audio Streaming Recorder Asset Verification
# ─────────────────────────────────────────────────────────────────────────────

def test_recorder_js_assets_exist():
    """Verify that recorder.js is present in both static/js/ and frontend/js/."""
    frontend_recorder = FRONTEND_DIR / "js" / "recorder.js"
    static_recorder = STATIC_DIR / "js" / "recorder.js"

    assert frontend_recorder.exists(), f"Missing {frontend_recorder}"
    assert static_recorder.exists(), f"Missing {static_recorder}"

    frontend_code = frontend_recorder.read_text(encoding="utf-8")
    static_code = static_recorder.read_text(encoding="utf-8")

    assert "class AudioStreamRecorder" in frontend_code
    assert "class AudioStreamRecorder" in static_code
    assert "AudioWorkletProcessor" in frontend_code
    assert "AudioWorkletNode" in frontend_code
    assert "Int16Array" in frontend_code
    assert "_resampleLinear" in frontend_code
    assert "getWaveformData" in frontend_code


def test_audio_recorder_spec_compliance():
    """Check key methods and properties of AudioStreamRecorder class."""
    code = (FRONTEND_DIR / "js" / "recorder.js").read_text(encoding="utf-8")

    # 16kHz default target sample rate
    assert "targetSampleRate || 16000" in code
    # AudioContext creation and resumption
    assert "AudioContext" in code
    assert "resume()" in code
    # Mono constraint
    assert "channelCount: 1" in code
    # Analyser node for waveform visualizer
    assert "createAnalyser" in code
    # Linear interpolation resampling
    assert "_resampleLinear" in code
    # Fallback to ScriptProcessor if AudioWorklet fails
    assert "_initScriptProcessor" in code


# ─────────────────────────────────────────────────────────────────────────────
# 2. Operational Real-Time UI Components in index.html
# ─────────────────────────────────────────────────────────────────────────────

def test_index_html_live_dashboard_elements():
    """Verify that all Phase 6 required UI elements and containers exist in index.html."""
    index_path = FRONTEND_DIR / "index.html"
    assert index_path.exists(), "frontend/index.html does not exist"
    html = index_path.read_text(encoding="utf-8")

    # 1. Navigation item
    assert 'data-section="live"' in html
    assert "Live Call Defense" in html

    # 2. Section container
    assert '<section class="section active" id="live">' in html or 'id="live"' in html

    # 3. Live Audio Waveform Canvas & VAD badge
    assert 'id="liveWaveformCanvas"' in html
    assert 'id="liveVadBadge"' in html

    # 4. Unified Risk Banner & components
    assert 'id="unifiedRiskBanner"' in html
    assert 'id="urbStateBadge"' in html
    assert 'id="urbCompositeRisk"' in html
    assert 'id="urbExplanation"' in html
    assert 'id="urbVadPill"' in html
    assert 'id="urbLatencyPill"' in html
    assert 'id="urbHashPill"' in html

    # 5. Four Explainable Metric Dials/Bars
    # Acoustic Authenticity
    assert 'id="cardAcoustic"' in html
    assert 'id="mdcAcousticVal"' in html
    assert 'id="mdcAcousticBar"' in html
    assert 'id="mdcAcousticPill"' in html
    assert 'id="mdcAcousticNote"' in html

    # Prosodic Naturalness
    assert 'id="cardProsody"' in html
    assert 'id="mdcProsodyVal"' in html
    assert 'id="mdcProsodyBar"' in html
    assert 'id="mdcProsodyPill"' in html
    assert 'id="mdcProsodyNote"' in html

    # Biometric Match
    assert 'id="cardSpeaker"' in html
    assert 'id="mdcSpeakerVal"' in html
    assert 'id="mdcSpeakerBar"' in html
    assert 'id="mdcSpeakerPill"' in html
    assert 'id="mdcSpeakerNote"' in html

    # Semantic Intent Threat
    assert 'id="cardSemantic"' in html
    assert 'id="mdcSemanticVal"' in html
    assert 'id="mdcSemanticBar"' in html
    assert 'id="mdcSemanticPill"' in html
    assert 'id="mdcSemanticNote"' in html

    # 6. Live Transcript & Threat Highlights
    assert 'id="liveTranscriptScroll"' in html
    assert 'id="transcriptPlaceholder"' in html
    assert 'id="liveDetectedIntents"' in html

    # 7. Audit Ledger Feed
    assert 'id="liveLedgerFeed"' in html
    assert 'id="ledgerPlaceholder"' in html
    assert 'id="liveChainPill"' in html

    # 8. Report Download Buttons
    assert 'id="downloadReportBtn"' in html
    assert 'id="downloadReportMdBtn"' in html

    # 9. Script tags
    assert '<script src="js/recorder.js"></script>' in html
    assert '<script src="app.js"></script>' in html


# ─────────────────────────────────────────────────────────────────────────────
# 3. CSS Styling & State Classes
# ─────────────────────────────────────────────────────────────────────────────

def test_styles_css_phase6_classes():
    """Verify that CSS rules exist for all Phase 6 components and state transitions."""
    css_path = FRONTEND_DIR / "styles.css"
    assert css_path.exists(), "frontend/styles.css does not exist"
    css = css_path.read_text(encoding="utf-8")

    # Banner and states
    assert ".unified-risk-banner" in css
    assert ".state-insufficient-audio" in css
    assert ".state-analyzing" in css
    assert ".state-low-risk" in css
    assert ".state-review" in css
    assert ".state-high-risk" in css

    # Grid and cards
    assert ".explainable-metrics-grid" in css
    assert ".metric-dial-card" in css
    assert ".mdc-progress-track" in css
    assert ".mdc-progress-fill" in css

    # Waveform
    assert ".waveform-box" in css
    assert "#liveWaveformCanvas" in css

    # Transcript and threat highlight
    assert ".transcript-scroll-area" in css
    assert ".threat-highlight" in css
    assert ".intent-pill" in css

    # Ledger block feed
    assert ".ledger-feed-area" in css
    assert ".ledger-block-entry" in css
    assert ".chain-badge-ok" in css


# ─────────────────────────────────────────────────────────────────────────────
# 4. App.js Telemetry Handlers & Streaming Logic
# ─────────────────────────────────────────────────────────────────────────────

def test_app_js_telemetry_functions():
    """Verify that app.js implements the streaming, visualizer, and telemetry handlers."""
    app_js_path = FRONTEND_DIR / "app.js"
    assert app_js_path.exists(), "frontend/app.js does not exist"
    js = app_js_path.read_text(encoding="utf-8")

    # Core Live functions
    assert "initLiveWaveformCanvas" in js
    assert "drawWaveformLoop" in js
    assert "toggleLiveCallMonitoring" in js
    assert "startLiveCallMonitoring" in js
    assert "stopLiveCallMonitoring" in js
    assert "handleLiveTelemetryMessage" in js
    assert "updateUnifiedRiskBanner" in js
    assert "updateWaveformVadBadge" in js
    assert "updateExplainableMetricDials" in js
    assert "updateLiveTranscript" in js
    assert "updateAuditLedgerFeed" in js
    assert "downloadIncidentReport" in js
    assert "fetchAndDownloadReport" in js
    assert "AudioStreamRecorder" in js


# ─────────────────────────────────────────────────────────────────────────────
# 5. FastAPI Static Asset Delivery & End-to-End API Integration
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_fastapi_serves_frontend_root(client):
    """Verify GET / returns index.html containing the Phase 6 dashboard."""
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "VISOR" in res.text
    assert "Live Call Defense" in res.text
    assert "liveWaveformCanvas" in res.text
    assert "unifiedRiskBanner" in res.text


def test_fastapi_serves_recorder_scripts(client):
    """Verify that both /js/recorder.js and /static/js/recorder.js are retrievable."""
    res_direct = client.get("/js/recorder.js")
    assert res_direct.status_code == 200
    assert "AudioStreamRecorder" in res_direct.text

    res_static = client.get("/static/js/recorder.js")
    assert res_static.status_code == 200
    assert "AudioStreamRecorder" in res_static.text


def test_fastapi_serves_app_js_and_styles(client):
    """Verify that app.js and styles.css are correctly served."""
    res_js = client.get("/app.js")
    assert res_js.status_code == 200
    assert "handleLiveTelemetryMessage" in res_js.text

    res_css = client.get("/styles.css")
    assert res_css.status_code == 200
    assert "state-high-risk" in res_css.text


def test_api_report_endpoints_for_download(client):
    """Verify /api/reports/{session_id} and markdown download endpoints."""
    # Seed an entry into the audit ledger so a report is non-empty
    ledger = get_audit_ledger()
    test_session = "phase6_test_session_001"
    ledger.record_event(
        session_id=test_session,
        audio_chunk=np.zeros(16000, dtype=np.float32),
        telemetry={
            "acoustic_spoof_risk": 0.05,
            "speaker_consistency_score": 0.91,
            "speaker_match": True,
            "semantic_threat_score": 0.0,
            "triggered_intents": [],
            "flagged_phrases": [],
            "transcript": "Hello, testing dashboard.",
            "w2v2_score": 0.04,
            "prosody_anomaly_score": 0.10,
            "wavlm_score": 0.05,
            "vad_active": True,
        },
        risk_state="LOW RISK",
        explanation="Phase 6 test verification",
    )

    # Test JSON report
    res_json = client.get(f"/api/reports/{test_session}")
    assert res_json.status_code == 200
    report_data = res_json.json()
    assert report_data["session_id"] == test_session
    assert "summary" in report_data
    assert "cryptographic_verification" in report_data
    assert report_data["summary"]["final_decision_state"] == "LOW RISK"

    # Test Markdown report
    res_md = client.get(f"/api/reports/{test_session}/markdown")
    assert res_md.status_code == 200
    assert "text/markdown" in res_md.headers["content-type"]
    assert "# Project VISOR - Incident Security Audit Report" in res_md.text
    assert test_session in res_md.text


def test_api_speakers_and_ledger_endpoints_active(client):
    """Verify backend endpoints powering dashboard live status."""
    res_speakers = client.get("/api/speakers")
    assert res_speakers.status_code == 200
    assert "enrolled_speakers" in res_speakers.json()

    res_ledger = client.get("/api/ledger/recent?limit=5")
    assert res_ledger.status_code == 200
    assert "entries" in res_ledger.json()

    res_status = client.get("/ws/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["target_sample_rate"] == 16000
    assert "Silero VAD" in status_data["vad"]
