"use client";

import * as React from "react"
import { usePathname } from "next/navigation"
import { Sidebar } from "./Sidebar"
import { Topbar } from "./Topbar"
import { Menu, X } from "lucide-react"

export function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  // Close mobile menu on route change
  React.useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  // Landing page doesn't get the dashboard layout
  if (pathname === "/") {
    return <main className="min-h-screen bg-transparent">{children}</main>
  }

  return (
    <div className="flex h-screen overflow-hidden bg-transparent">
      
      {/* Mobile Menu Backdrop */}
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar - Desktop and Mobile */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-auto lg:flex ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <Sidebar onClose={() => setMobileMenuOpen(false)} />
      </div>

      <div className="flex flex-1 flex-col overflow-hidden">
        
        {/* Mobile Header with Hamburger */}
        <div className="flex items-center justify-between border-b border-border bg-surface-primary h-14 px-4 lg:hidden z-10">
          <button 
            onClick={() => setMobileMenuOpen(true)}
            className="text-text-secondary hover:text-foreground focus:outline-none focus:ring-2 focus:ring-accent rounded-sm"
            aria-label="Open navigation menu"
            aria-expanded={mobileMenuOpen}
          >
            <Menu className="w-6 h-6" />
          </button>
          <span className="font-semibold text-foreground tracking-tight">VISOR</span>
          <div className="w-6" /> {/* Balance for center alignment */}
        </div>

        {/* Desktop Topbar */}
        <div className="hidden lg:block">
          <Topbar />
        </div>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden bg-transparent focus:outline-none" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  )
}
