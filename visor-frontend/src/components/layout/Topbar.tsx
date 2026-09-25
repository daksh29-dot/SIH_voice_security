"use client";

import * as React from "react";
import { useAppState } from "@/contexts/AppContext";
import { Building2, User } from "lucide-react";

export function Topbar() {
  const { state } = useAppState();
  const isEnterprise = state.deploymentMode === "enterprise";

  return (
    <header className="flex h-14 items-center justify-between border-b border-white/5 bg-surface-primary/20 backdrop-blur-2xl px-4 sm:px-6 lg:px-8 z-20">
      <div className="flex flex-1 items-center">
        <h1 className="text-sm font-medium text-foreground tracking-tight">
          Control Center
        </h1>
      </div>
      <div className="flex items-center space-x-5">
        {/* Mode badge */}
        <div className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-md border ${
          isEnterprise 
            ? "bg-accent/10 border-accent/20 text-accent" 
            : "bg-surface-secondary border-border text-text-secondary"
        }`}>
          {isEnterprise ? <Building2 className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
          {isEnterprise ? "Enterprise" : "Retail"}
        </div>

        {/* System status */}
        <div className="flex items-center space-x-2">
          <span className="relative flex h-2 w-2">
            {state.systemStatus.status === "Operational" && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success/75 opacity-75"></span>}
            <span className={`relative inline-flex rounded-full h-2 w-2 ${state.systemStatus.status === "Operational" ? "bg-success" : "bg-warning"}`}></span>
          </span>
          <span className="text-xs font-medium text-text-secondary">
            {state.systemStatus.status} <span className="text-text-secondary/50">·</span> {state.systemStatus.latencyMs}ms
          </span>
        </div>
      </div>
    </header>
  )
}
