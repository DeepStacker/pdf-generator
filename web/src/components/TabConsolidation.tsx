import React, { useState, useEffect, useRef } from 'react';
import { UploadCloud, FileSpreadsheet, Trash2, Play, CheckCircle2, AlertTriangle, RefreshCw, Download, Layers, TrendingUp, Users, Search, Eye, Check, Loader2 } from 'lucide-react';
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

export const TabConsolidation: React.FC<TabConsolidationProps> = ({ onConsolidateRun, onUploadFiles }) => {
  const [stagedItems, setStagedItems] = useState<StagedItem[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [outputPath, setOutputPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchLog, setSearchLog] = useState('');
  const [consolidationPct, setConsolidationPct] = useState<number>(0);
  const [progressText, setProgressText] = useState<string>('');

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

  return (
    <div className="space-y-6">
      {/* Title Header */}
      <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-100 tracking-tight flex items-center space-x-2">
          <Layers className="w-5 h-5 text-blue-400" />
          <span>Multi-Bank Consolidation Engine</span>
        </h2>
        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/80 px-2.5 py-0.5 rounded border border-emerald-800/60 font-semibold">
          Instant Pre-Parse Active
        </span>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/50 border border-red-800/60 text-red-300 text-xs flex items-center space-x-2 animate-in fade-in duration-200">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {!summary ? (
        /* Upload & Staging View */
        <div className="space-y-6">
          {/* Dropzone */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            className="glass-panel p-10 rounded-2xl border-2 border-dashed border-slate-700 hover:border-blue-500/50 transition flex flex-col items-center justify-center text-center relative group cursor-pointer"
          >
            <input
              type="file"
              id="consolidationFileInput"
              name="consolidationFileInput"
              multiple
              accept=".xlsx,.xls"
              onChange={handleFileChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
            />
            <div className="flex flex-col items-center justify-center space-y-3 pointer-events-none">
              <div className="p-4 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 group-hover:scale-110 transition duration-200">
                <UploadCloud className="w-8 h-8" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-200">Drag & Drop Client Excel Workbooks Here</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Click anywhere in this box or drop bank payment trackers (.xlsx / .xls).
                </p>
              </div>
              <label htmlFor="consolidationFileInput" className="px-4 py-2 rounded-xl bg-slate-800 text-xs font-semibold text-slate-200 transition border border-slate-700 cursor-pointer">
                Browse Files
              </label>
            </div>
          </div>

          {/* Staged Files List */}
          {stagedItems.length > 0 && (
            <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
              <div className="p-4 border-b border-slate-800 bg-[#0f172a] flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                    Staged Workbooks ({stagedItems.length})
                  </span>
                  <span className="text-[10px] font-mono text-blue-400 bg-blue-950 px-2 py-0.5 rounded border border-blue-800 font-bold">
                    {totalSizeMb} MB Total
                  </span>
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800 font-bold">
                    {readyCount} / {stagedItems.length} Pre-Parsed
                  </span>
                </div>
                <button
                  onClick={handleClear}
                  className="text-xs text-slate-400 hover:text-red-400 transition flex items-center space-x-1 cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Clear Queue</span>
                </button>
              </div>

              <div className="max-h-60 overflow-y-auto custom-scrollbar divide-y divide-slate-800/80 bg-[#090d16]">
                {stagedItems.map((item) => (
                  <div key={item.id} className="px-4 py-3 flex items-center justify-between text-xs hover:bg-slate-800/30">
                    <div className="flex items-center space-x-2.5 truncate">
                      <FileSpreadsheet className="w-4 h-4 text-blue-400 flex-shrink-0" />
                      <span className="truncate font-medium text-slate-200">{item.file.name}</span>
                      {item.clientName && (
                        <span className="text-[10px] font-mono text-indigo-300 bg-indigo-950/80 px-2 py-0.5 rounded border border-indigo-800/60">
                          {item.clientName}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="text-[10px] font-mono text-slate-400">{(item.file.size / 1024).toFixed(1)} KB</span>

                      {/* Status Badges */}
                      {item.status === 'pending' || item.status === 'uploading' ? (
                        <span className="text-[10px] font-mono text-amber-400 bg-amber-950/80 px-2 py-0.5 rounded border border-amber-800/60 flex items-center space-x-1">
                          <Loader2 className="w-3 h-3 animate-spin text-amber-400" />
                          <span>Pre-parsing...</span>
                        </span>
                      ) : item.status === 'ready' ? (
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/60 flex items-center space-x-1 font-bold">
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span>Pre-parsed (Instant)</span>
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono text-red-400 bg-red-950/80 px-2 py-0.5 rounded border border-red-800/60">
                          Upload Failed
                        </span>
                      )}

                      <button onClick={() => handleRemoveItem(item.id)} className="text-slate-400 hover:text-red-400 transition cursor-pointer">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="p-4 border-t border-slate-800 bg-[#0f172a] flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-col space-y-1">
                  <span className="text-xs text-slate-300 font-medium">
                    {isProcessing
                      ? progressText || `Consolidating batch (${consolidationPct.toFixed(1)}%)...`
                      : readyCount === stagedItems.length
                      ? 'All files pre-parsed in memory. Ready for instant batch consolidation!'
                      : 'Background pre-parsing in progress...'}
                  </span>
                  {isProcessing && (
                    <div className="w-64 bg-[#090d16] h-1.5 rounded-full overflow-hidden border border-slate-800">
                      <div className="h-full bg-blue-500 transition-all duration-300" style={{ width: `${consolidationPct}%` }}></div>
                    </div>
                  )}
                </div>

                <button
                  onClick={handleConsolidate}
                  disabled={isProcessing}
                  className={`relative overflow-hidden px-6 py-2.5 rounded-xl text-xs font-bold text-white transition flex items-center justify-center space-x-2 cursor-pointer shadow-lg min-w-[200px] ${
                    isProcessing ? 'bg-slate-800 border border-blue-500/40 text-slate-200' : 'bg-blue-600 hover:bg-blue-500 shadow-blue-600/20'
                  }`}
                >
                  {isProcessing && (
                    <div
                      className="absolute inset-0 bg-blue-600/50 transition-all duration-300 pointer-events-none"
                      style={{ width: `${consolidationPct}%` }}
                    />
                  )}
                  {isProcessing ? (
                    <div className="relative z-10 flex items-center space-x-2">
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span className="font-mono font-bold">{consolidationPct.toFixed(1)}%</span>
                    </div>
                  ) : (
                    <div className="relative z-10 flex items-center space-x-2">
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>Run Batch Consolidation</span>
                    </div>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Summary Dashboard */
        <div className="space-y-6 animate-in fade-in duration-300">
          <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 bg-emerald-950/20 border-emerald-800/60 shadow-lg">
            <div className="flex items-center space-x-3.5">
              <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-100">Batch Processing Complete</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Successfully compiled {summary.file_summaries.length} client workbooks into standard consolidated schema. Zero storage retained on disk.
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={handleReset}
                className="px-4 py-2.5 rounded-xl border border-slate-700 bg-[#090d16] hover:bg-slate-800 text-slate-300 text-xs font-semibold flex items-center space-x-1.5 cursor-pointer transition"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Process New Batch</span>
              </button>

              {outputPath && (
                <button
                  onClick={() => setPreviewModal({ path: outputPath, name: outputPath ? outputPath.split(/[\\/]/).pop()! : 'consolidated.xlsx' })}
                  className="px-4 py-2.5 rounded-xl border border-blue-500/40 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 text-xs font-bold flex items-center space-x-1.5 cursor-pointer transition"
                >
                  <Eye className="w-4 h-4" />
                  <span>Preview Master Excel</span>
                </button>
              )}

              {outputPath && (
                <a
                  href={`/api/download?path=${encodeURIComponent(outputPath)}`}
                  download={outputPath ? outputPath.split(/[\\/]/).pop()! : 'consolidated.xlsx'}
                  className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-lg shadow-blue-600/20 flex items-center space-x-2 transition"
                >
                  <Download className="w-4 h-4" />
                  <span>Export Consolidated Workbook (.xlsx)</span>
                </a>
              )}
            </div>
          </div>

          {/* Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-blue-500 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[10px] font-bold uppercase tracking-wider">Total Consolidated Pay</span>
                <TrendingUp className="w-4 h-4 text-blue-400" />
              </div>
              <p className="text-2xl font-bold font-mono text-slate-100">
                {formatCurrency(summary.total_pay)}
              </p>
            </div>

            <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-indigo-500 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[10px] font-bold uppercase tracking-wider">Payment Tracker Rows</span>
                <FileSpreadsheet className="w-4 h-4 text-indigo-400" />
              </div>
              <p className="text-2xl font-bold font-mono text-slate-100">
                {summary.pt_rows.toLocaleString()}
              </p>
            </div>

            <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-purple-500 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[10px] font-bold uppercase tracking-wider">Master Data Assignments</span>
                <Layers className="w-4 h-4 text-purple-400" />
              </div>
              <p className="text-2xl font-bold font-mono text-slate-100">
                {summary.md_rows.toLocaleString()}
              </p>
            </div>

            <div className="glass-panel p-5 rounded-2xl border-l-4 border-l-emerald-500 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[10px] font-bold uppercase tracking-wider">Validated Clients</span>
                <Users className="w-4 h-4 text-emerald-400" />
              </div>
              <p className="text-2xl font-bold font-mono text-slate-100">
                {summary.pt_clients.length} Clients
              </p>
            </div>
          </div>

          {/* Parsing Log Table */}
          <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-[#0f172a]">
              <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                Workbook Parsing & Schema Mapping Log
              </h4>
              <div className="relative w-64">
                <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
                <input
                  type="text"
                  id="consolidationSearchLog"
                  name="consolidationSearchLog"
                  aria-label="Filter consolidation log"
                  placeholder="Filter log..."
                  value={searchLog}
                  onChange={(e) => setSearchLog(e.target.value)}
                  className="w-full bg-[#090d16] border border-slate-800 text-slate-200 text-xs rounded-xl pl-9 pr-3 py-1.5 focus:outline-none focus:border-blue-500 font-mono"
                />
              </div>
            </div>

            <div className="overflow-x-auto custom-scrollbar bg-[#090d16]">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[#0f172a] text-slate-400 font-semibold border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Filename</th>
                    <th className="py-3 px-4">Identified Client</th>
                    <th className="py-3 px-4">PT Rows</th>
                    <th className="py-3 px-4">MD Rows</th>
                    <th className="py-3 px-4 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredLogs.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/40 transition">
                      <td className="py-2.5 px-4 text-slate-300 truncate max-w-xs">{item.filename}</td>
                      <td className="py-2.5 px-4 font-bold text-blue-400">{item.client}</td>
                      <td className="py-2.5 px-4 text-slate-300">{item.pt_rows}</td>
                      <td className="py-2.5 px-4 text-slate-300">{item.md_rows}</td>
                      <td className="py-2.5 px-4 text-right">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            item.status === 'SUCCESS'
                              ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                              : 'bg-red-950/80 text-red-400 border border-red-800/60'
                          }`}
                        >
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
