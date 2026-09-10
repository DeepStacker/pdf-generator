import React, { useState, useEffect, useRef } from 'react';
import { UploadCloud, FileSpreadsheet, X, Play, CheckCircle2, AlertTriangle, RefreshCw, Download, Layers, TrendingUp, Users, Search, Eye, Check, Loader2, Trash2 } from 'lucide-react';
import { DocumentViewerModal } from './DocumentViewerModal';

export interface FileSummary {
  filename: string;
  client: string;
  pt_rows: number;
  md_rows: number;
  status: string;
}

export interface SummaryData {
  total_pay: number;
  pt_rows: number;
  md_rows: number;
  pt_clients: string[];
  md_clients: string[];
  file_summaries: FileSummary[];
  flags: string[];
  output_path?: string;
}

export interface StagedItem {
  id: string;
  file: File;
  serverPath?: string;
  clientName?: string;
  status: 'pending' | 'uploading' | 'ready' | 'error';
}

export interface TabConsolidationProps {
  onConsolidateRun: (filePaths: string[]) => Promise<any>;
  onUploadFiles: (files: File[]) => Promise<string[]>;
}

/* Progress ring geometry: .progress-ring-wrap is 72x72 and already rotates
   the svg -90deg, so the arc starts at twelve o'clock. */
const RING_R = 30;
const RING_C = 2 * Math.PI * RING_R;

export const TabConsolidation: React.FC<TabConsolidationProps> = ({ onConsolidateRun, onUploadFiles }) => {
  const [stagedItems, setStagedItems] = useState<StagedItem[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [outputPath, setOutputPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchLog, setSearchLog] = useState('');
  const [consolidationPct, setConsolidationPct] = useState<number>(0);
  const [progressText, setProgressText] = useState<string>('');
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Preview Modal state
  const [previewModal, setPreviewModal] = useState<{ path: string; name: string } | null>(null);

  // Add files to queue and trigger one-time background pre-upload & pre-parsing
  const addFilesToQueue = async (files: File[]) => {
    const newItems: StagedItem[] = files.map((file) => ({
      id: `${file.name}-${file.size}-${Math.random()}`,
      file,
      status: 'pending',
    }));

    setStagedItems((prev) => [...prev, ...newItems]);
    setError(null);

    // Pre-upload and pre-parse each file exactly once
    for (const item of newItems) {
      setStagedItems((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, status: 'uploading' } : i))
      );
      try {
        const paths = await onUploadFiles([item.file]);
        if (paths && paths.length > 0) {
          const serverPath = paths[0];
          const res = await fetch('/api/consolidate/preparse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filepath: serverPath }),
          });
          const preparseData = await res.json();
          setStagedItems((prev) =>
            prev.map((i) =>
              i.id === item.id
                ? {
                    ...i,
                    serverPath,
                    clientName: preparseData?.client || 'Auto-Detected',
                    status: preparseData?.success ? 'ready' : 'error',
                  }
                : i
            )
          );
        } else {
          setStagedItems((prev) =>
            prev.map((i) => (i.id === item.id ? { ...i, status: 'error' } : i))
          );
        }
      } catch {
        setStagedItems((prev) =>
          prev.map((i) => (i.id === item.id ? { ...i, status: 'error' } : i))
        );
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFilesToQueue(Array.from(e.target.files));
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFilesToQueue(Array.from(e.dataTransfer.files));
    }
  };

  const handleRemoveItem = (id: string) => {
    setStagedItems((prev) => prev.filter((i) => i.id !== id));
  };

  const handleClear = () => {
    setStagedItems([]);
    setError(null);
  };

  const handleReset = () => {
    setStagedItems([]);
    setSummary(null);
    setOutputPath(null);
    setError(null);
  };

  // Held so it can be stopped. It used to be a local nothing kept, so the
  // 250 ms poll outlived every failed run.
  const pollRef = useRef<number | null>(null);

  const stopPolling = () => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  useEffect(() => stopPolling, []);

  const pollConsolidationProgress = () => {
    stopPolling();
    const interval = window.setInterval(async () => {
      try {
        const res = await fetch('/api/consolidate/progress');
        const data = await res.json();
        if (data) {
          if (typeof data.pct === 'number') {
            setConsolidationPct(data.pct);
          }
          if (data.progress_text) {
            setProgressText(data.progress_text);
          }
          if (data.is_running === false) {
            stopPolling();
            setIsProcessing(false);
            setConsolidationPct(100);
            if (data.summary) {
              setSummary(data.summary);
              setOutputPath(data.summary.output_path || (data.summary.items && data.summary.items[0]?.value) || null);
            } else if (data.error_msg) {
              setError(data.error_msg);
            }
          }
        }
      } catch (err) {
        console.error('Error polling consolidation progress:', err);
      }
    }, 250);
    pollRef.current = interval;
  };

  const handleConsolidate = async () => {
    if (stagedItems.length === 0) return;

    setIsProcessing(true);
    setConsolidationPct(0);
    setError(null);

    try {
      // Gather pre-uploaded server paths
      const readyPaths = stagedItems.filter((i) => i.serverPath).map((i) => i.serverPath!);

      let filePathsToRun = readyPaths;
      if (filePathsToRun.length < stagedItems.length) {
        // Upload any remaining un-uploaded files
        const unuploaded = stagedItems.filter((i) => !i.serverPath).map((i) => i.file);
        if (unuploaded.length > 0) {
          const freshPaths = await onUploadFiles(unuploaded);
          filePathsToRun = [...readyPaths, ...freshPaths];
        }
      }

      if (filePathsToRun.length === 0) {
        throw new Error('No valid client workbooks ready for consolidation.');
      }

      const res = await onConsolidateRun(filePathsToRun);
      if (res && res.success && !res.summary) {
        pollConsolidationProgress();
      } else if (res && res.summary) {
        setSummary(res.summary);
        setOutputPath(res.output_path);
        setIsProcessing(false);
        setConsolidationPct(100);
      } else {
        throw new Error(res?.error || 'Consolidation failed to start.');
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred during consolidation.');
      setIsProcessing(false);
    }
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const filteredLogs = summary?.file_summaries.filter((f) =>
    f.filename.toLowerCase().includes(searchLog.toLowerCase()) ||
    f.client.toLowerCase().includes(searchLog.toLowerCase())
  ) || [];

  const totalSizeMb = (stagedItems.reduce((acc, i) => acc + i.file.size, 0) / (1024 * 1024)).toFixed(2);
  const readyCount = stagedItems.filter((i) => i.status === 'ready').length;
  const failedCount = stagedItems.filter((i) => i.status === 'error').length;

  return (
    <div className="space-y-6">
      <div className="section-header">
        <div>
          <h2 className="section-title">Batch Workbook Consolidation</h2>
          <p className="text-xs text-slate-400 mt-1">
            Upload Payment Tracker and Master Data client workbooks to consolidate every record into one standard schema.
          </p>
        </div>
        <span className="section-badge badge-emerald">Instant Pre-Parse</span>
      </div>

      {/* The only place a failure is visible, so it sits above everything. */}
      {error && (
        <div className="validation-box flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
          <span className="text-rose-400">{error}</span>
        </div>
      )}

      {!summary ? (
        /* Upload & Staging View */
        <div className="space-y-6">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`drop-zone ${dragging ? 'dragover' : ''}`}
          >
            <input
              ref={fileInputRef}
              type="file"
              id="consolidationFileInput"
              name="consolidationFileInput"
              multiple
              accept=".xlsx,.xls"
              onChange={handleFileChange}
              className="hidden"
            />
            <UploadCloud className="drop-zone-icon w-8 h-8" />
            <span className="drop-zone-title">Upload Client Excel Workbooks</span>
            <span className="drop-zone-sub">Drag &amp; drop .xlsx files here, or click to select from your computer</span>
            <button type="button" className="btn btn-ghost btn-sm mt-3">Select Workbooks</button>
          </div>

          {/* Staged Files */}
          {stagedItems.length > 0 && (
            <div className="card space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    Staged Client Workbooks ({stagedItems.length})
                  </h3>
                  <span className="section-badge badge-blue font-mono">{totalSizeMb} MB</span>
                  <span className="section-badge badge-emerald font-mono">
                    {readyCount} / {stagedItems.length} pre-parsed
                  </span>
                  {failedCount > 0 && (
                    <span className="section-badge badge-rose font-mono">{failedCount} failed</span>
                  )}
                </div>
                <button onClick={handleClear} className="btn btn-ghost btn-sm">
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Clear Batch</span>
                </button>
              </div>

              <div className="file-list-container space-y-1 p-1.5">
                {stagedItems.map((item) => (
                  <div key={item.id} className="file-row">
                    <div className="flex items-center gap-2.5 min-w-0 flex-1">
                      <FileSpreadsheet className="w-4 h-4 text-blue-400 shrink-0" />
                      <div className="min-w-0">
                        <span className="block text-xs font-semibold text-slate-200 truncate" title={item.file.name}>
                          {item.file.name}
                        </span>
                        <span className="block text-2xs font-mono text-slate-500">
                          {(item.file.size / 1024).toFixed(1)} KB
                          {item.clientName ? ` · ${item.clientName}` : ''}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {item.status === 'pending' || item.status === 'uploading' ? (
                        <span className="section-badge badge-amber inline-flex items-center gap-1">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          <span>Pre-parsing</span>
                        </span>
                      ) : item.status === 'ready' ? (
                        <span className="section-badge badge-emerald inline-flex items-center gap-1">
                          <Check className="w-3 h-3" />
                          <span>Ready</span>
                        </span>
                      ) : (
                        <span className="section-badge badge-rose inline-flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" />
                          <span>Upload failed</span>
                        </span>
                      )}

                      <button
                        onClick={() => handleRemoveItem(item.id)}
                        className="btn btn-ghost btn-sm"
                        aria-label={`Remove ${item.file.name}`}
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {isProcessing && (
                <div className="progress-container">
                  <div className="progress-ring-wrap">
                    <svg width="72" height="72">
                      <circle
                        cx="36" cy="36" r={RING_R} fill="transparent" strokeWidth="6"
                        style={{ stroke: 'var(--bg-elevated)' }}
                      />
                      <circle
                        cx="36" cy="36" r={RING_R} fill="transparent" strokeWidth="6" strokeLinecap="round"
                        strokeDasharray={RING_C}
                        strokeDashoffset={RING_C * (1 - Math.min(Math.max(consolidationPct, 0), 100) / 100)}
                        style={{ stroke: 'var(--accent-blue)', transition: 'stroke-dashoffset 250ms ease' }}
                      />
                    </svg>
                    <span className="progress-pct">{Math.round(consolidationPct)}%</span>
                  </div>
                  <div className="min-w-0">
                    <span className="block text-xs font-bold text-slate-200 truncate">
                      {progressText || 'Consolidating batch…'}
                    </span>
                    <span className="block text-xs text-slate-400 mt-1">
                      {stagedItems.length} workbook{stagedItems.length === 1 ? '' : 's'} in this batch
                    </span>
                  </div>
                </div>
              )}

              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="text-xs text-slate-400">
                  {isProcessing
                    ? progressText || 'Consolidating batch…'
                    : readyCount === stagedItems.length
                    ? 'All workbooks pre-parsed. Ready for batch consolidation.'
                    : 'Pre-parsing workbooks in the background…'}
                </span>

                <button onClick={handleConsolidate} disabled={isProcessing} className="btn btn-primary">
                  {isProcessing ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span className="font-mono">{consolidationPct.toFixed(1)}%</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5" />
                      <span>Run Batch Consolidation</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Summary Dashboard */
        <div className="space-y-6">
          <div className="card flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-6 h-6 shrink-0 text-emerald-400" />
              <div>
                <h3 className="text-sm font-bold text-slate-200">Batch Processing Complete</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Consolidated {summary.file_summaries.length} client workbook
                  {summary.file_summaries.length === 1 ? '' : 's'} into the standard schema. Nothing was retained on disk.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button onClick={handleReset} className="btn btn-ghost btn-sm">
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Process New Batch</span>
              </button>

              {outputPath && (
                <button
                  onClick={() => setPreviewModal({ path: outputPath, name: outputPath ? outputPath.split(/[\\/]/).pop()! : 'consolidated.xlsx' })}
                  className="btn btn-ghost btn-sm"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Preview Master Excel</span>
                </button>
              )}

              {outputPath && (
                <a
                  href={`/api/download?path=${encodeURIComponent(outputPath)}`}
                  download={outputPath ? outputPath.split(/[\\/]/).pop()! : 'consolidated.xlsx'}
                  className="btn btn-primary btn-sm"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Export Consolidated Workbook (.xlsx)</span>
                </a>
              )}
            </div>
          </div>

          {/* Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="stat-card">
              <div className="flex items-center justify-between gap-2">
                <span className="stat-label">Total Consolidated Pay</span>
                <TrendingUp className="w-4 h-4 text-blue-400" />
              </div>
              <span className="stat-value font-mono truncate">{formatCurrency(summary.total_pay)}</span>
            </div>

            <div className="stat-card">
              <div className="flex items-center justify-between gap-2">
                <span className="stat-label">Payment Tracker Rows</span>
                <FileSpreadsheet className="w-4 h-4 text-violet-400" />
              </div>
              <span className="stat-value font-mono">{summary.pt_rows.toLocaleString()}</span>
            </div>

            <div className="stat-card">
              <div className="flex items-center justify-between gap-2">
                <span className="stat-label">Master Data Assignments</span>
                <Layers className="w-4 h-4 text-sky-400" />
              </div>
              <span className="stat-value font-mono">{summary.md_rows.toLocaleString()}</span>
            </div>

            <div className="stat-card">
              <div className="flex items-center justify-between gap-2">
                <span className="stat-label">Validated Clients</span>
                <Users className="w-4 h-4 text-emerald-400" />
              </div>
              <span className="stat-value font-mono">{summary.pt_clients.length}</span>
            </div>
          </div>

          {/* Parsing Log Table */}
          <div className="card card-flush">
            <div
              className="p-4 border-b flex flex-wrap items-center justify-between gap-3"
              style={{ borderColor: 'var(--border-subtle)' }}
            >
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Workbook Parsing &amp; Schema Mapping Log
              </h4>
              <div className="relative w-64">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
                <input
                  type="text"
                  id="consolidationSearchLog"
                  name="consolidationSearchLog"
                  aria-label="Filter consolidation log"
                  placeholder="Filter log..."
                  value={searchLog}
                  onChange={(e) => setSearchLog(e.target.value)}
                  className="input-field"
                  style={{ paddingLeft: '2.1rem' }}
                />
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="preview-table">
                <thead>
                  <tr>
                    <th>Source Workbook</th>
                    <th>Mapped Client Entity</th>
                    <th>PT Records</th>
                    <th>MD Records</th>
                    <th style={{ textAlign: 'right' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLogs.map((item, idx) => (
                    <tr key={idx}>
                      <td className="truncate" style={{ maxWidth: '20rem' }}>{item.filename}</td>
                      <td className="font-bold text-blue-400">{item.client}</td>
                      <td>{item.pt_rows}</td>
                      <td>{item.md_rows}</td>
                      <td style={{ textAlign: 'right' }}>
                        <span className={`section-badge ${item.status === 'SUCCESS' ? 'badge-emerald' : 'badge-rose'}`}>
                          {item.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Document Viewer Modal for In-App Generated Excel Preview */}
      {previewModal && (
        <DocumentViewerModal
          filePath={previewModal.path}
          fileName={previewModal.name}
          onClose={() => setPreviewModal(null)}
        />
      )}
    </div>
  );
};
