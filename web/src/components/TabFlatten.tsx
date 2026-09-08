import React, { useState, useRef } from 'react';
import { FileStack, Upload, X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

/**
 * Flatten PDF.
 *
 * The desktop app has had this tab since the feature shipped and the server has
 * had `/api/flatten/upload` for just as long, but nothing in the browser ever
 * called it. This is that missing half.
 *
 * One request does the whole job: the file goes up, the flattened PDF comes
 * straight back, and the server keeps neither. Nothing is stored to poll.
 */

interface FlattenResult {
  name: string;
  pages: string | null;
  fields: string | null;
  linksRemoved: string | null;
  bytes: number;
}

export const TabFlatten: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FlattenResult | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const choose = (picked: File | null) => {
    if (!picked) return;
    if (!picked.name.toLowerCase().endsWith('.pdf')) {
      setError('Only .pdf files can be flattened.');
      return;
    }
    setError(null);
    setResult(null);
    setFile(picked);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    choose(e.dataTransfer.files?.[0] ?? null);
  };

  const run = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);

    try {
      const body = new FormData();
      body.append('file', file);
      const res = await fetch('/api/flatten/upload', { method: 'POST', body });

      if (!res.ok) {
        let detail = `Flatten failed (HTTP ${res.status})`;
        try {
          const payload = await res.json();
          if (payload?.detail) detail = payload.detail;
        } catch {
          /* the body was not JSON; the status line is all we have */
        }
        setError(detail);
        return;
      }

      const blob = await res.blob();
      const name = `${file.name.replace(/\.pdf$/i, '')}_flattened.pdf`;

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);

      setResult({
        name,
        pages: res.headers.get('X-Flatten-Pages'),
        fields: res.headers.get('X-Flatten-Fields'),
        linksRemoved: res.headers.get('X-Flatten-Links-Removed'),
        bytes: blob.size,
      });
    } catch {
      setError('Could not reach the server.');
    } finally {
      setBusy(false);
    }
  };

  const sizeLabel = (bytes: number) =>
    bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold tracking-tight flex items-center gap-2">
          <FileStack className="w-5 h-5 text-emerald-400" />
          Flatten PDF
        </h2>
        <span className="px-2.5 py-1 text-[10px] font-bold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          NOTHING STORED
        </span>
      </div>

      <div className="bg-[#0f1523] border border-slate-800/80 rounded-xl p-6 space-y-4 max-w-3xl">
        <p className="text-xs text-slate-400 leading-relaxed">
          Bakes form fields and annotations into the page so the values can no longer be edited
          or cleared, and drops link annotations. Filled values are preserved. Your upload and the
          flattened copy are both removed from the server as soon as the download is sent.
        </p>

        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`rounded-lg border border-dashed p-8 text-center cursor-pointer transition-colors ${
            dragging ? 'border-emerald-500 bg-emerald-500/5' : 'border-slate-700 hover:border-emerald-500/50'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => choose(e.target.files?.[0] ?? null)}
          />
          <Upload className="w-7 h-7 mx-auto text-slate-500 mb-2" />
          <p className="text-sm font-semibold text-slate-300">Drop a PDF here, or click to browse</p>
          <p className="text-[11px] text-slate-500 mt-1">Single file · .pdf only</p>
        </div>

        {file && (
          <div className="flex items-center justify-between bg-[#0b0f19] border border-slate-800 rounded-lg px-3 py-2">
            <span className="text-xs text-slate-300 truncate">{file.name}</span>
            <div className="flex items-center gap-3 shrink-0">
              <span className="text-[11px] text-slate-500">{sizeLabel(file.size)}</span>
              <button onClick={() => { setFile(null); setResult(null); }} className="text-slate-500 hover:text-red-400">
                <X className="w-4 h-4" />
              </button>
            </div>
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
          {busy ? (<><Loader2 className="w-4 h-4 animate-spin" /> Flattening…</>) : 'Flatten PDF'}
        </button>

        {result && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              <span className="text-xs font-semibold">Downloaded {result.name}</span>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {[
                ['Pages', result.pages ?? '—'],
                ['Fields baked in', result.fields ?? '—'],
                ['Links removed', result.linksRemoved ?? '—'],
                ['Size', sizeLabel(result.bytes)],
              ].map(([label, value]) => (
                <div key={label} className="bg-[#0b0f19] border border-slate-800 rounded-lg px-3 py-2">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">{label}</span>
                  <span className="block text-sm font-bold text-slate-200 mt-0.5">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
