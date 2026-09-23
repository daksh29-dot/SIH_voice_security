"use client";

import React, { useState, useMemo } from "react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Search, Filter, ArrowDownUp, FileAudio, FolderOpen, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useAppState } from "@/contexts/AppContext";
import { Button } from "@/components/ui/Button";

type SortOption = "newest" | "oldest" | "risk" | "confidence";
type RiskFilter = "All" | "Low" | "Moderate" | "High" | "Critical";
type DateFilter = "All" | "Today" | "Last 7 Days" | "Last 30 Days";
type AuthFilter = "All" | "High" | "Low";

export default function HistoryPage() {
  const router = useRouter();
  const { state, actions } = useAppState();

  const [searchQuery, setSearchQuery] = useState("");
  const [sortOption, setSortOption] = useState<SortOption>("newest");
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("All");
  const [dateFilter, setDateFilter] = useState<DateFilter>("All");
  const [authFilter, setAuthFilter] = useState<AuthFilter>("All");

  const getRiskLabel = (score: number) => {
    if (score >= 0.8) return "Critical";
    if (score >= 0.6) return "High";
    if (score >= 0.3) return "Moderate";
    return "Low";
  };

  const processedRecords = useMemo(() => {
    let result = [...state.analysisHistory];

    if (searchQuery.trim() !== "") {
      const q = searchQuery.toLowerCase();
      result = result.filter(r => r.id.toLowerCase().includes(q) || r.signalContext.source.toLowerCase().includes(q));
    }

    if (riskFilter !== "All") {
      result = result.filter(r => getRiskLabel(r.composite_risk_score) === riskFilter);
    }

    if (dateFilter !== "All") {
      const now = Date.now();
      const msPerDay = 1000 * 60 * 60 * 24;
      result = result.filter(r => {
        const t = new Date(r.timestamp).getTime();
        if (dateFilter === "Today") return (now - t) < msPerDay;
        if (dateFilter === "Last 7 Days") return (now - t) < (msPerDay * 7);
        if (dateFilter === "Last 30 Days") return (now - t) < (msPerDay * 30);
        return true;
      });
    }

    if (authFilter !== "All") {
      result = result.filter(r => {
        const auth = 1 - r.pillars.voice_clone.score;
        if (authFilter === "High") return auth >= 0.5;
        if (authFilter === "Low") return auth < 0.5;
        return true;
      });
    }

    result.sort((a, b) => {
      switch (sortOption) {
        case "newest": return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
        case "oldest": return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
        case "confidence": return a.pillars.voice_clone.score - b.pillars.voice_clone.score; // Lower spoof score = higher confidence
        case "risk": return b.composite_risk_score - a.composite_risk_score;
        default: return 0;
      }
    });

    return result;
  }, [state.analysisHistory, searchQuery, sortOption, riskFilter, dateFilter, authFilter]);

  const getRiskBadgeVariant = (score: number) => {
    if (score >= 0.8) return "danger";
    if (score >= 0.6) return "warning";
    if (score >= 0.3) return "default";
    return "success";
  };

  return (
    <PageWrapper className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between border-b border-border pb-4 gap-4">
        <div>
          <h1 className="text-3xl font-light tracking-tight text-foreground">Analysis Ledger</h1>
          <p className="text-sm font-medium text-text-secondary uppercase tracking-widest mt-1">Cryptographic Audit Trail</p>
        </div>
        
        <div className="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
          <Button variant="ghost" onClick={actions.clearHistory} className="mr-2 text-danger hover:bg-danger/10 hover:text-danger">
            <Trash2 className="w-4 h-4 mr-2" /> Clear
          </Button>

          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-text-secondary" />
            <input 
              type="text" placeholder="Search ID or Source..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-surface-secondary/50 border border-border rounded-md pl-9 pr-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent transition-colors"
            />
          </div>
          
          <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
            <div className="relative flex items-center bg-surface-secondary/50 border border-border rounded-md px-3 py-2">
              <Filter className="w-4 h-4 text-text-secondary mr-2" />
              <select value={riskFilter} onChange={(e) => setRiskFilter(e.target.value as RiskFilter)} className="bg-transparent text-sm text-foreground focus:outline-none cursor-pointer appearance-none pr-4">
                <option value="All">All Risks</option>
                <option value="Critical">Critical Only</option>
                <option value="High">High Only</option>
                <option value="Moderate">Moderate Only</option>
                <option value="Low">Low Only</option>
              </select>
            </div>
            
            <div className="relative flex items-center bg-surface-secondary/50 border border-border rounded-md px-3 py-2">
              <select value={authFilter} onChange={(e) => setAuthFilter(e.target.value as AuthFilter)} className="bg-transparent text-sm text-foreground focus:outline-none cursor-pointer appearance-none pr-4">
                <option value="All">All Auth</option>
                <option value="High">Authentic</option>
                <option value="Low">Synthetic</option>
              </select>
            </div>

            <div className="relative flex items-center bg-surface-secondary/50 border border-border rounded-md px-3 py-2">
              <ArrowDownUp className="w-4 h-4 text-text-secondary mr-2" />
              <select value={sortOption} onChange={(e) => setSortOption(e.target.value as SortOption)} className="bg-transparent text-sm text-foreground focus:outline-none cursor-pointer appearance-none pr-4">
                <option value="newest">Newest</option>
                <option value="oldest">Oldest</option>
                <option value="risk">Highest Risk</option>
                <option value="confidence">Highest Auth</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <Card className="overflow-hidden border-border bg-surface-primary/30 min-h-[400px] flex flex-col">
        {processedRecords.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-text-secondary space-y-4 py-12">
            <div className="w-16 h-16 rounded-full bg-surface-secondary flex items-center justify-center mb-2">
              <FolderOpen className="w-8 h-8 opacity-50" />
            </div>
            <p className="text-base font-medium text-foreground">No records found</p>
            <p className="text-sm text-text-secondary">Run an analysis or adjust your filters.</p>
          </div>
        ) : (
          <div className="w-full overflow-x-auto">
            <table className="w-full text-sm text-left whitespace-nowrap">
              <thead className="text-xs text-text-secondary bg-surface-secondary/50 uppercase tracking-wider border-b border-border">
                <tr>
                  <th className="px-6 py-4 font-medium">Analysis ID</th>
                  <th className="px-6 py-4 font-medium">Timestamp</th>
                  <th className="px-6 py-4 font-medium">Source</th>
                  <th className="px-6 py-4 font-medium">Authenticity</th>
                  <th className="px-6 py-4 font-medium">Risk</th>
                  <th className="px-6 py-4 font-medium text-right">Policy</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {processedRecords.map((record) => {
                  const auth = 1 - record.pillars.voice_clone.score;
                  return (
                    <tr 
                      key={record.id} 
                      onClick={() => router.push('/analyze')} 
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') router.push('/analyze') }}
                      className="hover:bg-surface-secondary/40 transition-colors cursor-pointer group focus:outline-none focus:bg-surface-secondary/60"
                      tabIndex={0}
                      role="link"
                      aria-label={`View analysis for ${record.id}`}
                    >
                      <td className="px-6 py-4 font-mono text-xs text-text-secondary group-hover:text-foreground transition-colors">{record.id}</td>
                      <td className="px-6 py-4 text-text-secondary">{new Date(record.timestamp).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center">
                          <FileAudio className="w-3.5 h-3.5 mr-2 text-text-secondary" />
                          <span className="font-medium text-foreground">{record.signalContext.source}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4"><span className={auth < 0.5 ? "text-danger" : "text-success"}>{(auth * 100).toFixed(1)}%</span></td>
                      <td className="px-6 py-4"><Badge variant={getRiskBadgeVariant(record.composite_risk_score)}>{getRiskLabel(record.composite_risk_score)}</Badge></td>
                      <td className="px-6 py-4 text-right"><Badge variant={record.policy_action === "BLOCK_AND_HOLD" ? "danger" : "success"}>{record.policy_action.replace(/_/g, " ")}</Badge></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </PageWrapper>
  );
}
