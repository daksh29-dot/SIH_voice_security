const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:5000";
const IS_DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

export type WsState = "disconnected" | "connecting" | "connected" | "recording" | "processing" | "error";

export interface WsCallbacks {
  onStateChange: (state: WsState) => void;
  onPartialResult: (data: any) => void;
  onFinalResult: (data: any) => void;
  onError: (error: string) => void;
}

class WebSocketClient {
  private ws: WebSocket | null = null;
  private callbacks: WsCallbacks | null = null;
  private state: WsState = "disconnected";

  connect(callbacks: WsCallbacks) {
    this.callbacks = callbacks;
    if (IS_DEMO_MODE) {
      this.setState("connected");
      return;
    }

    this.setState("connecting");
    try {
      this.ws = new WebSocket(`${WS_URL}/ws/analyze`);
      
      this.ws.onopen = () => this.setState("connected");
      
      this.ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type === "processing") this.setState("processing");
        if (payload.type === "partial") this.callbacks?.onPartialResult(payload.data);
        if (payload.type === "final") this.callbacks?.onFinalResult(payload.data);
        if (payload.type === "error") {
          this.callbacks?.onError(payload.message || "Backend error");
          this.setState("error");
        }
      };

      this.ws.onerror = () => {
        this.callbacks?.onError("Backend unavailable");
        this.setState("error");
      };

      this.ws.onclose = () => {
        this.setState("disconnected");
      };
    } catch (e) {
      this.callbacks?.onError("Backend unavailable");
      this.setState("error");
    }
  }

  sendAudioChunk(chunk: Blob) {
    if (this.state === "connected" || this.state === "recording") {
      this.setState("recording");
      if (!IS_DEMO_MODE && this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(chunk);
      }
    }
  }

  finishRecording() {
    if (this.state === "recording") {
      this.setState("processing");
      if (!IS_DEMO_MODE && this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "finish" }));
      }
    }
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
    this.setState("disconnected");
  }

  private setState(newState: WsState) {
    this.state = newState;
    this.callbacks?.onStateChange(newState);
  }
}

export const wsClient = new WebSocketClient();

