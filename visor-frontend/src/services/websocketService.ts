/**
 * WebSocket service abstraction for real-time inference.
 */
export class WebSocketService {
  private ws: WebSocket | null = null;
  private onMessageCallback: ((data: any) => void) | null = null;

  connect(url: string) {
    console.log(`[WS] Prepared to connect to ${url}`);
  }

  onMessage(callback: (data: any) => void) {
    this.onMessageCallback = callback;
  }

  sendAudioChunk(chunk: Blob) {
    // Implement sending binary payload to backend
  }

  disconnect() {
    console.log("[WS] Disconnected");
  }
}

export const websocketService = new WebSocketService();

