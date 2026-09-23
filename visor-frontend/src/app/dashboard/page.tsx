"use client";

import React from "react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Activity, ShieldAlert, Zap, Server, ChevronRight } from "lucide-react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { useRouter } from "next/navigation";
import { useAppState } from "@/contexts/AppContext";

export default function DashboardPage() {
  const router = useRouter();
  const { state } = useAppState();

  const analysesToday = state.analysisHistory.filter(h => {
    const diff = Date.now() - new Date(h.timestamp).getTime();
    return diff < 1000 * 60 * 60 * 24;
  });

  const spoofSignals = state.analysisHistory.filter(h => h.pillars.voice_clone.score > 0.6).length;
  const highRiskSessions = state.analysisHistory.filter(h => h.composite_risk_score > 0.6).length;

  // Generate Activity Line Chart Data from real history (Grouped by hour)
  const lineChartData = React.useMemo(() => {
    const hours = new Array(24).fill(0);
    analysesToday.forEach(h => {
      const hour = new Date(h.timestamp).getHours();
      hours[hour]++;
    });
    // Return last 12 hours for compact view
    const currentHour = new Date().getHours();
    const data = [];
    for (let i = 11; i >= 0; i--) {
      let h = currentHour - i;
      if (h < 0) h += 24;
      data.push({
        time: `${h.toString().padStart(2, '0')}:00`,
        count: hours[h]
      });
    }
    return data;
  }, [analysesToday]);

  // Generate Authenticity Distribution Data (Bucketed)
  const authenticityData = React.useMemo(() => {
    const buckets = { "0-20%": 0, "20-40%": 0, "40-60%": 0, "60-80%": 0, "80-100%": 0 };
    state.analysisHistory.forEach(h => {
      const auth = (1 - h.pillars.voice_clone.score) * 100;
      if (auth <= 20) buckets["0-20%"]++;
      else if (auth <= 40) buckets["20-40%"]++;
      else if (auth <= 60) buckets["40-60%"]++;
      else if (auth <= 80) buckets["60-80%"]++;
      else buckets["80-100%"]++;
    });
    return Object.entries(buckets).map(([name, count]) => ({ name, count }));
  }, [state.analysisHistory]);

  const riskData = [
    { category: "Clean", value: state.analysisHistory.filter(h => h.composite_risk_score < 0.3).length },
    { category: "Moderate", value: state.analysisHistory.filter(h => h.composite_risk_score >= 0.3 && h.composite_risk_score < 0.6).length },
    { category: "High", value: state.analysisHistory.filter(h => h.composite_risk_score >= 0.6 && h.composite_risk_score < 0.8).length },
    { category: "Critical", value: state.analysisHistory.filter(h => h.composite_risk_score >= 0.8).length },
  ];

  const getRiskColor = (risk: string) => {
    switch(risk) {
      case "Critical": return "var(--color-danger)";
      case "High": return "var(--color-warning)";
      case "Moderate": return "var(--color-accent)";
      default: return "var(--color-text-secondary)";
    }
  };

  const getRiskLabel = (score: number) => {
    if (score >= 0.8) return "Critical";
    if (score >= 0.6) return "High";
    if (score >= 0.3) return "Moderate";
    return "Low";
  };

  return (
    <PageWrapper className="p-6 max-w-7xl mx-auto space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-border pb-4 gap-4">
        <div>
          <h1 className="text-3xl font-light tracking-tight">VISOR</h1>
          <p className="text-sm font-medium text-text-secondary uppercase tracking-widest mt-1">Security Overview</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-surface-primary/50">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-xs text-text-secondary uppercase tracking-wider">Analyses Today</CardTitle>
            <Activity className="w-4 h-4 text-text-secondary" />
          </CardHeader>
          <CardContent><div className="text-3xl font-light">{analysesToday.length}</div></CardContent>
        </Card>
        <Card className="bg-surface-primary/50">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-xs text-text-secondary uppercase tracking-wider">Spoof Signals</CardTitle>
            <ShieldAlert className="w-4 h-4 text-warning" />
          </CardHeader>
          <CardContent><div className="text-3xl font-light text-warning">{spoofSignals}</div></CardContent>
        </Card>
        <Card className="bg-surface-primary/50">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-xs text-text-secondary uppercase tracking-wider">High Risk</CardTitle>
            <Zap className="w-4 h-4 text-danger" />
          </CardHeader>
          <CardContent><div className="text-3xl font-light text-danger">{highRiskSessions}</div></CardContent>
        </Card>
        <Card className="bg-surface-primary/50 border-accent/20">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-xs text-text-secondary uppercase tracking-wider">System Status</CardTitle>
            <Server className="w-4 h-4 text-success" />
          </CardHeader>
          <CardContent><div className="text-2xl font-light">{state.systemStatus.status}</div></CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-lg font-medium">Activity Volume (12h)</h2>
          <Card className="p-4 h-64 bg-surface-primary/30">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={lineChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="time" stroke="var(--color-text-secondary)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--color-text-secondary)" fontSize={12} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--color-surface-primary)', border: '1px solid var(--color-border)', borderRadius: '4px' }}
                  itemStyle={{ color: 'var(--color-foreground)' }}
                />
                <Line type="monotone" dataKey="count" stroke="var(--color-accent)" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: 'var(--color-accent)' }} />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          <h2 className="text-lg font-medium pt-2">Recent Analysis Activity</h2>
          <Card className="overflow-hidden">
            <div className="w-full overflow-x-auto">
              <table className="w-full text-sm text-left whitespace-nowrap">
                <thead className="text-xs text-text-secondary bg-surface-secondary/50 uppercase tracking-wider border-b border-border">
                  <tr>
                    <th className="px-6 py-4 font-medium">Time</th>
                    <th className="px-6 py-4 font-medium">Source</th>
                    <th className="px-6 py-4 font-medium">Authenticity</th>
                    <th className="px-6 py-4 font-medium">Risk</th>
                    <th className="px-6 py-4 font-medium text-right">Policy</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {state.analysisHistory.slice(0, 8).map((row) => (
                    <tr 
                      key={row.id} 
                      onClick={() => router.push('/history')} 
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') router.push('/history') }}
                      className="hover:bg-surface-secondary/30 transition-colors cursor-pointer group focus:outline-none focus:bg-surface-secondary/50"
                      tabIndex={0}
                      role="link"
                      aria-label={`View history for ${row.signalContext.source}`}
                    >
                      <td className="px-6 py-4 text-text-secondary">{new Date(row.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
                      <td className="px-6 py-4 font-medium">{row.signalContext.source}</td>
                      <td className="px-6 py-4">
                        <span className={row.pillars.voice_clone.score > 0.5 ? "text-danger" : "text-success"}>
                          {((1 - row.pillars.voice_clone.score) * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <Badge variant={row.composite_risk_score > 0.6 ? "danger" : "default"}>{getRiskLabel(row.composite_risk_score)}</Badge>
                      </td>
                      <td className="px-6 py-4 text-right flex items-center justify-end space-x-2">
                        <Badge variant={row.policy_action === "BLOCK_AND_HOLD" ? "danger" : "success"}>{row.policy_action.replace(/_/g, " ")}</Badge>
                        <ChevronRight className="w-4 h-4 text-transparent group-hover:text-text-secondary transition-colors" />
                      </td>
                    </tr>
                  ))}
                  {state.analysisHistory.length === 0 && (
                    <tr><td colSpan={5} className="text-center py-8 text-text-secondary">No recent activity. Try analyzing audio.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <div className="space-y-8">
          <div className="space-y-6">
            <h2 className="text-lg font-medium">Threat Overview</h2>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-xs text-text-secondary uppercase">Risk Distribution</CardTitle></CardHeader>
              <CardContent className="h-40">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={riskData} layout="vertical" margin={{ left: 10, right: 10 }}>
                    <XAxis type="number" hide />
                    <YAxis dataKey="category" type="category" axisLine={false} tickLine={false} tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }} width={70} />
                    <Tooltip cursor={{ fill: 'var(--color-surface-secondary)' }} contentStyle={{ backgroundColor: 'var(--color-surface-primary)', border: '1px solid var(--color-border)', borderRadius: '8px' }} />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={12}>
                      {riskData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={getRiskColor(entry.category)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-xs text-text-secondary uppercase">Authenticity Spread</CardTitle></CardHeader>
              <CardContent className="h-40">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={authenticityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <XAxis dataKey="name" stroke="var(--color-text-secondary)" fontSize={10} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--color-text-secondary)" fontSize={10} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip cursor={{ fill: 'var(--color-surface-secondary)' }} contentStyle={{ backgroundColor: 'var(--color-surface-primary)', border: '1px solid var(--color-border)', borderRadius: '4px' }} />
                    <Bar dataKey="count" fill="var(--color-success)" radius={[2, 2, 0, 0]} barSize={16} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <h2 className="text-lg font-medium">Model Status</h2>
            <Card className="bg-surface-primary/30">
              <CardContent className="p-5 space-y-4 text-sm">
                <div className="flex justify-between items-center border-b border-border/50 pb-3"><span className="text-text-secondary">Engine</span><span className="font-medium">{state.modelStatus.engine}</span></div>
                <div className="flex justify-between items-center border-b border-border/50 pb-3"><span className="text-text-secondary">Inference</span><span className="font-medium">{state.modelStatus.inference}</span></div>
                <div className="flex justify-between items-center border-b border-border/50 pb-3"><span className="text-text-secondary">Backend</span><span className="font-medium text-accent">{state.modelStatus.backend}</span></div>
                <div className="flex justify-between items-center"><span className="text-text-secondary">Live Latency</span><span className="font-mono flex items-center"><div className="w-1.5 h-1.5 rounded-full bg-success mr-2" />{state.systemStatus.latencyMs} ms</span></div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
