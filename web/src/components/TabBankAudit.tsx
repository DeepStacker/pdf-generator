import React, { useState, useEffect, useRef } from 'react';
import { Upload, Play, AlertCircle, CheckCircle2, Download, Terminal, FileSpreadsheet, FileText, Archive, Eye, Trash2, ShieldCheck, Sparkles, RotateCcw } from 'lucide-react';
import { FilePreviewModal } from './FilePreviewModal';
import { ArvogRebuildPanel } from './ArvogRebuildPanel';
import { DocumentViewerModal } from './DocumentViewerModal';

export interface BankAuditOptions {
  audit_type?: string;
  output_mode?: string;
  equitas_stage?: string;
  equitas_format?: string;
  equitas_pack?: string;
  arvog_format?: string;
  arvog_mode?: string;
}

export interface BankAuditProps {
  onRunReport: (bank: string, filePaths: string[], options: BankAuditOptions) => Promise<any>;
  onUploadFiles: (files: File[]) => Promise<string[]>;
}

export interface OutputFileInfo {
  name: string;
  path: string;
  size: number;
}

export const TabBankAudit: React.FC<BankAuditProps> = ({ onRunReport, onUploadFiles }) => {
  const [selectedBank, setSelectedBank] = useState<string>(() => {
    return localStorage.getItem('bank_audit_selectedBank') || 'IDFC First Bank';
  });
  
  // Bank options with localStorage persistence.
  //
  // These values go straight to the API, which validates them against its own
  // enums and rejects anything it does not recognise. The options here once
  // sent 'PDF', 'EXCEL', 'ZIP', 'BRANCH', 'SINGLE' and 'Touch and Feel', none
  // of which the backend accepts, so every choice except the default failed.
  // A saved value from that era is still in people's browsers, so anything
  // unrecognised falls back to the default rather than being sent on.
  const AUDIT_TYPES = ['POA', 'TAF'];
  const PACKAGING_MODES = ['FOLDER', 'ZIP ONLY', 'BOTH'];
  const OUTPUT_FORMATS = ['PDF ONLY', 'EXCEL ONLY', 'BOTH'];
  const EQUITAS_STAGES = ['STAGE 1', 'STAGE 2'];

  const readOption = (key: string, allowed: string[], fallback: string): string => {
    const saved = localStorage.getItem(key);
    return saved && allowed.includes(saved) ? saved : fallback;
  };

  const [idfcAuditType, setIdfcAuditType] = useState<string>(() =>
    readOption('bank_audit_idfcAuditType', AUDIT_TYPES, 'POA'));
  const [idfcOutputMode, setIdfcOutputMode] = useState<string>(() =>
    readOption('bank_audit_idfcOutputMode', PACKAGING_MODES, 'BOTH'));
  const [equitasStage, setEquitasStage] = useState<string>(() =>
    readOption('bank_audit_equitasStage', EQUITAS_STAGES, 'STAGE 1'));
  const [equitasFormat, setEquitasFormat] = useState<string>(() =>
    readOption('bank_audit_equitasFormat', OUTPUT_FORMATS, 'BOTH'));
  const [arvogFormat, setArvogFormat] = useState<string>(() =>
    readOption('bank_audit_arvogFormat', OUTPUT_FORMATS, 'BOTH'));
  const [arvogMode, setArvogMode] = useState<string>(() =>
    readOption('bank_audit_arvogMode', PACKAGING_MODES, 'BOTH'));

  // Which leg of the Arvog round trip: out to the branch, or back from it.
  // Mirrors the desktop's sub-tab inside the Arvog panel.
  // Equitas packaging is matched by substring in the service, not by an enum,
  // so these are the seven the desktop offers. The browser never sent this
  // field at all, leaving every web Equitas run on the FOLDER default.
  const EQUITAS_PACKS = [
    'FOLDER', 'ZIP OF PDF', 'ZIP OF EXCEL', 'ZIP OF BOTH',
    'BOTH (FOLDER + ZIP OF PDF)', 'BOTH (FOLDER + ZIP OF EXCEL)',
    'BOTH (FOLDER + ZIP OF BOTH)',
  ];
  const [equitasPack, setEquitasPack] = useState<string>(() =>
    readOption('bank_audit_equitasPack', EQUITAS_PACKS, 'FOLDER'));

  const [arvogPanel, setArvogPanel] = useState<'GENERATE' | 'REBUILD'>(() =>
    localStorage.getItem('bank_audit_arvogPanel') === 'REBUILD' ? 'REBUILD' : 'GENERATE');

  // Execution states with localStorage persistence
  const [stagedFiles, setStagedFiles] = useState<File[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressPct, setProgressPct] = useState(0);
  const [logs, setLogs] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('bank_audit_logs');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [error, setError] = useState<string | null>(null);
  
  // Inspection Modal & Output states with localStorage persistence
  const [previewFile, setPreviewFile] = useState<File | null>(null);
  const [outputDir, setOutputDir] = useState<string | null>(() => {
    return localStorage.getItem('bank_audit_outputDir');
  });
  const [outputFiles, setOutputFiles] = useState<OutputFileInfo[]>(() => {
    try {
      const saved = localStorage.getItem('bank_audit_outputFiles');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [fileFilter, setFileFilter] = useState<'ALL' | 'PDF' | 'ZIP' | 'EXCEL'>('ALL');
  const [docViewerState, setDocViewerState] = useState<{ path: string; name: string } | null>(null);

  // Sync state changes to localStorage
  useEffect(() => {
    localStorage.setItem('bank_audit_selectedBank', selectedBank);
  }, [selectedBank]);

  useEffect(() => {
    localStorage.setItem('bank_audit_idfcAuditType', idfcAuditType);
  }, [idfcAuditType]);

  useEffect(() => {
    localStorage.setItem('bank_audit_idfcOutputMode', idfcOutputMode);
  }, [idfcOutputMode]);

  useEffect(() => {
    localStorage.setItem('bank_audit_equitasStage', equitasStage);
  }, [equitasStage]);

  useEffect(() => {
    localStorage.setItem('bank_audit_equitasFormat', equitasFormat);
  }, [equitasFormat]);

  useEffect(() => {
    localStorage.setItem('bank_audit_equitasPack', equitasPack);
  }, [equitasPack]);

  useEffect(() => {
    localStorage.setItem('bank_audit_arvogFormat', arvogFormat);
  }, [arvogFormat]);

  useEffect(() => {
    localStorage.setItem('bank_audit_arvogMode', arvogMode);
  }, [arvogMode]);

  useEffect(() => {
    localStorage.setItem('bank_audit_logs', JSON.stringify(logs));
  }, [logs]);

  useEffect(() => {
    if (outputDir) {
      localStorage.setItem('bank_audit_outputDir', outputDir);
    } else {
      localStorage.removeItem('bank_audit_outputDir');
    }
  }, [outputDir]);

  useEffect(() => {
    localStorage.setItem('bank_audit_outputFiles', JSON.stringify(outputFiles));
  }, [outputFiles]);

  const banks = [
    {
      name: 'IDFC First Bank',
      label: 'IDFC First Bank',
      desc: 'Physical Verification & Touch & Feel Reports',
      activeClass: 'bg-rose-600 text-white shadow-md shadow-rose-600/20 font-bold',
      textClass: 'text-rose-400',
      borderClass: 'border-rose-500/30',
      badgeClass: 'bg-rose-950/80 text-rose-400 border-rose-800/60',
    },
    {
      name: 'Equitas Small Finance Bank',
      label: 'Equitas Bank',
      desc: 'Single Packet Audit & Consolidated Bundles',
      activeClass: 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20 font-bold',
      textClass: 'text-emerald-400',
      borderClass: 'border-emerald-500/30',
      badgeClass: 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60',
    },
    {
      name: 'Arvog Bank',
      label: 'Arvog Bank',
      desc: 'Branch & Single PDF Groupings',
      activeClass: 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20 font-bold',
      textClass: 'text-indigo-400',
      borderClass: 'border-indigo-500/30',
      badgeClass: 'bg-indigo-950/80 text-indigo-400 border-indigo-800/60',
    },
  ];

  const currentBankMeta = banks.find((b) => b.name === selectedBank) || banks[0];

  const [elapsedSec, setElapsedSec] = useState(0);

  useEffect(() => {
    let timer: any;
    if (isProcessing) {
      setElapsedSec(0);
      timer = setInterval(() => {
        setElapsedSec((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isProcessing]);

  const validateFiles = (files: File[]): boolean => {
    const invalid = files.filter((f) => !f.name.match(/\.(xlsx|xls)$/i));
    if (invalid.length > 0) {
      setError(`Invalid file format: ${invalid.map((f) => f.name).join(', ')}. Only Excel spreadsheets (.xlsx, .xls) are supported.`);
      return false;
    }
    return true;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selected = Array.from(e.target.files);
      if (validateFiles(selected)) {
        setStagedFiles((prev) => [...prev, ...selected]);
        setError(null);
      }
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const selected = Array.from(e.dataTransfer.files);
      if (validateFiles(selected)) {
        setStagedFiles((prev) => [...prev, ...selected]);
        setError(null);
      }
    }
  };

  const handleRemoveFile = (idx: number) => {
    setStagedFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const loadOutputFiles = async (dirPath: string) => {
    try {
      const res = await fetch(`/api/list_output?path=${encodeURIComponent(dirPath)}`);
      const data = await res.json();
      if (data.success && Array.isArray(data.files)) {
        setOutputFiles(data.files);
      }
    } catch (err) {
      console.error('Failed to list output files:', err);
    }
  };

  // Held in a ref so Cancel can stop it and so an unmount clears it. It used
  // to be a local that handleExecute dropped on the floor, which left the
  // 400 ms poll running for the life of the page on every error path.
  const pollRef = useRef<number | null>(null);

  const stopPolling = () => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  useEffect(() => stopPolling, []);

  const handleCancel = async () => {
    setLogs((prev) => [...prev, '[WARN] Cancelling…']);
    try {
      await fetch('/api/cancel');
    } catch {
      /* the run may already have finished; the poll below settles it */
    }
  };

  const pollProgress = () => {
    stopPolling();
    const interval = window.setInterval(async () => {
      try {
        const res = await fetch('/api/progress');
        const data = await res.json();

        if (data) {
          if (typeof data.pct === 'number') {
            setProgressPct(Math.round(data.pct));
          }
          if (Array.isArray(data.logs)) {
            setLogs(data.logs);
          }

          if (data.is_running === false) {
            stopPolling();
            setIsProcessing(false);

            let foundDir: string | null = null;
            if (data.summary && Array.isArray(data.summary.items)) {
              const dirItem = data.summary.items.find(
                (item: any) =>
                  item.label === 'Staging Directory' ||
                  item.label === 'Output Directory' ||
                  item.label === 'Output Folder' ||
                  item.label === 'Output Path' ||
                  (typeof item.value === 'string' && (item.value.includes('/var/') || item.value.includes('/tmp/')))
              );
              if (dirItem) foundDir = dirItem.value;
            }

            if (foundDir) {
              setOutputDir(foundDir);
              await loadOutputFiles(foundDir);
            }
          }
        }
      } catch (err) {
        console.error('Error polling progress:', err);
      }
    }, 400);
    pollRef.current = interval;
  };

  const handleExecute = async () => {
    if (stagedFiles.length === 0) {
      setError('Please select at least one audit spreadsheet file.');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setOutputDir(null);
    setOutputFiles([]);
    setProgressPct(5);
    setLogs([`[INFO] Initializing PDF Report Generation for ${selectedBank}...`]);

    try {
      setLogs((prev) => [...prev, `[INFO] Uploading ${stagedFiles.length} audit spreadsheet(s)...`]);
      const filePaths = await onUploadFiles(stagedFiles);

      if (filePaths.length === 0) {
        throw new Error('Failed to upload source spreadsheet files.');
      }

      setLogs((prev) => [...prev, `[INFO] Launching generation pipeline...`]);

      const options: BankAuditOptions = {
        audit_type: idfcAuditType,
        output_mode: idfcOutputMode,
        equitas_stage: equitasStage,
        equitas_format: equitasFormat,
        equitas_pack: equitasPack,
        arvog_format: arvogFormat,
        arvog_mode: arvogMode,
      };

      const res = await onRunReport(selectedBank, filePaths, options);

      if (res && res.success) {
        pollProgress();
      } else {
        throw new Error(res?.error || 'Report generation failed to start.');
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred during report generation.');
      setLogs((prev) => [...prev, `[ERROR] ${err.message}`]);
      setIsProcessing(false);
    }
  };

  const renderLogText = (logItem: any): string => {
    if (typeof logItem === 'string') return logItem;
    if (logItem && typeof logItem === 'object') {
      const time = logItem.timestamp ? `[${logItem.timestamp}] ` : '';
      const level = logItem.level ? `[${logItem.level}] ` : '';
      const msg = logItem.message || JSON.stringify(logItem);
      return `${time}${level}${msg}`;
    }
    return String(logItem);
  };

  const pdfFiles = outputFiles.filter((f) => f.name.toLowerCase().endsWith('.pdf'));
  const handleResetAll = () => {
    setStagedFiles([]);
    setOutputDir(null);
    setOutputFiles([]);
    setLogs([]);
    setError(null);
    setProgressPct(0);
    localStorage.removeItem('bank_audit_outputDir');
    localStorage.removeItem('bank_audit_outputFiles');
    localStorage.removeItem('bank_audit_logs');
  };

  const zipFiles = outputFiles.filter((f) => f.name.toLowerCase().endsWith('.zip'));
  const excelFiles = outputFiles.filter(
    (f) => f.name.toLowerCase().endsWith('.xlsx') || f.name.toLowerCase().endsWith('.xls')
  );

  const filteredDisplayFiles = outputFiles.filter((f) => {
    if (fileFilter === 'PDF') return f.name.toLowerCase().endsWith('.pdf');
    if (fileFilter === 'ZIP') return f.name.toLowerCase().endsWith('.zip');
    if (fileFilter === 'EXCEL') return f.name.toLowerCase().endsWith('.xlsx') || f.name.toLowerCase().endsWith('.xls');
    return true;
  });

  return (
    <div className="space-y-6">
      {/* File Inspection Modal */}
      <FilePreviewModal file={previewFile} onClose={() => setPreviewFile(null)} />

      {/* Header & Bank Selection Cards */}
      <div className="space-y-4">
        <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-100 tracking-tight flex items-center space-x-2">
            <FileText className="w-5 h-5 text-blue-400" />
            <span>Bank Audit Generator</span>
          </h2>

          <button
            onClick={handleResetAll}
            className="px-4 py-2 rounded-xl border border-rose-600/60 bg-gradient-to-r from-rose-950/80 via-slate-900 to-amber-950/80 hover:from-rose-900 hover:to-amber-900 text-rose-200 hover:text-white text-xs font-extrabold flex items-center space-x-2 cursor-pointer transition shadow-lg shadow-rose-950/40 border-glow group"
            title="Clear all staged files, terminal logs, and generated outputs to start fresh"
          >
            <RotateCcw className="w-4 h-4 text-rose-400 group-hover:rotate-180 transition duration-500" />
            <span>Start New Audit Batch</span>
          </button>
        </div>

        {/* Bank Selection Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {banks.map((b) => {
            const isSelected = selectedBank === b.name;
            return (
              <div
                key={b.name}
                onClick={() => {
                  setSelectedBank(b.name);
                  setError(null);
                }}
                className={`glass-panel glass-panel-hover p-4 rounded-xl cursor-pointer transition relative overflow-hidden border-2 ${
                  isSelected ? `${b.borderClass} bg-[#0f172a]` : 'border-transparent bg-[#0d1322]/80'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={`text-xs font-bold ${isSelected ? b.textClass : 'text-slate-300'}`}>
                    {b.label}
                  </span>
                  {isSelected && (
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${b.badgeClass}`}>
                      Active
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 mt-1.5 line-clamp-1">{b.desc}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bank Options Panel */}
      <div className={`glass-panel p-6 space-y-4 border-l-4 ${
        selectedBank === 'IDFC First Bank'
          ? 'border-l-rose-500'
          : selectedBank.includes('Equitas')
          ? 'border-l-emerald-500'
          : 'border-l-indigo-500'
      }`}>
        <div className="flex items-center justify-between">
          <h3 className={`text-xs font-bold uppercase tracking-wider ${currentBankMeta.textClass}`}>
            {selectedBank} Parameters & Output Configuration
          </h3>
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">In-Memory Engine</span>
        </div>

        {selectedBank.includes('Arvog') && (
          <div className="flex bg-[#0b0f19] border border-slate-800 rounded-lg p-0.5 w-max">
            {(['GENERATE', 'REBUILD'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => {
                  setArvogPanel(mode);
                  localStorage.setItem('bank_audit_arvogPanel', mode);
                }}
                className={`px-3 py-1 text-xs rounded-md transition-colors ${
                  arvogPanel === mode
                    ? 'bg-emerald-500 text-white font-bold'
                    : 'text-slate-400 hover:text-white font-semibold'
                }`}
              >
                {mode === 'GENERATE' ? 'Generate PDF / Excel' : 'Rebuild Master Sheet'}
              </button>
            ))}
          </div>
        )}

        {selectedBank.includes('Arvog') && arvogPanel === 'REBUILD' && <ArvogRebuildPanel />}

        {selectedBank === 'IDFC First Bank' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="idfcAuditType" className="block text-xs font-semibold text-slate-300 mb-1.5">Audit Type</label>
              <select
                id="idfcAuditType"
                name="idfcAuditType"
                value={idfcAuditType}
                onChange={(e) => setIdfcAuditType(e.target.value)}
                className="app-input font-medium"
              >
                <option value="POA">POA (Physical Verification)</option>
                <option value="TAF">TAF (Touch and Feel)</option>
              </select>
            </div>

            <div>
              <label htmlFor="idfcOutputMode" className="block text-xs font-semibold text-slate-300 mb-1.5">Packaging Mode</label>
              <select
                id="idfcOutputMode"
                name="idfcOutputMode"
                value={idfcOutputMode}
                onChange={(e) => setIdfcOutputMode(e.target.value)}
                className="app-input font-medium"
              >
                <option value="BOTH">Folder & ZIP Archive (Recommended)</option>
                <option value="FOLDER">Folder Only</option>
                <option value="ZIP ONLY">ZIP Archive Only</option>
              </select>
            </div>
          </div>
        )}

        {selectedBank.includes('Equitas') && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="equitasStage" className="block text-xs font-semibold text-slate-300 mb-1.5">Workflow Stage</label>
              <select
                id="equitasStage"
                name="equitasStage"
                value={equitasStage}
                onChange={(e) => setEquitasStage(e.target.value)}
                className="app-input font-medium"
              >
                <option value="STAGE 1">STAGE 1: Single-Packet Audit Report</option>
                <option value="STAGE 2">STAGE 2: Consolidate Reports</option>
              </select>
            </div>

            <div>
              <label htmlFor="equitasFormat" className="block text-xs font-semibold text-slate-300 mb-1.5">Output Package Format</label>
              <select
                id="equitasFormat"
                name="equitasFormat"
                value={equitasFormat}
                onChange={(e) => setEquitasFormat(e.target.value)}
                className="app-input font-medium"
              >
                <option value="BOTH">PDF & Excel Spreadsheet</option>
                <option value="PDF ONLY">PDF Only</option>
                <option value="EXCEL ONLY">Excel Only</option>
              </select>
            </div>

            <div>
              <label htmlFor="equitasPack" className="block text-xs font-semibold text-slate-300 mb-1.5">Packaging Mode</label>
              <select
                id="equitasPack"
                name="equitasPack"
                value={equitasPack}
                onChange={(e) => setEquitasPack(e.target.value)}
                className="app-input font-medium"
              >
                {EQUITAS_PACKS.map((mode) => (
                  <option key={mode} value={mode}>{mode}</option>
                ))}
              </select>
            </div>
          </div>
        )}

        {selectedBank.includes('Arvog') && arvogPanel === 'GENERATE' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="arvogMode" className="block text-xs font-semibold text-slate-300 mb-1.5">Packaging Mode</label>
              <select
                id="arvogMode"
                name="arvogMode"
                value={arvogMode}
                onChange={(e) => setArvogMode(e.target.value)}
                className="app-input font-medium"
              >
                <option value="BOTH">Folder & ZIP Archive</option>
                <option value="FOLDER">Folder Only</option>
                <option value="ZIP ONLY">ZIP Archive Only</option>
              </select>
            </div>

            <div>
              <label htmlFor="arvogFormat" className="block text-xs font-semibold text-slate-300 mb-1.5">Output Package Format</label>
              <select
                id="arvogFormat"
                name="arvogFormat"
                value={arvogFormat}
                onChange={(e) => setArvogFormat(e.target.value)}
                className="app-input font-medium"
              >
                <option value="BOTH">PDF & Excel Spreadsheet</option>
                <option value="PDF ONLY">PDF Only</option>
                <option value="EXCEL ONLY">Excel Only</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/60 text-red-300 text-xs flex items-center space-x-2.5 animate-in fade-in">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Step 1 & Step 2 Workflows */}
      {/* Staging and execution belong to the generate leg. The rebuild carries
          its own upload, and showing both would offer two conflicting ways in. */}
      <div className={`grid grid-cols-1 lg:grid-cols-2 gap-6 ${
        selectedBank.includes('Arvog') && arvogPanel === 'REBUILD' ? 'hidden' : ''
      }`}>
        {/* File Dropzone & Queue Manager */}
        <div className="glass-panel p-6 space-y-4 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Step 1: Select Audit Spreadsheets
              </h3>
              {stagedFiles.length > 0 && (
                <button
                  onClick={() => setStagedFiles([])}
                  className="text-[11px] text-slate-400 hover:text-red-400 transition cursor-pointer flex items-center space-x-1"
                >
                  <Trash2 className="w-3 h-3" />
                  <span>Clear Queue</span>
                </button>
              )}
            </div>

            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className="border-2 border-dashed border-slate-700/80 bg-[#090d16]/80 hover:border-blue-500/60 hover:bg-[#0f172a]/90 rounded-2xl p-8 text-center cursor-pointer transition shadow-inner relative group"
            >
              <input
                type="file"
                id="bankFileInput"
                multiple
                accept=".xlsx,.XLSX,.xls"
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                onChange={handleFileChange}
              />
              <div className="pointer-events-none space-y-2">
                <Upload className={`w-8 h-8 mx-auto mb-2 ${currentBankMeta.textClass} group-hover:scale-110 transition duration-200`} />
                <p className="text-xs font-bold text-slate-100">
                  Drag & drop audit spreadsheets or click anywhere to browse
                </p>
                <p className="text-[11px] text-slate-400">Click anywhere in this area to select .xlsx / .xls files</p>
              </div>
            </div>

            {stagedFiles.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  <span>Queue Staging ({stagedFiles.length} files)</span>
                </div>
                <div className="max-h-48 overflow-y-auto custom-scrollbar divide-y divide-slate-800/80 border border-slate-800 rounded-xl bg-[#090d16]">
                  {stagedFiles.map((f, i) => (
                    <div key={i} className="px-3.5 py-2.5 text-xs flex items-center justify-between text-slate-200 hover:bg-slate-800/30">
                      <div className="flex items-center space-x-2 truncate pr-2">
                        <FileSpreadsheet className={`w-4 h-4 flex-shrink-0 ${currentBankMeta.textClass}`} />
                        <span className="truncate font-medium">{f.name}</span>
                      </div>
                      <div className="flex items-center space-x-2 flex-shrink-0">
                        <span className="text-[10px] font-mono text-slate-400">
                          {(f.size / 1024).toFixed(1)} KB
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setPreviewFile(f);
                          }}
                          className="p-1 rounded text-slate-400 hover:text-blue-400 hover:bg-slate-800 transition cursor-pointer"
                          title="Inspect File"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRemoveFile(i);
                          }}
                          className="p-1 rounded text-slate-400 hover:text-red-400 hover:bg-slate-800 transition cursor-pointer"
                          title="Remove File"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Execution & Live Pipeline Stepper */}
        <div className="glass-panel p-6 space-y-5 flex flex-col justify-between">
          <div className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Step 2: Pipeline Execution & Status
            </h3>

            <button
              onClick={handleExecute}
              disabled={isProcessing || stagedFiles.length === 0}
              className={`relative overflow-hidden w-full py-3 px-4 rounded-xl text-xs font-bold text-white transition flex items-center justify-center space-x-2 shadow-lg cursor-pointer ${
                isProcessing
                  ? 'bg-slate-800 border border-slate-700 text-slate-200'
                  : stagedFiles.length === 0
                  ? 'bg-slate-800/60 text-slate-500 border border-slate-800 cursor-not-allowed'
                  : selectedBank === 'IDFC First Bank'
                  ? 'bg-rose-600 hover:bg-rose-500 shadow-rose-600/20'
                  : selectedBank.includes('Equitas')
                  ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/20'
                  : 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-600/20'
              }`}
            >
              {isProcessing && (
                <div
                  className={`absolute inset-0 transition-all duration-300 pointer-events-none ${
                    selectedBank === 'IDFC First Bank'
                      ? 'bg-rose-600/50'
                      : selectedBank.includes('Equitas')
                      ? 'bg-emerald-600/50'
                      : 'bg-indigo-600/50'
                  }`}
                  style={{ width: `${progressPct}%` }}
                />
              )}
              {isProcessing ? (
                <div className="relative z-10 flex items-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span className="font-mono font-bold">Processing... {progressPct.toFixed(1)}% ({elapsedSec}s)</span>
                </div>
              ) : (
                <div className="relative z-10 flex items-center space-x-2">
                  <Play className="w-4 h-4 fill-current" />
                  <span>Execute Audit Generation ({stagedFiles.length} files)</span>
                </div>
              )}
            </button>

            {isProcessing && (
              <button
                onClick={handleCancel}
                className="w-full py-2 rounded-lg text-xs font-bold bg-red-500/10 hover:bg-red-500/20 text-red-300 border border-red-500/30 transition-colors"
              >
                Stop Generation
              </button>
            )}

            {isProcessing && (
              <div className="space-y-2 pt-1">
                <div className="flex justify-between text-[11px] font-mono text-slate-400">
                  <span>Processing Execution Time ({elapsedSec}s)</span>
                  <span className="font-bold text-slate-200">{progressPct}%</span>
                </div>
                <div className="w-full bg-[#090d16] h-2.5 rounded-full overflow-hidden border border-slate-800 shadow-inner">
                  <div
                    className={`h-full transition-all duration-300 ${
                      selectedBank === 'IDFC First Bank'
                        ? 'bg-rose-500'
                        : selectedBank.includes('Equitas')
                        ? 'bg-emerald-500'
                        : 'bg-indigo-500'
                    }`}
                    style={{ width: `${progressPct}%` }}
                  ></div>
                </div>
              </div>
            )}
          </div>

          {/* Terminal Console */}
          <div className="bg-[#090d16] rounded-xl p-3.5 border border-slate-800/80 font-mono text-[11px] text-slate-300 space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar shadow-inner">
            <div className="flex items-center justify-between text-slate-500 text-[10px] pb-1.5 border-b border-slate-900">
              <div className="flex items-center space-x-1.5">
                <Terminal className="w-3 h-3 text-blue-400" />
                <span className="font-bold uppercase tracking-wider">Console Log</span>
              </div>
              <span className="text-slate-600">Confidential Processing</span>
            </div>
            {logs.length === 0 ? (
              <span className="text-slate-600 italic">Ready to process audit job.</span>
            ) : (
              logs.map((l, idx) => <div key={idx}>{renderLogText(l)}</div>)
            )}
          </div>
        </div>
      </div>

      {/* Generated Outputs Panel */}
      {outputDir && (
        <div className="glass-panel p-6 space-y-6 bg-emerald-950/20 border-emerald-800/60 animate-in fade-in duration-300">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-emerald-800/40 pb-4">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-100">
                  Audit Reports Generated Successfully
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Output directory contains {outputFiles.length} generated files (.pdf, .zip, .xlsx). Zero trace retained on disk.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={handleResetAll}
                className="px-4 py-2.5 rounded-xl border border-rose-600/60 bg-gradient-to-r from-rose-950/90 via-slate-900 to-amber-950/90 hover:from-rose-900 hover:to-amber-900 text-rose-200 hover:text-white text-xs font-extrabold flex items-center space-x-2 cursor-pointer transition shadow-lg group"
              >
                <RotateCcw className="w-4 h-4 text-rose-400 group-hover:rotate-180 transition duration-500" />
                <span>Start New Audit Batch</span>
              </button>

              <a
                href={`/api/download?path=${encodeURIComponent(outputDir)}`}
                download="audit_reports_all.zip"
                className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/20 flex items-center space-x-2 transition"
              >
                <Archive className="w-4 h-4" />
                <span>Download All (ZIP Archive)</span>
              </a>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-slate-400 mr-1">Filter Files:</span>
            <button
              onClick={() => setFileFilter('ALL')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer transition ${
                fileFilter === 'ALL' ? 'bg-blue-600 text-white' : 'bg-[#090d16] text-slate-400 hover:text-slate-200'
              }`}
            >
              All ({outputFiles.length})
            </button>
            <button
              onClick={() => setFileFilter('PDF')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer transition ${
                fileFilter === 'PDF' ? 'bg-emerald-600 text-white' : 'bg-[#090d16] text-slate-400 hover:text-slate-200'
              }`}
            >
              PDFs ({pdfFiles.length})
            </button>
            <button
              onClick={() => setFileFilter('ZIP')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer transition ${
                fileFilter === 'ZIP' ? 'bg-purple-600 text-white' : 'bg-[#090d16] text-slate-400 hover:text-slate-200'
              }`}
            >
              ZIPs ({zipFiles.length})
            </button>
            <button
              onClick={() => setFileFilter('EXCEL')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer transition ${
                fileFilter === 'EXCEL' ? 'bg-amber-600 text-white' : 'bg-[#090d16] text-slate-400 hover:text-slate-200'
              }`}
            >
              Excel ({excelFiles.length})
            </button>
          </div>

          {/* Output Files Grid */}
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-72 overflow-y-auto custom-scrollbar">
              {filteredDisplayFiles.map((file, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl bg-[#090d16] border border-slate-800 flex items-center justify-between hover:border-slate-700 transition"
                >
                  <div className="flex items-center space-x-3 truncate pr-2">
                    {file.name.endsWith('.pdf') ? (
                      <FileText className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    ) : file.name.endsWith('.zip') ? (
                      <Archive className="w-4 h-4 text-purple-400 flex-shrink-0" />
                    ) : (
                      <FileSpreadsheet className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    )}
                    <div className="truncate">
                      <p className="text-xs font-bold text-slate-200 truncate">{file.name}</p>
                      <p className="text-[10px] font-mono text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 flex-shrink-0">
                    <button
                      onClick={() => setDocViewerState({ path: file.path, name: file.name })}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold flex items-center space-x-1 transition cursor-pointer"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Preview</span>
                    </button>
                    <a
                      href={`/api/download?path=${encodeURIComponent(file.path)}`}
                      download={file.name}
                      className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold flex items-center space-x-1.5 shadow-sm transition"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download</span>
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Document Viewer Modal */}
      {docViewerState && (
        <DocumentViewerModal
          filePath={docViewerState.path}
          fileName={docViewerState.name}
          onClose={() => setDocViewerState(null)}
        />
      )}
    </div>
  );
};
