export class AudioService {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private microphone: MediaStreamAudioSourceNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private animationFrameId: number | null = null;
  private stream: MediaStream | null = null;
  private pcmData: Float32Array[] = [];
  private isRecording = false;

  async startRecording(onVolumeUpdate: (vol: number) => void): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, sampleRate: 16000, echoCancellation: false, noiseSuppression: false, autoGainControl: false }
    });
    
    this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    
    this.microphone = this.audioContext.createMediaStreamSource(this.stream);
    this.microphone.connect(this.analyser);

    // Set up PCM capture
    const bufferSize = 4096;
    this.processor = this.audioContext.createScriptProcessor(bufferSize, 1, 1);
    this.pcmData = [];
    this.isRecording = true;

    this.processor.onaudioprocess = (e) => {
      if (!this.isRecording) return;
      const inputData = e.inputBuffer.getChannelData(0);
      this.pcmData.push(new Float32Array(inputData));
    };

    this.microphone.connect(this.processor);
    this.processor.connect(this.audioContext.destination);

    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    
    const updateVolume = () => {
      if (this.analyser && this.isRecording) {
        this.analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        onVolumeUpdate(sum / dataArray.length);
      }
      if (this.isRecording) {
        this.animationFrameId = requestAnimationFrame(updateVolume);
      }
    };
    updateVolume();
  }

  stopRecording(): Promise<File> {
    return new Promise((resolve) => {
      if (!this.isRecording) {
        resolve(new File([], "empty.wav"));
        return;
      }
      this.isRecording = false;

      // Flatten PCM data
      const totalLength = this.pcmData.reduce((acc, val) => acc + val.length, 0);
      const flattenedData = new Float32Array(totalLength);
      let offset = 0;
      for (const buffer of this.pcmData) {
        flattenedData.set(buffer, offset);
        offset += buffer.length;
      }

      const sampleRate = this.audioContext?.sampleRate || 16000;
      const wavBlob = this.encodeWAV(flattenedData, sampleRate);
      const file = new File([wavBlob], `recording_${Date.now()}.wav`, { type: "audio/wav" });
      
      this.cleanup();
      resolve(file);
    });
  }

  private encodeWAV(samples: Float32Array, sampleRate: number): Blob {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);
    
    const writeString = (view: DataView, offset: number, string: string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };
    
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM format
    view.setUint16(22, 1, true); // Mono channel
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true); // Byte rate
    view.setUint16(32, 2, true); // Block align
    view.setUint16(34, 16, true); // Bits per sample
    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);
    
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      let s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    
    return new Blob([view], { type: 'audio/wav' });
  }

  private cleanup() {
    this.isRecording = false;
    if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);
    
    if (this.processor) {
      this.processor.disconnect();
      this.processor.onaudioprocess = null;
      this.processor = null;
    }
    if (this.microphone) {
      this.microphone.disconnect();
      this.microphone = null;
    }
    if (this.analyser) {
      this.analyser.disconnect();
      this.analyser = null;
    }
    if (this.audioContext && this.audioContext.state !== "closed") {
      this.audioContext.close();
      this.audioContext = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.pcmData = [];
  }
}

export const audioService = new AudioService();
