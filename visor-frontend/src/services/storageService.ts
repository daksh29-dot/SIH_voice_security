import { Analysis, ThreatIndicator } from "../types/models";

const HISTORY_KEY = "visor_history_v2";
const THREATS_KEY = "visor_threats_v2";
const SETTINGS_KEY = "visor_settings_v2";

export const storageService = {
  getHistory: (): Analysis[] => {
    if (typeof window === "undefined") return [];
    try {
      const data = localStorage.getItem(HISTORY_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  },
  
  saveHistory: (history: Analysis[]) => {
    if (typeof window === "undefined") return;
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  },

  getThreats: (): ThreatIndicator[] => {
    if (typeof window === "undefined") return [];
    try {
      const data = localStorage.getItem(THREATS_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  },

  saveThreats: (threats: ThreatIndicator[]) => {
    if (typeof window === "undefined") return;
    localStorage.setItem(THREATS_KEY, JSON.stringify(threats));
  },

  clearAll: () => {
    if (typeof window === "undefined") return;
    localStorage.removeItem(HISTORY_KEY);
    localStorage.removeItem(THREATS_KEY);
    localStorage.removeItem(SETTINGS_KEY);
  }
};

