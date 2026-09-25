"use client";

import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAppState } from "@/contexts/AppContext";
import { Building2, User, Fingerprint, Shield, SlidersHorizontal } from "lucide-react";
import { motion } from "framer-motion";

export default function SettingsPage() {
  const { state, actions } = useAppState();
  const isEnterprise = state.deploymentMode === "enterprise";

  return (
    <PageWrapper className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="border-b border-border pb-5">
        <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-text-secondary mt-1">System configuration and deployment preferences.</p>
      </div>

      {/* Deployment Mode Card */}
      <Card>
        <CardHeader className="border-b border-border pb-4">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-text-secondary" />
            Deployment Mode
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-border">
            <button
              onClick={() => actions.setDeploymentMode("retail")}
              className={`flex flex-col gap-3 p-5 text-left transition-colors duration-200 ${
                !isEnterprise ? "bg-surface-secondary/40" : "hover:bg-surface-primary/50"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${!isEnterprise ? "bg-foreground/10 text-foreground" : "bg-surface-secondary text-text-secondary"}`}>
                  <User className="w-4 h-4" />
                </div>
                <div>
                  <p className={`text-sm font-medium ${!isEnterprise ? "text-foreground" : "text-text-secondary"}`}>Retail</p>
                  <p className="text-[11px] text-text-secondary/70">Consumer / personal</p>
                </div>
                {!isEnterprise && (
                  <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="ml-auto w-4 h-4 rounded-full bg-success/80 flex items-center justify-center">
                    <svg className="w-2.5 h-2.5 text-background" fill="none" viewBox="0 0 10 10"><path d="M1.5 5l2.5 2.5 4.5-4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  </motion.div>
                )}
              </div>
              <ul className="text-[11px] text-text-secondary space-y-0.5 ml-11">
                <li>· 3-pillar risk scoring</li>
                <li>· Acoustic + Telecom + NLP</li>
                <li>· No biometric features</li>
              </ul>
            </button>

            <button
              onClick={() => actions.setDeploymentMode("enterprise")}
              className={`flex flex-col gap-3 p-5 text-left transition-colors duration-200 ${
                isEnterprise ? "bg-accent/5" : "hover:bg-surface-primary/50"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isEnterprise ? "bg-accent/15 text-accent" : "bg-surface-secondary text-text-secondary"}`}>
                  <Building2 className="w-4 h-4" />
                </div>
                <div>
                  <p className={`text-sm font-medium ${isEnterprise ? "text-foreground" : "text-text-secondary"}`}>Bank / Enterprise</p>
                  <p className="text-[11px] text-text-secondary/70">Financial-grade security</p>
                </div>
                {isEnterprise && (
                  <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="ml-auto w-4 h-4 rounded-full bg-accent flex items-center justify-center">
                    <svg className="w-2.5 h-2.5 text-background" fill="none" viewBox="0 0 10 10"><path d="M1.5 5l2.5 2.5 4.5-4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  </motion.div>
                )}
              </div>
              <ul className="text-[11px] text-text-secondary space-y-0.5 ml-11">
                <li>· 4-pillar risk scoring</li>
                <li>· + Voiceprint biometrics (25%)</li>
                <li className="text-accent/80">· Enrollment module unlocked</li>
              </ul>
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Model thresholds */}
      <Card>
        <CardHeader className="border-b border-border pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Shield className="w-4 h-4 text-text-secondary" />
            Model Thresholds
          </CardTitle>
        </CardHeader>
        <CardContent className="divide-y divide-border p-0">
          <div className="flex justify-between items-center px-5 py-4">
            <div>
              <p className="text-sm font-medium">Anti-Spoofing (W2V2-AASIST)</p>
              <p className="text-xs text-text-secondary mt-0.5">Current threshold: 0.60</p>
            </div>
            <Button variant="outline" size="sm">Configure</Button>
          </div>
          <div className="flex justify-between items-center px-5 py-4">
            <div>
              <p className="text-sm font-medium">Automated Risk Action</p>
              <p className="text-xs text-text-secondary mt-0.5">
                {isEnterprise ? "Enterprise: Block on > 0.55 composite" : "Retail: Block on > 0.60 composite"}
              </p>
            </div>
            <Button variant="outline" size="sm">Configure</Button>
          </div>
          {isEnterprise && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-between items-center px-5 py-4 bg-accent/3"
            >
              <div>
                <p className="text-sm font-medium flex items-center gap-1.5">
                  <Fingerprint className="w-3.5 h-3.5 text-accent" /> Biometric Match Threshold
                </p>
                <p className="text-xs text-text-secondary mt-0.5">Minimum cosine similarity: 0.75</p>
              </div>
              <Button variant="outline" size="sm">Configure</Button>
            </motion.div>
          )}
        </CardContent>
      </Card>

      {/* System info */}
      <Card className="bg-surface-secondary/20">
        <CardContent className="p-5 text-xs text-text-secondary space-y-1">
          <p><span className="text-foreground/50">Engine:</span> {state.modelStatus.engine}</p>
          <p><span className="text-foreground/50">Runtime:</span> {state.modelStatus.inference}</p>
          <p><span className="text-foreground/50">Backend:</span> {state.modelStatus.backend}</p>
          <p><span className="text-foreground/50">Version:</span> {state.modelStatus.version}</p>
        </CardContent>
      </Card>
    </PageWrapper>
  );
}
