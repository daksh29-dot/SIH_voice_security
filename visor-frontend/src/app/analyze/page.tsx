"use client";

import React, { useEffect, useRef, useState } from "react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Mic, Upload, Square, Activity, AlertTriangle, ShieldCheck, CheckCircle2, FileAudio, Info, Fingerprint, Building2, User, XCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAppState } from "@/contexts/AppContext";
import { api } from "@/lib/api";
import { AudioVisualizer } from "@/components/ui/AudioVisualizer";

// Score calculation utilities based on deployment mode
function computeRetailRisk(result: any): number {
  // Retail: weighted blend of voice clone + telecom + NLP only (no voiceprint)
  const voiceClone = result.pillars.voice_clone.score ?? 0;
  const telecom = result.pillars.caller_telecom.risk_score ?? 0;
  const nlp = result.pillars.scam_nlp.risk_score ?? 0;
  return (voiceClone * 0.5) + (telecom * 0.25) + (nlp * 0.25);
}

function computeEnterpriseRisk(result: any): number {
  // Enterprise: includes voiceprint biometric signal
  const voiceClone = result.pillars.voice_clone.score ?? 0;
  const telecom = result.pillars.caller_telecom.risk_score ?? 0;
  const nlp = result.pillars.scam_nlp.risk_score ?? 0;
  const biometric = result.pillars.voice_biometrics.risk_score ?? 0;
  const hasBiometric = result.pillars.voice_biometrics.risk_score !== null;

  if (hasBiometric) {
    return (voiceClone * 0.35) + (telecom * 0.20) + (nlp * 0.20) + (biometric * 0.25);
  }
  return computeRetailRisk(result);
}

function getRiskLabel(score: number): { label: string; color: string; bg: string } {
  if (score >= 0.75) return { label: "Critical Risk", color: "text-danger", bg: "bg-danger/8 border-danger/40" };
  if (score >= 0.55) return { label: "High Risk", color: "text-warning", bg: "bg-warning/8 border-warning/40" };
  if (score >= 0.35) return { label: "Moderate", color: "text-yellow-500", bg: "bg-yellow-500/8 border-yellow-500/40" };
  return { label: "Low Risk", color: "text-success", bg: "bg-success/8 border-success/40" };
}

// Circular score ring
function ScoreRing({ score, size = 120 }: { score: number; size?: number }) {
  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const dash = circumference * (1 - score);
  const risk = getRiskLabel(score);

  const strokeColor = score >= 0.75 ? "var(--danger)" : score >= 0.55 ? "var(--warning)" : score >= 0.35 ? "#eab308" : "var(--success)";

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg className="absolute inset-0 -rotate-90" width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="currentColor" strokeWidth="6" className="text-surface-secondary" />
        <motion.circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: dash }}
          transition={{ duration: 1.2, ease: "easeOut", delay: 0.3 }}
        />
      </svg>
      <div className="text-center">
        <div className={`text-2xl font-semibold tabular-nums ${risk.color}`}>
          {(score * 100).toFixed(0)}
          <span className="text-base font-normal">%</span>
        </div>
        <div className="text-[10px] text-text-secondary mt-0.5 font-medium uppercase tracking-wide">Risk</div>
      </div>
    </div>
  );
}

export default function AnalyzePage() {
  const { state, actions } = useAppState();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [enrolledVoices, setEnrolledVoices] = useState<string[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<string>("none");
  const isEnterprise = state.deploymentMode === "enterprise";
  
  const [analysisStage, setAnalysisStage] = useState(0);

  useEffect(() => {
    import("@/lib/api").then((mod) => {
      mod.api.getEnrolledVoices().then(setEnrolledVoices);
    });
  }, []);

  useEffect(() => {
    if (!isEnterprise) setSelectedVoice("none");
  }, [isEnterprise]);

  useEffect(() => {
    if (state.analysisState === "ANALYZING") {
      setAnalysisStage(0);
      const stagesInterval = setInterval(() => {
        setAnalysisStage(prev => {
          if (prev < 4) return prev + 1;
          clearInterval(stagesInterval);
          return prev;
        });
      }, 500);
      return () => clearInterval(stagesInterval);
    }
  }, [state.analysisState]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) actions.uploadFile(file, selectedVoice !== "none" ? selectedVoice : undefined);
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const result = state.currentAnalysis;

  // Computed risk scores
  const effectiveRiskScore = result 
    ? (isEnterprise ? computeEnterpriseRisk(result) : computeRetailRisk(result))
    : 0;

  const analysisStages = [
    "Receiving audio payload...",
    "Processing acoustic features...",
    "Running spoof detection...",
    isEnterprise ? "Matching voiceprint biometrics..." : "Evaluating security signals...",
    "Preparing results..."
  ];

  return (
    <PageWrapper className="p-6 max-w-5xl mx-auto min-h-[calc(100vh-4rem)] flex flex-col justify-center pb-20">
      <AnimatePresence mode="wait">
        
        {/* READY STATE */}
        {state.analysisState === "READY" && (
          <motion.div key="ready" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98 }} className="flex flex-col items-center justify-center space-y-10 py-12">
            
            {/* Mode indicator banner */}
            <div className={`flex items-center gap-2 px-4 py-2 rounded-full border text-xs font-medium ${
              isEnterprise 
                ? "bg-accent/10 border-accent/25 text-accent" 
                : "bg-surface-secondary border-border text-text-secondary"
            }`}>
              {isEnterprise ? <Building2 className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
              {isEnterprise ? "Enterprise Mode — Voiceprint verification active" : "Retail Mode — Acoustic spoof detection only"}
            </div>

            <div className="text-center space-y-3">
              <h1 className="text-3xl font-semibold tracking-tight">Voice Analysis</h1>
              <p className="text-text-secondary text-sm max-w-md">
                {isEnterprise 
                  ? "Start recording or upload audio. Optionally select an enrolled voiceprint to verify speaker identity."
                  : "Start a live voice analysis or upload an audio recording for spoof detection."
                }
              </p>
            </div>

            {/* Voiceprint selector - enterprise only */}
            {isEnterprise && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-sm space-y-2"
              >
                <label htmlFor="voiceSelect" className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary uppercase tracking-wider">
                  <Fingerprint className="w-3.5 h-3.5 text-accent" />
                  Enrolled Voiceprint
                </label>
                <div className="relative">
                  <select 
                    id="voiceSelect"
                    value={selectedVoice}
                    onChange={(e) => setSelectedVoice(e.target.value)}
                    className="w-full bg-surface-secondary border border-border rounded-lg px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50 appearance-none pr-8 transition-all"
                  >
                    <option value="none">— No Voiceprint (Spoof Detection Only) —</option>
                    {enrolledVoices.map(voice => (
                      <option key={voice} value={voice}>{voice}</option>
                    ))}
                  </select>
                  <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  </div>
                </div>
                {enrolledVoices.length === 0 && (
                  <p className="text-[11px] text-text-secondary/70">No voiceprints enrolled yet. Visit <a href="/enrollment" className="text-accent hover:underline">Voice Enrollment</a> to add them.</p>
                )}
              </motion.div>
            )}

            {/* Big mic button */}
            <button 
              className="relative group cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-full" 
              onClick={actions.startRecording}
              aria-label="Start recording"
            >
              <div className="absolute inset-0 bg-accent/15 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
              <div className="w-40 h-40 rounded-full border border-border bg-surface-primary flex items-center justify-center relative shadow-sm group-hover:border-accent/40 transition-all duration-300 group-hover:bg-surface-secondary/60">
                <div className="absolute inset-3 rounded-full border border-border/30 border-dashed opacity-50" />
                <Mic className="w-10 h-10 text-text-secondary group-hover:text-accent transition-colors duration-300" />
              </div>
            </button>

            <div className="flex items-center gap-4">
              <Button size="lg" onClick={actions.startRecording} className="w-44 h-11">
                Start Recording
              </Button>
              <div className="relative">
                <input type="file" id="audio-upload" accept="audio/*" className="sr-only" onChange={handleFileUpload} ref={fileInputRef} />
                <Button variant="outline" size="lg" className="w-44 h-11 border-border" onClick={() => fileInputRef.current?.click()}>
                  <Upload className="w-4 h-4 mr-2" /> Upload Audio
                </Button>
              </div>
            </div>
          </motion.div>
        )}

        {/* RECORDING STATE */}
        {state.analysisState === "RECORDING" && (
          <motion.div key="recording" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, y: -10 }} className="flex flex-col items-center justify-center space-y-14 py-12 w-full max-w-2xl mx-auto">
            <div className="flex items-center space-x-3 bg-danger/10 text-danger px-4 py-1.5 rounded-full border border-danger/20">
              <div className="w-2 h-2 rounded-full bg-danger animate-pulse" />
              <span className="text-xs font-mono tracking-widest uppercase font-semibold">Recording</span>
            </div>

            <div className="flex flex-col items-center w-full space-y-6">
              <div className="text-6xl font-light tabular-nums tracking-tighter">{formatTime(state.recordingDuration)}</div>
              <div className="flex items-center justify-center w-full max-w-lg bg-surface-primary/30 border border-border/50 rounded-xl overflow-hidden p-2">
                <AudioVisualizer state={state.analysisState as "RECORDING" | "ANALYZING" | "IDLE" | "ERROR"} height={120} />
              </div>
              <div className="flex justify-between w-full max-w-lg px-2 text-xs font-mono text-text-secondary uppercase">
                <span>Mic Active</span>
                <span>Level: {state.audioLevel.toFixed(0)}</span>
              </div>
            </div>

            <Button variant="danger" size="lg" onClick={() => actions.stopRecording(selectedVoice !== "none" ? selectedVoice : undefined)} className="w-48 h-11 shadow-lg shadow-danger/20">
              <Square className="w-4 h-4 mr-2 fill-current" /> Stop & Analyze
            </Button>
          </motion.div>
        )}

        {/* ANALYZING STATE */}
        {state.analysisState === "ANALYZING" && (
          <motion.div key="analyzing" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98 }} className="flex flex-col items-center justify-center space-y-10 py-12 max-w-md mx-auto w-full">
            <div className="w-12 h-12 rounded-full border border-accent/30 flex items-center justify-center">
              <Activity className="w-6 h-6 text-accent animate-pulse" />
            </div>
            <div className="w-full space-y-4">
              {analysisStages.map((stageText, idx) => {
                const isActive = analysisStage === idx;
                const isComplete = analysisStage > idx;
                return (
                  <div key={idx} className={`flex items-center space-x-4 transition-all duration-500 ${isActive ? "opacity-100" : isComplete ? "opacity-40" : "opacity-15"}`}>
                    <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
                      {isComplete ? <CheckCircle2 className="w-5 h-5 text-success" /> : isActive ? <div className="w-2 h-2 rounded-full bg-accent animate-ping" /> : <div className="w-1.5 h-1.5 rounded-full bg-text-secondary" />}
                    </div>
                    <span className={`text-sm ${isActive ? "text-foreground font-medium" : "text-text-secondary"}`}>{stageText}</span>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* RESULT STATE */}
        {state.analysisState === "RESULT" && result && (
          <motion.div key="result" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-4xl mx-auto space-y-5">
            
            {/* Header */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-border pb-4 gap-3">
              <div>
                <h1 className="text-xl font-semibold tracking-tight">Analysis Report</h1>
                <p className="text-xs text-text-secondary mt-1 flex items-center gap-1.5">
                  <FileAudio className="w-3.5 h-3.5" /> {result.filename} <span className="opacity-40">•</span> {result.duration}
                  <span className="opacity-40">•</span>
                  <span className={`flex items-center gap-1 ${isEnterprise ? "text-accent" : "text-text-secondary"}`}>
                    {isEnterprise ? <Building2 className="w-3 h-3" /> : <User className="w-3 h-3" />}
                    {isEnterprise ? "Enterprise scoring" : "Retail scoring"}
                  </span>
                </p>
              </div>
              <Badge variant={effectiveRiskScore >= 0.6 ? "danger" : "success"} className="text-xs px-3 py-1 shrink-0">
                {result.policy_action.replace(/_/g, " ")}
              </Badge>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              
              {/* Left column: Overall score */}
              <div className="space-y-4">
                <Card className={`border ${getRiskLabel(effectiveRiskScore).bg}`}>
                  <CardContent className="pt-6 pb-5 flex flex-col items-center text-center space-y-4">
                    <ScoreRing score={effectiveRiskScore} size={130} />
                    <div>
                      <p className={`text-sm font-semibold ${getRiskLabel(effectiveRiskScore).color}`}>{getRiskLabel(effectiveRiskScore).label}</p>
                      <p className="text-[11px] text-text-secondary mt-0.5">Composite Risk Score</p>
                    </div>
                    {/* Score formula hint */}
                    <div className="w-full pt-3 border-t border-border/50 text-[10px] text-text-secondary/60 text-left space-y-0.5">
                      <p className="font-semibold uppercase tracking-wider text-text-secondary/40 mb-1">Scoring weights</p>
                      <p>Acoustic · {isEnterprise ? "35%" : "50%"}</p>
                      <p>Telecom · {isEnterprise ? "20%" : "25%"}</p>
                      {isEnterprise && <p className="text-accent/70">Voiceprint · 25%</p>}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-4 space-y-3">
                    <p className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider">Voice Authenticity</p>
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-medium">{result.pillars.voice_clone.label}</span>
                      <span className={`text-sm font-semibold tabular-nums ${result.pillars.voice_clone.score > 0.6 ? "text-danger" : "text-success"}`}>
                        {(result.pillars.voice_clone.score * 100).toFixed(1)}%
                      </span>
                    </div>
                    {/* Mini bar */}
                    <div className="h-1.5 bg-surface-secondary rounded-full overflow-hidden">
                      <motion.div
                        className={`h-full rounded-full ${result.pillars.voice_clone.score > 0.6 ? "bg-danger" : "bg-success"}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${result.pillars.voice_clone.score * 100}%` }}
                        transition={{ duration: 0.8, ease: "easeOut", delay: 0.5 }}
                      />
                    </div>
                    <p className="text-[11px] text-text-secondary">Spoof probability</p>
                  </CardContent>
                </Card>
              </div>

              {/* Right column: Signals */}
              <div className="lg:col-span-2 space-y-4">
                <Card>
                  <CardHeader className="border-b border-border pb-3 pt-4 px-5">
                    <CardTitle className="text-sm font-semibold">Security Signals</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="divide-y divide-border">
                      
                      {/* Acoustic */}
                      <div className="flex justify-between items-center px-5 py-3.5">
                        <div>
                          <p className="text-sm font-medium">Acoustic Analysis</p>
                          <p className="text-xs text-text-secondary mt-0.5">Wav2Vec2 Deep Embeddings · W2V2-AASIST</p>
                        </div>
                        <Badge variant={result.pillars.voice_clone.score > 0.6 ? "danger" : "success"}>
                          {result.pillars.voice_clone.score > 0.6 ? "Anomalous" : "Authentic"}
                        </Badge>
                      </div>

                      {/* Channel */}
                      <div className="flex justify-between items-center px-5 py-3.5">
                        <div>
                          <p className="text-sm font-medium">Channel Trust</p>
                          <p className="text-xs text-text-secondary mt-0.5">STIR/SHAKEN: {result.pillars.caller_telecom.stir_shaken}</p>
                        </div>
                        <Badge variant={result.pillars.caller_telecom.risk_score > 0.6 ? "warning" : "success"}>
                          {result.pillars.caller_telecom.voip ? "VoIP Gateway" : "Verified Carrier"}
                        </Badge>
                      </div>



                      {/* Biometric — only rendered in enterprise */}
                      {isEnterprise && (
                        <div className="flex justify-between items-center px-5 py-3.5 bg-accent/3">
                          <div>
                            <p className="text-sm font-medium flex items-center gap-1.5">
                              <Fingerprint className="w-3.5 h-3.5 text-accent" />
                              Voiceprint Match
                            </p>
                            <p className="text-xs text-text-secondary mt-0.5">
                              {selectedVoice !== "none" ? `Comparing to: ${selectedVoice}` : "Zero-enrollment biometric check"}
                            </p>
                          </div>
                          {result.pillars.voice_biometrics.risk_score === null ? (
                            <Badge variant="default" className="opacity-50">Not Enabled</Badge>
                          ) : result.pillars.voice_biometrics.match ? (
                            <Badge variant="success">Identity Matched</Badge>
                          ) : (
                            <Badge variant="danger">Identity Mismatch</Badge>
                          )}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                {/* Info footer */}
                <Card className="bg-surface-secondary/20">
                  <CardContent className="p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 text-xs text-text-secondary">
                    <div className="flex items-start space-x-2">
                      <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 opacity-60" />
                      <p>Model: W2V2-AASIST. Scores are risk indicators, not absolute proof. {isEnterprise ? "Enterprise 4-pillar scoring enabled." : "Retail 3-pillar scoring (no biometrics)."}</p>
                    </div>
                    <div className="flex items-center space-x-3 whitespace-nowrap border-t sm:border-t-0 sm:border-l border-border pt-3 sm:pt-0 sm:pl-4 w-full sm:w-auto shrink-0">
                      <span className="font-mono opacity-60">#{result.id}</span>
                      <span className="opacity-40">·</span>
                      <span>{new Date(result.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-end space-y-3 sm:space-y-0 sm:space-x-3 pt-4 border-t border-border">
              <Button variant="ghost" onClick={actions.resetAnalysis} className="w-full sm:w-auto">Analyze Again</Button>
              <Button variant="primary" onClick={actions.resetAnalysis} className="w-full sm:w-auto">Acknowledge & Close</Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </PageWrapper>
  );
}
