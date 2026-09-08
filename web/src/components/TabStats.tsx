import React, { useEffect, useState } from 'react';
import { BarChart3, FileText, CheckCircle2, Building2, Zap, Layers, TrendingUp, Users, ShieldCheck, DollarSign } from 'lucide-react';
import { AnalyticsCharts } from './AnalyticsCharts';

export const TabStats: React.FC = () => {
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    fetch('/api/stats')
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch(() => setStats(null));
  }, []);

  const totalReports = stats?.total_reports || stats?.total_pdfs || 0;
  const totalPay = stats?.total_consolidated_pay || 0;
  const mdRows = stats?.md_rows || 0;
  const avgSpeed = stats?.avg_speed_sec || 0;

  return (
    <div className="space-y-6">
      {/* Title Header */}
      <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-100 tracking-tight flex items-center space-x-2">
          <BarChart3 className="w-5 h-5 text-blue-400" />
          <span>Analytics & Metrics</span>
        </h2>
        <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/60">
          Connected to SQLite DB
        </span>
      </div>

      {/* Top Comprehensive Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-5 rounded-2xl space-y-1.5 border-l-4 border-l-blue-500 shadow-md">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Total Reports Compiled</span>
            <FileText className="w-4 h-4 text-blue-400" />
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">
            {totalReports}
          </p>
          <span className="text-[10px] text-slate-400 font-mono">Bank Audit + Consolidation</span>
        </div>

        <div className="glass-panel p-5 rounded-2xl space-y-1.5 border-l-4 border-l-emerald-500 shadow-md">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Consolidated Total Pay</span>
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">
            ₹{Number(totalPay).toLocaleString('en-IN')}
          </p>
          <span className="text-[10px] text-emerald-400 font-mono">Real-Time SQLite Total</span>
        </div>

        <div className="glass-panel p-5 rounded-2xl space-y-1.5 border-l-4 border-l-purple-500 shadow-md">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Master Data Assignments</span>
            <Layers className="w-4 h-4 text-purple-400" />
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">
            {Number(mdRows).toLocaleString()} Rows
          </p>
          <span className="text-[10px] text-slate-400 font-mono">62-Column Schema</span>
        </div>

        <div className="glass-panel p-5 rounded-2xl space-y-1.5 border-l-4 border-l-amber-500 shadow-md">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Avg Processing Speed</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">
            {avgSpeed}s / File
          </p>
          <span className="text-[10px] text-amber-400 font-mono">High Speed Multi-Thread</span>
        </div>
      </div>

      {/* Visual Analytics Charts Component */}
      <AnalyticsCharts stats={stats} />
    </div>
  );
};
