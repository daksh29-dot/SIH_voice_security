/**
 * static/js/recorder.js
 * 
 * Project VISOR Web Audio API Streaming Recorder (Phase 6).
 * Uses AudioContext and AudioWorkletNode to capture microphone audio at 16kHz mono,
 * encodes frames to Int16/Float32 PCM, and streams binary chunks continuously over WebSocket.
 */

class AudioStreamRecorder {
    constructor(options = {}) {
        this.targetSampleRate = options.targetSampleRate || 16000;
        this.chunkSize = options.chunkSize || 2048; // ~128ms at 16kHz
        this.onAudioChunk = options.onAudioChunk || null;
        this.onVolumeChange = options.onVolumeChange || null;
        this.onError = options.onError || console.error;

        this.audioContext = null;
        this.mediaStream = null;
        this.sourceNode = null;
        this.workletNode = null;
        this.scriptNode = null;
        this.analyserNode = null;
        this.isRecording = false;
        this.websocket = null;
    }

    async start(ws = null) {
        if (this.isRecording) return;
        this.websocket = ws;

        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
                video: false,
            });

            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            try {
                this.audioContext = new AudioCtx({ sampleRate: this.targetSampleRate });
            } catch (e) {
                this.audioContext = new AudioCtx();
            }

            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }

            this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

            this.analyserNode = this.audioContext.createAnalyser();
            this.analyserNode.fftSize = 512;
            this.analyserNode.smoothingTimeConstant = 0.8;
            this.sourceNode.connect(this.analyserNode);

            const workletSuccess = await this._initAudioWorklet();
            if (!workletSuccess) {
                this._initScriptProcessor();
            }

            this.isRecording = true;
            console.log(`[VISOR AudioStreamRecorder] Started at ${this.audioContext.sampleRate}Hz -> target ${this.targetSampleRate}Hz.`);
        } catch (err) {
            this.stop();
            this.onError(err);
            throw err;
        }
    }

    async _initAudioWorklet() {
        if (!this.audioContext.audioWorklet) return false;

        const workletCode = `
            class PCMStreamProcessor extends AudioWorkletProcessor {
                constructor() {
                    super();
                    this.bufferSize = ${this.chunkSize};
                    this.buffer = new Float32Array(this.bufferSize);
                    this.count = 0;
                }
                process(inputs, outputs, parameters) {
                    const input = inputs[0];
                    if (!input || !input[0]) return true;
                    const channel = input[0];
                    for (let i = 0; i < channel.length; i++) {
                        this.buffer[this.count++] = channel[i];
                        if (this.count >= this.bufferSize) {
                            this.port.postMessage(this.buffer.slice(0));
                            this.count = 0;
                        }
                    }
                    return true;
                }
            }
            registerProcessor('pcm-stream-processor', PCMStreamProcessor);
        `;

        try {
            const blob = new Blob([workletCode], { type: 'application/javascript' });
            const url = URL.createObjectURL(blob);
            await this.audioContext.audioWorklet.addModule(url);
            URL.revokeObjectURL(url);

            this.workletNode = new AudioWorkletNode(this.audioContext, 'pcm-stream-processor');
            this.workletNode.port.onmessage = (event) => {
                this._processFloat32Chunk(event.data);
            };

            this.sourceNode.connect(this.workletNode);
            const dummyGain = this.audioContext.createGain();
            dummyGain.gain.value = 0;
            this.workletNode.connect(dummyGain);
            dummyGain.connect(this.audioContext.destination);

            return true;
        } catch (e) {
            console.warn('[VISOR AudioStreamRecorder] AudioWorklet init failed, using fallback ScriptProcessor:', e);
            return false;
        }
    }

    _initScriptProcessor() {
        this.scriptNode = this.audioContext.createScriptProcessor(this.chunkSize, 1, 1);
        this.scriptNode.onaudioprocess = (e) => {
            if (!this.isRecording) return;
            const inputData = e.inputBuffer.getChannelData(0);
            this._processFloat32Chunk(new Float32Array(inputData));
        };
        this.sourceNode.connect(this.scriptNode);
        this.scriptNode.connect(this.audioContext.destination);
    }

    _processFloat32Chunk(float32Array) {
        if (!this.isRecording) return;

        let samples = float32Array;
        const currentRate = this.audioContext.sampleRate;
        if (currentRate !== this.targetSampleRate) {
            samples = this._resampleLinear(float32Array, currentRate, this.targetSampleRate);
        }

        let sumSq = 0;
        for (let i = 0; i < samples.length; i++) {
            sumSq += samples[i] * samples[i];
        }
        const rms = Math.sqrt(sumSq / samples.length);
        if (this.onVolumeChange) {
            this.onVolumeChange(Math.min(1.0, rms * 5.0));
        }

        const int16Buffer = new Int16Array(samples.length);
        for (let i = 0; i < samples.length; i++) {
            const s = Math.max(-1.0, Math.min(1.0, samples[i]));
            int16Buffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        const binaryChunk = int16Buffer.buffer;

        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(binaryChunk);
        }

        if (this.onAudioChunk) {
            this.onAudioChunk(binaryChunk, int16Buffer);
        }
    }

    _resampleLinear(buffer, fromRate, toRate) {
        if (fromRate === toRate) return buffer;
        const ratio = fromRate / toRate;
        const newLength = Math.round(buffer.length / ratio);
        const result = new Float32Array(newLength);
        for (let i = 0; i < newLength; i++) {
            const originIndex = i * ratio;
            const leftIndex = Math.floor(originIndex);
            const rightIndex = Math.min(leftIndex + 1, buffer.length - 1);
            const fraction = originIndex - leftIndex;
            result[i] = buffer[leftIndex] + fraction * (buffer[rightIndex] - buffer[leftIndex]);
        }
        return result;
    }

    getWaveformData(dataArray) {
        if (this.analyserNode) {
            this.analyserNode.getByteTimeDomainData(dataArray);
        }
    }

    stop() {
        this.isRecording = false;

        if (this.workletNode) {
            try { this.workletNode.disconnect(); } catch (e) {}
            this.workletNode = null;
        }
        if (this.scriptNode) {
            try { this.scriptNode.disconnect(); } catch (e) {}
            this.scriptNode = null;
        }
        if (this.sourceNode) {
            try { this.sourceNode.disconnect(); } catch (e) {}
            this.sourceNode = null;
        }
        if (this.analyserNode) {
            try { this.analyserNode.disconnect(); } catch (e) {}
            this.analyserNode = null;
        }
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach((track) => track.stop());
            this.mediaStream = null;
        }
        if (this.audioContext && this.audioContext.state !== 'closed') {
            try { this.audioContext.close(); } catch (e) {}
            this.audioContext = null;
        }
        this.websocket = null;
        console.log('[VISOR AudioStreamRecorder] Stopped.');
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AudioStreamRecorder };
}
if (typeof window !== 'undefined') {
    window.AudioStreamRecorder = AudioStreamRecorder;
}
