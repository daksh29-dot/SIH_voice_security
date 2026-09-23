export class AudioService {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private microphone: MediaStreamAudioSourceNode | null = null;
  private animationFrameId: number | null = null;
  private stream: MediaStream | null = null;

  async startRecording(onVolumeUpdate: (vol: number) => void): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    
    this.microphone = this.audioContext.createMediaStreamSource(this.stream);
    this.microphone.connect(this.analyser);

    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    
    const updateVolume = () => {
      if (this.analyser) {
        this.analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        onVolumeUpdate(sum / dataArray.length);
      }
      this.animationFrameId = requestAnimationFrame(updateVolume);
    };
    updateVolume();

    this.mediaRecorder = new MediaRecorder(this.stream);
    this.audioChunks = [];
    
    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) this.audioChunks.push(e.data);
    };
    
    this.mediaRecorder.start(100); // 100ms chunks
  }

  stopRecording(): Promise<File> {
    return new Promise((resolve) => {
      if (!this.mediaRecorder || this.mediaRecorder.state === "inactive") {
        resolve(new File([], "empty.wav"));
        return;
      }

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: "audio/webm" });
        const file = new File([audioBlob], `recording_${Date.now()}.webm`, { type: "audio/webm" });
        this.cleanup();
        resolve(file);
      };

      this.mediaRecorder.stop();
    });
  }

  private cleanup() {
    if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);
    if (this.microphone) this.microphone.disconnect();
    if (this.analyser) this.analyser.disconnect();
    if (this.audioContext && this.audioContext.state !== "closed") {
      this.audioContext.close();
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }
  }
}

export const audioService = new AudioService();

