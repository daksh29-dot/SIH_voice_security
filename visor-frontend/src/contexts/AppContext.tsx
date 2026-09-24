"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { Analysis, ThreatIndicator, SystemStatus, ModelStatus } from "../types/models";
import { storageService } from "../services/storageService";
import { audioService } from "../services/audioService";
import { api } from "../lib/api";

type AnalysisState = "READY" | "RECORDING" | "ANALYZING" | "RESULT";

interface AppState {
  isInitializing: boolean;
  analysisState: AnalysisState;
  currentAnalysis: Analysis | null;
  analysisHistory: Analysis[];
  threatIndicators: ThreatIndicator[];
  systemStatus: SystemStatus;
  modelStatus: ModelStatus;
  audioLevel: number;
  recordingDuration: number;
}

interface AppContextActions {
  startRecording: () => Promise<void>;
  stopRecording: (enrolledSpeakerId?: string) => Promise<void>;
  uploadFile: (file: File, enrolledSpeakerId?: string) => Promise<void>;
  analyzePreset: (preset: any, enrolledSpeakerId?: string) => Promise<void>;
  resetAnalysis: () => void;
  clearHistory: () => void;
}

const defaultState: AppState = {
  isInitializing: true,
  analysisState: "READY",
  currentAnalysis: null,
  analysisHistory: [],
  threatIndicators: [],
  systemStatus: { status: "Operational", lastCheck: new Date().toISOString(), activeConnections: 142, latencyMs: 14 },
  modelStatus: { engine: "W2V2-AASIST", inference: "ONNX Runtime", backend: "Demo Mode", version: "v2.4.1" },
  audioLevel: 0,
  recordingDuration: 0,
};

const AppContext = createContext<{ state: AppState; actions: AppContextActions } | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>(defaultState);
  const [timerInterval, setTimerInterval] = useState<NodeJS.Timeout | null>(null);

  // Initialize from storage or API
  useEffect(() => {
    const initData = async () => {
      try {
        let history = [];
        let initialThreats = [];
        if (api.getIsDemoMode()) {
          history = storageService.getHistory();
          const localThreats = storageService.getThreats();
          if (localThreats.length === 0) {
            initialThreats = [
              { 
                id: "ti_001", 
                category: "Voice Spoofing Indicators" as const, 
                title: "Wav2Vec2 Neural Artifact Detected", 
                severity: "Critical" as const, 
                summary: "Sub-perceptual acoustic anomalies matching known synthetic profiles.", 
                evidence: [{ signal: "Pitch Variance", observedValue: "0.02", interpretation: "Unnaturally stable", confidence: 0.98 }], 
                timestamp: new Date().toISOString() 
              }
            ];
            storageService.saveThreats(initialThreats);
          } else {
            initialThreats = localThreats;
          }
        } else {
          history = await api.getHistory();
          initialThreats = await api.getThreats();
        }

        setState(prev => ({ 
          ...prev, 
          isInitializing: false,
          analysisHistory: history, 
          threatIndicators: initialThreats,
          modelStatus: { ...prev.modelStatus, backend: api.getIsDemoMode() ? "Demo Mode" : "Connected" }
        }));
      } catch (e) {
        console.error("Initialization error:", e);
        setState(prev => ({ 
          ...prev, 
          isInitializing: false,
          modelStatus: { ...prev.modelStatus, backend: "Disconnected" },
          systemStatus: { ...prev.systemStatus, status: "Offline" }
        }));
      }
    };

    initData();

    // Simulate system jitter
    const jitter = setInterval(() => {
      setState(prev => ({
        ...prev,
        systemStatus: { 
          ...prev.systemStatus, 
          latencyMs: Math.max(8, prev.systemStatus.latencyMs + (Math.random() > 0.5 ? 2 : -2)) 
        }
      }));
    }, 2000);
    
    return () => clearInterval(jitter);
  }, []);

  const updateState = (updates: Partial<AppState>) => {
    setState(prev => ({ ...prev, ...updates }));
  };

  const processAudioFile = async (file: File, enrolledSpeakerId?: string) => {
    updateState({ analysisState: "ANALYZING" });
    try {
      const result = await api.analyze(file, enrolledSpeakerId);
      const newHistory = [result, ...state.analysisHistory];
      
      if (api.getIsDemoMode()) {
        storageService.saveHistory(newHistory);
      }
      
      updateState({ 
        analysisState: "RESULT", 
        currentAnalysis: result,
        analysisHistory: newHistory
      });
    } catch (e: any) {
      alert(e.message || "Backend unavailable");
      updateState({ analysisState: "READY" });
    }
  };

  const actions: AppContextActions = {
    startRecording: async () => {
      try {
        await audioService.startRecording((level) => updateState({ audioLevel: level }));
        updateState({ analysisState: "RECORDING", recordingDuration: 0 });
        
        const timer = setInterval(() => {
          setState(prev => ({ ...prev, recordingDuration: prev.recordingDuration + 1 }));
        }, 1000);
        setTimerInterval(timer);
      } catch (err) {
        console.error("Microphone access denied", err);
      }
    },
    
    stopRecording: async (enrolledSpeakerId?: string) => {
      if (timerInterval) clearInterval(timerInterval);
      const file = await audioService.stopRecording();
      updateState({ audioLevel: 0, recordingDuration: 0 });
      await processAudioFile(file, enrolledSpeakerId);
    },

    uploadFile: async (file: File, enrolledSpeakerId?: string) => {
      await processAudioFile(file, enrolledSpeakerId);
    },

    analyzePreset: async (preset: any, enrolledSpeakerId?: string) => {
      updateState({ analysisState: "ANALYZING" });
      try {
        const result = await api.analyzePreset(preset, enrolledSpeakerId);
        const newHistory = [result, ...state.analysisHistory];
        updateState({ 
          analysisState: "RESULT", 
          currentAnalysis: result,
          analysisHistory: newHistory
        });
      } catch (e: any) {
        updateState({ analysisState: "READY", currentAnalysis: null });
        alert(e.message || "Failed to analyze preset");
      }
    },

    resetAnalysis: () => {
      updateState({ analysisState: "READY", currentAnalysis: null, recordingDuration: 0, audioLevel: 0 });
    },

    clearHistory: () => {
      storageService.clearAll();
      updateState({ analysisHistory: [], threatIndicators: [] });
    }
  };

  return <AppContext.Provider value={{ state, actions }}>{children}</AppContext.Provider>;
}

export function useAppState() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useAppState must be used within AppProvider");
  return context;
}

