"""
app.py

Flask web server providing a REST API around the voice-security
Phase 1 pipeline plus a beautiful frontend dashboard.

Endpoints:
    GET  /                   → serves the frontend
    POST /api/analyze        → single-file deepfake detection
    GET  /api/metrics        → latest batch-evaluation metrics
    GET  /api/history        → recent analysis history (in-memory)
    GET  /api/pipeline-info  → pipeline configuration details
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# ── Make the src/ package importable ──────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import config  # noqa: E402
from inference import VoiceSpoofDetector  # noqa: E402

# ── Flask setup ───────────────────────────────────────────────────────
app = Flask(__name__, static_folder="frontend", static_url_path="")
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max upload
CORS(app)

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory analysis history (resets on restart — fine for a demo)
_history: list = []

# Lazy-load detector to avoid ONNX crashes with Flask's debug reloader
_detector = None

def get_detector():
    global _detector
    if _detector is None:
        print("[*] Loading AASIST-L model...")
        _detector = VoiceSpoofDetector()
        print("[*] Model loaded successfully.")
    return _detector


# ── Serve frontend ────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ── API: Analyze a single audio file ─────────────────────────────────
@app.route("/api/analyze", methods=["POST"])
def analyze():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Save to a temp file
    ext = Path(audio_file.filename).suffix or ".wav"
    save_name = f"{uuid.uuid4().hex}{ext}"
    save_path = UPLOAD_DIR / save_name
    audio_file.save(str(save_path))

    try:
        start = time.perf_counter()
        result = get_detector().analyze(str(save_path))
        elapsed = time.perf_counter() - start

        response = {
            "id": uuid.uuid4().hex[:8],
            "filename": audio_file.filename,
            "decision": result.decision.value,
            "aggregated_score": round(result.aggregated_score, 6),
            "spoof_probability": round(result.aggregated_score * 100, 2),
            "segment_scores": [round(s, 6) for s in result.segment_scores],
            "num_segments": len(result.segment_scores),
            "inference_time_s": round(elapsed, 4),
            "threshold_used": config.SPOOF_THRESHOLD,
            "aggregation_strategy": config.AGGREGATION_STRATEGY,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        _history.insert(0, response)
        if len(_history) > 50:
            _history.pop()

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Clean up uploaded file
        try:
            save_path.unlink()
        except OSError:
            pass


# ── API: Batch-evaluation metrics ────────────────────────────────────
@app.route("/api/metrics")
def metrics():
    metrics_path = config.METRICS_JSON
    if not metrics_path.exists():
        return jsonify({"error": "No metrics available. Run batch evaluation first."}), 404
    with open(metrics_path) as f:
        data = json.load(f)
    return jsonify(data)


# ── API: Analysis history ────────────────────────────────────────────
@app.route("/api/history")
def history():
    return jsonify(_history)


# ── API: Pipeline configuration ──────────────────────────────────────
@app.route("/api/pipeline-info")
def pipeline_info():
    return jsonify({
        "model": "AASIST-L (ONNX)",
        "sample_rate": config.TARGET_SAMPLE_RATE,
        "window_samples": config.FIXED_WINDOW_SAMPLES,
        "sliding_windows": config.USE_SLIDING_WINDOWS,
        "aggregation_strategy": config.AGGREGATION_STRATEGY,
        "spoof_threshold": config.SPOOF_THRESHOLD,
        "uncertain_margin": config.UNCERTAIN_MARGIN,
    })


if __name__ == "__main__":
    print("\n[*] Voice Security Dashboard starting...")
    print(f"    Model: {config.MODEL_PATH}")
    print(f"    Upload dir: {UPLOAD_DIR}")
    print(f"    Frontend: http://localhost:5000\n")
    # use_reloader=False prevents ONNX Runtime crash on Windows
    # (the reloader spawns a child process that re-imports everything)
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
