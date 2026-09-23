"use client";
import React, { useEffect, useState } from "react";

import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useAppState } from "@/contexts/AppContext";
import { ThreatIndicator, Severity, ThreatCategory } from "@/types/models";
import { ShieldAlert, Fingerprint, Network, ShieldQuestion, Activity, Eye, FileText, ChevronRight, CheckCircle2, Lock } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function ThreatIntelligencePage() {
  const { state } = useAppState();
  const indicators = state.threatIndicators;
  
  const [selectedIndicator, setSelectedIndicator] = useState<ThreatIndicator | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>("All");

  useEffect(() => {
    if (indicators.length > 0 && !selectedIndicator) {
      setSelectedIndicator(indicators[0]);
    }
  }, [indicators, selectedIndicator]);

  const getSeverityColor = (severity: Severity) => {
    switch(severity) {
      case "Critical": return "text-danger border-danger/30 bg-danger/5";
      case "High": return "text-warning border-warning/30 bg-warning/5";
      case "Moderate": return "text-accent border-accent/30 bg-accent/5";
      case "Low": return "text-foreground border-border bg-surface-secondary/20";
      case "Informational": return "text-text-secondary border-border bg-transparent";
    }
  };

  const getSeverityBadgeVariant = (severity: Severity) => {
    switch(severity) {
      case "Critical": return "danger";
      case "High": return "warning";
      case "Moderate": return "default";
      default: return "success";
    }
  };

  const getCategoryIcon = (cat: string) => {
    switch(cat) {
      case "Voice Spoofing Indicators": return <Fingerprint className="w-4 h-4" />;
      case "Channel Trust": return <Network className="w-4 h-4" />;
      case "Communication Risk": return <ShieldQuestion className="w-4 h-4" />;
      case "Speaker Signals": return <Activity className="w-4 h-4" />;
      case "Suspicious Patterns": return <Eye className="w-4 h-4" />;
      default: return <FileText className="w-4 h-4" />;
    }
  };

  const filteredIndicators = indicators.filter(i => activeCategory === "All" || i.category === activeCategory);

  return (
    <PageWrapper className="p-6 max-w-7xl mx-auto space-y-6">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:items-end justify-between border-b border-border pb-4 gap-4">
        <div>
          <h1 className="text-3xl font-light tracking-tight text-foreground">Global Threat Intelligence</h1>
          <p className="text-sm font-medium text-text-secondary uppercase tracking-widest mt-1">Signals & Telemetry</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* LEFT COLUMN: Categories & Timeline Cards */}
        <div className="lg:col-span-7 space-y-8">
          
          <div className="space-y-4">
            <h2 className="text-sm font-medium text-text-secondary uppercase tracking-wider">Threat Vectors</h2>
            <div className="flex flex-wrap gap-2">
              <button 
                onClick={() => setActiveCategory("All")}
                className={`px-4 py-2 rounded-full text-xs font-medium border transition-colors ${activeCategory === "All" ? 'bg-foreground text-background border-foreground' : 'bg-surface-primary border-border text-text-secondary hover:text-foreground'}`}
              >
                All Vectors
              </button>
              {["Voice Spoofing Indicators", "Channel Trust", "Communication Risk", "Speaker Signals", "Suspicious Patterns"].map((cat) => (
                <button 
                  key={cat}
                  onClick={() => setActiveCategory(cat as ThreatCategory)}
                  className={`px-4 py-2 rounded-full text-xs font-medium border transition-colors flex items-center space-x-2 ${activeCategory === cat ? 'bg-surface-secondary border-text-secondary text-foreground' : 'bg-surface-primary border-border text-text-secondary hover:text-foreground'}`}
                >
                  {getCategoryIcon(cat)}
                  <span>{cat}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <h2 className="text-sm font-medium text-text-secondary uppercase tracking-wider">Live Indicator Timeline</h2>
            
            <div className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-border before:via-border before:to-transparent">
              
              {filteredIndicators.map((indicator, idx) => {
                const isSelected = selectedIndicator?.id === indicator.id;
                
                return (
                  <motion.div 
                    key={indicator.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    onClick={() => setSelectedIndicator(indicator)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setSelectedIndicator(indicator) }}
                    className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group cursor-pointer focus:outline-none focus:bg-surface-secondary/10 rounded-sm"
                    tabIndex={0}
                    role="button"
                    aria-label={`View evidence for ${indicator.title}`}
                    aria-pressed={isSelected}
                  >
                    {/* Timeline Dot */}
                    <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-background bg-surface-secondary shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 relative z-10 transition-colors group-hover:bg-accent/20">
                      {getCategoryIcon(indicator.category)}
                    </div>
                    
                    {/* Card */}
                    <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)]">
                      <Card className={`transition-all duration-300 ${isSelected ? 'border-accent shadow-[0_0_20px_rgba(84,123,158,0.15)] bg-surface-secondary/50' : 'border-border bg-surface-primary hover:border-text-secondary/40'}`}>
                        <CardContent className="p-4 space-y-3">
                          <div className="flex justify-between items-start">
                            <span className="text-xs font-mono text-text-secondary">
                              {new Date(indicator.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                            </span>
                            <Badge variant={getSeverityBadgeVariant(indicator.severity)} className="text-[10px] uppercase">
                              {indicator.severity}
                            </Badge>
                          </div>
                          <div>
                            <h3 className="font-medium text-foreground text-sm">{indicator.title}</h3>
                            <p className="text-xs text-text-secondary mt-1 line-clamp-2">{indicator.summary}</p>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </motion.div>
                )
              })}

            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Evidence Panel (Sticky) */}
        <div className="lg:col-span-5 relative">
          <div className="sticky top-24 space-y-6">
            <h2 className="text-sm font-medium text-text-secondary uppercase tracking-wider">Intelligence Dossier</h2>
            
            <AnimatePresence mode="wait">
              {selectedIndicator ? (
                <motion.div
                  key={selectedIndicator.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <Card className={`overflow-hidden border-2 ${selectedIndicator.severity === 'Critical' ? 'border-danger/30' : selectedIndicator.severity === 'High' ? 'border-warning/30' : 'border-border'}`}>
                    
                    {/* Header */}
                    <div className={`p-6 border-b border-border/50 ${getSeverityColor(selectedIndicator.severity)}`}>
                      <div className="flex items-center space-x-3 mb-4">
                        <div className="p-2 bg-background/50 rounded-lg backdrop-blur-sm">
                          {getCategoryIcon(selectedIndicator.category)}
                        </div>
                        <span className="text-xs font-mono tracking-widest uppercase opacity-80">{selectedIndicator.category}</span>
                      </div>
                      <h3 className="text-xl font-light text-foreground mb-2">{selectedIndicator.title}</h3>
                      <p className="text-sm opacity-90 leading-relaxed">{selectedIndicator.summary}</p>
                    </div>

                    {/* Evidence List */}
                    <div className="p-6 space-y-6 bg-surface-primary/30">
                      <div>
                        <h4 className="text-xs font-medium text-text-secondary uppercase tracking-widest mb-4 flex items-center">
                          <Lock className="w-3 h-3 mr-2" />
                          Cryptographic Evidence
                        </h4>
                        
                        <div className="space-y-4">
                          {selectedIndicator.evidence.map((ev, i) => (
                            <div key={i} className="p-4 rounded-sm border border-border bg-background space-y-3">
                              <div className="flex justify-between items-start">
                                <span className="font-medium text-sm text-foreground">{ev.signal}</span>
                                <Badge variant="default" className="text-[10px] font-mono border-border bg-surface-secondary/50">
                                  Conf: {(ev.confidence * 100).toFixed(0)}%
                                </Badge>
                              </div>
                              <div className="flex flex-col space-y-1">
                                <span className="text-xs text-text-secondary uppercase tracking-wider">Observed</span>
                                <span className="text-sm font-mono text-foreground bg-surface-secondary px-2 py-1 rounded w-max">{ev.observedValue}</span>
                              </div>
                              <div className="pt-2 border-t border-border/50">
                                <p className="text-xs text-text-secondary leading-relaxed">
                                  <span className="font-medium text-foreground mr-1">Interpretation:</span>
                                  {ev.interpretation}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="pt-4 flex items-center justify-between border-t border-border/50 text-xs text-text-secondary">
                        <span className="font-mono">ID: {selectedIndicator.id}</span>
                        <span>Logged: {new Date(selectedIndicator.timestamp).toLocaleString()}</span>
                      </div>
                    </div>

                  </Card>
                </motion.div>
              ) : (
                <div className="h-96 flex flex-col items-center justify-center border border-dashed border-border rounded-sm text-text-secondary">
                  <ShieldAlert className="w-8 h-8 mb-4 opacity-50" />
                  <p>Select an indicator to view evidence</p>
                </div>
              )}
            </AnimatePresence>
          </div>
        </div>

      </div>
    </PageWrapper>
  );
}
