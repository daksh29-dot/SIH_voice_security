"use client";

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, Activity, ShieldAlert, FileAudio, Shield, Info, Settings, X } from "lucide-react"

interface SidebarProps {
  onClose?: () => void;
}

export function Sidebar({ onClose }: SidebarProps) {
  const pathname = usePathname()

  const navItems = [
    { href: "/dashboard", label: "Dashboard", icon: <LayoutDashboard className="w-5 h-5" /> },
    { href: "/analyze", label: "Analysis", icon: <Activity className="w-5 h-5" /> },
    { href: "/threat-intelligence", label: "Threat Intel", icon: <ShieldAlert className="w-5 h-5" /> },
    { href: "/history", label: "History", icon: <FileAudio className="w-5 h-5" /> },
  ]

  const bottomItems = [
    { href: "/about", label: "About VISOR", icon: <Info className="w-5 h-5" /> },
    { href: "/settings", label: "Settings", icon: <Settings className="w-5 h-5" /> },
  ]

  return (
    <aside className="flex flex-col h-full w-64 bg-surface-primary border-r border-border">
      <div className="flex h-14 items-center justify-between px-6 border-b border-border">
        <Link href="/" className="flex items-center space-x-3 text-foreground hover:opacity-80 transition-opacity focus:outline-none focus:ring-2 focus:ring-accent rounded-sm" aria-label="VISOR Home">
          <Shield className="w-6 h-6" />
          <span className="font-semibold text-lg tracking-tight">VISOR</span>
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

      <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-1" aria-label="Main Navigation">
        {navItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center space-x-3 px-3 py-2.5 rounded-sm transition-colors text-sm font-medium focus:outline-none focus:ring-2 focus:ring-accent ${
                isActive 
                  ? "bg-surface-secondary text-foreground" 
                  : "text-text-secondary hover:bg-surface-secondary/50 hover:text-foreground"
              }`}
              aria-current={isActive ? "page" : undefined}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t border-border space-y-1">
        {bottomItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center space-x-3 px-3 py-2.5 rounded-sm transition-colors text-sm font-medium focus:outline-none focus:ring-2 focus:ring-accent ${
                isActive 
                  ? "bg-surface-secondary text-foreground" 
                  : "text-text-secondary hover:bg-surface-secondary/50 hover:text-foreground"
              }`}
              aria-current={isActive ? "page" : undefined}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          )
        })}
      </div>
    </aside>
  )
}
