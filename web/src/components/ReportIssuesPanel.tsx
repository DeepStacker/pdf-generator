import type { UploadResponse } from '../report-types'

/**
 * These are findings about the user's report, not run logs: every row here is
 * something the validator saw in the workbook. Severity drives the colour --
 * rose for a finding that needs a human, amber for one worth a look, emerald
 * for one the validator already corrected on its own.
 */
type Severity = 'error' | 'warn' | 'ok'

const SEVERITY_BADGE: Record<Severity, string> = {
  error: 'badge-rose',
  warn: 'badge-amber',
  ok: 'badge-emerald',
}

const TYPE_CONFIG: Record<string, { label: string; severity: Severity }> = {
  duplicate_packet: { label: 'Duplicate', severity: 'error' },
  duplicate_packet_topup: { label: 'Top-Up Dup', severity: 'warn' },
  closed_empty_packet: { label: 'Closed', severity: 'ok' },
  unexpected_empty_packet: { label: 'Empty Pkt', severity: 'error' },
  topup_resolved: { label: 'Top-Up', severity: 'ok' },
  topup_source_no_packet: { label: 'No Src Pkt', severity: 'warn' },
  topup_source_not_found: { label: 'Src Miss', severity: 'warn' },
  topup_multiple_matches: { label: 'Multi Match', severity: 'warn' },
  topup_no_match: { label: 'No Match', severity: 'error' },
  topup_diff_zeroed: { label: 'Diff Zeroed', severity: 'ok' },
  date_outlier: { label: 'Date', severity: 'warn' },
  tampered: { label: 'Tampered', severity: 'error' },
  magnet_not_ok: { label: 'Magnet', severity: 'error' },
  na_to_zero: { label: 'NA→0', severity: 'ok' },
  fresh_zero_actual_gross: { label: 'Zero Gross', severity: 'error' },
  gross_diff_fixed: { label: 'Gross Diff', severity: 'ok' },
  net_diff_fixed: { label: 'Net Diff', severity: 'ok' },
  net_diff_av_not_zero: { label: 'Net Diff', severity: 'error' },
  spur_pct_mismatch: { label: 'Spur %', severity: 'warn' },
  ornament_diff_fixed: { label: 'Orn Diff', severity: 'ok' },
  ornament_diff_nonzero: { label: 'Orn Diff', severity: 'warn' },
  ornaments_gdr_non_positive: { label: 'Orn Zero', severity: 'error' },
  whitespace_fixed: { label: 'Whitespace', severity: 'ok' },
  weight_outlier: { label: 'Weight', severity: 'error' },
  weight_negative: { label: 'Neg Wt', severity: 'error' },
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
  const severity: Severity = cfg?.severity ?? 'warn'
  return <span className={`section-badge ${SEVERITY_BADGE[severity]} shrink-0`}>{cfg?.label || k}</span>
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
      <div className="grid grid-2 gap-3">
        <div className="stat-card">
          <span className="stat-label">Needs Review</span>
          <span className="stat-value text-rose-400">{highlightedIssues}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Marked Cells</span>
          <span className="stat-value text-amber-400">{uniqueHighlightedCells}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Auto-Fixed</span>
          <span className="stat-value text-emerald-400">{appliedFixes}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Rows Scanned</span>
          <span className="stat-value text-blue-400">{data.rows.length}</span>
        </div>
      </div>

      <div className="card card-flush">
        <div className="px-4 pt-4 pb-1">
          <span className="stat-label">Findings</span>
        </div>
        {nonZeroCategories.length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-slate-500">Nothing flagged — this report is clean.</p>
        ) : (
          <table className="history-table">
            <thead>
              <tr>
                <th>Finding</th>
                <th style={{ textAlign: 'right', width: '4.5rem' }}>Count</th>
              </tr>
            </thead>
            <tbody>
              {nonZeroCategories.map(([key, count]) => (
                <tr key={key}>
                  <td>
                    <div className="flex items-center gap-2 min-w-0">
                      <Badge k={key} />
                      <span className="truncate text-slate-400">{ISSUE_LABELS[key] || key.replace(/_/g, ' ')}</span>
                    </div>
                  </td>
                  <td className="font-mono text-slate-300" style={{ textAlign: 'right' }}>
                    {count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {nonZeroCategories.length > 0 && summary_details && (
        <div className="card card-flush">
          <div className="px-4 pt-4 pb-1">
            <span className="stat-label">Finding Details</span>
          </div>
          <div className="max-h-[420px] overflow-y-auto px-4 pb-4 space-y-3">
            {nonZeroCategories.map(([key]) => {
              const details = summary_details[key]
              if (!details || details.length === 0) return null
              return (
                <div key={key}>
                  <div className="flex items-center gap-2 py-1">
                    <Badge k={key} />
                    <span className="text-xs text-slate-500">{details.length} items</span>
                  </div>
                  <div className="pl-3 ml-1 border-l border-[var(--border-subtle)]">
                    {details.slice(0, 20).map((d: string, i: number) => (
                      <div key={i} className="py-0.5 text-xs text-slate-500 font-mono leading-tight break-words">
                        {d}
                      </div>
                    ))}
                    {details.length > 20 && (
                      <div className="pt-1 text-xs text-slate-600">…and {details.length - 20} more</div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
