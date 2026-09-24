"""
backend/api/websocket.py

FastAPI WebSocket endpoint for Project VISOR Real-Time Audio Pipeline (Phase 4).
Wires together:
  1. AudioPreprocessor (16kHz mono float32 conversion & energy check)
  2. Silero VAD (sub-millisecond speech vs. non-speech gating)
  3. RollingAudioBuffer (thread-safe circular FIFO: 3.0s window, 500ms cadence)
  4. W2V2-AASIST ONNX (acoustic deepfake voice clone detection)
  5. OpenSMILEProsodyExtractor (targeted low-latency prosody & anomaly scoring)
  6. SpeakerEncoder (ECAPA-TDNN 192-dim biometric speaker consistency verification)
  7. AsyncWavLMWorker (asynchronous, non-blocking complementary representation branch)
  8. MultiSignalFusionHead (calibrated multi-signal score fusion with graceful degradation)
  9. UtteranceAccumulator (VAD-guided natural pause / boundary detection: >600ms silence)
 10. AsyncASRWorker & ScamIntentClassifier (faster-whisper ASR & telecom fraud intent scoring)

Endpoint:
    ws://<host>:<port>/ws/audio?speaker_id=<optional_speaker_id>
"""

import json
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, Query, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import numpy as np

from backend.audio.preprocessing import AudioPreprocessor
from backend.audio.vad import SileroVAD
from backend.audio.stream import RollingAudioBuffer
from backend.models.w2v2_aasist import get_w2v2_aasist_model, W2V2AASISTModel
from backend.models.opensmile_features import get_prosody_extractor, OpenSMILEProsodyExtractor
from backend.models.speaker_encoder import get_speaker_encoder, SpeakerEncoder
from backend.models.wavlm import get_wavlm_worker, AsyncWavLMWorker
from backend.fusion.feature_fusion import get_fusion_head, MultiSignalFusionHead, AcousticFusionResult
from backend.fusion.risk_engine import get_risk_engine, RiskEngine, RiskState, RiskEvaluationResult
from backend.audit.ledger import get_audit_ledger, AuditLedger
from backend.reports.generator import get_report_generator, IncidentReportGenerator
from backend.nlp.transcription import get_whisper_transcriber, UtteranceAccumulator, AsyncASRWorker
from backend.nlp.scam_intent import get_scam_classifier, ScamIntentClassifier

logger = logging.getLogger("visor.websocket")

router = APIRouter()


class TextClassificationRequest(BaseModel):
    text: str


@router.websocket("/ws/audio")
async def audio_websocket_endpoint(
    websocket: WebSocket,
    speaker_id: Optional[str] = Query(None),
):
    """
    Real-time streaming audio WebSocket endpoint with multi-signal fusion, ASR, and NLP intent.

    Ingests binary PCM audio chunks, runs Silero VAD, feeds valid speech frames into
    a rolling FIFO buffer (3s window, 500ms step), and executes synchronous inference:
      - W2V2-AASIST acoustic spoof score (Weight: 0.50)
      - OpenSMILE physical prosody & anomaly score (Weight: 0.20)
      - WavLM secondary spoof score (Weight: 0.30, async non-blocking worker)
      - Multi-signal calibrated score fusion -> acoustic_spoof_risk
      - ECAPA-TDNN speaker consistency score against enrolled profile
      - VAD natural pause boundary detector (>600ms silence) triggering Async faster-whisper ASR
      - Real-time social engineering intent classifier updating semantic threat scores

    Streams back:
      {
        "status": "ANALYZING",
        "acoustic_spoof_risk": float,
        "w2v2_score": float,
        "prosody_anomaly_score": float,
        "wavlm_score": float | null,
        "wavlm_active": bool,
        "semantic_threat_score": float,
        "transcript": str,
        "triggered_intents": list[str],
        "flagged_phrases": list[str],
        "speaker_similarity": float,
        "speaker_consistency_score": float,
        "speaker_match": bool,
        "latency_ms": float,
        "vad_active": bool,
        "prosody_features": dict
      }
    """
    await websocket.accept()
    active_speaker_id = speaker_id.strip() if speaker_id else None
    logger.info(f"Client connected to /ws/audio (target speaker: {active_speaker_id}).")

    active_session_id: str = f"sess_{int(time.time() * 1000)}"

    # Send immediate handshake packet so client receives confirmation instantly
    await websocket.send_json({
        "status": "ANALYZING",
        "risk_state": "INSUFFICIENT AUDIO",
        "explanation": "WebSocket connection established. Awaiting live audio stream...",
        "composite_risk": 0.0,
        "acoustic_spoof_risk": 0.0,
        "w2v2_score": 0.0,
        "prosody_anomaly_score": 0.0,
        "wavlm_score": None,
        "wavlm_active": False,
        "semantic_threat_score": 0.0,
        "transcript": "",
        "triggered_intents": [],
        "flagged_phrases": [],
        "speaker_similarity": 0.0,
        "speaker_consistency_score": 0.0,
        "speaker_match": None,
        "latency_ms": 0.0,
        "vad_active": False,
        "session_id": active_session_id,
    })

    # Per-connection audio ingest pipeline components
    preprocessor = AudioPreprocessor(target_sample_rate=16000)
    vad = SileroVAD(threshold=0.5)
    rolling_buffer = RollingAudioBuffer(
        sample_rate=16000,
        window_duration_sec=3.0,
        step_duration_sec=0.5,
    )
    utterance_accumulator = UtteranceAccumulator(
        sample_rate=16000,
        silence_boundary_ms=600.0,
        min_speech_ms=400.0,
    )

    # Shared global model singletons
    w2v2_model: W2V2AASISTModel = get_w2v2_aasist_model()
    prosody_extractor: OpenSMILEProsodyExtractor = get_prosody_extractor()
    speaker_encoder: SpeakerEncoder = get_speaker_encoder()
    fusion_head: MultiSignalFusionHead = get_fusion_head()
    scam_classifier: ScamIntentClassifier = get_scam_classifier()
    risk_engine: RiskEngine = get_risk_engine()
    audit_ledger: AuditLedger = get_audit_ledger()

    wavlm_worker: Optional[AsyncWavLMWorker] = None
    try:
        wavlm_worker = get_wavlm_worker()
    except Exception as e:
        logger.warning(f"WavLM worker init notice: {e}")

    asr_worker: Optional[AsyncASRWorker] = None
    try:
        whisper_transcriber = get_whisper_transcriber()
        asr_worker = AsyncASRWorker(transcriber=whisper_transcriber)
    except Exception as e:
        logger.warning(f"Whisper transcriber init notice: {e}")

    active_session_id: str = f"sess_{int(time.time() * 1000)}"
    last_block_hash: Optional[str] = None
    last_risk_state: str = "INSUFFICIENT AUDIO"
    last_risk_explanation: str = "Awaiting audio stream."
    last_contributing_factors: Dict[str, Any] = {}

    last_fused_risk: float = 0.0
    last_w2v2_score: float = 0.0
    last_prosody_anomaly: float = 0.0
    last_wavlm_score: Optional[float] = None
    last_wavlm_active: bool = False
    last_similarity: float = 0.0
    last_consistency: float = 0.0
    last_is_match: bool = False
    last_prosody_dict: Dict[str, Any] = {}
    client_sample_rate: int = 16000

    # NLP state
    current_full_transcript: str = ""
    current_semantic_threat: float = 0.0
    current_triggered_intents: List[str] = []
    current_flagged_phrases: List[str] = []
    last_transcribed_count: int = 0

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                logger.info("Client sent disconnect signal.")
                break

            # Handle JSON control commands
            if "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    cmd = payload.get("command")

                    if cmd == "reset":
                        rolling_buffer.clear()
                        vad.reset_states()
                        utterance_accumulator.reset()
                        asr_worker.clear()
                        last_fused_risk = 0.0
                        last_w2v2_score = 0.0
                        last_prosody_anomaly = 0.0
                        last_wavlm_score = None
                        last_wavlm_active = False
                        last_similarity = 0.0
                        last_consistency = 0.0
                        last_is_match = False
                        current_full_transcript = ""
                        current_semantic_threat = 0.0
                        current_triggered_intents = []
                        current_flagged_phrases = []
                        active_session_id = f"sess_{int(time.time() * 1000)}"
                        last_block_hash = None
                        last_risk_state = "INSUFFICIENT AUDIO"
                        last_risk_explanation = "Pipeline reset."
                        last_contributing_factors = {}
                        await websocket.send_json({
                            "status": "RESET_ACK",
                            "risk_state": "INSUFFICIENT AUDIO",
                            "session_id": active_session_id,
                            "acoustic_spoof_risk": 0.0,
                            "w2v2_score": 0.0,
                            "prosody_anomaly_score": 0.0,
                            "wavlm_score": None,
                            "wavlm_active": False,
                            "semantic_threat_score": 0.0,
                            "transcript": "",
                            "triggered_intents": [],
                            "flagged_phrases": [],
                            "speaker_similarity": 0.0,
                            "speaker_consistency_score": 0.0,
                            "speaker_match": False,
                            "latency_ms": 0.0,
                            "vad_active": False,
                        })
                        continue

                    elif cmd == "get_report":
                        rep_gen = get_report_generator()
                        rep = rep_gen.generate_json_report(active_session_id)
                        await websocket.send_json({
                            "status": "REPORT_ACK",
                            "session_id": active_session_id,
                            "report": rep,
                        })
                        continue

                    elif cmd == "set_speaker":
                        active_speaker_id = payload.get("speaker_id")
                        await websocket.send_json({
                            "status": "SPEAKER_SET_ACK",
                            "speaker_id": active_speaker_id,
                            "is_enrolled": active_speaker_id in speaker_encoder.enrolled_speakers,
                        })
                        continue

                    elif cmd == "enroll":
                        enroll_id = payload.get("speaker_id") or active_speaker_id
                        if enroll_id and rolling_buffer.current_samples >= 8000:
                            current_audio = rolling_buffer.peek_window()
                            speaker_encoder.enroll_speaker(enroll_id, current_audio)
                            active_speaker_id = enroll_id
                            await websocket.send_json({
                                "status": "ENROLL_SUCCESS",
                                "speaker_id": enroll_id,
                                "samples_used": len(current_audio),
                            })
                        else:
                            await websocket.send_json({
                                "status": "ENROLL_FAILED",
                                "reason": "Insufficient speech buffered (need >= 0.5s speech)",
                            })
                        continue

                    if "sample_rate" in payload:
                        client_sample_rate = int(payload["sample_rate"])
                        continue
                except Exception as parse_err:
                    logger.debug(f"JSON command parse note: {parse_err}")

            if "bytes" not in message or not message["bytes"]:
                continue

            chunk_bytes = message["bytes"]
            chunk_start_time = time.perf_counter()

            # 1. Validation & Preprocessing (16kHz mono float32 [-1.0, 1.0])
            audio_16k, is_valid, info = preprocessor.process_chunk(
                chunk_bytes,
                input_sr=client_sample_rate,
            )

            # Check for completed utterance boundaries (>600ms silence after speech)
            # If frame is invalid, treat as silence for boundary calculation
            is_speech_flag = False

            if is_valid:
                # 2. Silero VAD Classification
                is_speech, vad_prob = vad.is_speech(audio_16k)
                is_speech_flag = is_speech

            # Feed to Utterance Accumulator to track sentence boundaries
            completed_utterance = utterance_accumulator.process_frame(
                audio_16k if len(audio_16k) > 0 else np.zeros(1600, dtype=np.float32),
                is_speech=is_speech_flag,
            )

            if completed_utterance is not None and asr_worker is not None:
                # Natural pause / boundary reached (>600ms silence): offload to background ASR worker
                asr_worker.submit_utterance(completed_utterance)

            # Check if ASR worker has updated transcript
            if asr_worker is not None:
                utterances = asr_worker.get_all_utterances()
                if len(utterances) > last_transcribed_count:
                    last_transcribed_count = len(utterances)
                    current_full_transcript = asr_worker.get_full_transcript()
                    nlp_res = scam_classifier.classify(current_full_transcript)
                    current_semantic_threat = nlp_res["semantic_threat_score"]
                    current_triggered_intents = nlp_res["triggered_intents"]
                    current_flagged_phrases = nlp_res["flagged_phrases"]

            if not is_valid or not is_speech_flag:
                # Frame is empty, silent, or non-speech: skip expensive acoustic model inference
                vad_time_ms = (time.perf_counter() - chunk_start_time) * 1000.0

                # Phase 5: Risk Engine evaluation for non-speech / insufficient audio
                risk_eval = risk_engine.evaluate(
                    is_valid_audio=is_valid,
                    vad_active=is_speech_flag,
                    window_ready=False,
                    acoustic_spoof_risk=last_fused_risk,
                    speaker_consistency=last_consistency,
                    speaker_similarity=last_similarity,
                    speaker_match=last_is_match if active_speaker_id else None,
                    speaker_enrolled=bool(active_speaker_id and active_speaker_id in speaker_encoder.enrolled_speakers),
                    semantic_threat_score=current_semantic_threat,
                    triggered_intents=current_triggered_intents,
                    flagged_phrases=current_flagged_phrases,
                    w2v2_score=last_w2v2_score,
                    prosody_anomaly_score=last_prosody_anomaly,
                    wavlm_score=last_wavlm_score,
                )
                last_risk_state = risk_eval.state.value
                last_risk_explanation = risk_eval.explanation
                last_contributing_factors = risk_eval.contributing_factors

                await websocket.send_json({
                    "status": last_risk_state,
                    "risk_state": last_risk_state,
                    "explanation": last_risk_explanation,
                    "composite_risk": round(risk_eval.composite_risk, 4),
                    "contributing_factors": last_contributing_factors,
                    "session_id": active_session_id,
                    "current_hash": last_block_hash,
                    "acoustic_spoof_risk": round(last_fused_risk, 4),
                    "w2v2_score": round(last_w2v2_score, 4),
                    "prosody_anomaly_score": round(last_prosody_anomaly, 4),
                    "wavlm_score": round(last_wavlm_score, 4) if last_wavlm_score is not None else None,
                    "wavlm_active": last_wavlm_active,
                    "semantic_threat_score": round(current_semantic_threat, 4),
                    "transcript": current_full_transcript,
                    "triggered_intents": current_triggered_intents,
                    "flagged_phrases": current_flagged_phrases,
                    "speaker_similarity": round(last_similarity, 4),
                    "speaker_consistency_score": round(last_consistency, 4),
                    "speaker_match": last_is_match,
                    "latency_ms": round(vad_time_ms, 2),
                    "vad_active": False,
                })
                continue

            # 3. Speech detected: Push into rolling FIFO buffer
            is_window_ready = rolling_buffer.push(audio_16k)

            if is_window_ready:
                window_audio = rolling_buffer.get_window()

                # Query latest WavLM score (non-blocking)
                if wavlm_worker is not None:
                    wavlm_worker.submit_audio(window_audio)
                    wavlm_score, is_fresh = wavlm_worker.get_latest_score()
                else:
                    wavlm_score, is_fresh = None, False

                # A. W2V2-AASIST Acoustic Deepfake Inference
                pred = w2v2_model.predict(window_audio)
                last_w2v2_score = pred.spoof_score

                # B. OpenSMILE Prosody & Micro-Stability Analysis
                prosody_result = prosody_extractor.extract_features(window_audio)
                last_prosody_anomaly = prosody_result["prosody_anomaly_score"]
                last_prosody_dict = prosody_result["features"]

                # C. Multi-Signal Score Fusion Engine (with Graceful Degradation)
                fusion_result: AcousticFusionResult = fusion_head.fuse(
                    w2v2_score=last_w2v2_score,
                    prosody_score=last_prosody_anomaly,
                    wavlm_score=wavlm_score if is_fresh else None,
                )
                last_fused_risk = fusion_result.acoustic_spoof_risk
                last_wavlm_score = fusion_result.wavlm_score
                last_wavlm_active = fusion_result.wavlm_active

                # D. ECAPA-TDNN Speaker Biometric Verification
                if active_speaker_id and active_speaker_id in speaker_encoder.enrolled_speakers:
                    spk_res = speaker_encoder.verify_speaker(active_speaker_id, window_audio)
                    last_similarity = spk_res["similarity"]
                    last_is_match = spk_res["is_match"]
                    last_consistency = spk_res["speaker_consistency_score"]
                else:
                    last_similarity = 0.0
                    last_is_match = False
                    last_consistency = 0.0

                total_latency_ms = (time.perf_counter() - chunk_start_time) * 1000.0

                # Phase 5: Explainable Risk Engine evaluation
                risk_eval = risk_engine.evaluate(
                    is_valid_audio=True,
                    vad_active=True,
                    window_ready=True,
                    acoustic_spoof_risk=last_fused_risk,
                    speaker_consistency=last_consistency,
                    speaker_similarity=last_similarity,
                    speaker_match=last_is_match if active_speaker_id else None,
                    speaker_enrolled=bool(active_speaker_id and active_speaker_id in speaker_encoder.enrolled_speakers),
                    semantic_threat_score=current_semantic_threat,
                    triggered_intents=current_triggered_intents,
                    flagged_phrases=current_flagged_phrases,
                    w2v2_score=last_w2v2_score,
                    prosody_anomaly_score=last_prosody_anomaly,
                    wavlm_score=last_wavlm_score,
                )
                last_risk_state = risk_eval.state.value
                last_risk_explanation = risk_eval.explanation
                last_contributing_factors = risk_eval.contributing_factors

                # Phase 5: Cryptographic append-only Audit Ledger recording
                ledger_entry = audit_ledger.record_event(
                    session_id=active_session_id,
                    audio_chunk=window_audio,
                    telemetry={
                        "acoustic_spoof_risk": last_fused_risk,
                        "speaker_consistency_score": last_consistency,
                        "speaker_similarity": last_similarity,
                        "speaker_match": last_is_match if active_speaker_id else None,
                        "semantic_threat_score": current_semantic_threat,
                        "triggered_intents": current_triggered_intents,
                        "flagged_phrases": current_flagged_phrases,
                        "w2v2_score": last_w2v2_score,
                        "prosody_anomaly_score": last_prosody_anomaly,
                        "wavlm_score": last_wavlm_score,
                        "vad_active": True,
                    },
                    risk_state=last_risk_state,
                    explanation=last_risk_explanation,
                )
                last_block_hash = ledger_entry["current_hash"]

                await websocket.send_json({
                    "status": last_risk_state,
                    "risk_state": last_risk_state,
                    "explanation": last_risk_explanation,
                    "composite_risk": round(risk_eval.composite_risk, 4),
                    "contributing_factors": last_contributing_factors,
                    "session_id": active_session_id,
                    "current_hash": last_block_hash,
                    "acoustic_spoof_risk": round(last_fused_risk, 4),
                    "w2v2_score": round(last_w2v2_score, 4),
                    "prosody_anomaly_score": round(last_prosody_anomaly, 4),
                    "wavlm_score": round(last_wavlm_score, 4) if last_wavlm_score is not None else None,
                    "wavlm_active": last_wavlm_active,
                    "semantic_threat_score": round(current_semantic_threat, 4),
                    "transcript": current_full_transcript,
                    "triggered_intents": current_triggered_intents,
                    "flagged_phrases": current_flagged_phrases,
                    "speaker_similarity": round(last_similarity, 4),
                    "speaker_consistency_score": round(last_consistency, 4),
                    "speaker_match": last_is_match,
                    "latency_ms": round(total_latency_ms, 2),
                    "vad_active": True,
                    "prosody_features": last_prosody_dict,
                })
            else:
                elapsed_ms = (time.perf_counter() - chunk_start_time) * 1000.0

                # Phase 5: Risk Engine evaluation for speech buffering phase
                risk_eval = risk_engine.evaluate(
                    is_valid_audio=True,
                    vad_active=True,
                    window_ready=False,
                    acoustic_spoof_risk=last_fused_risk,
                    speaker_consistency=last_consistency,
                    speaker_similarity=last_similarity,
                    speaker_match=last_is_match if active_speaker_id else None,
                    speaker_enrolled=bool(active_speaker_id and active_speaker_id in speaker_encoder.enrolled_speakers),
                    semantic_threat_score=current_semantic_threat,
                    triggered_intents=current_triggered_intents,
                    flagged_phrases=current_flagged_phrases,
                    w2v2_score=last_w2v2_score,
                    prosody_anomaly_score=last_prosody_anomaly,
                    wavlm_score=last_wavlm_score,
                )
                last_risk_state = risk_eval.state.value
                last_risk_explanation = risk_eval.explanation
                last_contributing_factors = risk_eval.contributing_factors

                await websocket.send_json({
                    "status": last_risk_state,
                    "risk_state": last_risk_state,
                    "explanation": last_risk_explanation,
                    "composite_risk": round(risk_eval.composite_risk, 4),
                    "contributing_factors": last_contributing_factors,
                    "session_id": active_session_id,
                    "current_hash": last_block_hash,
                    "acoustic_spoof_risk": round(last_fused_risk, 4),
                    "w2v2_score": round(last_w2v2_score, 4),
                    "prosody_anomaly_score": round(last_prosody_anomaly, 4),
                    "wavlm_score": round(last_wavlm_score, 4) if last_wavlm_score is not None else None,
                    "wavlm_active": last_wavlm_active,
                    "semantic_threat_score": round(current_semantic_threat, 4),
                    "transcript": current_full_transcript,
                    "triggered_intents": current_triggered_intents,
                    "flagged_phrases": current_flagged_phrases,
                    "speaker_similarity": round(last_similarity, 4),
                    "speaker_consistency_score": round(last_consistency, 4),
                    "speaker_match": last_is_match,
                    "latency_ms": round(elapsed_ms, 2),
                    "vad_active": True,
                })

    except (WebSocketDisconnect, RuntimeError):
        logger.info("Client disconnected from /ws/audio.")
    except Exception as e:
        logger.error(f"Error in /ws/audio streaming loop: {e}", exc_info=True)
    finally:
        rolling_buffer.clear()
        vad.reset_states()
        utterance_accumulator.reset()
        if asr_worker is not None:
            asr_worker.stop()


# ── Standalone FastAPI Application ──────────────────────────────────────────

app = FastAPI(
    title="Project VISOR - Real-Time Audio Pipeline (Phase 4)",
    description="Multi-Modal Voice Security Pipeline with W2V2-AASIST, OpenSMILE, WavLM, ECAPA-TDNN, faster-whisper ASR, and Social Engineering NLP",
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


def _warmup_worker():
    """Background worker to warm up models without blocking the async event loop."""
    logger.info("[*] Pre-warming Project VISOR pipeline models in background thread...")
    try:
        get_w2v2_aasist_model()
        get_prosody_extractor()
        get_speaker_encoder()
        get_wavlm_worker()
        get_whisper_transcriber()
        get_scam_classifier()
        get_risk_engine()
        get_audit_ledger()
        logger.info("[+] All VISOR models warmed up and ready for real-time streaming.")
    except Exception as e:
        logger.warning(f"Model warm-up notice: {e}")


@app.on_event("startup")
def warmup_pipeline_models():
    """Launch model pre-warming in background thread so port 8000 opens instantly."""
    threading.Thread(target=_warmup_worker, daemon=True, name="visor-model-warmup").start()


@app.get("/health")
async def health_check():
    """Health check endpoint confirming pipeline availability."""
    return {
        "status": "HEALTHY",
        "service": "Project VISOR Audio Ingest Pipeline (Phase 5)",
        "endpoints": [
            "/ws/audio",
            "/health",
            "/ws/status",
            "/api/speakers",
            "/api/nlp/classify-intent",
            "/api/reports/{session_id}",
            "/api/reports/{session_id}/markdown",
            "/api/ledger/verify",
            "/api/ledger/recent",
        ],
    }


@app.get("/ws/status")
async def ws_status():
    """Return pipeline configuration, model inventory, and fusion settings."""
    spk_encoder = get_speaker_encoder()
    fusion_head = get_fusion_head()
    return {
        "target_sample_rate": 16000,
        "rolling_window_sec": 3.0,
        "step_cadence_sec": 0.5,
        "vad": "Silero VAD v5 ONNX",
        "deepfake_model": "W2V2-AASIST ONNX",
        "prosody_engine": "OpenSMILE GeMAPSv01b LLD",
        "speaker_encoder": "SpeechBrain ECAPA-TDNN (192-dim)",
        "wavlm_branch": "Async WavLM Base Plus Worker (~1.5s cadence)",
        "asr_engine": "faster-whisper (tiny.en, INT8 CPU)",
        "nlp_classifier": "Rule-Boosted Telecom Fraud Intent Engine (<2ms)",
        "utterance_boundary_silence_ms": 600.0,
        "fusion_weights": {
            "w2v2_weight": fusion_head.w2v2_weight,
            "prosody_weight": fusion_head.prosody_weight,
            "wavlm_weight": fusion_head.wavlm_weight,
        },
        "enrolled_speakers_count": len(spk_encoder.enrolled_speakers),
    }


@app.get("/api/speakers")
async def list_speakers():
    """List all currently enrolled speaker IDs."""
    encoder = get_speaker_encoder()
    return {"enrolled_speakers": encoder.list_enrolled_speakers()}


@app.post("/api/speakers/enroll")
async def enroll_speaker_endpoint(
    speaker_id: str = Form(...),
    audio_file: UploadFile = File(...),
):
    """Enroll a new speaker reference profile from an uploaded audio file."""
    import soundfile as sf
    import io

    content = await audio_file.read()
    data, sr = sf.read(io.BytesIO(content))

    preprocessor = AudioPreprocessor(target_sample_rate=16000)
    audio_16k, valid, _ = preprocessor.process_chunk(data, input_sr=sr)

    if not valid or len(audio_16k) < 8000:
        return {"success": False, "error": "Audio file too short or silent (need >= 0.5s speech)."}

    encoder = get_speaker_encoder()
    emb = encoder.enroll_speaker(speaker_id, audio_16k)

    return {
        "success": True,
        "speaker_id": speaker_id,
        "embedding_dim": len(emb),
        "samples_enrolled": len(audio_16k),
    }


@app.post("/api/nlp/classify-intent")
async def classify_intent_endpoint(request: TextClassificationRequest):
    """Scan transcript text for telecom fraud, pressure tactics, and credential theft."""
    classifier = get_scam_classifier()
    result = classifier.classify(request.text)
    return result


@app.get("/api/reports/{session_id}")
async def get_incident_report(session_id: str):
    """Retrieve structured JSON incident report for a streaming session."""
    generator = get_report_generator()
    report = generator.generate_json_report(session_id)
    return report


@app.get("/api/reports/{session_id}/markdown")
async def get_markdown_incident_report(session_id: str):
    """Retrieve formatted Markdown incident report for a streaming session."""
    from fastapi.responses import PlainTextResponse
    generator = get_report_generator()
    md_content = generator.generate_markdown_report(session_id)
    return PlainTextResponse(content=md_content, media_type="text/markdown")


@app.get("/api/ledger/verify")
async def verify_audit_ledger(session_id: Optional[str] = None):
    """Cryptographically verify the SHA-256 hash chain of the audit ledger."""
    ledger = get_audit_ledger()
    is_valid, count, err = ledger.verify_chain(session_id=session_id)
    return {
        "is_valid": is_valid,
        "verified_blocks": count,
        "error": err,
        "session_id": session_id,
    }


@app.get("/api/ledger/recent")
async def get_recent_ledger_entries(limit: int = 20):
    """Retrieve recent cryptographic audit ledger entries."""
    ledger = get_audit_ledger()
    entries = ledger.get_recent_entries(limit=limit)
    return {"entries": entries, "count": len(entries)}


@app.get("/api/audit-ledger")
async def get_audit_ledger_legacy(limit: int = 50):
    """Legacy compatibility endpoint for Audit Ledger tab."""
    ledger = get_audit_ledger()
    entries = ledger.get_recent_entries(limit=limit)
    formatted = []
    for i, e in enumerate(entries, start=1):
        t = e.get("telemetry", {})
        formatted.append({
            "index": i,
            "timestamp": e.get("timestamp", ""),
            "phone_number": e.get("session_id", "Live Call"),
            "composite_risk": float(t.get("acoustic_score", 0.0)),
            "policy_action": t.get("risk_state", "ANALYZING"),
            "threat_category": ", ".join(t.get("semantic_flags", [])) or "CLEAN",
            "block_hash": e.get("current_hash", ""),
        })
    return {"total_records": len(entries), "entries": formatted}


@app.get("/api/threat-db")
async def get_threat_db_legacy():
    """Legacy compatibility endpoint for Threat DB tab."""
    return []


@app.get("/favicon.ico")
async def favicon():
    """No content favicon to avoid 404 logs."""
    return Response(status_code=204)



# ── Mount Frontend Static Assets (Phase 6) ──────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_FRONTEND_DIR = _PROJECT_ROOT / "frontend"
_STATIC_DIR = _PROJECT_ROOT / "static"

if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

if _FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")


