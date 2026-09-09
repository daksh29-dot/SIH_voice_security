# 🛡️ VoiceGuard AI — Multi-Modal Voice Deepfake & Scam Defense System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Server-Flask-green.svg)](https://flask.palletsprojects.com/)
[![Deep Learning](https://img.shields.io/badge/Models-Wav2Vec2%20%7C%20AASIST--L-orange.svg)](https://huggingface.co/)
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
   • Wav2Vec2-XLSR     • STIR/SHAKEN (A/B/C Attestation)      • Indian Context   • Acoustic Metadata
   • AASIST-L ONNX     • TRAI DND Registry                    • Extortion & Panic • Speaker Verification
   • Artifact Detection • VoIP / SIP Gateway Flag              • Banking Keywords • Identity Confidence
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

1. **Pillar 1: Voice Authenticity (Deepfake & Clone Detection)**
   * Detects synthetic artifacts, vocoder glitches, and neural speech synthesis using:
     * **Wav2Vec2 Deepfake Detector** (`garystafford/wav2vec2-deepfake-voice-detector` - 94.4M parameters).
     * **AASIST-L ONNX Engine** (`models/aasist-l.onnx` - ultra-lightweight 85k parameters, ~3ms inference).
2. **Pillar 2: Caller ID & Telecom Verification**
   * Inspects STIR/SHAKEN cryptographic call attestation (Full, Partial, Gateway).
   * Cross-references the **TRAI National Do-Not-Disturb (DND)** registry and flags virtual VoIP/SIP proxy routing.
3. **Pillar 3: Semantic & Scam Intent NLP Engine**
   * Real-time speech-to-text transcription (supporting Indian English & Hindi/Hinglish).
   * Rapid pattern matching against high-danger extortion themes (*Digital Arrest*, *CBI/ED*, *SBI NetBanking KYC expiry*, *FedEx contraband narcotics*).
4. **Pillar 4: Zero-Enrollment Biometrics Matching**
   * Evaluates speaker acoustic signatures and baseline enrollment without requiring pre-recorded voice samples.

---

## ✨ Key System Features

* 🎙️ **Live Call Defense Simulator**: Test real-time defenses using your computer microphone or choose pre-recorded authentic Indian voice scenarios (CBI, SBI KYC, FedEx, Family Emergency SOS).
* 📁 **Single Audio Deepfake Scanner**: Drag-and-drop any WAV, MP3, FLAC, or WebM audio file for an instant acoustic authenticity verdict with confidence metrics.
* 📜 **Tamper-Evident Cryptographic Audit Ledger**: Every analyzed call is hashed into an immutable, SHA-256 linked cryptographic ledger to provide forensic evidence for law enforcement and CERT-In compliance.
* 🛡️ **Threat Intelligence Registry**: Live repository tracking malicious numbers, spoofing signatures, and extortion attack vectors.
* ⚡ **Automated Active Countermeasures**: Instantly trigger simulated banking account security freezes and telecom automated disconnects.

---

## 📂 Project Structure

```
SIH_voice_security/
├── app.py                      ← Flask Web Server & Multi-Modal REST API
├── config.py                   ← Central Configuration (Models, thresholds, rates)
├── main.py                     ← CLI Entry Point for single-file & batch evaluation
├── requirements.txt            ← Project dependencies
│
├── src/                        ← Core Defense Engines
│   ├── inference.py            ← Pipeline Orchestrator (VoiceSpoofDetector)
│   ├── audio_preprocessing.py  ← Audio loader (Mono, 16kHz, WebM/Opus PyAV decoding)
│   ├── model.py                ← HuggingFace Wav2Vec2 Deepfake Voice Detector
│   ├── aasist_onnx.py          ← Ultra-fast AASIST-L ONNX runtime wrapper
│   ├── speech_to_text.py       ← Speech Recognition Engine (en-IN / hi-IN fallback)
│   ├── multi_modal_engine.py   ← 4-Pillar Risk Engine & Scam Keyword NLP
│   ├── audit_ledger.py         ← SHA-256 Tamper-evident Audit Ledger
│   ├── segment_audio.py        ← Waveform windowing & batch segmenter
│   ├── aggregation.py          ← Multi-window score aggregation
│   ├── decision.py             ← Thresholding (REAL / SPOOF / UNCERTAIN)
│   └── evaluate.py             ← Batch evaluation & accuracy metrics calculator
│
├── frontend/                   ← Interactive UI & Live Simulator
│   ├── index.html              ← Glassmorphism Dashboard
│   ├── styles.css              ← High-contrast Cyber Defense Theme
│   ├── app.js                  ← Audio recording, API client, & live meters
│   └── audio/                  ← Authentic Indian male neural scenario audios
│
├── models/
│   └── aasist-l.onnx           ← Pretrained AASIST-L ONNX model (85k params)
├── scripts/
│   └── generate_scenarios.py   ← Edge Neural TTS scenario voice generator
├── test_audio/                 ← Labeled evaluation audio clips
│   ├── real_asvspoof/          ← Genuine human speech samples
│   └── spoof_4sec/             ← Synthesized / cloned voice samples
└── results/
    ├── predictions.csv         ← Batch evaluation predictions
    └── metrics.json            ← Accuracy, Precision, Recall, EER report
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
* **Python**: 3.10, 3.11, or 3.12
* **Operating System**: Windows, Linux, or macOS
* **Hardware**: CPU (Intel/AMD/Apple Silicon) or optional CUDA-enabled GPU

### 2. Installation

Clone the repository and create a virtual environment:

```bash
# Clone the repository
git clone https://github.com/daksh29-dot/SIH_voice_security.git
cd SIH_voice_security

# Create and activate virtual environment
python -m venv venv

# Windows:
.\venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

---

## 💻 Running the Application

### Option A: Launch the Web Dashboard & Live Simulator (Recommended)

Start the Flask server:

```bash
python app.py
```

Then open your browser and navigate to:
👉 **`http://localhost:5000`**

From the dashboard you can:
1. Click **"Start Live Mic"** to speak into your headset and inspect live speech-to-text and multi-modal risk scoring.
2. Select any **Pre-configured Scenario** (CBI Digital Arrest, SBI KYC Theft, FedEx Customs, Family SOS) to test automated countermeasures.
3. Upload an audio file under **"Deepfake Scanner"** for acoustic analysis.
4. View the **Cryptographic Audit Ledger** and **Threat Intelligence Registry**.

---

### Option B: Command Line Interface (CLI)

#### 1. Inspect Model Architecture
```bash
python main.py inspect-model
```

#### 2. Analyze a Single Audio File
```bash
python main.py analyze test_audio/real_asvspoof/sample_001.flac
```

#### 3. Run Batch Evaluation on Datasets
```bash
python main.py evaluate
```
This computes metrics across `test_audio/` and updates `results/metrics.json` and `results/predictions.csv`.

#### 4. Run Unit Tests
```bash
pytest tests/ -v
```

---

## ⚙️ Configuration (`config.py`)

All tuning options and hyperparameters are managed in [`config.py`](file:///config.py):

| Parameter | Default Value | Description |
| :--- | :--- | :--- |
| `MODEL_NAME` | `"garystafford/wav2vec2-deepfake-voice-detector"` | Acoustic model (`"aasist"` or HF repo) |
| `MODEL_PATH` | `models/aasist-l.onnx` | Path to local ONNX model |
| `TARGET_SAMPLE_RATE` | `16000` | Native sample rate for audio models (16 kHz) |
| `FORCE_MONO` | `True` | Downmix stereo/multi-channel to mono |
| `FIXED_WINDOW_SAMPLES` | `64600` | AASIST-L window length (~4.04 seconds) |
| `SPOOF_THRESHOLD` | `0.95` | Decision boundary for synthetic classification |
| `AGGREGATION_STRATEGY` | `"mean"` | Multi-segment pooling (`mean`, `median`, `top_k`) |

---

## 📊 Evaluation & Benchmark Results

Performance benchmarked on ASVspoof evaluation subsets:

| Metric | Result | Description |
| :--- | :---: | :--- |
| **Accuracy** | **90.0%** | Overall correct classification rate |
| **Precision** | **100.0%** | Zero false positive spoofs (no false alarms on real voices) |
| **Recall** | **80.0%** | Detection of AI-synthesized voices |
| **F1 Score** | **88.89%** | Harmonic mean of precision and recall |
| **Equal Error Rate (EER)** | **0.0%** | Perfect separability on reference sample distribution |
| **Inference Latency** | **~3ms** | AASIST-L ONNX runtime latency per window |

---

## 🔒 Security & Privacy

* **Zero Cloud Audio Storage**: Audio streams processed in live calls are evaluated in-memory and cleaned up immediately.
* **Tamper-Evident Ledger**: Logs are secured with chained SHA-256 hashes ($Hash_n = \text{SHA256}(Hash_{n-1} + Payload)$) ensuring post-call evidentiary validity.
* **Fail-Safe Offline Mode**: Preprocessing and NLP engines operate entirely locally without requiring third-party cloud connections.

---

## 👥 Authors & Acknowledgments
* Developed for **Smart India Hackathon (SIH)** — Cyber Security & Voice Anti-Spoofing Track.
* Built with PyTorch, Hugging Face Transformers, ONNX Runtime, and Flask.
