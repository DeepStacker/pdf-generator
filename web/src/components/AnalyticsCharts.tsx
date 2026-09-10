import React from 'react';
import { Activity, Layers, Zap } from 'lucide-react';

interface AnalyticsChartsProps {
  stats: any;
}

// The palette's accent colours, in the order series are handed out. Rose is
// deliberately absent: in this app it only ever means error or destructive.
const SERIES_COLORS = [
  'var(--accent-blue)',
  'var(--accent-emerald)',
  'var(--accent-violet)',
  'var(--accent-amber)',
  'var(--accent-sky)',
];

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({ stats }) => {
  const monthlyTrends = stats?.monthly_trends && stats.monthly_trends.length > 0
    ? stats.monthly_trends
    : [];

  const maxPdfs = Math.max(...(monthlyTrends.map((d: any) => d.pdfs || 0)), 1);
  const totalPaySum = stats?.total_consolidated_pay || 0;
  const auditBreakdown = stats?.audit_breakdown || [];

  const liveRankings = auditBreakdown.map((item: any, idx: number) => {
    const itemPay = item.pay || 0;
    const share = Math.min(100, Math.max(0, Math.round((itemPay / (totalPaySum || 1)) * 100)));
    return {
      name: `${item.type || 'Bank Audit'} (${item.runs} runs)`,
      pay: `₹${Number(itemPay).toLocaleString('en-IN')}`,
      share: share,
      color: SERIES_COLORS[idx % SERIES_COLORS.length],
    };
  });

  // Donut arcs: r is chosen so the circumference is exactly 100, which makes
  // each slice's dash length its percentage share and the offsets trivial.
  let arcCursor = 0;
  const arcs = liveRankings.map((c: any) => {
    const arc = { share: c.share, offset: arcCursor, color: c.color };
    arcCursor += c.share;
    return arc;
  });
  const topShare = liveRankings.length
    ? Math.max(...liveRankings.map((c: any) => c.share))
    : 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Audit type share distribution */}
        <div className="card space-y-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="stat-label">Audit Type Share Distribution</h3>
              <p className="text-2xs text-slate-500 mt-1">
                Relative proportion of consolidated pay grouped by audit type
              </p>
            </div>
            <span className="text-xs font-mono text-slate-400" style={{ whiteSpace: 'nowrap' }}>
              Total: ₹{Number(totalPaySum).toLocaleString('en-IN')}
            </span>
          </div>

          {liveRankings.length === 0 ? (
            <p className="text-sm text-slate-500 italic">No activity logs recorded yet.</p>
          ) : (
            <div className="donut-chart-wrap">
              <div className="donut-svg-container">
                <svg viewBox="0 0 36 36" className="w-full h-full" style={{ transform: 'rotate(-90deg)' }}>
                  <circle
                    cx="18"
                    cy="18"
                    r="15.9155"
                    fill="none"
                    stroke="var(--bg-input)"
                    strokeWidth="4"
                  />
                  {arcs.map((a: any, i: number) => (
                    <circle
                      key={i}
                      cx="18"
                      cy="18"
                      r="15.9155"
                      fill="none"
                      stroke={a.color}
                      strokeWidth="4"
                      strokeDasharray={`${a.share} ${100 - a.share}`}
                      strokeDashoffset={-a.offset}
                    />
                  ))}
                </svg>
                <div className="donut-center">{topShare}%</div>
              </div>

              <div className="flex-1 space-y-3" style={{ minWidth: 0 }}>
                {liveRankings.map((c: any, i: number) => (
                  <div key={i} className="flex items-center gap-3">
                    <span
                      style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        background: c.color,
                        flexShrink: 0,
                      }}
                    />
                    <span className="text-xs text-slate-300 truncate flex-1">{c.name}</span>
                    <span className="text-xs font-mono font-bold">{c.pay}</span>
                    <span className="text-2xs font-mono text-slate-400">{c.share}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Monthly report volume */}
        <div className="card space-y-5">
          <div>
            <h3 className="stat-label">Monthly Report Volume</h3>
            <p className="text-2xs text-slate-500 mt-1">
              Generated worksheet runs per month
            </p>
          </div>

          {monthlyTrends.length === 0 ? (
            <p className="text-sm text-slate-500 italic">No recent history.</p>
          ) : (
            <div className="flex items-end justify-between gap-3" style={{ height: '11rem' }}>
              {monthlyTrends.map((d: any, i: number) => {
                const heightPct = Math.round(((d.pdfs || 0) / maxPdfs) * 100);
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-2" style={{ minWidth: 0 }}>
                    <span className="text-2xs font-mono text-slate-400">{d.pdfs || 0}</span>
                    <div
                      className="w-full flex items-end"
                      style={{
                        height: '8rem',
                        background: 'var(--bg-input)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '2px',
                      }}
                    >
                      <div
                        style={{
                          width: '100%',
                          height: `${Math.max(4, heightPct)}%`,
                          background: 'var(--accent-blue)',
                          borderRadius: '3px',
                        }}
                      />
                    </div>
                    <span className="text-2xs font-semibold text-slate-400 truncate w-full text-center">
                      {d.month}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Throughput facts */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="stat-card flex items-center gap-3">
          <Zap className="w-5 h-5 text-blue-400" />
          <div>
            <span className="stat-label">Avg Parsing Speed</span>
            <span className="text-xs font-mono font-bold mt-1 block">
              {stats?.avg_speed_sec || 0.12} sec / file
            </span>
          </div>
        </div>

        <div className="stat-card flex items-center gap-3">
          <Activity className="w-5 h-5 text-emerald-400" />
          <div>
            <span className="stat-label">System Memory Stream</span>
            <span className="text-xs font-mono font-bold mt-1 block">100% in-RAM</span>
          </div>
        </div>

        <div className="stat-card flex items-center gap-3">
          <Layers className="w-5 h-5 text-violet-400" />
          <div>
            <span className="stat-label">Column Schema Match</span>
            <span className="text-xs font-mono font-bold mt-1 block">62 / 62 columns</span>
          </div>
        </div>
      </div>
    </div>
  );
};
