import { Analysis } from "../types/models";

export const analysisService = {
  simulateAnalysis: async (file: File): Promise<Analysis> => {
    return new Promise((resolve) => {
      setTimeout(() => {
        const isSpoof = Math.random() > 0.6;
        const result: Analysis = {
          id: `req_${Math.random().toString(36).substring(2, 9)}`,
          timestamp: new Date().toISOString(),
          status: "completed",
          filename: file.name,
          duration: "Variable",
          composite_risk_score: isSpoof ? 0.82 : 0.14,
          policy_action: isSpoof ? "BLOCK_AND_HOLD" : "PROCEED_NORMALLY",
          signalContext: {
            durationMs: 4000,
            format: "audio/webm",
            sampleRate: 48000,
            channels: 1,
            source: file.name
          },
          pillars: {
            voice_clone: {
              score: isSpoof ? 0.91 : 0.04,
              label: isSpoof ? "Synthetic / Spoofed" : "Authentic",
            },
            caller_telecom: {
              risk_score: isSpoof ? 0.75 : 0.1,
              stir_shaken: isSpoof ? "C" : "A",
              voip: isSpoof,
            },
            scam_nlp: {
              risk_score: isSpoof ? 0.8 : 0.05,
              detected_intent: isSpoof ? "Financial Extortion" : "Routine Inquiry",
              keywords: isSpoof ? ["wire", "urgent"] : [],
            },
            voice_biometrics: {
              risk_score: isSpoof ? 0.95 : 0.02,
              match: !isSpoof
            }
          }
        };
        resolve(result);
      }, 2500); // Simulate network/inference latency
    });
  }
};

