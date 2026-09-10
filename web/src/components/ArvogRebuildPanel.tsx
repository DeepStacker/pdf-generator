import React, { useState, useRef } from 'react';
import { Upload, X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

/**
 * The return leg of the Arvog round trip, for the browser.
 *
 * The desktop has this as a sub-tab inside the Arvog panel; this is the same
 * thing, driving `/api/arvog/rebuild/upload` instead of the path-based
 * endpoints the desktop uses. One request: the filled audit sheet goes up, the
 * rebuilt master comes back, and the server keeps neither.
 *
 * It renders inside the bank options panel, so it deliberately carries no card
 * of its own — the panel around it is the card.
 */

interface RebuildResult {
  name: string;
  loans: string | null;
  ornaments: string | null;
  columns: string | null;
  auditColumns: string | null;
}

const EXCEL_SUFFIXES = ['.xlsx', '.xlsm', '.xls'];

export const ArvogRebuildPanel: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RebuildResult | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const choose = (picked: File | null) => {
    if (!picked) return;
    if (!EXCEL_SUFFIXES.some((s) => picked.name.toLowerCase().endsWith(s))) {
      setError('Only Excel workbooks can be rebuilt.');
      return;
    }
    setError(null);
    setResult(null);
    setFile(picked);
  };

  const run = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);

    try {
      const body = new FormData();
      body.append('file', file);
      const res = await fetch('/api/arvog/rebuild/upload', { method: 'POST', body });

      if (!res.ok) {
        let detail = `Rebuild failed (HTTP ${res.status})`;
        try {
          const payload = await res.json();
          if (payload?.detail) detail = payload.detail;
        } catch {
          /* not JSON; the status line is all we have */
        }
        setError(detail);
        return;
      }

      const blob = await res.blob();
      const name = `${file.name.replace(/\.(xlsx|xlsm|xls)$/i, '')}_master.xlsx`;

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);

      const auditColumns = res.headers.get('X-Rebuild-Audit-Columns');
      setResult({
        name,
        loans: res.headers.get('X-Rebuild-Loans'),
        ornaments: res.headers.get('X-Rebuild-Ornaments'),
        columns: res.headers.get('X-Rebuild-Columns'),
        auditColumns,
      });
    } catch {
      setError('Could not reach the server.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-400 leading-relaxed">
        Takes the audit sheet back after the branch has filled in the{' '}
        <span className="text-emerald-400 font-semibold">Sumeru</span> block, and folds it into the
        master layout &mdash; one row per loan, each ornament&rsquo;s findings beside the
        branch&rsquo;s own figures. Your upload is removed from the server once the download is sent.
      </p>

      <div>
        <label className="field-label">Filled Audit Sheet</label>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); choose(e.dataTransfer.files?.[0] ?? null); }}
          onClick={() => inputRef.current?.click()}
          className={`drop-zone ${dragging ? 'dragover' : ''}`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx,.xlsm,.xls"
            className="hidden"
            onChange={(e) => choose(e.target.files?.[0] ?? null)}
          />
          <Upload className="drop-zone-icon w-6 h-6" />
          <span className="drop-zone-title">Drop the filled audit sheet here, or click to browse</span>
          <span className="drop-zone-sub">Single workbook · .xlsx, .xlsm, .xls</span>
        </div>
      </div>

      {file && (
        <div className="file-row">
          <span className="text-xs font-semibold text-slate-200 truncate" title={file.name}>{file.name}</span>
          <button
            onClick={(e) => { e.stopPropagation(); setFile(null); setResult(null); }}
            className="btn btn-ghost btn-sm"
            aria-label="Remove selected workbook"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Nothing else reports a failed rebuild, so this must always show. */}
      {error && (
        <div className="validation-box flex items-start gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
          <span className="text-rose-400">{error}</span>
        </div>
      )}

      <button onClick={run} disabled={!file || busy} className="btn btn-success w-full">
        {busy ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Rebuilding…</span>
          </>
        ) : (
          'Rebuild Master Sheet'
        )}
      </button>

      {result && (
        <div className="space-y-3">
          <div className="validation-box flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span className="text-slate-300 truncate">
              Downloaded <span className="font-mono text-slate-200">{result.name}</span>
            </span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[
              ['Loans', result.loans ?? '—'],
              ['Ornaments', result.ornaments ?? '—'],
              ['Columns', result.columns ?? '—'],
            ].map(([label, value]) => (
              <div key={label} className="stat-card">
                <span className="stat-label">{label}</span>
                <span className="stat-value font-mono">{value}</span>
              </div>
            ))}
          </div>
          {result.auditColumns === '0' && (
            <div className="validation-box flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
              <span className="text-amber-400">
                This sheet had no audit block, so those columns came out empty. It may predate the
                block, or be the wrong file.
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
