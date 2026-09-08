/* ═══════════════════════════════════════════════════════════════════
   VoiceGuard AI — Frontend Application Logic
   ═══════════════════════════════════════════════════════════════════ */

// ── Constants ─────────────────────────────────────────────────────
const API_BASE = '';  // Same origin

// ── State ─────────────────────────────────────────────────────────
let mediaRecorder = null;
let audioChunks = [];
let recordingInterval = null;
let recordingStartTime = 0;
let analysisHistory = [];

// ══════════════════════════════════════════════════════════════════
// NAVIGATION
// ══════════════════════════════════════════════════════════════════
function navigateTo(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.remove('active');
        // Force reflow for animation
        void section.offsetWidth;
        section.classList.add('active');
    }

    const link = document.querySelector(`.nav-link[data-section="${sectionId}"]`);
    if (link) link.classList.add('active');

    // Load data for specific sections
    if (sectionId === 'metrics') loadMetrics();
    if (sectionId === 'dashboard') {
        loadHistory();
        animateStats();
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Nav link handlers
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        navigateTo(link.dataset.section);
    });
});

// Navbar scroll effect
window.addEventListener('scroll', () => {
    const nav = document.getElementById('navbar');
    nav.classList.toggle('scrolled', window.scrollY > 20);
});

// ══════════════════════════════════════════════════════════════════
// PARTICLE BACKGROUND
// ══════════════════════════════════════════════════════════════════
(function initParticles() {
    const canvas = document.getElementById('particleCanvas');
    const ctx = canvas.getContext('2d');
    let particles = [];
    const PARTICLE_COUNT = 60;

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }

    function createParticle() {
        return {
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 0.3,
            vy: (Math.random() - 0.5) * 0.3,
            size: Math.random() * 2 + 0.5,
            opacity: Math.random() * 0.3 + 0.1,
            hue: Math.random() > 0.5 ? 185 : 270,  // cyan or purple
        };
    }

    function init() {
        resize();
        particles = Array.from({ length: PARTICLE_COUNT }, createParticle);
    }

    function drawParticles() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw connections
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 150) {
                    const opacity = (1 - dist / 150) * 0.08;
                    ctx.beginPath();
                    ctx.strokeStyle = `rgba(0, 240, 255, ${opacity})`;
                    ctx.lineWidth = 0.5;
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.stroke();
                }
            }
        }

        // Draw particles
        particles.forEach(p => {
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${p.hue}, 100%, 70%, ${p.opacity})`;
            ctx.fill();

            p.x += p.vx;
            p.y += p.vy;

            if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
            if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
        });

        requestAnimationFrame(drawParticles);
    }

    window.addEventListener('resize', resize);
    init();
    drawParticles();
})();

// ══════════════════════════════════════════════════════════════════
// HERO WAVEFORM ANIMATION
// ══════════════════════════════════════════════════════════════════
(function initHeroWaveform() {
    const canvas = document.getElementById('waveformCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    function resizeCanvas() {
        const rect = canvas.parentElement.getBoundingClientRect();
        canvas.width = rect.width - 48;
        canvas.height = 200;
    }

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    let time = 0;
    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const centerY = canvas.height / 2;

        // Draw grid lines
        ctx.strokeStyle = 'rgba(255,255,255,0.04)';
        ctx.lineWidth = 1;
        for (let y = 0; y < canvas.height; y += 20) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(canvas.width, y);
            ctx.stroke();
        }

        // Draw multiple waveforms
        const waves = [
            { amp: 40, freq: 0.015, speed: 0.03, color: 'rgba(0, 240, 255, 0.5)', width: 2 },
            { amp: 25, freq: 0.02, speed: 0.02, color: 'rgba(123, 47, 247, 0.4)', width: 1.5 },
            { amp: 15, freq: 0.035, speed: 0.04, color: 'rgba(247, 47, 160, 0.3)', width: 1 },
        ];

        waves.forEach(wave => {
            ctx.beginPath();
            ctx.strokeStyle = wave.color;
            ctx.lineWidth = wave.width;

            for (let x = 0; x < canvas.width; x++) {
                const y = centerY +
                    Math.sin(x * wave.freq + time * wave.speed) * wave.amp *
                    Math.sin(x * 0.003 + time * 0.01) +
                    Math.sin(x * wave.freq * 2.7 + time * wave.speed * 1.3) * wave.amp * 0.3;
                if (x === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
        });

        // Center line
        ctx.strokeStyle = 'rgba(0, 240, 255, 0.1)';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(0, centerY);
        ctx.lineTo(canvas.width, centerY);
        ctx.stroke();
        ctx.setLineDash([]);

        time++;
        requestAnimationFrame(draw);
    }

    draw();
})();

// ══════════════════════════════════════════════════════════════════
// STAT COUNTER ANIMATION
// ══════════════════════════════════════════════════════════════════
function animateStats() {
    document.querySelectorAll('.stat-value[data-target]').forEach(el => {
        const target = parseInt(el.dataset.target);
        const duration = 1500;
        const startTime = performance.now();
        const startVal = 0;

        function update(now) {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.round(startVal + (target - startVal) * eased);
            if (progress < 1) requestAnimationFrame(update);
        }

        requestAnimationFrame(update);
    });
}

// ══════════════════════════════════════════════════════════════════
// FILE UPLOAD
// ══════════════════════════════════════════════════════════════════
const uploadZone = document.getElementById('uploadZone');
const audioInput = document.getElementById('audioInput');

uploadZone.addEventListener('click', () => audioInput.click());

uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
        analyzeFile(e.dataTransfer.files[0]);
    }
});

audioInput.addEventListener('change', () => {
    if (audioInput.files.length > 0) {
        analyzeFile(audioInput.files[0]);
    }
});

// ══════════════════════════════════════════════════════════════════
// ANALYZE FILE
// ══════════════════════════════════════════════════════════════════
async function analyzeFile(file) {
    // Show loading overlay
    const overlay = document.createElement('div');
    overlay.className = 'analyzing-overlay';
    overlay.innerHTML = `
        <div class="analyzing-spinner"></div>
        <div class="analyzing-text">Analyzing Voice Sample</div>
        <div class="analyzing-subtext">Running AASIST-L neural network inference…</div>
    `;
    document.body.appendChild(overlay);

    // Hide previous results
    document.getElementById('resultContainer').style.display = 'none';

    const formData = new FormData();
    formData.append('audio', file);

    try {
        const response = await fetch(`${API_BASE}/api/analyze`, {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Analysis failed');
        }

        displayResult(data);
        showToast('Analysis complete!', 'success');

    } catch (err) {
        showToast(`Error: ${err.message}`, 'error');
        console.error('Analysis error:', err);
    } finally {
        overlay.remove();
    }
}

// ══════════════════════════════════════════════════════════════════
// DISPLAY RESULT
// ══════════════════════════════════════════════════════════════════
function displayResult(data) {
    const container = document.getElementById('resultContainer');
    const card = document.getElementById('resultCard');

    // Set card class based on decision
    card.className = 'result-card ' + data.decision.toLowerCase();

    // Verdict icon
    const iconMap = {
        REAL: '✅',
        SPOOF: '⚠️',
        UNCERTAIN: '❓'
    };
    document.getElementById('verdictIcon').textContent = iconMap[data.decision] || '❓';
    document.getElementById('verdictLabel').textContent = data.decision;
    document.getElementById('verdictFile').textContent = data.filename;

    // Score
    document.getElementById('scoreValue').textContent = data.spoof_probability + '%';

    // Draw score gauge
    drawScoreGauge(data.spoof_probability / 100);

    // Details
    document.getElementById('detailTime').textContent = data.inference_time_s + 's';
    document.getElementById('detailSegments').textContent = data.num_segments;
    document.getElementById('detailAggregation').textContent = data.aggregation_strategy;
    document.getElementById('detailThreshold').textContent = data.threshold_used;

    // Segment bars
    const barsContainer = document.getElementById('segmentBars');
    barsContainer.innerHTML = '';
    data.segment_scores.forEach((score, i) => {
        const bar = document.createElement('div');
        bar.className = 'segment-bar';
        bar.classList.add(score < 0.4 ? 'low' : score > 0.6 ? 'high' : 'mid');
        bar.style.height = '0%';
        bar.dataset.score = score.toFixed(4);
        bar.title = `Segment ${i + 1}: ${score.toFixed(4)}`;
        barsContainer.appendChild(bar);

        // Animate in
        requestAnimationFrame(() => {
            setTimeout(() => {
                bar.style.height = Math.max(score * 100, 5) + '%';
            }, i * 80);
        });
    });

    container.style.display = 'block';
    container.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ══════════════════════════════════════════════════════════════════
// SCORE GAUGE (Canvas arc)
// ══════════════════════════════════════════════════════════════════
function drawScoreGauge(value) {
    const canvas = document.getElementById('scoreGauge');
    const ctx = canvas.getContext('2d');
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const radius = 55;
    const lineWidth = 8;
    const startAngle = Math.PI * 0.75;
    const endAngle = Math.PI * 2.25;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background arc
    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, endAngle);
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Value arc
    const valueAngle = startAngle + (endAngle - startAngle) * value;
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);

    if (value < 0.4) {
        gradient.addColorStop(0, '#00e676');
        gradient.addColorStop(1, '#00b0ff');
    } else if (value > 0.6) {
        gradient.addColorStop(0, '#ff3d71');
        gradient.addColorStop(1, '#f72fa0');
    } else {
        gradient.addColorStop(0, '#ffab00');
        gradient.addColorStop(1, '#ff6d00');
    }

    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, valueAngle);
    ctx.strokeStyle = gradient;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();
}

// ══════════════════════════════════════════════════════════════════
// RESET ANALYSIS
// ══════════════════════════════════════════════════════════════════
function resetAnalysis() {
    document.getElementById('resultContainer').style.display = 'none';
    audioInput.value = '';
}

// ══════════════════════════════════════════════════════════════════
// RECORDING
// ══════════════════════════════════════════════════════════════════
const recordBtn = document.getElementById('recordBtn');
const recordBtnText = document.getElementById('recordBtnText');
const recordingTimer = document.getElementById('recordingTimer');
const timerDisplay = document.getElementById('timerDisplay');
const liveWaveformContainer = document.getElementById('liveWaveformContainer');
let audioContext, analyser, dataArray, liveWaveformCtx, animFrameId;

recordBtn.addEventListener('click', toggleRecording);

async function toggleRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopRecording();
    } else {
        await startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
        mediaRecorder.onstop = async () => {
            // Browser records in WebM/Opus, NOT WAV.
            // Convert to real PCM WAV so librosa can decode it.
            const webmBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
            try {
                const wavBlob = await convertToWav(webmBlob);
                const file = new File([wavBlob], 'recording.wav', { type: 'audio/wav' });
                analyzeFile(file);
            } catch (err) {
                showToast('Failed to process recording: ' + err.message, 'error');
            }
            stream.getTracks().forEach(t => t.stop());
            cancelAnimationFrame(animFrameId);
        };

        mediaRecorder.start();
        recordBtn.classList.add('recording');
        recordBtnText.textContent = 'Stop Recording';
        recordingTimer.classList.add('active');
        recordingStartTime = Date.now();

        recordingInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
            const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
            const secs = String(elapsed % 60).padStart(2, '0');
            timerDisplay.textContent = `${mins}:${secs}`;
        }, 1000);

        // Live waveform
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        dataArray = new Uint8Array(analyser.frequencyBinCount);

        liveWaveformContainer.style.display = 'block';
        const liveCanvas = document.getElementById('liveWaveformCanvas');
        liveWaveformCtx = liveCanvas.getContext('2d');
        liveCanvas.width = liveCanvas.parentElement.clientWidth - 32;

        drawLiveWaveform();

    } catch (err) {
        showToast('Microphone access denied', 'error');
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    }
    recordBtn.classList.remove('recording');
    recordBtnText.textContent = 'Start Recording';
    recordingTimer.classList.remove('active');
    clearInterval(recordingInterval);
    liveWaveformContainer.style.display = 'none';
}

function drawLiveWaveform() {
    if (!analyser) return;
    analyser.getByteTimeDomainData(dataArray);

    const canvas = document.getElementById('liveWaveformCanvas');
    const ctx = liveWaveformCtx;
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    // Draw waveform
    ctx.beginPath();
    const gradient = ctx.createLinearGradient(0, 0, w, 0);
    gradient.addColorStop(0, '#ff3d71');
    gradient.addColorStop(0.5, '#f72fa0');
    gradient.addColorStop(1, '#7b2ff7');
    ctx.strokeStyle = gradient;
    ctx.lineWidth = 2;

    const sliceWidth = w / dataArray.length;
    let x = 0;

    for (let i = 0; i < dataArray.length; i++) {
        const v = dataArray[i] / 128.0;
        const y = (v * h) / 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        x += sliceWidth;
    }
    ctx.stroke();

    animFrameId = requestAnimationFrame(drawLiveWaveform);
}

// ══════════════════════════════════════════════════════════════════
// LOAD METRICS
// ══════════════════════════════════════════════════════════════════
async function loadMetrics() {
    try {
        const res = await fetch(`${API_BASE}/api/metrics`);
        if (!res.ok) return;
        const data = await res.json();

        // Update values
        document.getElementById('accuracyValue').textContent = (data.accuracy * 100) + '%';
        document.getElementById('f1Value').textContent = data.f1.toFixed(2);
        document.getElementById('eerValue').textContent = (data.eer * 100) + '%';
        document.getElementById('precisionVal').textContent = data.precision.toFixed(2);
        document.getElementById('recallVal').textContent = data.recall.toFixed(2);
        document.getElementById('fprVal').textContent = data.false_positive_rate.toFixed(2);
        document.getElementById('fnrVal').textContent = data.false_negative_rate.toFixed(2);

        // Confusion matrix
        if (data.confusion_matrix) {
            document.querySelector('#matrixTP .cell-value').textContent = data.confusion_matrix.tp;
            document.querySelector('#matrixTN .cell-value').textContent = data.confusion_matrix.tn;
            document.querySelector('#matrixFP .cell-value').textContent = data.confusion_matrix.fp;
            document.querySelector('#matrixFN .cell-value').textContent = data.confusion_matrix.fn;
        }

        // Draw metric rings
        drawMetricRing('accuracyRing', data.accuracy, '#00e676', '#00b0ff');
        drawMetricRing('f1Ring', data.f1, '#00f0ff', '#7b2ff7');
        drawMetricRing('eerRing', 1 - data.eer, '#f72fa0', '#7b2ff7');  // Invert EER for visual

    } catch (err) {
        console.error('Failed to load metrics:', err);
    }
}

function drawMetricRing(canvasId, value, color1, color2) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const radius = 65;
    const lineWidth = 10;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background ring
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = lineWidth;
    ctx.stroke();

    // Value ring with animation
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    gradient.addColorStop(0, color1);
    gradient.addColorStop(1, color2);

    const startAngle = -Math.PI / 2;
    const endAngle = startAngle + (Math.PI * 2 * value);

    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, endAngle);
    ctx.strokeStyle = gradient;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();
}

// ══════════════════════════════════════════════════════════════════
// LOAD HISTORY
// ══════════════════════════════════════════════════════════════════
async function loadHistory() {
    try {
        const res = await fetch(`${API_BASE}/api/history`);
        if (!res.ok) return;
        const data = await res.json();

        const list = document.getElementById('historyList');
        if (data.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
                    <p>No analyses yet. Upload an audio file to get started.</p>
                </div>
            `;
            return;
        }

        list.innerHTML = data.map(item => `
            <div class="history-item">
                <span class="history-badge ${item.decision.toLowerCase()}">${item.decision}</span>
                <span class="history-filename">${item.filename}</span>
                <span class="history-score">Score: ${item.aggregated_score.toFixed(4)}</span>
                <span class="history-time">${item.inference_time_s}s</span>
            </div>
        `).join('');

    } catch (err) {
        console.error('Failed to load history:', err);
    }
}

// ══════════════════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ══════════════════════════════════════════════════════════════════
function showToast(message, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ══════════════════════════════════════════════════════════════════
// WAV CONVERSION (Browser records WebM/Opus, backend needs WAV)
// ══════════════════════════════════════════════════════════════════
async function convertToWav(blob) {
    const arrayBuffer = await blob.arrayBuffer();
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
    ctx.close();

    // Downsample to 16kHz mono (matches AASIST-L input)
    const targetSampleRate = 16000;
    const offlineCtx = new OfflineAudioContext(1, audioBuffer.duration * targetSampleRate, targetSampleRate);
    const source = offlineCtx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(offlineCtx.destination);
    source.start(0);
    const renderedBuffer = await offlineCtx.startRendering();

    const pcmData = renderedBuffer.getChannelData(0);
    return encodeWav(pcmData, targetSampleRate);
}

function encodeWav(samples, sampleRate) {
    const numChannels = 1;
    const bitsPerSample = 16;
    const bytesPerSample = bitsPerSample / 8;
    const blockAlign = numChannels * bytesPerSample;
    const dataSize = samples.length * bytesPerSample;
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);

    // RIFF header
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeString(view, 8, 'WAVE');

    // fmt chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);                     // chunk size
    view.setUint16(20, 1, true);                      // PCM format
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * blockAlign, true); // byte rate
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);

    // data chunk
    writeString(view, 36, 'data');
    view.setUint32(40, dataSize, true);

    // PCM samples (float32 -> int16)
    let offset = 44;
    for (let i = 0; i < samples.length; i++) {
        const s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        offset += 2;
    }

    return new Blob([buffer], { type: 'audio/wav' });
}

function writeString(view, offset, str) {
    for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
    }
}

// ══════════════════════════════════════════════════════════════════
// INITIALIZATION
// ══════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    animateStats();
    loadMetrics();

    // Draw initial metric rings with defaults
    setTimeout(() => {
        drawMetricRing('accuracyRing', 1.0, '#00e676', '#00b0ff');
        drawMetricRing('f1Ring', 1.0, '#00f0ff', '#7b2ff7');
        drawMetricRing('eerRing', 1.0, '#f72fa0', '#7b2ff7');
    }, 200);
});
