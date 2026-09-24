"use client";

import React, { useEffect, useRef, useState } from "react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Mic, Square, Activity, Trash2, UserPlus, CheckCircle2, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";
import { audioService } from "@/services/audioService";

export default function EnrollmentPage() {
  const [enrolledVoices, setEnrolledVoices] = useState<string[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [waveData, setWaveData] = useState<number[]>(Array(40).fill(10));
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

  useEffect(() => {
    if (isRecording) {
      const interval = setInterval(() => {
        setWaveData(prev => {
          const newData = [...prev.slice(1)];
          const baseHeight = Math.max(10, audioLevel * 0.8);
          const jitter = Math.random() * 15;
          newData.push(baseHeight + jitter);
          return newData;
        });
      }, 100);
      return () => clearInterval(interval);
    } else {
      setWaveData(Array(40).fill(10));
    }
  }, [isRecording, audioLevel]);

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
                  <button 
                    className={`relative group cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-full ${!speakerId.trim() ? 'opacity-50 cursor-not-allowed' : ''}`}
                    onClick={startRecording}
                    disabled={!speakerId.trim()}
                    aria-label="Start recording"
                  >
                    <div className="absolute inset-0 bg-accent/20 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
                    <div className="w-32 h-32 rounded-full border border-border bg-surface-primary flex items-center justify-center relative shadow-sm group-hover:border-accent/50 transition-colors">
                      <Mic className="w-8 h-8 text-text-secondary group-hover:text-foreground transition-colors" />
                    </div>
                  </button>
                  <p className="text-sm text-text-secondary mt-4">Click to start recording voice sample</p>
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
                
                <div className="flex items-end justify-center space-x-1 h-24 w-full bg-surface-primary/30 border border-border/50 rounded-sm p-4">
                  {waveData.map((h, i) => (
                    <motion.div key={i} animate={{ height: `${Math.min(100, Math.max(10, h))}%` }} transition={{ type: "tween", duration: 0.1 }} className="w-1.5 bg-accent/80 rounded-t-sm flex-1" />
                  ))}
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
