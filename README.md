# 🛡️ VoiceGuard AI — Multi-Modal Voice Deepfake & Scam Defense System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Server-Flask-green.svg)](https://flask.palletsprojects.com/)
[![Deep Learning](https://img.shields.io/badge/Model-W2V2--AASIST%20ONNX-orange.svg)](https://huggingface.co/SpeechAntiSpoofingBenchmarks/W2V2-AASIST)
[![Inference Engine](https://img.shields.io/badge/Inference-ONNX%20Runtime-blueviolet.svg)](https://onnxruntime.ai/)
[![Hackathon](https://img.shields.io/badge/SIH-Cyber%20Security%20Track-purple.svg)](#)

**VoiceGuard AI** is a real-time, multi-modal voice security intelligence platform engineered for the **Smart India Hackathon (SIH)**. It defends citizens, enterprises, and financial institutions against the surging epidemic of **AI-generated voice clones**, **deepfake extortion calls (CBI / Digital Arrest)**, **KYC / OTP phishing scams**, and **courier customs fraud**.

Instead of relying solely on acoustic heuristics, VoiceGuard AI implements an end-to-end **4-Pillar Multi-Modal Defense Matrix**, pairing state-of-the-art acoustic neural networks with live telecom verification, real-time code-mixed speech NLP, and cryptographic auditability.

---

## 🏛️ The 4-Pillar Multi-Modal Defense Architecture

```
                                  INCOMING CALL / AUDIO STREAM
                                                │
         ┌──────────────────┬───────────────────┴──────────────────┬──────────────────┐
         ▼                  ▼                                      ▼                  ▼
    【PILLAR 1】       【PILLAR 2】                           【PILLAR 3】       【PILLAR 4】
   Voice Authenticity   Caller Verification                    Scam Intent NLP    Zero-Enrollment Match
   • Wav2Vec2 + AASIST  • STIR/SHAKEN (A/B/C Attestation)      • Indian Context   • Acoustic Metadata
   • 64,600 Raw Audio   • TRAI DND Registry                    • Extortion & Panic • Spectral Consistency
   • Synthetic Artifacts• VoIP / SIP Gateway Flag              • Banking Keywords • Identity Confidence
         │                  │                                      │                  │
         └──────────────────┼──────────────────────────────────────┴──────────────────┘
                            ▼
              DYNAMIC RISK ORCHESTRATOR (0.0 — 1.0)
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
     [LOW RISK]        [MEDIUM RISK]       [HIGH RISK]
      (<0.25)          (0.25 — 0.60)         (>0.60)
  Proceed Normally      Step-Up MFA       Instant Call Drop
                                          Simulated Banking Freeze
                                          Immutable SHA-256 Audit Log
```

1. **Pillar 1: Voice Authenticity (Acoustic Deepfake & Clone Detection)**
   * Detects synthetic artifacts, vocoder glitches, and neural speech synthesis using **W2V2-AASIST ONNX** (`models/w2v2-aasist.onnx` — 1.2 GB Wav2Vec2 front-end + AASIST graph attention anti-spoofing back-end) evaluating raw 16 kHz audio windows.
2. **Pillar 2: Caller ID & Telecom Verification**
   * Inspects STIR/SHAKEN cryptographic call attestation (Full, Partial, Gateway).
   * Cross-references the **TRAI National Do-Not-Disturb (DND)** registry and flags virtual VoIP/SIP proxy routing.
3. **Pillar 3: Semantic & Scam Intent NLP Engine**
   * Real-time speech-to-text transcription (supporting Indian English & Hindi/Hinglish).
   * Rapid pattern matching against high-danger extortion themes (*Digital Arrest*, *CBI/ED*, *SBI NetBanking KYC expiry*, *FedEx contraband narcotics*).
4. **Pillar 4: Zero-Enrollment Biometrics & Acoustic Consistency**
   * Evaluates speaker acoustic signatures and baseline consistency without requiring pre-recorded voice enrollment.

---

## 📂 Project File Structure & System Components

The repository is organized into distinct functional layers: core inference engines, web APIs, frontend dashboard, pre-recorded scenario datasets, evaluation tools, and cryptographic audit storage.

```
SIH_voice_security/
│
├── app.py                             # Flask web server & Multi-Modal REST API endpoints
├── config.py                          # Central configuration hub (paths, model weights, thresholds)
├── config.py.backup                   # Configuration backup
├── main.py                            # CLI entry point for analysis, evaluation, and inspection
├── conftest.py                        # Pytest test discovery & environment configuration
├── requirements.txt                   # Complete Python package dependencies
├── README.md                          # System documentation and operational manual
├── .gitignore                         # Git exclusion rules (venv, checkpoints, uploads, caches)
├── yashveer-clone-1788962405365.mp3   # Cloned voice test audio file
├── test_audio_check.flac              # Diagnostic sample audio file
│
├── src/                               # Core Python Detection & Multi-Modal Engine
│   ├── _pathfix.py                    # Prepend src/ to sys.path for clean module imports
│   ├── model.py                       # W2V2AASISTSpoofDetector ONNX Runtime wrapper
│   ├── aasist_onnx.py                 # Legacy lightweight AASIST-L ONNX wrapper
│   ├── inference.py                   # High-level pipeline orchestrator (VoiceSpoofDetector)
│   ├── audio_preprocessing.py         # Audio loader, resampling (16kHz), mono conversion, PyAV fallback
│   ├── segment_audio.py               # Waveform windowing, sliding segments, and zero-padding
│   ├── aggregation.py                 # Multi-segment pooling (mean, median, top_k, majority_vote)
│   ├── decision.py                    # Decision boundary classifier (REAL / SPOOF / UNCERTAIN)
│   ├── multi_modal_engine.py          # 4-Pillar Risk Engine & Scam Keyword NLP Analyzer
│   ├── speech_to_text.py              # Speech-to-Text transcriber (Google STT with en-IN/hi-IN fallback)
│   ├── audit_ledger.py                # SHA-256 chained tamper-evident audit ledger & threat DB
│   ├── evaluate.py                    # Batch dataset benchmark metrics (Accuracy, Precision, Recall, EER)
│   └── inspect_model.py               # ONNX model inspector (inspects input/output shapes and types)
│
├── frontend/                          # Interactive Security Operations Dashboard
│   ├── index.html                     # Single-Page Application (SPA) dashboard interface
│   ├── styles.css                     # Glassmorphism cyber-defense dark mode stylesheet
│   ├── app.js                         # Web Audio API PCM capture, REST client, and UI logic
│   └── audio/                         # Pre-recorded authentic Indian neural scam scenario clips
│       ├── cbi_digital_arrest.mp3 / .wav          # Digital Arrest / CBI extortion scenario
│       ├── sbi_kyc_otp_theft.mp3 / .wav           # SBI KYC expiration & OTP phishing scenario
│       ├── fedex_customs_drugs.mp3 / .wav         # FedEx illegal parcel & customs extortion scenario
│       ├── cloned_relative_emergency.mp3 / .wav   # Deepfake cloned voice emergency kidnapping scenario
│       └── legitimate_colleague_call.mp3 / .wav   # Legitimate human workplace conversation (control)
│
├── models/                            # Pre-trained Deep Learning Model Checkpoints
│   ├── .gitkeep                       # Preserves directory in git tracking
│   ├── w2v2-aasist.onnx               # Primary production model: Wav2Vec2 + AASIST (1.2 GB)
│   └── aasist-l.onnx                  # Lightweight baseline model: AASIST-L (85k params)
│
├── scripts/                           # Operational & Utility Scripts
│   ├── generate_scenario_audio.py     # Synthesizes realistic Indian scam voice scenarios via Edge-TTS
│   └── fetch_sample_data.py           # Downloads evaluation samples from ASVspoof datasets
│
├── tests/                             # Automated Pytest Test Suite
│   ├── test_audio.py                  # Unit tests for audio loading, resampling, and padding
│   └── test_model.py                  # Unit tests for model inference, output dimensions, and probabilities
│
├── test_audio/                        # Benchmark Audio Datasets
│   ├── real/                          # Genuine human speech FLAC files (ASVspoof 2019 LA eval)
│   ├── real_asvspoof/                 # Curated genuine human speech audio samples
│   ├── spoof/                         # Deepfake and synthesized voice FLAC files
│   └── spoof_4sec/                    # Normalized 4-second spoof benchmark audio clips
│
├── results/                           # Generated Reports & Persistent Ledger Storage
│   ├── immutable_audit_ledger.json    # Cryptographic SHA-256 linked audit records
│   ├── federated_threat_db.json       # Persisted threat database of malicious numbers and scam vectors
│   ├── metrics.json                   # Automated benchmark metrics (Accuracy, F1, EER)
│   └── predictions.csv                # Batch evaluation file-by-file predictions
│
├── references/                        # Research Papers & Baseline Implementations
│   ├── AASIST-L.pth                   # Original PyTorch weights for AASIST-L
│   ├── aasist_l.py                    # PyTorch model architecture definition
│   ├── _net.py                        # Graph neural network spectral layers
│   ├── README.md                      # Upstream research reference notes
│   └── LICENSE                        # Research code license
│
└── uploads/                           # Temporary working directory for uploaded audio files
```

---

## 🔍 Detailed File Breakdown: What Each File Does

### 1. Root Directory

| File | Purpose & Responsibilities |
| :--- | :--- |
| **`app.py`** | **Flask Web Application & REST API Server.** Serves the frontend single-page interface and powers all REST API endpoints: `/api/analyze` (single audio deepfake scanner), `/api/analyze-call` (full 4-pillar multi-modal call evaluation), `/api/analyze-scam-intent` (instant NLP scan), `/api/caller-lookup` (telecom verification), `/api/audit-ledger` (cryptographic ledger), `/api/threat-db` (malicious numbers database), and `/api/execute-action` (automated banking freezes and call termination). |
| **`config.py`** | **Central Configuration Single Source of Truth.** Defines paths, chosen model weights (`models/w2v2-aasist.onnx`), sample rate (`16000`), fixed window size (`64600` samples / 4.0375s), sliding window parameters (`USE_SLIDING_WINDOWS = True`, `SEGMENT_OVERLAP_SECONDS = 2.0`), aggregation strategy (`"mean"`), and decision threshold (`SPOOF_THRESHOLD = 0.95`). |
| **`main.py`** | **Command-Line Interface (CLI).** Provides terminal commands for testing and administration: `inspect-model` (displays ONNX tensor shapes), `analyze <path>` (evaluates a single audio file), `evaluate` (runs batch evaluation over `test_audio/`), and `test-synthetic` (generates a synthetic test tone). |
| **`conftest.py`** | **Pytest Configuration.** Sets up Python test environment and path resolution so test suites run smoothly without path errors. |
| **`requirements.txt`** | **Dependency Manifest.** Lists required packages: `torch`, `torchaudio`, `onnxruntime`, `librosa`, `soundfile`, `av`, `flask`, `flask-cors`, `SpeechRecognition`, `numpy`, `scipy`, `scikit-learn`, `pytest`, etc. |
| **`README.md`** | **System Manual & Documentation.** Comprehensive project guide, architecture breakdown, file structure catalog, quickstart, API documentation, and benchmark metrics. |

---

### 2. Core Defense Engine (`src/`)

| File | Component | Key Functions / Classes | Responsibilities |
| :--- | :--- | :--- | :--- |
| **`src/model.py`** | **Primary ONNX Detector** | `W2V2AASISTSpoofDetector` | Wraps ONNX Runtime session for `w2v2-aasist.onnx`. Handles batch input tensors of shape `(batch, 64600)`, applies zero-padding to short audio, extracts bona fide / spoof logits, applies softmax, and returns spoof probability $[0.0, 1.0]$. |
| **`src/inference.py`** | **Pipeline Orchestrator** | `VoiceSpoofDetector` | End-to-end audio pipeline. Accepts raw audio path or array $\rightarrow$ calls `preprocess_audio()` $\rightarrow$ windows audio via `segment_waveform_sliding()` $\rightarrow$ runs batch inference $\rightarrow$ aggregates segment scores via `aggregate()` $\rightarrow$ applies decision boundary via `decide()`. |
| **`src/multi_modal_engine.py`** | **4-Pillar Risk Engine** | `MultiModalRiskEngine`, `ScamIntentAnalyzer`, `CallerVerificationEngine`, `BiometricConsistencyEngine` | Combines all 4 security pillars into a composite risk score: computes weighted risk from acoustic spoof score, telecom reputation (STIR/SHAKEN, DND), NLP scam indicators (urgency, money extortion, OTP demands), and biometric consistency. Triggers automated countermeasures. |
| **`src/audio_preprocessing.py`** | **Audio Pipeline** | `load_audio()`, `to_mono()`, `resample()`, `normalize()`, `preprocess_audio()` | Decodes any audio container (WAV, MP3, FLAC, OGG, WebM/Opus) using `librosa` with robust PyAV fallback. Ensures mono channel, standardizes sample rate to 16 kHz, and performs peak amplitude normalization. |
| **`src/segment_audio.py`** | **Windowing & Framing** | `segment_waveform()`, `segment_waveform_sliding()`, `pad_fixed()` | Splits variable-length audio into fixed 64,600-sample windows with 2.0s overlap. Employs zero-padding for clips shorter than 4.04 seconds (mitigating self-similarity artifacts caused by tile-repeats). |
| **`src/aggregation.py`** | **Score Pooling** | `aggregate()` | Consolidates scores across multiple temporal audio windows using strategies: `"mean"` (default), `"median"`, `"top_k"`, `"majority_vote"`, or `"max"`. |
| **`src/decision.py`** | **Threshold Classifier** | `decide()` | Compares aggregated spoof probability against `SPOOF_THRESHOLD` (0.95). Returns categorical label (`"REAL"`, `"SPOOF"`, or `"UNCERTAIN"`) and normalized confidence metric. |
| **`src/speech_to_text.py`** | **Speech Transcriber** | `SpeechToTextEngine`, `transcribe_audio()` | Converts speech to text using Google Speech Recognition API with multilingual support for Indian English (`en-IN`) and Hindi (`hi-IN`). |
| **`src/audit_ledger.py`** | **Cryptographic Ledger & Threat DB** | `AuditLedger`, `ThreatIntelligenceDB` | Implements tamper-evident audit logging using chained SHA-256 hashes ($H_n = \text{SHA256}(H_{n-1} + \text{Payload})$). Manages the federated threat registry tracking reported fraud numbers and attack vectors. |
| **`src/evaluate.py`** | **Batch Benchmark Evaluator** | `evaluate_dataset()`, `compute_eer()`, `compute_metrics()` | Iterates through labeled `test_audio/real/` and `test_audio/spoof/` sets, computes classification predictions, generates confusion matrices, and writes `results/predictions.csv` and `results/metrics.json`. |
| **`src/inspect_model.py`** | **ONNX Diagnostics** | `inspect_onnx_model()` | Prints ONNX model metadata, input/output tensor names, execution providers, and data shapes. |
| **`src/aasist_onnx.py`** | **Legacy Baseline** | `AasistOnnxModel` | Lightweight ONNX runtime wrapper for standalone AASIST-L (85k parameters). Kept as a fast alternative baseline. |
| **`src/_pathfix.py`** | **Import Helper** | N/A | Injects `src/` into Python's `sys.path` so submodules can be imported cleanly across environments. |

---

### 3. Frontend & Security Operations Dashboard (`frontend/`)

| File / Folder | Role & Description |
| :--- | :--- |
| **`frontend/index.html`** | **Interactive Web Dashboard.** Provides a responsive, tabbed cyber-security interface including: Live Call Defense Simulator, Standalone Deepfake Scanner, Tamper-Evident Audit Ledger viewer, Federated Threat Registry, and System Architecture visualizer. |
| **`frontend/styles.css`** | **Cyber Defense Styling.** Modern dark-mode UI with glassmorphism cards, glowing status badges (Green = Safe, Red = Malicious Spoof), audio waveform visualizers, and responsive grid layouts. |
| **`frontend/app.js`** | **Client-Side Orchestrator.** Uses Web Audio API (`AudioContext`, `ScriptProcessorNode`) to record raw PCM audio without browser DSP distortion (disabling echo cancellation and noise suppression). Encodes uncompressed 16-bit WAV audio client-side, communicates with Flask REST endpoints, renders live risk meters, and manages scenario playback. |
| **`frontend/audio/`** | **Demo Scenario Audio Files.** Pre-generated realistic Indian voice scenarios used in the Live Simulator: <br>• `cbi_digital_arrest.mp3 / .wav`: Fake police / Digital Arrest intimidation.<br>• `sbi_kyc_otp_theft.mp3 / .wav`: Banking KYC phishing and OTP theft.<br>• `fedex_customs_drugs.mp3 / .wav`: Fake courier customs narcotics extortion.<br>• `cloned_relative_emergency.mp3 / .wav`: Voice-cloned family emergency ransom.<br>• `legitimate_colleague_call.mp3 / .wav`: Authentic human work communication. |

---

### 4. Models, Scripts, Tests & Results

| Path | Description |
| :--- | :--- |
| **`models/w2v2-aasist.onnx`** | Primary production model (1.2 GB). Pairs Wav2Vec2 self-supervised speech representations with AASIST graph attention anti-spoofing network. Downloaded from [HuggingFace](https://huggingface.co/SpeechAntiSpoofingBenchmarks/W2V2-AASIST). |
| **`models/aasist-l.onnx`** | Lightweight legacy AASIST-L model (85k parameters, ~3ms latency). |
| **`scripts/generate_scenario_audio.py`** | Generates authentic Indian-accented scenario audios using Edge Neural TTS (`en-IN-PrabhatNeural`). |
| **`scripts/fetch_sample_data.py`** | Downloads evaluation samples from the ASVspoof 2019 dataset from Hugging Face or public mirrors. |
| **`tests/test_audio.py`** | Tests audio loading, format decoding, resampling, mono mixing, and sliding-window segmentation. |
| **`tests/test_model.py`** | Tests ONNX model loading, input tensor dimensions, output probability bounds, and decision logic. |
| **`test_audio/real/` & `test_audio/spoof/`** | Labeled FLAC audio files used for automated model evaluation and benchmark tests. |
| **`results/immutable_audit_ledger.json`** | Chained SHA-256 JSON records of all call analyses performed by the system. |
| **`results/federated_threat_db.json`** | Known fraudulent telephone numbers, threat categories, and risk scores. |
| **`results/predictions.csv` & `metrics.json`** | Batch evaluation output files with accuracy, precision, recall, and EER metrics. |

---

## 🚀 Quickstart Guide

### 1. Prerequisites
* **Python**: 3.10, 3.11, or 3.12
* **ffmpeg**: Recommended for decoding all audio formats (`winget install Gyan.FFmpeg` on Windows or `sudo apt install ffmpeg` on Linux)
* **Model Checkpoint**: Download `w2v2-aasist.onnx` (1.2 GB) from [HuggingFace](https://huggingface.co/SpeechAntiSpoofingBenchmarks/W2V2-AASIST/blob/main/w2v2-aasist.onnx) and place it in the `models/` directory.

### 2. Installation

Clone the repository and set up a Python virtual environment:

```bash
# Clone repository
git clone https://github.com/daksh29-dot/SIH_voice_security.git
cd SIH_voice_security

# Create and activate virtual environment
python -m venv .venv

# Windows:
.\.venv\Scripts\activate

# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 💻 Running the System

### Option A: Web Operations Dashboard & Live Simulator (Recommended)

Start the Flask server:

```bash
python app.py
```

Open your browser and navigate to:
👉 **`http://localhost:5000`**

* **Live Call Simulator**: Use your microphone to speak in real time or select a pre-recorded Indian scam scenario (CBI Digital Arrest, SBI KYC, FedEx Customs, Cloned Family SOS).
* **Deepfake Scanner**: Upload any audio file (WAV, MP3, FLAC, WebM) for instant acoustic authenticity verification.
* **Audit Ledger**: Review forensic, SHA-256 tamper-evident records of all processed calls.
* **Threat Registry**: Inspect flagged phone numbers and fraud vectors.

---

### Option B: Command Line Interface (CLI)

```bash
# 1. Inspect ONNX model inputs, outputs, and execution providers
python main.py inspect-model

# 2. Analyze a single audio file
python main.py analyze test_audio/real_asvspoof/real_01.flac

# 3. Run full batch dataset evaluation
python main.py evaluate

# 4. Run automated test suite
pytest tests/ -v
```

---

## 🌐 REST API Endpoints Reference

The Flask backend exposes the following RESTful APIs:

| Method | Endpoint | Description | Key Parameters / Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Serves the web dashboard SPA | None |
| `POST` | `/api/analyze` | Single audio deepfake scan (Acoustic Pillar 1) | `multipart/form-data`: `audio` file |
| `POST` | `/api/analyze-call` | Full 4-Pillar multi-modal call evaluation | `audio` file, `caller_id`, `transcript`, `carrier`, `voip_detected` |
| `POST` | `/api/analyze-scam-intent` | Rapid NLP scam & extortion intent scan (<5ms) | JSON: `{"transcript": "Your account is blocked share OTP"}` |
| `POST` | `/api/caller-lookup` | Telecom & STIR/SHAKEN reputation lookup | JSON: `{"phone_number": "+919876543210"}` |
| `GET` | `/api/audit-ledger` | Fetches SHA-256 tamper-evident ledger logs | Query param: `?limit=50` |
| `GET` | `/api/threat-db` | Fetches federated scam intelligence records | None |
| `POST` | `/api/execute-action` | Simulates bank freeze / telecom call termination | JSON: `{"action": "bank_freeze", "case_id": "VG-..."}` |
| `GET` | `/api/presets` | Returns pre-configured demo call scenarios | None |
| `GET` | `/api/pipeline-info` | Returns active model, sample rate, and thresholds | None |
| `GET` | `/api/metrics` | Returns batch evaluation metrics summary | None |

---

## 🔬 Model Architecture & Calibration Notes

### The W2V2-AASIST Model
The production anti-spoofing model combines:
1. **Wav2Vec2 Front-End**: Self-supervised transformer trained on thousands of hours of human speech, extracting deep acoustic contextual embeddings.
2. **AASIST Back-End**: Audio Anti-Spoofing using Integrated Spectro-Temporal Graph Attention Networks. Models fine-grained spectral and temporal relationships across speech frames to catch vocoder artifacts and neural synthesis fingerprints.

### Acoustic Domain Calibration (Why `SPOOF_THRESHOLD = 0.95`)
* **ASVspoof 2019 LA Dataset**: The model was trained on high-grade condenser microphones in anechoic studio environments.
* **Real-World Consumer Microphones**: Everyday laptop/headset microphones introduce ambient room reverberation, non-linear microphone frequency responses, and background noise. In pure studio-trained models, these acoustic characteristics shift the baseline score of a genuine human voice to **~60%–70%**.
* **Synthesized Voice Clones**: AI-synthesized voices (ElevenLabs, Edge-TTS, Tortoise, etc.) score **>99%**.
* **Threshold Calibration**: To prevent false positives while preserving 100% detection of actual synthetic speech, `SPOOF_THRESHOLD` is set to **`0.95`** in `config.py`.

### Zero-Padding vs. Tile-Repeat
Upstream AASIST evaluation code historically used tile-repetition for audio shorter than 4.04 seconds. However, tile-repetition creates artificial periodic self-similarity boundaries that transformer models flag as synthetic. VoiceGuard AI uses **clean zero-padding** in `src/segment_audio.py` and `src/model.py`, significantly improving genuine speech fidelity.

---

## 🔒 Cryptographic Audit Ledger & Compliance

Every voice call analyzed by VoiceGuard AI generates an immutable forensic audit record:

$$\text{Block Hash}_n = \text{SHA256}(\text{Block Hash}_{n-1} + \text{CaseID} + \text{Timestamp} + \text{RiskScore} + \text{Verdict})$$

* **Non-Repudiation**: If any historical log entry or verdict is altered, the cryptographic chain is invalidated.
* **Legal Forensics**: Provides CERT-In and law enforcement agencies with cryptographically verifiable evidence of extortion or identity impersonation.
* **Privacy Preservation**: Audio files are analyzed in-memory and removed from server disk storage immediately after processing.

---

## 👥 Authors & Acknowledgments

* Developed for the **Smart India Hackathon (SIH)** — Cyber Security & Voice Anti-Spoofing Track.
* Built using PyTorch, ONNX Runtime, Hugging Face Transformers, Flask, and Web Audio API.
