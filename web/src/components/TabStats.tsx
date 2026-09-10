import React, { useEffect, useState } from 'react';
import { FileText, Zap, Layers, IndianRupee } from 'lucide-react';
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
      <div className="section-header">
        <div>
          <h2 className="section-title">Insight Analytics</h2>
          <p className="text-sm text-slate-400 mt-1">
            Run volume, consolidated pay and throughput, read live from the audit database.
          </p>
        </div>
        <span className="section-badge badge-emerald">Live Data</span>
      </div>

      {/* Headline metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Total Reports Compiled</span>
            <FileText className="w-4 h-4 text-blue-400" />
          </div>
          <span className="stat-value font-mono">{totalReports}</span>
          <span className="text-2xs font-mono text-slate-400 mt-1 block">Bank Audit + Consolidation</span>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Consolidated Total Pay</span>
            <IndianRupee className="w-4 h-4 text-emerald-400" />
          </div>
          <span className="stat-value font-mono">₹{Number(totalPay).toLocaleString('en-IN')}</span>
          <span className="text-2xs font-mono text-slate-400 mt-1 block">Across every consolidation run</span>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Master Data Assignments</span>
            <Layers className="w-4 h-4 text-violet-400" />
          </div>
          <span className="stat-value font-mono">{Number(mdRows).toLocaleString()}</span>
          <span className="text-2xs font-mono text-slate-400 mt-1 block">Rows on the 62-column schema</span>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Avg Processing Speed</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <span className="stat-value font-mono">{avgSpeed}s</span>
          <span className="text-2xs font-mono text-slate-400 mt-1 block">Per file, multi-threaded</span>
        </div>
      </div>

      <AnalyticsCharts stats={stats} />
    </div>
  );
};
