/**
 * VoiceGuard AI — app.js
 * Real-Time Scam & Deepfake Call Defense Simulator
 * - Headphone / Headset optimized audio capture
 * - Word-by-word real-time live transcription in the box
 * - Real Web Audio API Analyser waveform reacting to actual voice
 * - Single-click "Stop & Analyze Call" running 4-Pillar Multi-Modal Defense
 * - Cryptographic SHA-256 audit ledger & federated threat DB
 */

// State
let presetsData = {};
let currentPresetId = 'cbi_digital_arrest';
let callActive = false;
let liveMicActive = false;
let callTimerInterval = null;
let callSeconds = 0;

// Live Mic & Headset Audio State
let liveStream = null;
let liveMediaRecorder = null;
let liveAudioChunks = [];
let speechRecognition = null;
let liveTranscriptAccum = '';
let currentInterimText = '';
let audioCtx = null;
let audioAnalyser = null;
let audioSourceNode = null;
let analyserDataArray = null;

// Demo Audio
let demoAudioPlayer = new Audio();
let waveActive = false;

// Standalone Deepfake Check State
let recordBtnActive = false;
let recordMediaRecorder = null;
let recordTimer = null;
let recordSeconds = 0;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    initNavigation();
    initParticleCanvas();
    startWaveformLoop();
    await fetchPresets();
    await loadScenarioData('cbi_digital_arrest');
    setupFileUpload();
    drawGauge(null);
});

// Navigation
function initNavigation() {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            navigateTo(link.getAttribute('data-section'));
        });
    });
    window.addEventListener('hashchange', () => {
        navigateTo(window.location.hash.replace('#', '') || 'simulator');
    });
}

function navigateTo(id) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    const sec = document.getElementById(id) || document.getElementById('simulator');
    sec.classList.add('active');
    const lnk = document.querySelector('.nav-link[data-section="' + id + '"]');
    if (lnk) lnk.classList.add('active');
    window.location.hash = id;
    if (id === 'ledger') fetchAuditLedger();
    if (id === 'threats') fetchThreatDB();
}

// Fetch Presets
async function fetchPresets() {
    try {
        const res = await fetch('/api/presets');
        const data = await res.json();
        data.forEach(p => { presetsData[p.id] = p; });
    } catch (e) {
        console.error('Failed to fetch presets:', e);
    }
}

// Scenario Selection
function selectScenario(btn, presetId) {
    if (callActive || liveMicActive) endLiveCall(false);
    currentPresetId = presetId;
    document.querySelectorAll('.scenario-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadScenarioData(presetId);
}

async function loadScenarioData(presetId) {
    if (Object.keys(presetsData).length === 0) await fetchPresets();
    const preset = presetsData[presetId];
    if (!preset) return;

    const emojiMap = {
        'cbi_digital_arrest': '&#128680;',
        'sbi_kyc_otp_theft': '&#9888;',
        'fedex_customs_drugs': '&#128230;',
        'cloned_relative_emergency': '&#127917;',
        'legitimate_colleague_call': '&#128737;'
    };

    document.getElementById('callerAvatar').innerHTML = emojiMap[presetId] || '&#128222;';
    document.getElementById('callerName').textContent = preset.caller_name;
    document.getElementById('callerPhone').textContent = preset.phone_number;
    document.getElementById('tagCarrier').textContent = preset.carrier;
    document.getElementById('tagStir').textContent = 'STIR-' + preset.stir_shaken;

    if (preset.audio_url) {
        demoAudioPlayer.src = preset.audio_url;
        demoAudioPlayer.load();
    }

    // Show clean scenario preview in transcript
    const transBox = document.getElementById('liveTranscript');
    transBox.innerHTML = '<span style="color:var(--text-secondary)">' +
        '<strong style="color:var(--cyan)">Scenario Selected: ' + escapeHtml(preset.title) + '</strong><br>' +
        '<span style="font-size:0.85em;color:var(--text-muted);display:block;margin-top:6px">Audio Script: "' + escapeHtml(preset.transcript) + '"</span>' +
        '<span style="display:block;margin-top:8px;font-size:0.8em;color:var(--cyan)">Click <strong>Start Demo Call</strong> to simulate incoming audio, or click <strong>Start Live Mic</strong> to speak yourself.</span>' +
        '</span>';

    resetPillarsState();
}

// ─────────────────────────────────────────────────────────────────────────────
// Start Demo Call (Preset Audio)
// ─────────────────────────────────────────────────────────────────────────────
async function startDemoCall() {
    const preset = presetsData[currentPresetId];
    if (!preset) return;

    if (liveMicActive) endLiveCall(false);
    callActive = true;
    liveMicActive = false;
    setCallUI(true, false);
    setWfStatus('CALL SIMULATING...', true);

    try {
        demoAudioPlayer.currentTime = 0;
        await demoAudioPlayer.play();
    } catch (e) {
        console.warn('Audio play notice:', e);
    }

    document.getElementById('liveTranscript').innerHTML = '<span class="tp-placeholder">&#128225; Analyzing voice stream against 4-pillar neural engine...</span>';

    try {
        const t0 = performance.now();
        const res = await fetch('/api/analyze-call', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone_number: preset.phone_number,
                carrier: preset.carrier,
                stir_shaken: preset.stir_shaken,
                voip_flag: preset.voip_flag,
                transcript: preset.transcript,
                preset_voice_score: preset.preset_voice_score
            })
        });
        const data = await res.json();
        const latency = Math.round(performance.now() - t0);
        renderAnalysis(data, latency, preset.transcript);
        setWfStatus('CALL ACTIVE', true);
    } catch (e) {
        console.error('Demo call analysis failed:', e);
        setWfStatus('ANALYSIS ERROR', false);
    }

    demoAudioPlayer.onended = () => {
        if (callActive && !liveMicActive) {
            setWfStatus('CALL COMPLETED (VERDICT LOGGED)', false);
            clearInterval(callTimerInterval);
            resetCallButtons();
        }
    };
}

// ─────────────────────────────────────────────────────────────────────────────
// Live Microphone Mode: Stream Real-Time Words & Analyze on Stop
// ─────────────────────────────────────────────────────────────────────────────
async function toggleLiveMic() {
    if (liveMicActive) {
        // User finished speaking! Stop recording and run the full 4-pillar analysis
        stopAndAnalyzeLiveCall();
        return;
    }

    if (callActive) {
        demoAudioPlayer.pause();
        callActive = false;
    }

    // Request high-quality headset/headphone audio with noise suppression & echo cancellation
    try {
        liveStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });
    } catch (e) {
        alert('Microphone access denied or unavailable. Please check your browser microphone permissions.');
        return;
    }

    liveMicActive = true;
    callActive = true;
    liveTranscriptAccum = '';
    currentInterimText = '';
    liveAudioChunks = [];

    // Connect Web Audio API Analyser to headset audio stream for real waveform reaction
    setupLiveAudioAnalyser(liveStream);

    setCallUI(true, true);
    setWfStatus('LISTENING TO HEADSET (SPEAK NOW...)', true);

    document.getElementById('callerAvatar').innerHTML = '&#127909;';
    document.getElementById('callerName').textContent = 'Headphone / Headset Input';
    document.getElementById('callerPhone').textContent = 'Live Audio Stream';
    document.getElementById('tagCarrier').textContent = 'WebRTC-Direct';
    document.getElementById('tagStir').textContent = 'STIR-A (Verified)';

    // Set clear listening prompt
    document.getElementById('liveTranscript').innerHTML = '<span class="tp-placeholder" style="color:var(--cyan);font-size:0.95rem;">' +
        '&#127908; <strong>Listening to your headset mic...</strong><br>' +
        '<span style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-top:6px;">Start speaking now! Your words will stream directly into this box.<br>' +
        'When you are done speaking, click <strong>"⏹ Stop & Analyze Call"</strong> below to run the complete defense engine.</span>' +
        '</span>';

    // Start recording entire audio continuously into memory
    startLiveMediaRecorder(liveStream);

    // Start Web Speech API with immediate word-by-word streaming
    startLiveSpeechToText();
}

// Set up Web Audio API AnalyserNode for real microphone waveform visualizer
function setupLiveAudioAnalyser(stream) {
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        audioCtx = new AudioCtx();
        audioSourceNode = audioCtx.createMediaStreamSource(stream);
        audioAnalyser = audioCtx.createAnalyser();
        audioAnalyser.fftSize = 256;
        analyserDataArray = new Uint8Array(audioAnalyser.frequencyBinCount);
        audioSourceNode.connect(audioAnalyser);
    } catch (e) {
        console.warn('Web Audio API Analyser initialization notice:', e);
    }
}

// Continuous MediaRecorder capturing the complete call audio
function startLiveMediaRecorder(stream) {
    let mimeType = 'audio/webm;codecs=opus';
    if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm';
        if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = '';
    }

    try {
        liveMediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
        liveMediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) liveAudioChunks.push(e.data);
        };
        // Slice every 200ms into chunks buffer
        liveMediaRecorder.start(200);
    } catch (e) {
        console.error('Failed to initialize MediaRecorder:', e);
    }
}

// Continuous Web Speech API with immediate word-by-word live streaming
function startLiveSpeechToText() {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        console.warn('Web Speech API not supported. Backend Google STT will transcribe on stop.');
        return;
    }

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    try {
        speechRecognition = new SR();
        speechRecognition.continuous = true;
        speechRecognition.interimResults = true;
        speechRecognition.lang = 'en-IN'; // Optimized for Indian English & Hinglish

        speechRecognition.onresult = (event) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const textPart = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    liveTranscriptAccum += textPart + ' ';
                } else {
                    interim += textPart;
                }
            }
            currentInterimText = interim;
            const fullSpoken = (liveTranscriptAccum + currentInterimText).trim();
            if (fullSpoken) {
                // Instantly display words directly in the box as they are spoken!
                document.getElementById('liveTranscript').innerHTML = '"' + escapeHtml(fullSpoken) + '"';
                document.getElementById('nlpBadge').textContent = 'Speaking... (' + fullSpoken.split(/\s+/).length + ' words)';
            }
        };

        speechRecognition.onerror = (e) => {
            console.warn('SpeechRecognition event:', e.error);
            if (liveMicActive && e.error !== 'not-allowed') {
                setTimeout(() => {
                    if (liveMicActive) {
                        try { speechRecognition.start(); } catch (err) {}
                    }
                }, 300);
            }
        };

        speechRecognition.onend = () => {
            // Auto-reconnect so pauses in speech do not kill the recognizer
            if (liveMicActive) {
                try { speechRecognition.start(); } catch (e) {}
            }
        };

        speechRecognition.start();
    } catch (e) {
        console.warn('SpeechRecognition startup notice:', e);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// User Clicks "Stop & Analyze Call" — Run Full 4-Pillar Multi-Modal Defense
// ─────────────────────────────────────────────────────────────────────────────
async function stopAndAnalyzeLiveCall() {
    if (!liveMicActive) return;

    // Change status to analyzing
    setWfStatus('ANALYZING RECORDED VOICE & SCAM PATTERN...', true);
    const btnLive = document.getElementById('btnLiveMic');
    btnLive.disabled = true;
    btnLive.style.opacity = '0.6';
    btnLive.textContent = 'Analyzing Call...';

    // Stop Speech Recognition
    if (speechRecognition) {
        try { speechRecognition.stop(); } catch (e) {}
        speechRecognition = null;
    }

    const fullTranscriptText = (liveTranscriptAccum + currentInterimText).trim();

    // Stop MediaRecorder and extract complete audio
    if (liveMediaRecorder && liveMediaRecorder.state !== 'inactive') {
        liveMediaRecorder.onstop = async () => {
            const blob = new Blob(liveAudioChunks, { type: liveMediaRecorder.mimeType || 'audio/webm' });
            cleanupLiveMedia();
            await executeFullAnalysis(blob, fullTranscriptText);
        };
        try {
            liveMediaRecorder.stop();
        } catch (e) {
            cleanupLiveMedia();
            await executeFullAnalysis(null, fullTranscriptText);
        }
    } else {
        cleanupLiveMedia();
        await executeFullAnalysis(null, fullTranscriptText);
    }
}

// Send full audio and transcript to backend
async function executeFullAnalysis(audioBlob, userTranscript) {
    const t0 = performance.now();
    const fd = new FormData();
    if (audioBlob && audioBlob.size > 200) {
        fd.append('audio', audioBlob, 'headset_call.webm');
    }
    fd.append('phone_number', '+91 9988776655');
    fd.append('carrier', 'WebRTC-Direct');
    fd.append('stir_shaken', 'A');
    fd.append('voip_flag', 'false');
    if (userTranscript) {
        fd.append('transcript', userTranscript);
    }

    try {
        const res = await fetch('/api/analyze-call', { method: 'POST', body: fd });
        const data = await res.json();
        const latency = Math.round(performance.now() - t0);

        const finalDisplayTranscript = userTranscript || data.transcript || '(voice recorded)';
        renderAnalysis(data, latency, finalDisplayTranscript);
        setWfStatus('ANALYSIS COMPLETE (REPORT LOGGED)', false);
    } catch (e) {
        console.error('Call analysis failed:', e);
        setWfStatus('ANALYSIS ERROR', false);
    } finally {
        endLiveCall(true);
    }
}

// Clean up microphone streams and Web Audio resources
function cleanupLiveMedia() {
    if (liveStream) {
        liveStream.getTracks().forEach(t => t.stop());
        liveStream = null;
    }
    if (audioSourceNode) {
        try { audioSourceNode.disconnect(); } catch (e) {}
        audioSourceNode = null;
    }
    if (audioCtx && audioCtx.state !== 'closed') {
        try { audioCtx.close(); } catch (e) {}
        audioCtx = null;
    }
    audioAnalyser = null;
    analyserDataArray = null;
}

// End call cleanly and restore UI buttons
function endLiveCall(keepResultsVisible) {
    callActive = false;
    liveMicActive = false;

    if (demoAudioPlayer) {
        demoAudioPlayer.pause();
    }
    cleanupLiveMedia();
    if (speechRecognition) {
        try { speechRecognition.stop(); } catch (e) {}
        speechRecognition = null;
    }

    clearInterval(callTimerInterval);
    callTimerInterval = null;
    callSeconds = 0;

    resetCallButtons();

    if (!keepResultsVisible) {
        setWfStatus('Ready', false);
        resetPillarsState();
    }
}

function endCall() {
    endLiveCall(false);
}

// Reset call buttons to default interactive state
function resetCallButtons() {
    const btnStart = document.getElementById('btnStartDemo');
    const btnLive = document.getElementById('btnLiveMic');
    const btnDrop = document.getElementById('btnDropCall');
    const timerDisplay = document.getElementById('callTimerDisplay');

    if (btnStart) {
        btnStart.disabled = false;
        btnStart.style.opacity = '1';
    }
    if (btnLive) {
        btnLive.textContent = 'Start Live Mic';
        btnLive.classList.remove('recording');
        btnLive.disabled = false;
        btnLive.style.opacity = '1';
    }
    if (btnDrop) {
        btnDrop.style.display = 'none';
    }
    if (timerDisplay) {
        timerDisplay.style.display = 'none';
    }
    const durationEl = document.getElementById('callDuration');
    if (durationEl) durationEl.textContent = '00:00';
}

// Update Call UI controls during call
function setCallUI(active, isLiveMic) {
    const btnStart = document.getElementById('btnStartDemo');
    const btnLive = document.getElementById('btnLiveMic');
    const btnDrop = document.getElementById('btnDropCall');
    const timerDisplay = document.getElementById('callTimerDisplay');

    if (active) {
        btnStart.disabled = true;
        btnStart.style.opacity = '0.5';

        if (isLiveMic) {
            btnLive.innerHTML = '<span class="rec-dot active"></span> Stop & Analyze Call';
            btnLive.classList.add('recording');
            btnLive.disabled = false;
            btnLive.style.opacity = '1';
        } else {
            btnLive.disabled = true;
            btnLive.style.opacity = '0.5';
        }

        btnDrop.style.display = 'flex';
        timerDisplay.style.display = 'flex';
        callSeconds = 0;
        clearInterval(callTimerInterval);
        callTimerInterval = setInterval(() => {
            callSeconds++;
            const m = String(Math.floor(callSeconds / 60)).padStart(2, '0');
            const s = String(callSeconds % 60).padStart(2, '0');
            document.getElementById('callDuration').textContent = m + ':' + s;
        }, 1000);
    } else {
        resetCallButtons();
    }
}

function setWfStatus(text, active) {
    document.getElementById('wfStatus').textContent = text;
    const dot = document.getElementById('wfDot');
    dot.classList.toggle('active', active);
    waveActive = active;
}

function resetPillarsState() {
    ['p1Fill','p2Fill','p3Fill','p4Fill'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.style.width = '0%'; el.className = 'pi-bar-fill'; }
    });
    ['p1Verdict','p2Verdict','p3Verdict','p4Verdict'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.textContent = '--'; el.className = 'pi-verdict'; }
    });
    ['p1Score','p2Score','p3Score','p4Score'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '--';
    });
    document.getElementById('vpScore').textContent = '--';
    document.getElementById('vpScore').className = 'vp-score';
    document.getElementById('vpAction').textContent = 'Awaiting analysis...';
    document.getElementById('vpAction').className = 'vp-action';
    document.getElementById('gaugePercent').textContent = '--';
    document.getElementById('pbBadge').textContent = 'READY FOR CALL';
    document.getElementById('pbTitle').textContent = 'Start a call to see policy decision';
    document.getElementById('pbDesc').textContent = 'The Dynamic Risk Orchestrator will fuse all 4 pillar scores and recommend an action.';
    document.getElementById('policyBox').className = 'policy-box';
    document.getElementById('pbHash').style.display = 'none';
    document.getElementById('quickActions').style.display = 'none';
    document.getElementById('keywordStrip').innerHTML = '';
    document.getElementById('nlpBadge').textContent = 'Waiting...';
    document.getElementById('pillarsLatency').textContent = '--';
    document.getElementById('wfLatency').textContent = 'Engine: --';
    drawGauge(null);
}

// ─────────────────────────────────────────────────────────────────────────────
// Render Analysis & 4-Pillar Breakdown
// ─────────────────────────────────────────────────────────────────────────────
function renderAnalysis(data, clientLatencyMs, rawTranscript) {
    if (!data || !data.pillars) return;
    const orch = data.orchestration || {};
    const pillars = data.pillars || {};
    const totalMs = data.total_processing_time_ms || clientLatencyMs;

    document.getElementById('wfLatency').textContent = 'Engine: ' + totalMs + 'ms';
    document.getElementById('pillarsLatency').textContent = totalMs + 'ms';

    if (pillars.voice_clone) {
        renderPillar('p1', pillars.voice_clone.score, pillars.voice_clone.score >= 0.5,
            pillars.voice_clone.is_clone ? 'AI CLONE' : 'HUMAN NATURAL');
    }
    if (pillars.caller_telecom) {
        renderPillar('p2', pillars.caller_telecom.risk_score, pillars.caller_telecom.risk_score >= 0.5,
            pillars.caller_telecom.risk_score >= 0.5 ? 'SPOOFED' : 'VERIFIED');
    }
    if (pillars.scam_nlp) {
        renderPillar('p3', pillars.scam_nlp.risk_score, pillars.scam_nlp.risk_score >= 0.5,
            pillars.scam_nlp.severity || (pillars.scam_nlp.risk_score >= 0.5 ? 'SCAM' : 'CLEAN'));
    }
    if (pillars.voice_biometrics) {
        renderPillar('p4', pillars.voice_biometrics.risk_score, pillars.voice_biometrics.risk_score >= 0.5,
            pillars.voice_biometrics.risk_score >= 0.5 ? 'MISMATCH' : 'MATCH');
    }

    const risk = orch.composite_risk_score !== undefined ? orch.composite_risk_score : 0.0;
    const riskPct = orch.risk_percentage !== undefined ? orch.risk_percentage : Math.round(risk * 100);
    drawGauge(risk);
    document.getElementById('gaugePercent').textContent = riskPct + '%';

    const vpScore = document.getElementById('vpScore');
    const vpAction = document.getElementById('vpAction');
    vpScore.textContent = riskPct + '%';

    if (risk >= 0.60) {
        vpScore.className = 'vp-score danger';
        vpAction.textContent = orch.action_label || 'BLOCK & HOLD';
        vpAction.className = 'vp-action danger';
    } else if (risk >= 0.25) {
        vpScore.className = 'vp-score warn';
        vpAction.textContent = orch.action_label || 'STEP-UP MFA';
        vpAction.className = 'vp-action warn';
    } else {
        vpScore.className = 'vp-score safe';
        vpAction.textContent = orch.action_label || 'PROCEED NORMALLY';
        vpAction.className = 'vp-action safe';
    }

    const colorClass = risk >= 0.60 ? 'danger' : (risk >= 0.25 ? 'warn' : 'safe');
    document.getElementById('policyBox').className = 'policy-box ' + colorClass;
    document.getElementById('pbBadge').textContent = 'POLICY: ' + (orch.policy_action || 'EVALUATED');
    document.getElementById('pbTitle').textContent = orch.action_label || orch.policy_action || 'Call Evaluated';
    document.getElementById('pbDesc').textContent = orch.recommendation || 'Analysis complete.';

    if (data.ledger_block_hash) {
        document.getElementById('pbHash').style.display = 'block';
        document.getElementById('pbHashCode').textContent = data.ledger_block_hash.slice(0, 20) + '...';
    }
    document.getElementById('quickActions').style.display = 'flex';

    renderTranscript(rawTranscript, (pillars.scam_nlp && pillars.scam_nlp.matched_keywords) || []);
    if (pillars.scam_nlp) {
        document.getElementById('nlpBadge').textContent = 'NLP: ' + (pillars.scam_nlp.detected_intent || 'Analyzed');
    }
}

function renderPillar(prefix, score, isDanger, label) {
    const pct = Math.round(Math.min(100, Math.max(2, (score || 0) * 100)));
    const fillEl = document.getElementById(prefix + 'Fill');
    const verdictEl = document.getElementById(prefix + 'Verdict');
    const scoreEl = document.getElementById(prefix + 'Score');
    if (fillEl) {
        fillEl.style.width = pct + '%';
        fillEl.className = 'pi-bar-fill ' + (isDanger ? 'danger' : 'safe');
    }
    if (verdictEl) {
        verdictEl.textContent = label;
        verdictEl.className = 'pi-verdict ' + (isDanger ? 'danger' : 'safe');
    }
    if (scoreEl) {
        scoreEl.textContent = pct + '%';
    }
}

function renderTranscript(text, keywords) {
    const container = document.getElementById('liveTranscript');
    const strip = document.getElementById('keywordStrip');
    if (!text) {
        container.innerHTML = '<span class="tp-placeholder">(No speech detected)</span>';
        strip.innerHTML = '';
        return;
    }

    let highlighted = escapeHtml(text);
    if (keywords && keywords.length > 0) {
        keywords.forEach(kw => {
            const rx = new RegExp('(' + escapeRegex(kw) + ')', 'gi');
            highlighted = highlighted.replace(rx, '<mark class="danger-word">$1</mark>');
        });
    }
    container.innerHTML = '"' + highlighted + '"';

    if (keywords && keywords.length > 0) {
        strip.innerHTML = keywords.map(kw => '<span class="keyword-pill">&#128680; ' + escapeHtml(kw) + '</span>').join('');
    } else {
        strip.innerHTML = '<span class="keyword-pill safe">&#10003; No scam triggers detected</span>';
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Real Microphone Waveform & Idle Visualizer
// ─────────────────────────────────────────────────────────────────────────────
function startWaveformLoop() {
    const canvas = document.getElementById('waveformCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let phase = 0;

    function draw() {
        requestAnimationFrame(draw);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const w = canvas.width, h = canvas.height, cy = h / 2;

        ctx.beginPath();
        ctx.lineWidth = 1.8;
        const grad = ctx.createLinearGradient(0, 0, w, 0);
        grad.addColorStop(0, 'rgba(0,240,255,0.4)');
        grad.addColorStop(0.5, 'rgba(123,47,247,0.9)');
        grad.addColorStop(1, 'rgba(0,240,255,0.4)');
        ctx.strokeStyle = grad;

        // If real headset mic audio analyser is available, draw real-time mic frequencies!
        if (liveMicActive && audioAnalyser && analyserDataArray) {
            audioAnalyser.getByteTimeDomainData(analyserDataArray);
            const sliceWidth = w / analyserDataArray.length;
            let x = 0;
            for (let i = 0; i < analyserDataArray.length; i++) {
                const v = analyserDataArray[i] / 128.0; // 0.0 to 2.0
                const y = v * (h / 2);
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
                x += sliceWidth;
            }
            ctx.lineTo(w, cy);
            ctx.stroke();
            return;
        }

        // Idle or Demo Audio sine animation
        const amp = waveActive ? 22 : 6;
        for (let x = 0; x < w; x++) {
            const y = cy + Math.sin(x * 0.022 + phase) * amp + Math.sin(x * 0.048 + phase * 1.7) * (amp * 0.4);
            if (x === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();
        phase += waveActive ? 0.12 : 0.025;
    }
    draw();
}

// Risk Gauge Canvas
function drawGauge(risk) {
    const canvas = document.getElementById('riskGauge');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const cx = w / 2, cy = h / 2;
    const r = Math.min(w, h) / 2 - 14;

    ctx.clearRect(0, 0, w, h);

    ctx.beginPath();
    ctx.arc(cx, cy, r, 0.75 * Math.PI, 2.25 * Math.PI);
    ctx.lineWidth = 12;
    ctx.strokeStyle = 'rgba(255,255,255,0.07)';
    ctx.lineCap = 'round';
    ctx.stroke();

    if (risk === null || risk === undefined) return;

    const end = 0.75 * Math.PI + 1.5 * Math.PI * Math.min(1, Math.max(0.01, risk));
    const grad = ctx.createLinearGradient(0, h, w, 0);
    if (risk >= 0.6) {
        grad.addColorStop(0, '#f59e0b');
        grad.addColorStop(1, '#ef4444');
    } else if (risk >= 0.25) {
        grad.addColorStop(0, '#10b981');
        grad.addColorStop(1, '#f59e0b');
    } else {
        grad.addColorStop(0, '#00f0ff');
        grad.addColorStop(1, '#10b981');
    }

    ctx.beginPath();
    ctx.arc(cx, cy, r, 0.75 * Math.PI, end);
    ctx.lineWidth = 12;
    ctx.strokeStyle = grad;
    ctx.lineCap = 'round';
    ctx.stroke();
}

// Actions
async function triggerAction(action) {
    const phone = document.getElementById('callerPhone').textContent;
    try {
        const res = await fetch('/api/execute-action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, phone_number: phone })
        });
        const data = await res.json();
        alert('Action Executed: ' + data.message);
        fetchAuditLedger();
    } catch (e) {
        alert('Action execution failed.');
    }
}

function openMfaModal() {
    document.getElementById('mfaModal').style.display = 'flex';
}
function closeMfa(success) {
    document.getElementById('mfaModal').style.display = 'none';
    if (success) {
        alert('MFA SUCCESSFUL. In-Call banking operations approved.');
    } else {
        alert('MFA FAILED. Terminating suspicious call.');
        triggerAction('BLOCK_AND_HOLD');
    }
}

// Audit Ledger
async function fetchAuditLedger() {
    try {
        const res = await fetch('/api/audit-ledger');
        const data = await res.json();
        const tbody = document.getElementById('ledgerBody');
        if (!data.entries || data.entries.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-row">No audit entries yet.</td></tr>';
            return;
        }
        tbody.innerHTML = data.entries.map(e =>
            '<tr>' +
            '<td><strong>#' + e.index + '</strong></td>' +
            '<td class="mono-cell">' + e.timestamp + '</td>' +
            '<td>' + e.phone_number + '</td>' +
            '<td><span class="risk-badge ' + (e.composite_risk > 0.5 ? 'danger' : 'safe') + '">' + (e.composite_risk * 100).toFixed(1) + '%</span></td>' +
            '<td><strong>' + e.policy_action + '</strong></td>' +
            '<td><span class="threat-tag ' + (e.threat_category !== 'CLEAN' ? 'danger' : 'info') + '">' + e.threat_category + '</span></td>' +
            '<td class="mono-cell hash-cell">' + (e.block_hash ? e.block_hash.slice(0, 16) + '...' : '-') + '</td>' +
            '</tr>'
        ).join('');
    } catch (e) {
        console.error('Ledger fetch failed:', e);
    }
}

function exportLedger() {
    window.open('/api/audit-ledger', '_blank');
}

// Threat DB
async function fetchThreatDB() {
    try {
        const res = await fetch('/api/threat-db');
        const threats = await res.json();
        const grid = document.getElementById('threatGrid');
        if (!threats || threats.length === 0) {
            grid.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-muted)">No threats registered yet. Run a high-risk scenario.</div>';
            return;
        }
        grid.innerHTML = threats.map(t =>
            '<div class="threat-card">' +
            '<div class="tc-top"><span class="tc-number">' + t.phone_number + '</span><span class="tc-status danger">' + t.status + '</span></div>' +
            '<div class="tc-title">' + t.reported_as + '</div>' +
            '<div class="tc-meta">Type: <code>' + t.scam_type + '</code> &bull; ' + t.last_seen + '</div>' +
            '<div class="tc-sig">Sig: ' + t.voice_signature_hash + '</div>' +
            '</div>'
        ).join('');
    } catch (e) {
        console.error('Threat DB fetch failed:', e);
    }
}

// Standalone Deepfake Check
function setupFileUpload() {
    const zone = document.getElementById('uploadZone');
    const input = document.getElementById('audioInput');
    if (!zone || !input) return;

    zone.addEventListener('click', () => input.click());
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) analyzeFile(e.dataTransfer.files[0]);
    });
    input.addEventListener('change', () => {
        if (input.files.length) analyzeFile(input.files[0]);
    });
}

async function analyzeFile(file) {
    const resultEl = document.getElementById('analyzeResult');
    resultEl.style.display = 'block';
    document.getElementById('arVerdict').textContent = 'Analyzing...';
    document.getElementById('arVerdict').className = 'ar-verdict';
    document.getElementById('arScoreVal').textContent = '--';
    document.getElementById('ardTime').textContent = '--';

    const fd = new FormData();
    fd.append('audio', file);

    try {
        const t0 = performance.now();
        const res = await fetch('/api/analyze', { method: 'POST', body: fd });
        const data = await res.json();
        const ms = Math.round(performance.now() - t0);

        const verdictEl = document.getElementById('arVerdict');
        verdictEl.textContent = data.decision;
        verdictEl.className = 'ar-verdict ' + (data.decision === 'SPOOF' ? 'danger' : 'safe');

        const scoreEl = document.getElementById('arScoreVal');
        scoreEl.textContent = data.spoof_probability + '%';
        scoreEl.className = 'ar-score-val ' + (data.decision === 'SPOOF' ? 'danger' : 'safe');

        document.getElementById('ardTime').textContent = (data.inference_time_ms || ms) + 'ms';
    } catch (e) {
        document.getElementById('arVerdict').textContent = 'Error';
    }
}

function toggleRecord() {
    if (!recordBtnActive) startRecord();
    else stopRecord();
}

async function startRecord() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const chunks = [];
        recordMediaRecorder = new MediaRecorder(stream);
        recordMediaRecorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
        recordMediaRecorder.onstop = () => {
            analyzeFile(new Blob(chunks, { type: 'audio/wav' }));
            stream.getTracks().forEach(t => t.stop());
        };
        recordMediaRecorder.start();
        recordBtnActive = true;
        document.getElementById('recordBtnText').textContent = 'Stop Recording';
        document.getElementById('recDot').classList.add('active');
        document.getElementById('recTimer').style.display = 'flex';
        recordSeconds = 0;
        recordTimer = setInterval(() => {
            recordSeconds++;
            const m = String(Math.floor(recordSeconds / 60)).padStart(2, '0');
            const s = String(recordSeconds % 60).padStart(2, '0');
            document.getElementById('timerDisplay').textContent = m + ':' + s;
        }, 1000);
    } catch (e) {
        alert('Microphone access denied.');
    }
}

function stopRecord() {
    if (recordMediaRecorder && recordMediaRecorder.state !== 'inactive') recordMediaRecorder.stop();
    recordBtnActive = false;
    document.getElementById('recordBtnText').textContent = 'Start Recording';
    document.getElementById('recDot').classList.remove('active');
    document.getElementById('recTimer').style.display = 'none';
    clearInterval(recordTimer);
}

// Background Particles
function initParticleCanvas() {
    const canvas = document.getElementById('particleCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
    const pts = Array.from({ length: 35 }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        r: Math.random() * 1.8 + 0.6
    }));
    function loop() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = 'rgba(0,240,255,0.35)';
        pts.forEach(p => {
            p.x += p.vx; p.y += p.vy;
            if (p.x < 0) p.x = canvas.width;
            if (p.x > canvas.width) p.x = 0;
            if (p.y < 0) p.y = canvas.height;
            if (p.y > canvas.height) p.y = 0;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fill();
        });
        requestAnimationFrame(loop);
    }
    loop();
}

function escapeHtml(str) {
    return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function escapeRegex(str) {
    return String(str || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
