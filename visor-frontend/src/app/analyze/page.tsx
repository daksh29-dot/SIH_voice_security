"use client";

import React, { useEffect, useRef, useState } from "react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Mic, Upload, Square, Activity, AlertTriangle, ShieldCheck, CheckCircle2, FileAudio, Info } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAppState } from "@/contexts/AppContext";
import { api } from "@/lib/api";

export default function AnalyzePage() {
  const { state, actions } = useAppState();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [presets, setPresets] = useState<any[]>([]);
  const [enrolledVoices, setEnrolledVoices] = useState<string[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<string>("none");
  
  // Local UI state for analysis stage animation
  const [analysisStage, setAnalysisStage] = useState(0);
  const [waveData, setWaveData] = useState<number[]>(Array(40).fill(10));

  useEffect(() => {
    import("@/lib/api").then((mod) => {
      mod.api.getPresets().then(setPresets);
      mod.api.getEnrolledVoices().then(setEnrolledVoices);
    });
  }, []);

  useEffect(() => {
    if (state.analysisState === "RECORDING") {
      const interval = setInterval(() => {
        setWaveData(prev => {
          const newData = [...prev.slice(1)];
          const baseHeight = Math.max(10, state.audioLevel * 0.8);
          const jitter = Math.random() * 15;
          newData.push(baseHeight + jitter);
          return newData;
        });
      }, 100);
      return () => clearInterval(interval);
    } else if (state.analysisState === "READY") {
      setWaveData(Array(40).fill(10));
    }
  }, [state.analysisState, state.audioLevel]);

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

  return (
    <PageWrapper className="p-6 max-w-5xl mx-auto min-h-[calc(100vh-4rem)] flex flex-col justify-center pb-20">
      <AnimatePresence mode="wait">
        
        {state.analysisState === "READY" && (
          <motion.div key="ready" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98 }} className="flex flex-col items-center justify-center space-y-12 py-12">
            <div className="text-center space-y-4">
              <h1 className="text-4xl font-light tracking-tight">Ready to analyze</h1>
              <p className="text-text-secondary">Start a live voice analysis or upload an audio recording.</p>
            </div>

            <div className="w-full max-w-sm flex flex-col items-center space-y-2 mt-4">
              <label htmlFor="voiceSelect" className="text-sm font-medium text-text-secondary">Optional: Select Voiceprint to Verify</label>
              <select 
                id="voiceSelect"
                value={selectedVoice}
                onChange={(e) => setSelectedVoice(e.target.value)}
                className="w-full bg-surface-secondary border border-border rounded-md px-4 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-accent appearance-none"
              >
                <option value="none">-- No Voiceprint (Spoof Detection Only) --</option>
                {enrolledVoices.map(voice => (
                  <option key={voice} value={voice}>{voice}</option>
                ))}
              </select>
            </div>

            <button 
              className="relative group cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-full" 
              onClick={actions.startRecording}
              aria-label="Start recording"
            >
              <div className="absolute inset-0 bg-accent/20 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
              <div className="w-48 h-48 rounded-full border border-border bg-surface-primary flex items-center justify-center relative shadow-sm group-hover:border-accent/50 transition-colors">
                <Mic className="w-12 h-12 text-text-secondary group-hover:text-foreground transition-colors" />
              </div>
            </button>

            <div className="flex items-center space-x-6">
              <Button size="lg" onClick={actions.startRecording} className="w-48">Start Recording</Button>
              <div className="relative">
                <input type="file" id="audio-upload" accept="audio/*" className="sr-only" onChange={handleFileUpload} ref={fileInputRef} />
                <Button variant="outline" size="lg" className="w-48 border-border" onClick={() => fileInputRef.current?.click()}>
                  <Upload className="w-4 h-4 mr-2" /> Upload Audio
                </Button>
              </div>
            </div>
          </motion.div>
        )}

        {state.analysisState === "RECORDING" && (
          <motion.div key="recording" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, y: -10 }} className="flex flex-col items-center justify-center space-y-16 py-12 w-full max-w-2xl mx-auto">
            <div className="flex items-center space-x-3 bg-danger/10 text-danger px-4 py-1.5 rounded-full border border-danger/20">
              <div className="w-2 h-2 rounded-full bg-danger animate-pulse" />
              <span className="text-xs font-mono tracking-widest uppercase font-semibold">Live Analysis</span>
            </div>

            <div className="flex flex-col items-center w-full space-y-8">
              <div className="text-6xl font-light tabular-nums tracking-tighter">{formatTime(state.recordingDuration)}</div>
              <div className="flex items-end justify-center space-x-1 h-32 w-full max-w-lg bg-surface-primary/30 border border-border/50 rounded-sm p-6">
                {waveData.map((h, i) => (
                  <motion.div key={i} animate={{ height: `${Math.min(100, Math.max(10, h))}%` }} transition={{ type: "tween", duration: 0.1 }} className="w-2 bg-accent/80 rounded-t-sm flex-1" />
                ))}
              </div>
              <div className="flex justify-between w-full max-w-lg px-2 text-xs font-mono text-text-secondary uppercase">
                <span>Mic Status: Active</span>
                <span>Lvl: {state.audioLevel.toFixed(0)}</span>
              </div>
            </div>

            <Button variant="danger" size="lg" onClick={() => actions.stopRecording(selectedVoice !== "none" ? selectedVoice : undefined)} className="w-48 shadow-lg shadow-danger/20">
              <Square className="w-4 h-4 mr-2 fill-current" /> Stop Recording
            </Button>
          </motion.div>
        )}

        {state.analysisState === "ANALYZING" && (
          <motion.div key="analyzing" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98 }} className="flex flex-col items-center justify-center space-y-12 py-12 max-w-md mx-auto w-full">
            <div className="w-full flex justify-center mb-8"><Activity className="w-12 h-12 text-accent animate-pulse" /></div>
            <div className="w-full space-y-6">
              {["Receiving audio payload...", "Processing acoustic features...", "Running spoof detection...", "Evaluating security signals...", "Preparing results..."].map((stageText, idx) => {
                const isActive = analysisStage === idx;
                const isComplete = analysisStage > idx;
                return (
                  <div key={idx} className={`flex items-center space-x-4 transition-all duration-500 ${isActive ? 'opacity-100' : (isComplete ? 'opacity-50' : 'opacity-20')}`}>
                    <div className="w-6 h-6 flex items-center justify-center flex-shrink-0">
                      {isComplete ? <CheckCircle2 className="w-5 h-5 text-success" /> : isActive ? <div className="w-2 h-2 rounded-full bg-accent animate-ping" /> : <div className="w-1.5 h-1.5 rounded-full bg-text-secondary" />}
                    </div>
                    <span className={`text-sm ${isActive ? 'text-foreground font-medium' : 'text-text-secondary'}`}>{stageText}</span>
                  </div>
                )
              })}
            </div>
          </motion.div>
        )}

        {state.analysisState === "RESULT" && result && (
          <motion.div key="result" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-4xl mx-auto space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end border-b border-border pb-4 gap-4">
              <div>
                <h1 className="text-2xl font-light">Analysis Report</h1>
                <p className="text-sm text-text-secondary mt-1 flex items-center">
                  <FileAudio className="w-4 h-4 mr-1.5" /> {result.filename} <span className="mx-2">•</span> {result.duration}
                </p>
              </div>
              <Badge variant={result.policy_action === "BLOCK_AND_HOLD" ? "danger" : "success"} className="text-xs px-3 py-1">Policy: {result.policy_action.replace(/_/g, " ")}</Badge>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-1 space-y-6">
                <Card className={`border-2 ${result.composite_risk_score >= 0.6 ? 'border-danger/50 bg-danger/5' : 'border-success/50 bg-success/5'}`}>
                  <CardHeader className="pb-2"><CardTitle className="text-xs text-text-secondary uppercase tracking-widest font-semibold">Overall Assessment</CardTitle></CardHeader>
                  <CardContent className="text-center py-6">
                    {result.composite_risk_score >= 0.6 ? <AlertTriangle className="w-12 h-12 text-danger mx-auto mb-4" /> : <ShieldCheck className="w-12 h-12 text-success mx-auto mb-4" />}
                    <div className="text-5xl font-light mb-2">{(result.composite_risk_score * 100).toFixed(1)}%</div>
                    <p className="text-sm font-medium">Composite Risk Score</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2"><CardTitle className="text-xs text-text-secondary uppercase tracking-widest font-semibold">Voice Authenticity</CardTitle></CardHeader>
                  <CardContent>
                    <div className="flex justify-between items-end"><span className="text-2xl font-light">{result.pillars.voice_clone.label}</span></div>
                    <div className="mt-4 pt-4 border-t border-border flex justify-between items-center">
                      <span className="text-sm text-text-secondary">Spoof Probability</span>
                      <span className={`text-sm font-medium ${result.pillars.voice_clone.score > 0.6 ? 'text-danger' : 'text-success'}`}>{(result.pillars.voice_clone.score * 100).toFixed(1)}%</span>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="lg:col-span-2 space-y-6">
                <Card>
                  <CardHeader className="border-b border-border pb-4"><CardTitle className="text-sm font-medium">Security Signals</CardTitle></CardHeader>
                  <CardContent className="p-0">
                    <div className="divide-y divide-border">
                      <div className="flex justify-between items-center p-4">
                        <div><p className="text-sm font-medium">Acoustic Signals</p><p className="text-xs text-text-secondary mt-0.5">Wav2Vec2 Deep Embeddings</p></div>
                        <Badge variant={result.pillars.voice_clone.score > 0.6 ? "danger" : "success"}>{result.pillars.voice_clone.score > 0.6 ? "Anomalous" : "Authentic"}</Badge>
                      </div>
                      <div className="flex justify-between items-center p-4">
                        <div><p className="text-sm font-medium">Channel Signals</p><p className="text-xs text-text-secondary mt-0.5">STIR/SHAKEN: {result.pillars.caller_telecom.stir_shaken}</p></div>
                        <Badge variant={result.pillars.caller_telecom.risk_score > 0.6 ? "warning" : "success"}>{result.pillars.caller_telecom.voip ? "VoIP Gateway" : "Verified Carrier"}</Badge>
                      </div>
                      <div className="flex justify-between items-center p-4">
                        <div><p className="text-sm font-medium">Threat Indicators</p><p className="text-xs text-text-secondary mt-0.5">Semantic Intent: {result.pillars.scam_nlp.detected_intent}</p></div>
                        <Badge variant={result.pillars.scam_nlp.risk_score > 0.7 ? "danger" : "default"}>{result.pillars.scam_nlp.keywords.length > 0 ? `Flags: ${result.pillars.scam_nlp.keywords.join(', ')}` : "No threats detected"}</Badge>
                      </div>
                      <div className="flex justify-between items-center p-4">
                        <div><p className="text-sm font-medium">Biometric Match</p><p className="text-xs text-text-secondary mt-0.5">Zero-Enrollment Voiceprint</p></div>
                        {result.pillars.voice_biometrics.risk_score === null ? (
                          <Badge variant="default" className="opacity-50">Not Enabled</Badge>
                        ) : (
                          <Badge variant={result.pillars.voice_biometrics.match ? "success" : "danger"}>
                            {result.pillars.voice_biometrics.match ? "Identity Matched" : "Identity Mismatch"}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-surface-secondary/30">
                  <CardContent className="p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 text-xs text-text-secondary">
                    <div className="flex items-start space-x-2"><Info className="w-4 h-4 mt-0.5 flex-shrink-0" /><p><strong>Model Information:</strong> W2V2-AASIST. Values are generated by the backend model and are indicators of risk, not absolute proof of identity.</p></div>
                    <div className="flex items-center space-x-4 whitespace-nowrap border-t sm:border-t-0 sm:border-l border-border pt-4 sm:pt-0 sm:pl-4 w-full sm:w-auto">
                      <span>ID: {result.id}</span><span>{new Date(result.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-end space-y-3 sm:space-y-0 sm:space-x-4 pt-6 border-t border-border">
              <Button variant="ghost" onClick={actions.resetAnalysis} className="w-full sm:w-auto">Analyze Again</Button>
              <Button variant="primary" onClick={actions.resetAnalysis} className="w-full sm:w-auto">Acknowledge</Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </PageWrapper>
  );
}

