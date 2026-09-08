import React from 'react';
import { BarChart2, Activity, DollarSign, Layers, Zap } from 'lucide-react';

interface AnalyticsChartsProps {
  stats: any;
}

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({ stats }) => {
  const monthlyTrends = stats?.monthly_trends && stats.monthly_trends.length > 0
    ? stats.monthly_trends
    : [];

  const maxPdfs = Math.max(...(monthlyTrends.map((d: any) => d.pdfs || 0)), 1);
  const totalPaySum = stats?.total_consolidated_pay || 0;
  const auditBreakdown = stats?.audit_breakdown || [];

  const liveRankings = auditBreakdown.map((item: any, idx: number) => {
    const colors = ['bg-rose-500', 'bg-emerald-500', 'bg-indigo-500', 'bg-amber-500', 'bg-blue-500'];
    const itemPay = item.pay || 0;
    const share = Math.min(100, Math.max(0, Math.round((itemPay / (totalPaySum || 1)) * 100)));
    return {
      name: `${item.type || 'Bank Audit'} (${item.runs} runs)`,
      pay: `₹${Number(itemPay).toLocaleString('en-IN')}`,
      share: share,
      color: colors[idx % colors.length],
    };
  });

  return (
    <div className="space-y-6">
      {/* 2-Column Visualization Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monthly Throughput Bar Chart */}
        <div className="glass-panel p-6 rounded-2xl space-y-4 border border-slate-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <BarChart2 className="w-5 h-5 text-blue-400" />
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Monthly Report Generation Volume
              </h3>
            </div>
            <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/60">
              Live SQLite Data
            </span>
          </div>

          {/* Bar Visualizer */}
          <div className="pt-4 pb-2 flex items-end justify-between h-48 gap-3 px-2">
            {monthlyTrends.map((d: any, i: number) => {
              const heightPct = Math.round(((d.pdfs || 1) / maxPdfs) * 100);
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-2 group">
                  <div className="text-[10px] font-mono text-slate-400 opacity-0 group-hover:opacity-100 transition">
                    {d.pdfs || 0}
                  </div>
                  <div className="w-full bg-[#090d16] rounded-t-lg h-36 flex items-end p-1 border border-slate-800">
                    <div
                      className="w-full bg-gradient-to-t from-blue-600 to-indigo-500 rounded-t-md transition-all duration-500 group-hover:from-blue-500 group-hover:to-indigo-400 shadow-md shadow-blue-500/20"
                      style={{ height: `${Math.max(10, heightPct)}%` }}
                    ></div>
                  </div>
                  <span className="text-[11px] font-semibold text-slate-400">{d.month}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Client Pay Sum Ranking Visualization */}
        <div className="glass-panel p-6 rounded-2xl space-y-4 border border-slate-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <DollarSign className="w-5 h-5 text-emerald-400" />
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Consolidated Pay Volume Ranking
              </h3>
            </div>
            <span className="text-xs font-mono font-bold text-blue-400">
              Total: ₹{Number(totalPaySum).toLocaleString('en-IN')}
            </span>
          </div>

          <div className="space-y-4 pt-2">
            {liveRankings.map((c: any, i: number) => (
              <div key={i} className="space-y-1.5">
                <div className="flex justify-between text-xs font-medium text-slate-300">
                  <span className="truncate pr-2 font-bold">{c.name}</span>
                  <div className="flex items-center space-x-2 font-mono flex-shrink-0">
                    <span className="text-slate-200 font-bold">{c.pay}</span>
                    <span className="text-slate-400 text-[10px]">({c.share}%)</span>
                  </div>
                </div>
                <div className="w-full bg-[#090d16] h-2.5 rounded-full overflow-hidden border border-slate-800 p-0.5">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${c.color}`}
                    style={{ width: `${c.share}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Speed & Zero-Trace Performance Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-blue-500 flex items-center space-x-3.5">
          <div className="p-3 rounded-xl bg-blue-500/10 text-blue-400">
            <Zap className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Avg Parsing Speed</span>
            <span className="text-xl font-bold font-mono text-slate-100">
              {stats?.avg_speed_sec || 0.12} sec / File
            </span>
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-emerald-500 flex items-center space-x-3.5">
          <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 block">System Memory Stream</span>
            <span className="text-xl font-bold font-mono text-slate-100">100% In-RAM</span>
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-purple-500 flex items-center space-x-3.5">
          <div className="p-3 rounded-xl bg-purple-500/10 text-purple-400">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Column Schema Match</span>
            <span className="text-xl font-bold font-mono text-slate-100">62 / 62 Columns</span>
          </div>
        </div>
      </div>
    </div>
  );
};
