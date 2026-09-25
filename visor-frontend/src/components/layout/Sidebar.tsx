"use client";

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, Activity, ShieldAlert, Shield, Info, Settings, X, Building2, User, Fingerprint, History, Mic } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { useAppState } from "@/contexts/AppContext"

interface SidebarProps {
  onClose?: () => void;
}

export function Sidebar({ onClose }: SidebarProps) {
  const pathname = usePathname()
  const { state, actions } = useAppState()
  const isEnterprise = state.deploymentMode === "enterprise"

  const coreNavItems = [
    { href: "/dashboard", label: "Dashboard", icon: <LayoutDashboard className="w-4 h-4" /> },
    { href: "/analyze", label: "Analysis", icon: <Activity className="w-4 h-4" /> },
    { href: "/threat-intelligence", label: "Threat Intel", icon: <ShieldAlert className="w-4 h-4" /> },
    { href: "/history", label: "Audit Ledger", icon: <History className="w-4 h-4" /> },
  ]

  const enterpriseNavItems = [
    { href: "/enrollment", label: "Voice Enrollment", icon: <Fingerprint className="w-4 h-4" />, badge: "Enterprise" },
  ]

  const bottomItems = [
    { href: "/about", label: "About", icon: <Info className="w-4 h-4" /> },
    { href: "/settings", label: "Settings", icon: <Settings className="w-4 h-4" /> },
  ]

  const NavLink = ({ item }: { item: { href: string; label: string; icon: React.ReactNode; badge?: string } }) => {
    const isActive = pathname === item.href
    return (
      <Link
        href={item.href}
        className={`group relative flex items-center space-x-3 px-3 py-2 rounded-md transition-all duration-200 text-sm font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
          isActive 
            ? "text-foreground" 
            : "text-text-secondary hover:text-foreground"
        }`}
        aria-current={isActive ? "page" : undefined}
      >
        {isActive && (
          <div
            className="absolute inset-0 bg-surface-secondary/40 rounded-md shadow-sm"
          />
        )}
        <span className={`relative z-10 transition-colors duration-200 ${isActive ? "text-accent" : "text-text-secondary group-hover:text-foreground"}`}>
          {item.icon}
        </span>
        <span className="relative z-10">{item.label}</span>
        {item.badge && (
          <span className="relative z-10 ml-auto text-[10px] font-semibold tracking-wider bg-accent/15 text-accent px-1.5 py-0.5 rounded-sm uppercase">
            {item.badge}
          </span>
        )}
      </Link>
    )
  }

  return (
    <aside className="flex flex-col h-full w-64 bg-surface-primary/20 backdrop-blur-2xl border-r border-white/5">
      {/* Logo */}
      <div className="flex h-14 items-center justify-between px-5 border-b border-border">
        <Link href="/" className="flex items-center space-x-2.5 text-foreground hover:opacity-80 transition-opacity focus:outline-none focus:ring-2 focus:ring-accent rounded-sm" aria-label="VISOR Home">
          <div className="w-7 h-7 rounded-md bg-accent/10 border border-accent/20 flex items-center justify-center">
            <Mic className="w-4 h-4 text-accent" />
          </div>
          <span className="font-semibold text-base tracking-tight">VISOR</span>
        </Link>
        {onClose && (
          <button 
            onClick={onClose} 
            className="lg:hidden text-text-secondary hover:text-foreground p-1 focus:outline-none focus:ring-2 focus:ring-accent rounded-sm"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Deployment Mode Switcher */}
      <div className="px-4 py-4 border-b border-border">
        <p className="text-[10px] font-semibold tracking-widest text-text-secondary/60 uppercase mb-3 px-1">Deployment Mode</p>
        <div className="relative flex bg-background border border-border rounded-lg p-1 gap-1">
          <motion.div
            className="absolute top-1 bottom-1 rounded-md bg-surface-secondary border border-border/50"
            animate={{
              left: isEnterprise ? "calc(50% + 2px)" : "4px",
              width: "calc(50% - 6px)"
            }}
            transition={{ type: "spring", bounce: 0.18, duration: 0.4 }}
          />
          <button
            onClick={() => actions.setDeploymentMode("retail")}
            className={`relative z-10 flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded-md text-xs font-medium transition-colors duration-300 ${
              !isEnterprise ? "text-foreground" : "text-text-secondary hover:text-foreground"
            }`}
          >
            <User className="w-3.5 h-3.5" />
            <span>Retail</span>
          </button>
          <button
            onClick={() => actions.setDeploymentMode("enterprise")}
            className={`relative z-10 flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded-md text-xs font-medium transition-colors duration-300 ${
              isEnterprise ? "text-foreground" : "text-text-secondary hover:text-foreground"
            }`}
          >
            <Building2 className="w-3.5 h-3.5" />
            <span>Enterprise</span>
          </button>
        </div>
        <AnimatePresence>
          {isEnterprise && (
            <motion.p
              initial={{ opacity: 0, height: 0, marginTop: 0 }}
              animate={{ opacity: 1, height: "auto", marginTop: 8 }}
              exit={{ opacity: 0, height: 0, marginTop: 0 }}
              className="text-[10px] text-accent/80 px-1 leading-relaxed overflow-hidden"
            >
              Voiceprint enrollment & biometric verification enabled.
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      {/* Main Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5" aria-label="Main Navigation">
        <p className="text-[10px] font-semibold tracking-widest text-text-secondary/50 uppercase px-3 pb-2 pt-1">Core</p>
        {coreNavItems.map((item) => (
          <NavLink key={item.href} item={item} />
        ))}

        <AnimatePresence>
          {isEnterprise && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <p className="text-[10px] font-semibold tracking-widest text-accent/60 uppercase px-3 pb-2 pt-4">Biometrics</p>
              {enterpriseNavItems.map((item) => (
                <NavLink key={item.href} item={item} />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      {/* Bottom Nav */}
      <div className="p-3 border-t border-border space-y-0.5">
        {bottomItems.map((item) => (
          <NavLink key={item.href} item={{ ...item }} />
        ))}
      </div>
    </aside>
  )
}
