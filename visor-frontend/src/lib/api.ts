import { Analysis } from "@/types/models";
import { analysisService } from "@/services/analysisService"; // fallback for demo mode

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";
const IS_DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

export const api = {
  getIsDemoMode: () => IS_DEMO_MODE,

  analyze: async (file: File, enrolled_speaker_id?: string): Promise<Analysis> => {
    if (IS_DEMO_MODE) {
      return analysisService.simulateAnalysis(file);
    }

    const formData = new FormData();
    formData.append("audio", file);
    formData.append("phone_number", "Web Microphone");
    formData.append("carrier", "WebRTC");
    if (enrolled_speaker_id) {
      formData.append("enrolled_speaker_id", enrolled_speaker_id);
    }

    try {
      const response = await fetch(`${API_URL}/api/analyze-call`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
      }

      const data = await response.json();
      
      return {
        id: data.call_id || Math.random().toString(36).substring(2, 9),
        timestamp: data.timestamp || new Date().toISOString(),
        status: "completed",
        filename: file.name,
        duration: ((data.total_processing_time_ms || 1000) / 1000).toFixed(1) + "s",
        composite_risk_score: data.orchestration?.composite_risk_score || 0,
        policy_action: data.orchestration?.policy_action || "PROCEED_NORMALLY",
        pillars: {
          voice_clone: {
            score: data.pillars?.voice_clone?.score || 0,
            label: data.pillars?.voice_clone?.label || "Unknown",
          },
          caller_telecom: { 
            risk_score: data.pillars?.caller_telecom?.risk_score || 0,
            stir_shaken: data.pillars?.caller_telecom?.stir_shaken || "N/A",
            voip: data.pillars?.caller_telecom?.voip_flag || false
          },
          scam_nlp: { 
            risk_score: data.pillars?.scam_nlp?.risk_score || 0,
            detected_intent: data.pillars?.scam_nlp?.detected_intent || "No speech detected",
            keywords: data.pillars?.scam_nlp?.matched_keywords || []
          },
          voice_biometrics: {
            risk_score: data.pillars?.voice_biometrics?.risk_score,
            match: data.pillars?.voice_biometrics?.is_enrolled_match || false
          }
        },
        signalContext: {
          durationMs: data.total_processing_time_ms || 1000,
          format: "audio/wav",
          sampleRate: 16000,
          channels: 1,
          source: file.name
        }
      };
    } catch (error) {
      console.error("[API] analyze error:", error);
      throw new Error("Backend unavailable");
    }
  },

  analyzePreset: async (preset: any, enrolled_speaker_id?: string): Promise<Analysis> => {
    const formData = new FormData();
    formData.append("phone_number", preset.phone_number);
    formData.append("carrier", preset.carrier);
    formData.append("stir_shaken", preset.stir_shaken);
    formData.append("voip_flag", preset.voip_flag ? "true" : "false");
    formData.append("transcript", preset.transcript);
    formData.append("preset_voice_score", preset.preset_voice_score.toString());
    if (enrolled_speaker_id) {
      formData.append("enrolled_speaker_id", enrolled_speaker_id);
    }

    try {
      const response = await fetch(`${API_URL}/api/analyze-call`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error(`Backend error: ${response.status}`);
      const data = await response.json();
      
      return {
        id: data.call_id || Math.random().toString(36).substring(2, 9),
        timestamp: data.timestamp || new Date().toISOString(),
        status: "completed",
        filename: preset.name,
        duration: ((data.total_processing_time_ms || 1000) / 1000).toFixed(1) + "s",
        composite_risk_score: data.orchestration?.composite_risk_score || 0,
        policy_action: data.orchestration?.policy_action || "PROCEED_NORMALLY",
        pillars: {
          voice_clone: {
            score: data.pillars?.voice_clone?.score || 0,
            label: data.pillars?.voice_clone?.label || "Unknown",
          },
          caller_telecom: { 
            risk_score: data.pillars?.caller_telecom?.risk_score || 0,
            stir_shaken: data.pillars?.caller_telecom?.stir_shaken || "N/A",
            voip: data.pillars?.caller_telecom?.voip_flag || false
          },
          scam_nlp: { 
            risk_score: data.pillars?.scam_nlp?.risk_score || 0,
            detected_intent: data.pillars?.scam_nlp?.detected_intent || "No speech detected",
            keywords: data.pillars?.scam_nlp?.matched_keywords || []
          },
          voice_biometrics: {
            risk_score: data.pillars?.voice_biometrics?.risk_score,
            match: data.pillars?.voice_biometrics?.is_enrolled_match || false
          }
        },
        signalContext: {
          durationMs: data.total_processing_time_ms || 1000,
          format: "preset/json",
          sampleRate: 16000,
          channels: 1,
          source: preset.name
        }
      };
    } catch (error) {
      console.error("[API] analyzePreset error:", error);
      throw new Error("Backend unavailable");
    }
  },

  getHistory: async (): Promise<Analysis[]> => {
    if (IS_DEMO_MODE) {
      return [];
    }

    try {
      const response = await fetch(`${API_URL}/api/audit-ledger`);
      if (!response.ok) throw new Error("Failed to fetch history");
      
      const data = await response.json();
      return (data.entries || []).map((entry: any) => ({
        id: entry.block_hash.substring(0, 8),
        timestamp: entry.timestamp,
        status: "completed",
        filename: entry.phone_number || "Unknown",
        duration: "0.0s",
        composite_risk_score: entry.composite_risk || 0,
        policy_action: entry.policy_action || "PROCEED_NORMALLY",
        pillars: {
          voice_clone: {
            score: entry.pillar_details?.voice_clone_risk || 0,
            label: (entry.pillar_details?.voice_clone_risk || 0) > 0.6 ? "AI Synthetic Voice" : "Human Natural Voice",
          },
          caller_telecom: { 
            risk_score: entry.pillar_details?.caller_cli_risk || 0,
            stir_shaken: "N/A",
            voip: false
          },
          scam_nlp: { 
            risk_score: entry.pillar_details?.scam_words_risk || 0,
            detected_intent: entry.threat_category || "Unknown",
            keywords: entry.pillar_details?.matched_keywords || []
          },
          voice_biometrics: {
            risk_score: entry.pillar_details?.biometric_risk || 0,
            match: (entry.pillar_details?.biometric_risk || 0) < 0.5
          }
        },
        signalContext: {
          durationMs: 0,
          format: "audio/wav",
          sampleRate: 16000,
          channels: 1,
          source: entry.phone_number || "Unknown",
        }
      }));
    } catch (error) {
      console.error("[API] getHistory error:", error);
      throw new Error("Backend unavailable");
    }
  },

  getAnalysis: async (id: string): Promise<Analysis | null> => {
    if (IS_DEMO_MODE) return null;
    try {
      return null;
    } catch (error) {
      console.error("[API] getAnalysis error:", error);
      throw new Error("Backend unavailable");
    }
  },

  getThreats: async (): Promise<any[]> => {
    if (IS_DEMO_MODE) {
      return [];
    }

    try {
      const response = await fetch(`${API_URL}/api/threat-db`);
      if (!response.ok) throw new Error("Failed to fetch threats");
      const data = await response.json();
      
      return data.map((t: any) => ({
        id: t.id,
        category: "Voice Spoofing Indicators",
        title: t.reported_as || "Malicious Activity",
        severity: t.risk_level === "CRITICAL" ? "Critical" : "High",
        summary: `Threat actor mapped to ${t.phone_number}`,
        timestamp: t.last_seen || new Date().toISOString(),
        evidence: [
          { signal: "Voice Clone Hash", observedValue: t.voice_signature_hash || "N/A", interpretation: "Match", confidence: 0.99 }
        ]
      }));
    } catch (error) {
      console.error("[API] getThreats error:", error);
      throw new Error("Backend unavailable");
    }
  },

  getPresets: async (): Promise<any[]> => {
    if (IS_DEMO_MODE) return [];
    try {
      const response = await fetch(`${API_URL}/api/presets`);
      if (!response.ok) throw new Error("Failed to fetch presets");
      return await response.json();
    } catch (error) {
      console.error("[API] getPresets error:", error);
      return [];
    }
  },

  getEnrolledVoices: async (): Promise<string[]> => {
    if (IS_DEMO_MODE) return [];
    try {
      const response = await fetch(`${API_URL}/api/enrolled-voices`);
      if (!response.ok) throw new Error("Failed to fetch enrolled voices");
      return await response.json();
    } catch (error) {
      console.error("[API] getEnrolledVoices error:", error);
      return [];
    }
  },

  enrollVoice: async (file: Blob, speakerId: string): Promise<boolean> => {
    if (IS_DEMO_MODE) return true;
    const formData = new FormData();
    formData.append("audio", file, "enrollment.wav");
    formData.append("speaker_id", speakerId);
    
    try {
      const response = await fetch(`${API_URL}/api/enroll-voice`, {
        method: "POST",
        body: formData,
      });
      return response.ok;
    } catch (error) {
      console.error("[API] enrollVoice error:", error);
      return false;
    }
  },

  deleteEnrolledVoice: async (speakerId: string): Promise<boolean> => {
    if (IS_DEMO_MODE) return true;
    try {
      const response = await fetch(`${API_URL}/api/enrolled-voices/${speakerId}`, {
        method: "DELETE"
      });
      return response.ok;
    } catch (error) {
      console.error("[API] deleteEnrolledVoice error:", error);
      return false;
    }
  }
};

