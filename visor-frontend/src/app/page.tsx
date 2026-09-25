"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, Activity, ShieldCheck, Database, Zap, Lock, Eye, Globe, Building2, User, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useAppState } from "@/contexts/AppContext";

// -- TOP NAVIGATION --
function TopNav() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/30 backdrop-blur-xl border-b border-white/10 shadow-lg">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 rounded-md bg-accent/20 border border-accent/30 flex items-center justify-center">
              <Mic className="w-3.5 h-3.5 text-accent" />
            </div>
            <span className="font-semibold tracking-tight text-foreground">VISOR</span>
          </div>
          <div className="hidden md:flex space-x-6 text-sm font-medium text-text-secondary">
            <a href="#platform" className="hover:text-foreground transition-colors">Platform</a>
            <a href="#how-it-works" className="hover:text-foreground transition-colors">How It Works</a>
            <a href="#features" className="hover:text-foreground transition-colors">Features</a>
            <a href="#security" className="hover:text-foreground transition-colors">Security</a>
            <a href="#about" className="hover:text-foreground transition-colors">About</a>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <Link href="/dashboard">
            <Button variant="ghost" className="text-sm hidden sm:inline-flex">Dashboard</Button>
          </Link>
          <Link href="/analyze">
            <Button variant="primary" className="text-sm">
              Start Analysis
            </Button>
          </Link>
        </div>
      </div>
    </nav>
  );
}

// -- MODE SELECTOR (Landing) --
function LandingModeSelector() {
  const { state, actions } = useAppState();
  const isEnterprise = state.deploymentMode === "enterprise";

  const modes = [
    {
      id: "retail" as const,
      icon: <User className="w-5 h-5" />,
      title: "Retail / Consumer",
      desc: "Acoustic spoof detection, telecom trust & NLP threat analysis for individual calls.",
      features: ["Deepfake / clone detection", "STIR/SHAKEN attestation", "Scam intent analysis"],
    },
    {
      id: "enterprise" as const,
      icon: <Building2 className="w-5 h-5" />,
      title: "Bank / Enterprise",
      desc: "Full 4-pillar scoring with enrolled voiceprint biometrics for high-stakes identity verification.",
      features: ["All retail features", "Voiceprint enrollment", "Biometric identity match", "Enterprise risk weights"],
      badge: "Voiceprint enabled",
    },
  ];

  return (
    <section id="mode-select" className="py-24 border-t border-white/5 bg-surface-primary/10 backdrop-blur-md">
      <div className="max-w-4xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12 space-y-3"
        >
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="h-px flex-1 max-w-16 bg-border/50" />
            <span className="text-[11px] font-semibold tracking-widest uppercase text-text-secondary/60">Select Deployment</span>
            <div className="h-px flex-1 max-w-16 bg-border/50" />
          </div>
          <h2 className="text-3xl md:text-4xl font-light text-foreground">
            Who are you<br /><span className="font-semibold">deploying VISOR for?</span>
          </h2>
          <p className="text-text-secondary font-light max-w-lg mx-auto">Choose your deployment context. This unlocks the right features and score model for your use case.</p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {modes.map((mode, i) => {
            const isSelected = (mode.id === "enterprise") === isEnterprise;
            return (
              <motion.button
                key={mode.id}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                whileHover={{ y: -2 }}
                whileTap={{ scale: 0.99 }}
                onClick={() => actions.setDeploymentMode(mode.id)}
                className={`relative text-left p-6 rounded-xl border-2 transition-all duration-300 w-full backdrop-blur-md shadow-lg ${
                  isSelected
                    ? "border-accent/60 bg-accent/10 shadow-[0_0_20px_rgba(192,132,252,0.2)]"
                    : "border-white/10 bg-surface-primary/20 hover:border-white/20 hover:bg-surface-primary/30"
                }`}
              >
                {isSelected && (
                  <div className="absolute top-4 right-4">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="w-5 h-5 rounded-full bg-accent flex items-center justify-center"
                    >
                      <svg className="w-3 h-3 text-background" fill="none" viewBox="0 0 12 12"><path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                    </motion.div>
                  </div>
                )}
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-5 ${isSelected ? "bg-accent/15 text-accent" : "bg-surface-secondary text-text-secondary"}`}>
                  {mode.icon}
                </div>
                <div className="space-y-1 mb-4">
                  <div className="flex items-center gap-2">
                    <h3 className={`text-base font-semibold ${isSelected ? "text-foreground" : "text-foreground/80"}`}>{mode.title}</h3>
                    {mode.badge && (
                      <span className="text-[10px] font-semibold tracking-wider bg-accent/15 text-accent px-2 py-0.5 rounded-full uppercase">{mode.badge}</span>
                    )}
                  </div>
                  <p className="text-sm text-text-secondary font-light leading-relaxed">{mode.desc}</p>
                </div>
                <ul className="space-y-1.5">
                  {mode.features.map((f, j) => (
                    <li key={j} className="flex items-center gap-2 text-xs text-text-secondary">
                      <div className={`w-1 h-1 rounded-full ${isSelected ? "bg-accent" : "bg-text-secondary/40"}`} />
                      {f}
                    </li>
                  ))}
                </ul>
              </motion.button>
            );
          })}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4 }}
          className="mt-8 text-center"
        >
          <Link href="/analyze">
            <Button className="h-12 px-8 text-sm font-medium">
              {isEnterprise ? "Open Enterprise Dashboard" : "Open Retail Dashboard"}
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </Link>
          <p className="text-xs text-text-secondary/50 mt-3">You can change this anytime from the sidebar</p>
        </motion.div>
      </div>
    </section>
  );
}

// -- HERO STATUS WIDGET --
function HeroStatus() {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2, duration: 0.5 }}
      className="absolute bottom-8 left-8 md:bottom-12 md:left-12 flex space-x-8 text-xs text-text-secondary"
    >
      <div className="flex flex-col space-y-1">
        <span className="font-semibold text-[10px] tracking-widest uppercase opacity-50">System Status</span>
        <div className="flex items-center space-x-2">
          <div className="w-1.5 h-1.5 rounded-full bg-success/80 animate-pulse" />
          <span>Operational</span>
        </div>
      </div>
      <div className="flex flex-col space-y-1">
        <span className="font-semibold text-[10px] tracking-widest uppercase opacity-50">Voice Engine</span>
        <span>W2V2-AASIST</span>
      </div>
      <div className="flex flex-col space-y-1">
        <span className="font-semibold text-[10px] tracking-widest uppercase opacity-50">Analysis</span>
        <span>Ready</span>
      </div>
    </motion.div>
  );
}

// -- HERO SECTION --
function Hero() {
  const [isMicHovered, setIsMicHovered] = useState(false);
  const [waveHeights, setWaveHeights] = useState([10, 15, 8, 20, 12, 25, 10]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isMicHovered) {
      interval = setInterval(() => {
        setWaveHeights(Array.from({ length: 7 }, () => Math.floor(Math.random() * 24) + 8));
      }, 150);
    } else {
      setWaveHeights([10, 15, 8, 20, 12, 25, 10]);
    }
    return () => clearInterval(interval);
  }, [isMicHovered]);

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      {/* Restrained violet radial gradient and bottom-right purple glow */}
      <div className="absolute inset-0 bg-[#0D041C]" />
      <div className="absolute top-1/2 right-1/4 w-[600px] h-[600px] bg-accent/20 rounded-full blur-[120px] -translate-y-1/2 pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-lavender/10 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#8B3DFF08_1px,transparent_1px),linear-gradient(to_bottom,#8B3DFF08_1px,transparent_1px)] bg-[size:40px_40px]" />
      
      <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center relative z-10 w-full">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="space-y-6"
        >
          <h1 className="text-6xl lg:text-[88px] font-display font-bold tracking-tighter text-foreground leading-[0.95] uppercase">
            Your Voice.<br />
            Verified.
          </h1>
          <p className="text-base lg:text-lg text-text-secondary max-w-xl font-sans leading-relaxed">
            Advanced biometric voice verification and deepfake synthetic speech detection. 
            VISOR analyzes sub-perceptual acoustic artifacts to distinguish genuine human voices from AI clones in real-time.
          </p>
          <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4 pt-6">
            <Link href="/analyze">
              <Button className="bg-accent text-[#0D041C] hover:bg-lavender h-12 px-8 text-sm font-medium w-full sm:w-auto uppercase tracking-wide transition-colors">
                Start Voice Analysis
              </Button>
            </Link>
            <Link href="/enrollment">
              <Button variant="outline" className="h-12 px-8 text-sm font-medium border-border text-foreground hover:bg-surface-secondary w-full sm:w-auto uppercase tracking-wide transition-colors">
                Enroll My Voice
              </Button>
            </Link>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="flex justify-center lg:justify-end"
        >
          {/* Central Interactive Mic Interface */}
          <Link href="/analyze" className="group block relative">
            <motion.div 
              onMouseEnter={() => setIsMicHovered(true)}
              onMouseLeave={() => setIsMicHovered(false)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-80 h-80 rounded-full border border-white/10 bg-surface-primary/20 flex flex-col items-center justify-center relative shadow-[0_8px_32px_rgba(0,0,0,0.3)] backdrop-blur-xl cursor-pointer transition-all duration-300 group-hover:border-accent/40 group-hover:bg-surface-secondary/40 group-hover:shadow-[0_0_40px_rgba(192,132,252,0.2)]"
            >
              <div className="absolute inset-2 rounded-full border border-border/30 border-dashed" />
              <div className="absolute inset-4 rounded-full border border-border/20" />
              
              <motion.div 
                animate={{ y: isMicHovered ? [0, -10, 0] : [0, -5, 0] }}
                transition={{ repeat: Infinity, duration: isMicHovered ? 2 : 4, ease: "easeInOut" }}
                className="w-40 h-40 mb-2 relative z-10 drop-shadow-[0_0_30px_rgba(217,163,255,0.25)]"
              >
                {/* 3D-like Floating Microphone SVG */}
                <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full transform -rotate-12 transition-transform duration-500 group-hover:rotate-0">
                  <defs>
                    <linearGradient id="mic-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#D9A3FF" />
                      <stop offset="50%" stopColor="#8B3DFF" />
                      <stop offset="100%" stopColor="#0D041C" />
                    </linearGradient>
                    <linearGradient id="mesh-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#160B28" />
                      <stop offset="100%" stopColor="#0D041C" />
                    </linearGradient>
                    <radialGradient id="glow" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stopColor="#8B3DFF" stopOpacity="0.4" />
                      <stop offset="100%" stopColor="#8B3DFF" stopOpacity="0" />
                    </radialGradient>
                  </defs>
                  
                  {/* Background glow */}
                  <circle cx="50" cy="45" r="40" fill="url(#glow)" />
                  
                  {/* Floating purple ribbon / soundwave */}
                  <path d="M10 50 Q 30 20 50 50 T 90 50" stroke="#8B3DFF" strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.6" className="animate-pulse" />
                  
                  {/* Mic body / handle */}
                  <rect x="42" y="55" width="16" height="35" rx="8" fill="url(#mic-grad)" stroke="#D9A3FF" strokeWidth="0.5" />
                  
                  {/* Mic head (mesh) */}
                  <rect x="35" y="15" width="30" height="40" rx="15" fill="url(#mesh-grad)" stroke="url(#mic-grad)" strokeWidth="2" />
                  
                  {/* Mesh grid lines */}
                  <path d="M40 15 V 55 M 45 15 V 55 M 50 15 V 55 M 55 15 V 55 M 60 15 V 55" stroke="#8B3DFF" strokeWidth="0.5" opacity="0.4" />
                  <path d="M35 25 H 65 M 35 35 H 65 M 35 45 H 65" stroke="#8B3DFF" strokeWidth="0.5" opacity="0.4" />
                  
                  {/* Stand connection ring */}
                  <path d="M 30 45 A 25 25 0 0 0 70 45" fill="none" stroke="#D9A3FF" strokeWidth="3" strokeLinecap="round" />
                  <rect x="47" y="68" width="6" height="8" fill="#160B28" stroke="#D9A3FF" strokeWidth="1" />
                  
                  {/* Electric lime active indicator */}
                  <circle cx="50" cy="72" r="2.5" fill="#D5FF45" className={isMicHovered ? "animate-ping" : ""} />
                  <circle cx="50" cy="72" r="2.5" fill="#D5FF45" />
                </svg>
              </motion.div>
              
              {/* Status Text */}
              <div className="h-6 relative z-10">
                <AnimatePresence mode="wait">
                  {!isMicHovered ? (
                    <motion.span 
                      key="ready"
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -5 }}
                      className="text-xs tracking-[0.2em] font-medium text-text-secondary uppercase"
                    >
                      READY
                    </motion.span>
                  ) : (
                    <motion.span 
                      key="start"
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -5 }}
                      className="text-xs tracking-[0.2em] font-medium text-accent uppercase"
                    >
                      START ANALYSIS
                    </motion.span>
                  )}
                </AnimatePresence>
              </div>

              {/* Waveform */}
              <div className="absolute bottom-16 flex items-end space-x-1 h-8 z-10">
                {waveHeights.map((h, i) => (
                  <motion.div 
                    key={i}
                    animate={{ height: h }}
                    transition={{ duration: 0.15 }}
                    className="w-1 bg-text-secondary/40 rounded-t-sm"
                  />
                ))}
              </div>
            </motion.div>
          </Link>
        </motion.div>
      </div>
      
      <HeroStatus />

      {/* Scroll indicator */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1, duration: 1 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center space-y-2"
      >
        <div className="w-[1px] h-12 bg-gradient-to-b from-transparent via-text-secondary to-transparent opacity-50" />
      </motion.div>
    </section>
  );
}

// -- SECTION 2: ANIMATED PIPELINE --
function PipelineSection() {
  const stages = [
    { label: "VOICE INPUT", icon: <Mic className="w-4 h-4" /> },
    { label: "ACOUSTIC ANALYSIS", icon: <Activity className="w-4 h-4" /> },
    { label: "SPOOF DETECTION", icon: <ShieldCheck className="w-4 h-4" /> },
    { label: "THREAT INTELLIGENCE", icon: <Database className="w-4 h-4" /> },
    { label: "SECURITY INSIGHT", icon: <Lock className="w-4 h-4" /> },
  ];

  return (
    <section id="platform" className="py-32 border-t border-white/5 bg-transparent relative backdrop-blur-sm">
      <div className="max-w-4xl mx-auto px-6 text-center">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="space-y-6 mb-20"
        >
          <h2 className="text-3xl md:text-4xl font-light text-foreground">
            Voice is data.<br/>
            <span className="font-medium">VISOR turns it into intelligence.</span>
          </h2>
        </motion.div>

        <div className="flex flex-col items-center space-y-4">
          {stages.map((stage, i) => (
            <React.Fragment key={i}>
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.4, delay: i * 0.15 }}
                className="flex items-center space-x-3 bg-surface-primary/30 backdrop-blur-xl border border-white/10 px-6 py-4 rounded-xl shadow-lg w-full max-w-sm"
              >
                <div className="text-accent">{stage.icon}</div>
                <span className="text-sm font-medium tracking-wide text-foreground">{stage.label}</span>
              </motion.div>
              {i < stages.length - 1 && (
                <motion.div 
                  initial={{ height: 0, opacity: 0 }}
                  whileInView={{ height: 32, opacity: 1 }}
                  viewport={{ once: true, margin: "-50px" }}
                  transition={{ duration: 0.4, delay: (i * 0.15) + 0.1 }}
                  className="w-[1px] bg-border"
                />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    </section>
  );
}

// -- SECTION 3: FEATURES --
function FeaturesSection() {
  const features = [
    { title: "Voice Spoof Detection", desc: "Identifies AI-synthesized clones and vocoder artifacts with sub-millisecond precision.", icon: <ShieldCheck /> },
    { title: "Real-Time Analysis", desc: "Streaming acoustic evaluation designed for live telecom interception.", icon: <Activity /> },
    { title: "Threat Intelligence", desc: "Federated graph mapping caller identities against global fraud reports.", icon: <Globe /> },
    { title: "Speaker Verification", desc: "Zero-enrollment biometric mismatch detection for high-value targets.", icon: <UsersIcon /> },
    { title: "Channel Trust", desc: "STIR/SHAKEN attestation and VoIP gateway analysis.", icon: <Lock /> },
    { title: "Security Audit", desc: "Cryptographically signed SHA-256 ledger for undeniable compliance.", icon: <Database /> },
  ];

  return (
    <section id="features" className="py-32 border-t border-white/5 bg-surface-primary/10 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-light text-foreground">
            Built for the moments that matter.
          </h2>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              whileHover={{ y: -4 }}
              className="group p-6 rounded-xl border border-white/10 bg-surface-primary/20 backdrop-blur-xl transition-colors duration-300 hover:border-text-secondary/50 shadow-lg"
            >
              <div className="w-10 h-10 rounded-lg bg-surface-secondary flex items-center justify-center text-text-secondary mb-6 group-hover:text-foreground transition-colors">
                {f.icon}
              </div>
              <h3 className="text-lg font-medium text-foreground mb-2">{f.title}</h3>
              <p className="text-sm text-text-secondary leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function UsersIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
  );
}

// -- SECTION 4: INTERACTIVE STEPS --
function HowItThinksSection() {
  const [activeStep, setActiveStep] = useState(0);
  
  const steps = [
    { num: "01", title: "Capture", detail: "Isolates voice signal from ambient noise and normalizes the acoustic payload." },
    { num: "02", title: "Analyze", detail: "Extracts deep spectro-temporal embeddings using the Wav2Vec2 front-end architecture." },
    { num: "03", title: "Detect", detail: "Evaluates graph attention networks to identify sub-perceptual vocoder artifacts." },
    { num: "04", title: "Correlate", detail: "Cross-references acoustic scores with telecom metadata and NLP intent engines." },
    { num: "05", title: "Explain", detail: "Outputs a unified composite risk score with transparent, cryptographically backed evidence." },
  ];

  return (
    <section id="how-it-works" className="py-32 border-t border-white/5 bg-transparent backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-6">
        <h2 className="text-3xl md:text-4xl font-light text-foreground mb-16">
          How VISOR thinks
        </h2>

        <div className="flex flex-col lg:flex-row gap-12 lg:gap-24">
          <div className="flex-1 space-y-2">
            {steps.map((step, i) => (
              <div 
                key={i}
                onClick={() => setActiveStep(i)}
                className={`flex items-center space-x-6 p-4 rounded-sm cursor-pointer transition-all duration-300 ${
                  activeStep === i ? "bg-surface-secondary/50" : "hover:bg-surface-primary"
                }`}
              >
                <span className={`text-sm font-mono ${activeStep === i ? "text-accent" : "text-text-secondary"}`}>
                  {step.num}
                </span>
                <span className={`text-xl font-light ${activeStep === i ? "text-foreground" : "text-text-secondary"}`}>
                  {step.title}
                </span>
              </div>
            ))}
          </div>
          
          <div className="flex-1 flex items-center">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeStep}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
                className="p-8 rounded-xl border border-white/10 bg-surface-primary/30 backdrop-blur-xl shadow-lg w-full"
              >
                <div className="text-accent mb-4">
                  <Zap className="w-8 h-8" />
                </div>
                <h3 className="text-2xl font-light text-foreground mb-4">{steps[activeStep].title}</h3>
                <p className="text-text-secondary leading-relaxed text-lg font-light">
                  {steps[activeStep].detail}
                </p>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}

// -- SECTION 5: INTERACTIVE PREVIEW --
function PreviewSection() {
  return (
    <section className="py-32 border-t border-white/5 bg-transparent overflow-hidden backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center space-x-4 mb-16">
          <div className="w-2 h-2 rounded-full bg-accent" />
          <span className="text-sm font-mono text-text-secondary uppercase tracking-widest">Interactive preview</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
          {/* Waveform visual */}
          <div className="rounded-xl border border-white/10 bg-surface-primary/20 backdrop-blur-xl p-8 flex items-center justify-center min-h-[400px] relative overflow-hidden shadow-lg">
            <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_center,var(--accent)_0,transparent_70%)]" />
            <div className="flex items-center space-x-1.5 z-10 w-full max-w-md px-4">
              {Array.from({ length: 40 }).map((_, i) => {
                const h = 20 + Math.abs(Math.sin(i * 0.4) * 40) + ((i * 13) % 20);
                return (
                  <motion.div 
                    key={i}
                    animate={{ height: [h, h * 0.5, h] }}
                    transition={{ repeat: Infinity, duration: 1.5 + (i * 0.05), ease: "easeInOut" }}
                    className="w-1.5 bg-foreground/30 rounded-full flex-1 max-h-32"
                    style={{ height: h }}
                  />
                )
              })}
            </div>
            
            <div className="absolute bottom-6 left-6 flex items-center space-x-3">
              <div className="w-10 h-10 rounded-full bg-background flex items-center justify-center shadow-sm border border-border">
                <div className="w-3 h-3 bg-danger rounded-full" />
              </div>
              <span className="text-xs font-mono text-text-secondary">REC_001.WAV</span>
            </div>
          </div>

          {/* Analysis Data */}
          <div className="flex flex-col space-y-4">
            <div className="rounded-xl border border-white/10 bg-surface-primary/20 backdrop-blur-xl p-8 flex-1 space-y-8 shadow-lg">
              <div>
                <p className="text-xs text-text-secondary uppercase tracking-wider font-semibold mb-2">Voice Authenticity</p>
                <div className="flex items-end space-x-3">
                  <span className="text-5xl font-light text-foreground">91%</span>
                  <span className="text-sm text-text-secondary mb-1.5">confidence</span>
                </div>
              </div>

              <div className="space-y-4 pt-4 border-t border-border/50">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-foreground">Spoof Indicators</span>
                  <span className="text-sm text-success bg-success/10 px-3 py-1 rounded-full">Low</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-foreground">Channel Trust</span>
                  <span className="text-sm text-success bg-success/10 px-3 py-1 rounded-full">High</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-foreground">Communication Risk</span>
                  <span className="text-sm text-warning bg-warning/10 px-3 py-1 rounded-full">Moderate</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// -- SECTION 6: SECURITY PHILOSOPHY --
function PhilosophySection() {
  return (
    <section id="security" className="py-32 border-t border-white/5 bg-surface-primary/10 backdrop-blur-md">
      <div className="max-w-4xl mx-auto px-6 text-center space-y-8">
        <div className="w-16 h-16 rounded-sm bg-surface-secondary flex items-center justify-center mx-auto mb-8">
          <Eye className="w-8 h-8 text-text-secondary" />
        </div>
        <h2 className="text-3xl md:text-4xl font-light text-foreground">
          Security decisions should be <span className="font-medium italic">explainable.</span>
        </h2>
        <p className="text-lg text-text-secondary font-light leading-relaxed max-w-2xl mx-auto">
          VISOR surfaces underlying signals and concrete evidence rather than simply presenting an unexplained binary result. By exposing acoustic artifacts, telecom metadata, and semantic context, human analysts retain ultimate agency.
        </p>
      </div>
    </section>
  );
}

// -- FINAL CTA --
function CtaSection() {
  return (
    <section className="py-32 border-t border-white/5 bg-surface-primary/10 relative overflow-hidden backdrop-blur-lg">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-lg h-px bg-gradient-to-r from-transparent via-accent/50 to-transparent" />
      <div className="max-w-4xl mx-auto px-6 text-center space-y-10 relative z-10">
        <h2 className="text-4xl md:text-6xl font-light text-foreground">
          Ready to analyze a voice?
        </h2>
        <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
          <Link href="/analyze">
            <Button className="bg-foreground text-background hover:bg-foreground/90 h-12 px-8 text-sm font-medium w-full sm:w-auto">
              Start Analysis
            </Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="outline" className="h-12 px-8 text-sm font-medium border-border text-foreground hover:bg-surface-secondary w-full sm:w-auto">
              Open Dashboard
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
}

// -- FOOTER --
function Footer() {
  return (
    <footer className="border-t border-white/10 bg-surface-primary/5 backdrop-blur-xl py-16">
      <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-4 gap-12 md:gap-8">
        <div className="md:col-span-1 space-y-4">
          <div className="flex items-center space-x-2 text-foreground">
            <Mic className="w-5 h-5 text-accent" />
            <span className="font-semibold tracking-wide">VISOR</span>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed max-w-xs">
            Voice Intelligence & Security Operations. Turning raw audio into actionable security intelligence.
          </p>
        </div>
        
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-foreground">Platform</h4>
          <ul className="space-y-2 text-sm text-text-secondary">
            <li><Link href="/dashboard" className="hover:text-foreground transition-colors">Dashboard</Link></li>
            <li><Link href="/analyze" className="hover:text-foreground transition-colors">Analysis Engine</Link></li>
            <li><Link href="/history" className="hover:text-foreground transition-colors">Audit Ledger</Link></li>
          </ul>
        </div>
        
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-foreground">Technology</h4>
          <ul className="space-y-2 text-sm text-text-secondary">
            <li><a href="#how-it-works" className="hover:text-foreground transition-colors">Acoustic Processing</a></li>
            <li><a href="#features" className="hover:text-foreground transition-colors">Telecom Verification</a></li>
            <li><a href="#security" className="hover:text-foreground transition-colors">Explainable AI</a></li>
          </ul>
        </div>

        <div className="space-y-4">
          <h4 className="text-sm font-medium text-foreground">Company</h4>
          <ul className="space-y-2 text-sm text-text-secondary">
            <li><Link href="/about" className="hover:text-foreground transition-colors">About</Link></li>
            <li><a href="#" className="hover:text-foreground transition-colors flex items-center">GitHub <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3 ml-1.5"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.2c3-.3 6-1.5 6-6.5a5.5 5.5 0 0 0-1.5-3.8 5.5 5.5 0 0 0-.1-3.7s-1.2-.4-3.9 1.4a12.8 12.8 0 0 0-7 0C6.2 1.2 5 1.6 5 1.6a5.5 5.5 0 0 0-.1 3.7 5.5 5.5 0 0 0-1.5 3.8c0 5 3 6.2 6 6.5a4.8 4.8 0 0 0-1 3.2v4"/><path d="M9 18c-4.5 1.5-5-2.5-7-3"/></svg></a></li>
            <li><Link href="/settings" className="hover:text-foreground transition-colors">Settings</Link></li>
          </ul>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-6 pt-16 mt-16 border-t border-border/50 text-xs text-text-secondary/70 flex flex-col md:flex-row justify-between items-center">
        <p>&copy; {new Date().getFullYear()} VISOR Security. All rights reserved.</p>
        <p className="mt-2 md:mt-0">Enterprise Voice Defense Platform</p>
      </div>
    </footer>
  );
}

// -- MAIN EXPORT --
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-transparent selection:bg-accent/30">
      <TopNav />
      <main>
        <Hero />
        <PipelineSection />
        <FeaturesSection />
        <LandingModeSelector />
        <HowItThinksSection />
        <PreviewSection />
        <PhilosophySection />
        <CtaSection />
      </main>
      <Footer />
    </div>
  );
}
