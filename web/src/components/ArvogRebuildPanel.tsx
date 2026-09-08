import React, { useState, useRef } from 'react';
import { Upload, X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

/**
 * The return leg of the Arvog round trip, for the browser.
 *
 * The desktop has this as a sub-tab inside the Arvog panel; this is the same
 * thing, driving `/api/arvog/rebuild/upload` instead of the path-based
 * endpoints the desktop uses. One request: the filled audit sheet goes up, the
 * rebuilt master comes back, and the server keeps neither.
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

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); choose(e.dataTransfer.files?.[0] ?? null); }}
        onClick={() => inputRef.current?.click()}
        className={`rounded-lg border border-dashed p-6 text-center cursor-pointer transition-colors ${
          dragging ? 'border-emerald-500 bg-emerald-500/5' : 'border-slate-700 hover:border-emerald-500/50'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xlsm,.xls"
          className="hidden"
          onChange={(e) => choose(e.target.files?.[0] ?? null)}
        />
        <Upload className="w-6 h-6 mx-auto text-slate-500 mb-2" />
        <p className="text-sm font-semibold text-slate-300">Drop the filled audit sheet here, or click to browse</p>
        <p className="text-[11px] text-slate-500 mt-1">Single workbook · .xlsx, .xlsm, .xls</p>
      </div>

      {file && (
        <div className="flex items-center justify-between bg-[#0b0f19] border border-slate-800 rounded-lg px-3 py-2">
          <span className="text-xs text-slate-300 truncate">{file.name}</span>
          <button onClick={() => { setFile(null); setResult(null); }} className="text-slate-500 hover:text-red-400 shrink-0">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
          <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
          <span className="text-xs text-red-300">{error}</span>
        </div>
      )}

      <button
        onClick={run}
        disabled={!file || busy}
        className="w-full py-2.5 rounded-lg text-sm font-bold bg-emerald-500 hover:bg-emerald-400 disabled:bg-slate-700 disabled:text-slate-500 text-white transition-colors flex items-center justify-center gap-2"
      >
        {busy ? (<><Loader2 className="w-4 h-4 animate-spin" /> Rebuilding…</>) : 'Rebuild Master Sheet'}
      </button>

      {result && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-emerald-400">
            <CheckCircle2 className="w-4 h-4" />
            <span className="text-xs font-semibold">Downloaded {result.name}</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {[
              ['Loans', result.loans ?? '—'],
              ['Ornaments', result.ornaments ?? '—'],
              ['Columns', result.columns ?? '—'],
            ].map(([label, value]) => (
              <div key={label} className="bg-[#0b0f19] border border-slate-800 rounded-lg px-3 py-2">
                <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">{label}</span>
                <span className="block text-sm font-bold text-slate-200 mt-0.5">{value}</span>
              </div>
            ))}
          </div>
          {result.auditColumns === '0' && (
            <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2">
              <AlertCircle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
              <span className="text-xs text-amber-300">
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
