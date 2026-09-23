"use client";

import React from "react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardContent } from "@/components/ui/Card";
import { Mic, Activity, ShieldCheck, Database, Zap, FileText, ChevronDown, Cpu, Network, Layers, Code2 } from "lucide-react";
import { motion } from "framer-motion";

export default function AboutPage() {
  const architectureSteps = [
    { label: "Microphone / Audio", icon: <Mic className="w-5 h-5" /> },
    { label: "Audio Processing", icon: <Activity className="w-5 h-5" /> },
    { label: "W2V2-AASIST", icon: <Cpu className="w-5 h-5" /> },
    { label: "Spoof Detection", icon: <ShieldCheck className="w-5 h-5" /> },
    { label: "Security Intelligence", icon: <Network className="w-5 h-5" /> },
    { label: "Analysis Report", icon: <FileText className="w-5 h-5" /> },
  ];

  const techStack = [
    { name: "Python", category: "Backend" },
    { name: "FastAPI", category: "API Framework" },
    { name: "ONNX Runtime", category: "Inference Engine" },
    { name: "W2V2-AASIST", category: "Neural Network" },
    { name: "WebSocket", category: "Streaming Protocol" },
    { name: "React", category: "UI Library" },
    { name: "Next.js", category: "React Framework" },
    { name: "TypeScript", category: "Language" },
  ];

  return (
    <PageWrapper className="p-6 max-w-5xl mx-auto space-y-24 pb-32">
      
      {/* HEADER & INTRO */}
      <section className="space-y-8 pt-12">
        <div>
          <h1 className="text-4xl md:text-5xl font-light tracking-tight text-foreground">VISOR System Architecture</h1>
          <p className="text-sm font-medium text-text-secondary uppercase tracking-widest mt-3">Voice Intelligence & Security Operations</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 pt-8">
          <div className="space-y-4">
            <h2 className="text-xl font-medium text-foreground">What is VISOR?</h2>
            <p className="text-text-secondary leading-relaxed font-light text-lg">
              VISOR is a multi-modal voice security platform engineered to detect synthetic speech, telecom spoofing, and social engineering attacks. It transforms raw acoustic signals into explainable, cryptographic security intelligence.
            </p>
          </div>
          <div className="space-y-4">
            <h2 className="text-xl font-medium text-foreground">Why voice security matters</h2>
            <p className="text-text-secondary leading-relaxed font-light text-lg">
              With the advent of zero-shot neural voice cloning (e.g., ElevenLabs, VALL-E), acoustic authentication is fundamentally broken. Relying solely on human perception or traditional biometrics leaves organizations highly vulnerable to deepfake extortion and fraud.
            </p>
          </div>
        </div>
      </section>

      {/* ARCHITECTURE FLOW DIAGRAM */}
      <section className="space-y-12 border-t border-border/50 pt-24">
        <div className="text-center">
          <h2 className="text-2xl font-light text-foreground">How VISOR Works</h2>
          <p className="text-text-secondary mt-2">The end-to-end processing pipeline</p>
        </div>

        <div className="flex flex-col md:flex-row items-center justify-center w-full overflow-x-auto pb-8">
          {architectureSteps.map((step, idx) => (
            <React.Fragment key={idx}>
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1, duration: 0.5 }}
                className="flex flex-col items-center w-40 flex-shrink-0"
              >
                <div className="w-16 h-16 rounded-sm bg-surface-primary border border-border flex items-center justify-center text-text-secondary shadow-sm mb-4">
                  {step.icon}
                </div>
                <span className="text-xs font-medium text-foreground text-center uppercase tracking-wider">{step.label}</span>
              </motion.div>
              
              {idx < architectureSteps.length - 1 && (
                <div className="md:w-16 h-10 md:h-px flex-shrink-0 flex items-center justify-center text-border my-2 md:my-0">
                  <ChevronDown className="w-4 h-4 md:-rotate-90 md:translate-x-1" />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </section>

      {/* ARCHITECTURE LAYERS */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card className="bg-surface-primary/30 border-border">
          <CardContent className="p-8 space-y-4">
            <Layers className="w-8 h-8 text-text-secondary" />
            <h3 className="text-lg font-medium text-foreground">Model Layer</h3>
            <p className="text-text-secondary text-sm leading-relaxed font-light">
              VISOR utilizes a pre-trained <span className="font-medium text-foreground">Wav2Vec2 (W2V2) AASIST</span> architecture. Unlike older magnitude-spectrogram models, W2V2 extracts high-dimensional, sub-perceptual acoustic embeddings that are incredibly sensitive to neural vocoder artifacts introduced during deepfake synthesis.
            </p>
          </CardContent>
        </Card>
        
        <Card className="bg-surface-primary/30 border-border">
          <CardContent className="p-8 space-y-4">
            <Cpu className="w-8 h-8 text-text-secondary" />
            <h3 className="text-lg font-medium text-foreground">Inference Layer</h3>
            <p className="text-text-secondary text-sm leading-relaxed font-light">
              The acoustic detection system relies entirely on <span className="font-medium text-foreground">ONNX Runtime</span> for hardware-accelerated CPU/CUDA execution. This bypasses the heavy footprint of native PyTorch environments, ensuring minimal latency and strict deterministic output for every analysis frame.
            </p>
          </CardContent>
        </Card>
        
        <Card className="bg-surface-primary/30 border-border">
          <CardContent className="p-8 space-y-4">
            <ShieldCheck className="w-8 h-8 text-text-secondary" />
            <h3 className="text-lg font-medium text-foreground">Threat Intelligence Layer</h3>
            <p className="text-text-secondary text-sm leading-relaxed font-light">
              Acoustic scoring is only one piece of the puzzle. The intelligence layer cross-references raw W2V2 confidence outputs against STIR/SHAKEN telecom verification and NLP intent extraction to generate a robust, unified composite risk score.
            </p>
          </CardContent>
        </Card>
        
        <Card className="bg-surface-primary/30 border-border">
          <CardContent className="p-8 space-y-4">
            <Database className="w-8 h-8 text-text-secondary" />
            <h3 className="text-lg font-medium text-foreground">Audit Layer</h3>
            <p className="text-text-secondary text-sm leading-relaxed font-light">
              Security decisions require transparency. Every request is logged into a cryptographically auditable ledger, preserving the file hashes, timestamp telemetry, and exactly what sub-signals triggered the final blocking policy.
            </p>
          </CardContent>
        </Card>
      </section>

      {/* TECH STACK */}
      <section className="space-y-12 border-t border-border/50 pt-24">
        <div className="flex items-center space-x-3 mb-8">
          <Code2 className="w-6 h-6 text-text-secondary" />
          <h2 className="text-2xl font-light text-foreground">Technology Stack</h2>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {techStack.map((tech, i) => (
            <div key={i} className="p-4 rounded-sm border border-border bg-background flex flex-col justify-center space-y-1">
              <span className="font-medium text-foreground text-sm">{tech.name}</span>
              <span className="text-xs text-text-secondary">{tech.category}</span>
            </div>
          ))}
        </div>
      </section>

      {/* REAL-TIME SECTION */}
      <section className="p-8 md:p-12 rounded-sm bg-surface-secondary/20 border border-border flex flex-col items-center text-center space-y-6">
        <div className="w-16 h-16 rounded-full bg-background border border-border flex items-center justify-center text-accent shadow-sm mb-2">
          <Zap className="w-8 h-8" />
        </div>
        <h2 className="text-3xl font-light text-foreground">Designed for real-time analysis</h2>
        <p className="text-text-secondary text-lg font-light leading-relaxed max-w-2xl">
          While VISOR currently processes static audio uploads via standard REST endpoints, the architecture is purposefully engineered to support continuous live-stream interception.
        </p>
        <p className="text-text-secondary text-base font-light leading-relaxed max-w-2xl">
          The frontend interface leverages the Web Audio API and <span className="font-mono text-sm bg-surface-secondary px-1.5 py-0.5 rounded">MediaRecorder</span> to capture active microphone data. The foundational scaffolding for a <span className="font-medium text-foreground">WebSocket</span> streaming service has been built, positioning the system to instantly chunk and pipe binary audio streams to the FastAPI backend for sub-second, continuous inference reporting.
        </p>
      </section>

    </PageWrapper>
  );
}
