import React, { useState, useRef } from 'react';
import { Upload, X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

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
      <div className="section-header">
        <div>
          <h2 className="section-title">Flatten PDF</h2>
          <p className="text-xs text-slate-400 mt-1">
            Makes a PDF permanent: form fields, stamps and comments become part of the page and can no longer be edited.
          </p>
        </div>
        <span className="section-badge badge-emerald">Nothing Stored</span>
      </div>

      <div className="card space-y-4 max-w-3xl">
        <p className="text-xs text-slate-400 leading-relaxed">
          Bakes form fields and annotations into the page so the values can no longer be edited
          or cleared, and drops link annotations. Filled values are preserved. Your upload and the
          flattened copy are both removed from the server as soon as the download is sent.
        </p>

        <div>
          <label className="field-label">PDF File</label>
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`drop-zone ${dragging ? 'dragover' : ''}`}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => choose(e.target.files?.[0] ?? null)}
            />
            <Upload className="drop-zone-icon w-7 h-7" />
            <span className="drop-zone-title">Drop a PDF here, or click to browse</span>
            <span className="drop-zone-sub">Single file · .pdf only</span>
          </div>
        </div>

        {file && (
          <div className="file-row">
            <span className="text-xs font-semibold text-slate-200 truncate" title={file.name}>{file.name}</span>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-2xs font-mono text-slate-500">{sizeLabel(file.size)}</span>
              <button
                onClick={(e) => { e.stopPropagation(); setFile(null); setResult(null); }}
                className="btn btn-ghost btn-sm"
                aria-label="Remove selected file"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* The single place a failure shows up, so it stays next to the button. */}
        {error && (
          <div className="validation-box flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <span className="text-rose-400">{error}</span>
          </div>
        )}

        <button onClick={run} disabled={!file || busy} className="btn btn-primary w-full">
          {busy ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Flattening…</span>
            </>
          ) : (
            'Flatten PDF'
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
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                ['Pages', result.pages ?? '—'],
                ['Fields Baked In', result.fields ?? '—'],
                ['Links Removed', result.linksRemoved ?? '—'],
                ['Size', sizeLabel(result.bytes)],
              ].map(([label, value]) => (
                <div key={label} className="stat-card">
                  <span className="stat-label">{label}</span>
                  <span className="stat-value font-mono">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
