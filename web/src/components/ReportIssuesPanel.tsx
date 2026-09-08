import type { UploadResponse } from '../report-types'

const TYPE_CONFIG: Record<string, { label: string; cls: string }> = {
  duplicate_packet: { label: 'Duplicate', cls: 'bg-red-950/60 text-red-300 border-red-800/60' },
  duplicate_packet_topup: { label: 'Top-Up Dup', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  closed_empty_packet: { label: 'Closed', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  unexpected_empty_packet: { label: 'Empty Pkt', cls: 'bg-red-950/60 text-red-300 border-red-800/60' },
  topup_resolved: { label: 'Top-Up', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  topup_source_no_packet: { label: 'No Src Pkt', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  topup_source_not_found: { label: 'Src Miss', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  topup_multiple_matches: { label: 'Multi Match', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  topup_no_match: { label: 'No Match', cls: 'bg-red-950/60 text-red-300 border-red-800/60' },
  topup_diff_zeroed: { label: 'Diff Zeroed', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  date_outlier: { label: 'Date', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  tampered: { label: 'Tampered', cls: 'bg-red-950/60 text-red-300 border-red-800/60' },
  magnet_not_ok: { label: 'Magnet', cls: 'bg-red-950/60 text-red-300 border-red-800/60' },
  na_to_zero: { label: 'NA→0', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  fresh_zero_actual_gross: { label: 'Zero Gross', cls: 'bg-red-950/60 text-red-300 border-red-800/60' },
  gross_diff_fixed: { label: 'Gross Diff', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  net_diff_fixed: { label: 'Net Diff', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  net_diff_av_not_zero: { label: 'Net Diff', cls: 'bg-red-950/60 text-red-300 border-red-800/60' },
  spur_pct_mismatch: { label: 'Spur %', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  ornament_diff_fixed: { label: 'Orn Diff', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  ornament_diff_nonzero: { label: 'Orn Diff', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  ornaments_gdr_non_positive: { label: 'Orn Zero', cls: 'bg-red-950/60 text-red-300 border-red-800/60' },
  whitespace_fixed: { label: 'Whitespace', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  weight_outlier: { label: 'Weight', cls: 'bg-red-950/60 text-red-300 border-red-800/60' },
  weight_negative: { label: 'Neg Wt', cls: 'bg-red-950/60 text-red-300 border-red-800/60' },
}

const ISSUE_LABELS: Record<string, string> = {
  duplicate_packet: 'Unexpected Duplicate Packets',
  duplicate_packet_topup: 'Top-Up Duplicate Packets',
  closed_empty_packet: 'Closed Accounts (Empty Packet)',
  unexpected_empty_packet: 'Unexpected Empty Packets',
  topup_resolved: 'Top-Up Accounts Resolved',
  topup_source_no_packet: 'Top-Up Source Has No Packet',
  topup_source_not_found: 'Top-Up Source Not Found',
  topup_multiple_matches: 'Top-Up Multiple Name Matches',
  topup_no_match: 'Top-Up No Match Found',
  topup_diff_zeroed: 'Top-Up Diff Zeroed',
  date_outlier: 'Date Outliers',
  tampered: 'Tampered Packets',
  magnet_not_ok: 'Magnet Test Failures',
  na_to_zero: 'NA Converted to 0',
  fresh_zero_actual_gross: 'Fresh Zero Actual Gross',
  gross_diff_fixed: 'Gross Diff Auto-Fixed',
  net_diff_av_not_zero: 'Net Diff Not Zero (AV)',
  net_diff_fixed: 'Net Diff Auto-Fixed',
  spur_pct_mismatch: 'Spurious % Mismatch',
  ornament_diff_fixed: 'Ornament Diff Auto-Fixed',
  ornament_diff_nonzero: 'Ornament Diff Not Zero',
  ornaments_gdr_non_positive: 'Ornaments GDR Zero/Negative',
  whitespace_fixed: 'Whitespace Normalized',
  weight_outlier: 'Weight Outliers',
  weight_negative: 'Negative Weights',
}

function Badge({ k }: { k: string }) {
  const cfg = TYPE_CONFIG[k]
  return (
    <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded border font-semibold ${cfg?.cls || 'bg-slate-800 text-slate-300 border-slate-700'}`}>
      {cfg?.label || k}
    </span>
  )
}

export function ReportIssuesPanel({ data }: { data: UploadResponse }) {
  const { summary, summary_details, highlights, total_issues } = data
  const highlightCounts: Record<string, number> = {}
  for (const color of Object.values(highlights)) {
    highlightCounts[color] = (highlightCounts[color] || 0) + 1
  }

  const nonZeroCategories = Object.entries(summary)
    .filter(([, count]) => count > 0)
    .sort(([, a], [, b]) => b - a)

  const uniqueHighlightedCells = Object.keys(highlights).length
  const appliedFixes = ['whitespace_fixed', 'na_to_zero', 'gross_diff_fixed', 'net_diff_fixed', 'ornament_diff_fixed', 'ornament_diff_nonzero', 'topup_resolved', 'topup_diff_zeroed'].reduce(
    (sum, k) => sum + (summary[k] || 0),
    0,
  )
  const highlightedIssues = total_issues - appliedFixes

  return (
    <div className="space-y-4">
      <div className="glass-panel p-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3">Issues Summary</h3>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className="text-center p-3 rounded-lg bg-red-950/30 border border-red-900/40">
            <div className="text-2xl font-bold text-red-400">{highlightedIssues}</div>
            <div className="text-[11px] text-slate-500">Needs Review</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-amber-950/30 border border-amber-900/40">
            <div className="text-2xl font-bold text-amber-400">{uniqueHighlightedCells}</div>
            <div className="text-[11px] text-slate-500">Highlighted Cells</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-emerald-950/30 border border-emerald-900/40">
            <div className="text-2xl font-bold text-emerald-400">{appliedFixes}</div>
            <div className="text-[11px] text-slate-500">Auto-Fixes Applied</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-blue-950/30 border border-blue-900/40">
            <div className="text-2xl font-bold text-blue-400">{data.rows.length}</div>
            <div className="text-[11px] text-slate-500">Total Rows</div>
          </div>
        </div>

        <div className="border-t border-slate-800 pt-3 space-y-1.5">
          {nonZeroCategories.length === 0 && (
            <p className="text-sm text-slate-500 text-center py-4">No issues found</p>
          )}
          {nonZeroCategories.map(([key, count]) => (
            <div key={key} className="flex items-center justify-between py-1">
              <div className="flex items-center gap-2 min-w-0">
                <Badge k={key} />
                <span className="text-xs truncate text-slate-400">{ISSUE_LABELS[key] || key.replace(/_/g, ' ')}</span>
              </div>
              <span className="text-xs font-mono font-medium tabular-nums text-slate-300 ml-2">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {nonZeroCategories.length > 0 && summary_details && (
        <div className="glass-panel">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 px-4 pt-4">Issue Details</h3>
          <div className="max-h-[420px] overflow-y-auto custom-scrollbar">
            <div className="px-4 pb-4 space-y-1">
              {nonZeroCategories.map(([key]) => {
                const details = summary_details[key]
                if (!details || details.length === 0) return null
                return (
                  <div key={key}>
                    <div className="flex items-center gap-1.5 py-0.5">
                      <Badge k={key} />
                      <span className="text-[11px] text-slate-500">{details.length} items</span>
                    </div>
                    <div className="pl-2 border-l-2 border-slate-700 ml-1 my-1">
                      {details.slice(0, 20).map((d: string, i: number) => (
                        <div key={i} className="text-[11px] py-0.5 text-slate-500 font-mono leading-tight break-words">
                          {d}
                        </div>
                      ))}
                      {details.length > 20 && (
                        <div className="text-[10px] text-slate-600 pt-0.5">...and {details.length - 20} more</div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}