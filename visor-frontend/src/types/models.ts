export type Severity = "Informational" | "Low" | "Moderate" | "High" | "Critical";

export interface EvidenceItem {
  signal: string;
  observedValue: string;
  interpretation: string;
  confidence: number;
}

export type ThreatCategory = "Suspicious Patterns" | "Voice Spoofing Indicators" | "Communication Risk" | "Speaker Signals" | "Channel Trust";

export interface ThreatIndicator {
  id: string;
  category: ThreatCategory;
  title: string;
  severity: Severity;
  summary: string;
  evidence: EvidenceItem[];
  timestamp: string;
}

export interface VoiceSignal {
  durationMs: number;
  format: string;
  sampleRate: number;
  channels: number;
  source: string;
}

export interface SystemStatus {
  status: "Operational" | "Degraded" | "Offline";
  lastCheck: string;
  activeConnections: number;
  latencyMs: number;
}

export interface ModelStatus {
  engine: string;
  inference: string;
  backend: "Connected" | "Demo Mode" | "Disconnected";
  version: string;
}

export type PolicyAction = "PROCEED_NORMALLY" | "STEP_UP_MFA" | "BLOCK_AND_HOLD";

export interface Analysis {
  id: string;
  timestamp: string;
  status: "processing" | "completed" | "failed";
  filename: string;
  duration: string;
  composite_risk_score: number;
  policy_action: PolicyAction;
  signalContext: VoiceSignal;
  pillars: {
    voice_clone: { score: number; label: string };
    caller_telecom: { risk_score: number; stir_shaken: string; voip: boolean };
    scam_nlp: { risk_score: number; detected_intent: string; keywords: string[] };
    voice_biometrics: { risk_score: number; match: boolean };
  };
}
