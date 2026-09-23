"use client";

import * as React from "react";
import { useAppState } from "@/contexts/AppContext";

export function Topbar() {
  const { state } = useAppState();

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-surface-primary px-4 sm:px-6 lg:px-8">
      <div className="flex flex-1 items-center">
        <h1 className="text-lg font-semibold text-foreground tracking-tight">VISOR <span className="font-light text-text-secondary">| Control Center</span></h1>
      </div>
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <span className="relative flex h-3 w-3">
            {state.systemStatus.status === "Operational" && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success/75 opacity-75"></span>}
            <span className={`relative inline-flex rounded-full h-3 w-3 ${state.systemStatus.status === "Operational" ? 'bg-success' : 'bg-warning'}`}></span>
          </span>
          <span className="text-sm font-medium text-text-secondary">
            {state.systemStatus.status} • {state.systemStatus.latencyMs}ms
          </span>
        </div>
      </div>
    </header>
  )
}
