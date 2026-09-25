"use client";

import React, { useEffect, useRef, useState } from "react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Mic, Square, Activity, Trash2, UserPlus, CheckCircle2, AlertTriangle, Upload } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";
import { audioService } from "@/services/audioService";
import { AudioVisualizer } from "@/components/ui/AudioVisualizer";

export default function EnrollmentPage() {
  const [enrolledVoices, setEnrolledVoices] = useState<string[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [speakerId, setSpeakerId] = useState("");
  const [isEnrolling, setIsEnrolling] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadEnrolledVoices();
  }, []);

  const loadEnrolledVoices = async () => {
    const voices = await api.getEnrolledVoices();
    setEnrolledVoices(voices);
  };

  const handleDelete = async (id: string) => {
    if (confirm(`Delete enrolled voice for ${id}?`)) {
      await api.deleteEnrolledVoice(id);
      loadEnrolledVoices();
    }
  };

  const startRecording = async () => {
    if (!speakerId.trim()) {
      alert("Please enter a Speaker ID first.");
      return;
    }
    try {
      await audioService.startRecording((level) => setAudioLevel(level));
      setIsRecording(true);
      setRecordingDuration(0);
      
      timerRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);
    } catch (err) {
      console.error("Microphone access denied", err);
    }
  };

  const stopRecording = async () => {
    if (timerRef.current) clearInterval(timerRef.current);
    const file = await audioService.stopRecording();
    setIsRecording(false);
    setAudioLevel(0);
    
    setIsEnrolling(true);
    try {
      const success = await api.enrollVoice(file, speakerId.trim());
      if (success) {
        setSpeakerId("");
        loadEnrolledVoices();
      } else {
        alert("Failed to enroll voice. Make sure the recording has at least 0.5s of clear speech.");
      }
    } catch (e) {
      alert("Error enrolling voice.");
    } finally {
      setIsEnrolling(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!speakerId.trim()) {
      alert("Please enter a Speaker ID first.");
      return;
    }
    
    setIsEnrolling(true);
    try {
      const success = await api.enrollVoice(file, speakerId.trim());
      if (success) {
        setSpeakerId("");
        loadEnrolledVoices();
      } else {
        alert("Failed to enroll voice. Make sure the recording has at least 0.5s of clear speech.");
      }
    } catch (e) {
      alert("Error enrolling voice.");
    } finally {
      setIsEnrolling(false);
      if (event.target) event.target.value = '';
    }
  };

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  return (
    <PageWrapper className="p-6 max-w-5xl mx-auto min-h-[calc(100vh-4rem)] flex flex-col gap-8 pb-20">
      <div>
        <h1 className="text-3xl font-light tracking-tight mb-2">Voice Enrollment</h1>
        <p className="text-text-secondary">Register trusted voiceprints for Biometric matching and live caller verification.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card className="h-full">
          <CardHeader className="border-b border-border pb-4">
            <CardTitle className="text-lg font-medium flex items-center">
              <UserPlus className="w-5 h-5 mr-2 text-accent" />
              Enroll New Profile
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6 flex flex-col items-center justify-center space-y-6">
            {!isRecording && !isEnrolling && (
              <div className="w-full space-y-6">
                <div className="space-y-2">
                  <label htmlFor="speakerId" className="text-sm font-medium text-text-secondary">Speaker Identifier (e.g. Employee ID, Name)</label>
                  <input 
                    type="text" 
                    id="speakerId"
                    value={speakerId}
                    onChange={(e) => setSpeakerId(e.target.value)}
                    placeholder="Enter unique ID..."
                    className="w-full bg-surface-secondary border border-border rounded-md px-4 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-accent transition-all"
                  />
                </div>
                
                <div className="flex flex-col items-center justify-center py-6">
                  <div className="flex flex-col md:flex-row items-center gap-10">
                    <div className="flex flex-col items-center text-center">
                      <button 
                        className={`relative group cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-full ${!speakerId.trim() ? 'opacity-50 cursor-not-allowed' : ''}`}
                        onClick={startRecording}
                        disabled={!speakerId.trim()}
                        aria-label="Start recording"
                      >
                        <div className="absolute inset-0 bg-accent/20 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
                        <div className="w-24 h-24 rounded-full border border-border bg-surface-primary flex items-center justify-center relative shadow-sm group-hover:border-accent/50 transition-colors">
                          <Mic className="w-8 h-8 text-text-secondary group-hover:text-foreground transition-colors" />
                        </div>
                      </button>
                      <p className="text-sm text-text-secondary mt-4">Record Sample</p>
                    </div>

                    <div className="text-xs text-text-secondary/50 font-semibold uppercase tracking-widest hidden md:block">OR</div>

                    <div className="flex flex-col items-center text-center">
                      <input 
                        type="file" 
                        accept="audio/*" 
                        id="voice-upload" 
                        className="hidden" 
                        onChange={handleFileUpload} 
                        disabled={!speakerId.trim()}
                      />
                      <label 
                        htmlFor="voice-upload" 
                        className={`relative group flex items-center justify-center w-24 h-24 rounded-full border border-border bg-surface-primary transition-colors shadow-sm ${!speakerId.trim() ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-accent/50'}`}
                      >
                        {speakerId.trim() && <div className="absolute inset-0 bg-accent/20 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700" />}
                        <Upload className="w-8 h-8 text-text-secondary group-hover:text-foreground transition-colors relative z-10" />
                      </label>
                      <p className="text-sm text-text-secondary mt-4">Upload File</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {isRecording && (
              <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center w-full space-y-6 py-4">
                <div className="flex items-center space-x-3 bg-danger/10 text-danger px-4 py-1.5 rounded-full border border-danger/20">
                  <div className="w-2 h-2 rounded-full bg-danger animate-pulse" />
                  <span className="text-xs font-mono tracking-widest uppercase font-semibold">Recording...</span>
                </div>
                
                <div className="text-4xl font-light tabular-nums tracking-tighter">{formatTime(recordingDuration)}</div>
                
                <div className="flex items-center justify-center w-full max-w-sm bg-surface-primary/30 border border-border/50 rounded-xl overflow-hidden p-2">
                  <AudioVisualizer state={isRecording ? "RECORDING" : "IDLE"} height={96} />
                </div>

                <Button variant="danger" size="lg" onClick={stopRecording} className="w-full max-w-xs shadow-lg shadow-danger/20">
                  <Square className="w-4 h-4 mr-2 fill-current" /> Stop & Enroll
                </Button>
              </motion.div>
            )}

            {isEnrolling && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center justify-center py-12 space-y-4">
                <Activity className="w-10 h-10 text-accent animate-pulse" />
                <p className="text-sm text-text-secondary">Extracting ECAPA-TDNN embedding...</p>
              </motion.div>
            )}
          </CardContent>
        </Card>

        <Card className="h-full flex flex-col">
          <CardHeader className="border-b border-border pb-4">
            <CardTitle className="text-lg font-medium">Enrolled Profiles</CardTitle>
          </CardHeader>
          <CardContent className="pt-6 flex-1 overflow-y-auto">
            {enrolledVoices.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-text-secondary space-y-3 py-12">
                <AlertTriangle className="w-8 h-8 opacity-50" />
                <p className="text-sm">No voice profiles enrolled yet.</p>
              </div>
            ) : (
              <ul className="space-y-3">
                <AnimatePresence>
                  {enrolledVoices.map(voiceId => (
                    <motion.li 
                      key={voiceId} 
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className="flex items-center justify-between p-4 bg-surface-secondary/50 border border-border rounded-md hover:bg-surface-secondary transition-colors"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center border border-accent/20">
                          <CheckCircle2 className="w-4 h-4 text-accent" />
                        </div>
                        <span className="font-medium text-sm">{voiceId}</span>
                      </div>
                      <Button variant="ghost" onClick={() => handleDelete(voiceId)} className="text-danger hover:text-danger hover:bg-danger/10 px-2 py-1 h-auto">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </motion.li>
                  ))}
                </AnimatePresence>
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </PageWrapper>
  );
}
