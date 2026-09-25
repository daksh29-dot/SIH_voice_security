"""
app.py

VoiceGuard AI — SIH Multi-Modal Voice Security System
Flask web server implementing the Complete 4-Pillar Multi-Modal Defense,
Live Call Defense Simulator, Scam Pattern NLP Engine, and Immutable Audit Ledger.

Endpoints:
    GET  /                         → Frontend Dashboard & Live Simulator
    POST /api/analyze              → Single audio file deepfake detection
    POST /api/analyze-call         → Full 4-Pillar Multi-Modal Call Assessment
    POST /api/analyze-scam-intent  → Ultra-fast (<5ms) Scam Keywords & NLP intent
    POST /api/caller-lookup        → Telecom DND, STIR/SHAKEN & CLI verification
    GET  /api/audit-ledger         → Tamper-evident cryptographic ledger (SHA-256)
    GET  /api/threat-db            → Federated Threat Intelligence Registry
    POST /api/execute-action       → Simulated Banking Freeze & Telecom Drop action
    GET  /api/presets              → Real-world SIH Demo Scenarios (CBI, KYC, etc.)
    GET  /api/metrics              → Batch evaluation metrics
    GET  /api/pipeline-info        → System configuration
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import config

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

# ── Path setup ────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from inference import VoiceSpoofDetector
from speech_to_text import transcribe_audio_file
from multi_modal_engine import (
    analyze_scam_intent,
    check_caller_telecom,
    check_voice_biometrics,
    orchestrate_dynamic_risk,
    SCAM_CATEGORIES
)
from audit_ledger import ledger, threat_db

from backend.models.speaker_encoder import get_speaker_encoder
from backend.audio.preprocessing import AudioPreprocessor
from backend.models.w2v2_aasist import prepare_pcm

app = Flask(__name__, static_folder="frontend")
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
CORS(app)

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
AUDIO_DIR = Path(__file__).resolve().parent / "frontend" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

_detector = None

def get_detector():
    global _detector
    if _detector is None:
        print("[*] Initializing VoiceGuard Deepfake Detector in memory...", flush=True)
        _detector = VoiceSpoofDetector()
        print("[*] VoiceGuard Detector loaded & warmed up.", flush=True)
    return _detector


# ── Serve Frontend & Static Audio ────────────────────────────────────
@app.route("/", defaults={'path': ''}, methods=['GET', 'HEAD', 'OPTIONS'])
@app.route("/<path:path>", methods=['GET', 'HEAD', 'OPTIONS'])
def catch_all(path):
    print(f"[DEBUG] catch_all called with path: '{path}', method: {request.method}")
    if path.startswith("api/") or path.startswith("audio/"):
        return jsonify({"error": "Not found"}), 404
    
    # Check if a specific HTML file exists for this route (Next.js static export behavior)
    has_html = path and not path.endswith('.html') and Path(app.static_folder, path + '.html').is_file()
    print(f"[DEBUG] has_html for {path}: {has_html}")
    if has_html:
        return send_from_directory(app.static_folder, path + '.html')
        
    # If the exact file exists in static folder (like CSS/JS chunks), serve it
    has_exact = path and Path(app.static_folder, path).is_file()
    print(f"[DEBUG] has_exact for {path}: {has_exact}")
    if has_exact:
        return send_from_directory(app.static_folder, path)
        
    # Otherwise fallback to React index.html for client-side routing
    print(f"[DEBUG] fallback to index.html")
    return send_from_directory(app.static_folder, "index.html")

@app.route("/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)


# ── 1. Single Audio File Deepfake Detection ──────────────────────────
@app.route("/api/analyze", methods=["POST"])
def analyze():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    ext = Path(audio_file.filename).suffix or ".wav"
    save_name = f"{uuid.uuid4().hex}{ext}"
    save_path = UPLOAD_DIR / save_name
    audio_file.save(str(save_path))

    try:
        start = time.perf_counter()
        result = get_detector().analyze(str(save_path))
        elapsed = time.perf_counter() - start

        score = result.calibrated_score if result.calibrated_score is not None else result.aggregated_score
        dec = result.decision.value.upper() if result.decision else "UNCERTAIN"

        response = {
            "id": uuid.uuid4().hex[:8],
            "filename": audio_file.filename,
            "decision": dec,
            "aggregated_score": round(score, 6) if score is not None else None,
            "status": result.status,
            "reasons": result.reasons,
            "score_kind": "calibrated_score" if result.calibrated_score is not None else "uncalibrated_model_score",
            "spoof_probability": round(result.calibrated_score * 100, 2) if result.calibrated_score is not None else None,
            "model_score_percent": round(score * 100, 2) if score is not None else None,
            "segment_scores": [round(s, 6) for s in result.segment_scores],
            "num_segments": len(result.segment_scores),
            "inference_time_s": round(elapsed, 4),
            "inference_time_ms": round(elapsed * 1000, 1),
            "threshold_used": None,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Log to ledger
        if score is not None:
            ledger.record_event(
                event_type="AUDIO_FILE_ANALYSIS",
                phone_number="N/A (Direct File)",
                composite_risk=response["aggregated_score"],
                policy_action="BLOCK_AND_HOLD" if dec == "SPOOF" else ("PROCEED_NORMALLY" if dec == "REAL" else "STEP_UP_MFA"),
                pillar_details={"voice_clone_score": response["aggregated_score"]},
                transcript_snippet=f"File: {audio_file.filename}",
                threat_category="SPOOF_VOICE" if dec == "SPOOF" else ("CLEAN" if dec == "REAL" else "UNVERIFIED")
            )

        return jsonify(response)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            save_path.unlink()
        except OSError:
            pass


# ── 1.5 Voice Enrollment Endpoints ────────────────────────────────────
@app.route("/api/enrolled-voices", methods=["GET"])
def get_enrolled_voices():
    encoder = get_speaker_encoder()
    return jsonify(encoder.list_enrolled_speakers())

@app.route("/api/enroll-voice", methods=["POST"])
def enroll_voice():
    if "audio" not in request.files or "speaker_id" not in request.form:
        return jsonify({"error": "Missing audio or speaker_id"}), 400
    
    audio_file = request.files["audio"]
    speaker_id = request.form["speaker_id"].strip()
    
    if not speaker_id:
        return jsonify({"error": "Empty speaker_id"}), 400
        
    ext = Path(audio_file.filename).suffix or ".webm"
    save_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
    audio_file.save(str(save_path))
    
    try:
        from audio_preprocessing import load_audio
        data_sig, sr = load_audio(str(save_path))
        encoder = get_speaker_encoder()
        encoder.enroll_speaker(speaker_id, data_sig, sample_rate=sr)
        return jsonify({"success": True, "speaker_id": speaker_id})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            save_path.unlink()
        except OSError:
            pass

@app.route("/api/enrolled-voices/<speaker_id>", methods=["DELETE"])
def delete_enrolled_voice(speaker_id):
    encoder = get_speaker_encoder()
    try:
        clean_id = encoder._speaker_id(speaker_id)
    except ValueError as exc:
        return jsonify({"error":str(exc)}),400
    if clean_id in encoder.list_enrolled_speakers():
        del encoder.enrolled_speakers[clean_id]
        npy_path = encoder.enrolled_dir / f"{clean_id}.npy"
        if npy_path.exists():
            npy_path.unlink()
        return jsonify({"success": True})
    return jsonify({"error": "Speaker not found"}), 404


# ── 2. Full 4-Pillar Multi-Modal Call Assessment ─────────────────────
@app.route("/api/analyze-call", methods=["POST"])
def analyze_call():
    """
    Accepts:
    - Audio (optional file or blob)
    - phone_number (string)
    - carrier (string)
    - stir_shaken (string: A/B/C)
    - voip_flag (boolean)
    - transcript (string)
    - preset_voice_score (optional float override for instant live presets)
    """
    start_total = time.perf_counter()

    data = request.form if request.form else (request.get_json(silent=True) or {})
    
    phone_number = data.get("phone_number", "+91 9876500000")
    carrier = data.get("carrier", "Jio-Telecom")
    stir_shaken = data.get("stir_shaken", "A")
    voip_flag = str(data.get("voip_flag", "false")).lower() in ("true", "1", "yes")
    transcript = data.get("transcript", "")
    preset_voice_score = data.get("preset_voice_score")

    # 1. Check Voice (Clone?) & Speech-to-Text
    voice_inference_ms = 0.0
    transcription_status = "PRESET_TEXT"
    
    enrolled_speaker_id = data.get("enrolled_speaker_id")
    acoustic_consistency = None
    speaker_match = None
    speaker_similarity = None
    voice_decision = "UNCERTAIN"
    voice_status = "unavailable"
    voice_error = None
    
    if "audio" in request.files and request.files["audio"].filename != "":
        audio_file = request.files["audio"]
        ext = Path(audio_file.filename).suffix or ".wav"
        save_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
        audio_file.save(str(save_path))
        try:
            # 1. Run Deepfake Detection
            t0 = time.perf_counter()
            res = get_detector().analyze(str(save_path))
            voice_inference_ms = round((time.perf_counter() - t0) * 1000, 1)
            voice_score = res.calibrated_score if res.calibrated_score is not None else res.aggregated_score
            voice_decision = res.decision.value.upper()
            voice_status = res.status
        except Exception as e:
            print(f"[!] Voice inference error: {e}")
            voice_score = None
            voice_error = str(e)

        # 2. Run Real Speech-to-Text if transcript wasn't passed or is empty
        if not transcript or len(transcript.strip()) < 3:
            try:
                stt_res = transcribe_audio_file(str(save_path))
                if stt_res.get("text"):
                    transcript = stt_res["text"]
                    transcription_status = f"LIVE_STT ({stt_res.get('engine', 'Google')})"
                else:
                    transcription_status = "STT_NO_SPEECH_DETECTED"
            except Exception as e:
                print(f"[!] STT error: {e}")
                transcription_status = f"STT_ERROR: {e}"
        else:
            transcription_status = "CLIENT_STREAMED_TEXT"

        # Biometric check using the saved file
        if enrolled_speaker_id and enrolled_speaker_id != "none":
            try:
                encoder = get_speaker_encoder()
                from audio_preprocessing import load_audio
                data_sig, sr = load_audio(str(save_path))
                spk_res = encoder.verify_speaker(enrolled_speaker_id, data_sig, sample_rate=sr)
                speaker_match = spk_res["is_match"]
                speaker_similarity = spk_res["similarity"]
                if speaker_match is not None:
                    acoustic_consistency = spk_res["speaker_consistency_score"]
            except Exception as e:
                print(f"[!] Speaker verification error: {e}")

        try:
            save_path.unlink()
        except OSError:
            pass
    elif preset_voice_score is not None:
        try:
            voice_score = float(preset_voice_score)
            if not 0 <= voice_score <= 1:
                raise ValueError("Invalid preset score")
        except (TypeError,ValueError):
            return jsonify({"error":"preset_voice_score must be in [0,1]"}),400
        voice_status = "demo_preset"
        voice_inference_ms = 0.0
    else:
        voice_score = None
        voice_inference_ms = 0.0

    # 2. Check Caller (Spoofed?)
    caller_result = check_caller_telecom(
        phone_number=phone_number,
        carrier=carrier,
        stir_shaken_attestation=stir_shaken,
        voip_flag=voip_flag
    )

    # 3. Check Words (Scam?)
    nlp_result = analyze_scam_intent(transcript)

    # 4. Check Match (Is it them?)
    bio_result = check_voice_biometrics(
        voice_clone_score=voice_score,
        acoustic_consistency_score=acoustic_consistency,
        speaker_match=speaker_match, speaker_similarity=speaker_similarity
    )

    # Dynamic Risk Orchestrator
    orchestration = orchestrate_dynamic_risk(
        voice_clone_risk=voice_score,
        caller_cli_risk=caller_result["risk_score"],
        scam_words_risk=nlp_result["risk_score"],
        biometric_mismatch_risk=bio_result["risk_score"]
    )

    if voice_decision == "UNCERTAIN" and orchestration["policy_action"] == "PROCEED_NORMALLY":
        orchestration.update(policy_action="STEP_UP_MFA",action_label="Voice result requires review",
                             action_color="amber",recommendation="No calibrated real/spoof conclusion is available.")
    total_time_ms = round((time.perf_counter() - start_total) * 1000, 1)

    # Record in cryptographic immutable ledger
    ledger_entry = ledger.record_event(
        event_type="LIVE_CALL_VERIFICATION",
        phone_number=phone_number,
        composite_risk=orchestration["composite_risk_score"],
        policy_action=orchestration["policy_action"],
        pillar_details={
            "voice_clone_risk": voice_score,
            "caller_cli_risk": caller_result["risk_score"],
            "scam_words_risk": nlp_result["risk_score"],
            "biometric_risk": bio_result["risk_score"],
            "matched_keywords": nlp_result["matched_keywords"]
        },
        transcript_snippet=transcript,
        threat_category=nlp_result.get("category_id", "CLEAN")
    )

    # If Critical Threat, register into Threat DB
    if orchestration["composite_risk_score"] >= 0.70 and voice_decision != "UNCERTAIN":
        threat_db.add_threat({
            "id": f"THREAT-{uuid.uuid4().hex[:6].upper()}",
            "phone_number": phone_number,
            "reported_as": nlp_result.get("detected_intent", "Malicious Voice Activity"),
            "risk_level": "CRITICAL",
            "scam_type": nlp_result.get("category_id", "UNKNOWN"),
            "voice_signature_hash": ledger_entry["block_hash"][:32],
            "flagged_count": 1,
            "status": "ACTIVE_BLACKLIST",
            "last_seen": "Just now"
        })

    response = {
        "call_id": uuid.uuid4().hex[:10].upper(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_processing_time_ms": total_time_ms,
        "voice_inference_time_ms": voice_inference_ms,
        "transcript": transcript,
        "transcription_status": transcription_status,
        "orchestration": orchestration,
        "pillars": {
            "voice_clone": {
                "score": round(voice_score, 4) if voice_score is not None else None,
                "is_clone": (voice_decision == "SPOOF") if voice_decision in ("REAL","SPOOF") else None,
                "label": {"REAL":"Genuine prediction","SPOOF":"Spoof prediction"}.get(voice_decision,"Uncertain — uncalibrated or unavailable"),
                "status": voice_status, "error": voice_error,
                "decision": voice_decision
            },
            "caller_telecom": caller_result,
            "scam_nlp": nlp_result,
            "voice_biometrics": bio_result
        },
        "ledger_block_hash": ledger_entry["block_hash"]
    }

    return jsonify(response)


# ── 3. Real-Time Scam NLP Intent Analysis (<5ms) ─────────────────────
@app.route("/api/analyze-scam-intent", methods=["POST"])
def scam_intent():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "")
    res = analyze_scam_intent(text)
    return jsonify(res)


# ── 4. Telecom & Caller ID Verification Lookup ───────────────────────
@app.route("/api/caller-lookup", methods=["POST"])
def caller_lookup():
    data = request.get_json(force=True, silent=True) or {}
    phone = data.get("phone_number", "+91 9876543210")
    carrier = data.get("carrier", "Jio-Telecom")
    stir = data.get("stir_shaken", "A")
    voip = data.get("voip", False)
    res = check_caller_telecom(phone, carrier, stir, voip)
    return jsonify(res)


# ── 5. Immutable Audit Ledger ────────────────────────────────────────
@app.route("/api/audit-ledger")
def get_ledger():
    return jsonify({
        "total_records": len(ledger.get_entries(200)),
        "entries": ledger.get_entries(50)
    })


# ── 6. Federated Threat Intelligence Database ────────────────────────
@app.route("/api/threat-db")
def get_threats():
    return jsonify(threat_db.get_threats())


# ── 7. Action Execution Hook (Simulated Banking / Telecom Drop) ──────
@app.route("/api/execute-action", methods=["POST"])
def execute_action():
    data = request.get_json(force=True, silent=True) or {}
    action = data.get("action", "BLOCK_AND_HOLD")
    phone = data.get("phone_number", "Unknown")
    
    if action == "BLOCK_AND_HOLD":
        msg = f"EMERGENCY TELECOM DROP EXECUTED: Connection to {phone} severed. Core Banking UPI & NetBanking temporarily locked."
    elif action == "STEP_UP_MFA":
        msg = f"STEP-UP MFA DISPATCHED: Interactive Out-of-Band OTP challenge triggered to registered mobile."
    else:
        msg = "Call cleared to proceed normally."

    return jsonify({
        "status": "SUCCESS",
        "action": action,
        "message": msg,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })


# ── 8. Real-World SIH Presentation Presets ───────────────────────────
@app.route("/api/presets")
def get_presets():
    presets = [
        {
            "id": "cbi_digital_arrest",
            "name": "🚨 CBI 'Digital Arrest' Extortion Scam",
            "caller_name": "Delhi Police / CBI Cyber Cell",
            "phone_number": "+91 11-23459812",
            "carrier": "Unknown-SIP-Gateway",
            "stir_shaken": "C",
            "voip_flag": True,
            "preset_voice_score": 0.985,
            "audio_url": "/audio/cbi_digital_arrest.mp3",
            "audio_file": "frontend/audio/cbi_digital_arrest.wav",
            "transcript": "Hello, this is Inspector Rathore from Central Bureau of Investigation CBI Cyber Crime Branch New Delhi. An arrest warrant has been issued in your name for money laundering and narcotics trafficking. You are under digital arrest. Do not disconnect Skype call, immediately transfer funds to RBI verification escrow account.",
            "expected_outcome": "HIGH RISK (>95%) -> Instant Call Drop & Police Alert"
        },
        {
            "id": "sbi_kyc_otp_theft",
            "name": "⚠️ SBI / HDFC Bank KYC Expiry & OTP Scam",
            "caller_name": "SBI Card & Account Security",
            "phone_number": "+91 9823411092",
            "carrier": "VirtualPBX-Cloud",
            "stir_shaken": "B",
            "voip_flag": True,
            "preset_voice_score": 0.92,
            "audio_url": "/audio/sbi_kyc_otp_theft.mp3",
            "audio_file": "frontend/audio/sbi_kyc_otp_theft.wav",
            "transcript": "Dear customer, your State Bank of India Net Banking KYC has expired today. Your bank account will be frozen within two hours. Please share the six digit OTP received on your mobile to update your Aadhaar card and PAN card immediately.",
            "expected_outcome": "HIGH RISK (88%) -> Step-Up MFA / Banking Freeze"
        },
        {
            "id": "fedex_customs_drugs",
            "name": "📦 FedEx / Mumbai Customs Illegal Parcel Scam",
            "caller_name": "FedEx Customs Intelligence",
            "phone_number": "+91 22-67123984",
            "carrier": "Twilio-VoIP-Proxy",
            "stir_shaken": "C",
            "voip_flag": True,
            "preset_voice_score": 0.96,
            "audio_url": "/audio/fedex_customs_drugs.mp3",
            "audio_file": "frontend/audio/fedex_customs_drugs.wav",
            "transcript": "This is FedEx Customs Clearance at Mumbai Airport. A courier parcel sent under your PAN card to Taiwan contains five illegal passports and contraband drugs. Customs officers have seized the parcel. Pay penalty immediately.",
            "expected_outcome": "HIGH RISK (94%) -> Immediate Block & Hold"
        },
        {
            "id": "cloned_relative_emergency",
            "name": "🎭 AI-Cloned Relative Emergency SOS Scam",
            "caller_name": "Son / Relative (Cloned Voice)",
            "phone_number": "+91 9845012345",
            "carrier": "Airtel-Mobile",
            "stir_shaken": "B",
            "voip_flag": False,
            "preset_voice_score": 0.99,
            "audio_url": "/audio/cloned_relative_emergency.mp3",
            "audio_file": "frontend/audio/cloned_relative_emergency.wav",
            "transcript": "Papa, police ne pakad liya hai mujhe. Accident ho gaya car se. Hospital me hu, bail money chahiye fifty thousand rupees emergency. Please kisi ko mat batana, jaldi transfer karo.",
            "expected_outcome": "HIGH RISK (96%) -> Voice Clone Alert & Step-Up Biometrics"
        },
        {
            "id": "legitimate_colleague_call",
            "name": "🛡️ Verified Legitimate Call (Colleague/Friend)",
            "caller_name": "Rahul Sharma (Verified Contact)",
            "phone_number": "+91 9811223344",
            "carrier": "Jio-Telecom (5G Verified)",
            "stir_shaken": "A",
            "voip_flag": False,
            "preset_voice_score": 0.02,
            "audio_url": "/audio/legitimate_colleague_call.mp3",
            "audio_file": "frontend/audio/legitimate_colleague_call.wav",
            "transcript": "Hey, good afternoon! Just checking if we are still on for the project presentation and team sync at 4 PM today? Let me know once you review the slides.",
            "expected_outcome": "LOW RISK (6%) -> Verified Safe • Proceed Normally"
        }
    ]
    return jsonify(presets)


# ── 9. Batch Evaluation Metrics ──────────────────────────────────────
@app.route("/api/metrics")
def metrics():
    metrics_path = Path(getattr(config, "METRICS_JSON", Path(__file__).parent / "metrics.json"))
    if not metrics_path.exists():
        return jsonify({"status":"not_evaluated","accuracy":None,"precision":None,
                        "recall":None,"f1_score":None,"eer":None,"fpr":None,"fnr":None,
                        "confusion_matrix":None})
    with open(metrics_path) as f:
        data = json.load(f)
    return jsonify(data)


# ── 10. Pipeline Info ────────────────────────────────────────────────
@app.route("/api/pipeline-info")
def pipeline_info():
    return jsonify({
        "architecture": "4-Pillar Multi-Modal Voice Security Defense",
        "pillars": [
            "Pillar 1: Check Voice (Clone?) — Wav2Vec2 / Acoustic Neural Network",
            "Pillar 2: Check Caller (Spoofed?) — Telecom TRAI DND / STIR-SHAKEN CLI",
            "Pillar 3: Check Words (Scam?) — Code-Mixed NLP Intent Detector",
            "Pillar 4: Check Match (Is it them?) — Zero-Enrollment Biometrics"
        ],
        "orchestrator": "Dynamic Weighted Risk Engine (0.0 - 1.0)",
        "persistence": "Cryptographic SHA-256 Immutable Audit Ledger & Federated Threat DB",
        "thresholds": {
            "low_risk": "< 0.25 (Proceed Normally)",
            "medium_risk": "0.25 - 0.60 (Step-Up MFA)",
            "high_risk": "> 0.60 (Block & Hold / Auto-Terminate)"
        }
    })


if __name__ == "__main__":
    print("\n" + "="*60)
    print(" [!] VISOR -- TACTICAL VOICE INTELLIGENCE & SECURITY DEFENSE")
    print("="*60)
    # Eagerly load the model at startup so it's ready and the user sees the log
    get_detector()
    
    # print(f" [*] Model: {config.MODEL_NAME}")
    print(f" [*] Model: W2V2-AASIST ONNX")
    print(f" [*] Model Path: {config.MODEL_PATH}")
    print(f" [*] Upload Directory: {UPLOAD_DIR}")
    print(" [*] Web Dashboard & Simulator: http://localhost:5000")
    print("="*60 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
