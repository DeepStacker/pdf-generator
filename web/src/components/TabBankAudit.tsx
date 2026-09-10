import React, { useState, useEffect, useRef } from 'react';
import {
  Upload, Play, AlertCircle, AlertTriangle, CheckCircle2, Download, Loader2,
  FileSpreadsheet, FileText, Archive, Eye, Trash2, RotateCcw,
} from 'lucide-react';
import { FilePreviewModal } from './FilePreviewModal';
import { ArvogRebuildPanel } from './ArvogRebuildPanel';
import { DocumentViewerModal } from './DocumentViewerModal';
import { BANKS } from '../banks';

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
  /** Owned by App, because the sidebar selects it -- as it does on the desktop. */
  selectedBank: string;
}

export interface OutputFileInfo {
  name: string;
  path: string;
  size: number;
}

/**
 * A failure the user has to see.
 *
 * This screen used to carry a terminal-style console, which nobody read but
 * which was also the only place a failure showed up. The console is gone; the
 * ERROR and WARN lines the backend reports are pulled out of the log stream
 * and raised into the alert strip below the header instead, so a run that goes
 * wrong still says so.
 */
interface RunAlert {
  level: 'ERROR' | 'WARN';
  text: string;
}

const LEVEL_IN_TEXT = /\[(ERROR|WARN|WARNING|CRITICAL|FATAL)\]/i;

const extractAlerts = (items: unknown[]): RunAlert[] => {
  const out: RunAlert[] = [];

  for (const item of items) {
    let level = '';
    let text = '';

    if (item && typeof item === 'object') {
      // The tracker's own shape: { timestamp, level, message }.
      const entry = item as { level?: unknown; message?: unknown };
      level = String(entry.level ?? '').toUpperCase();
      text = String(entry.message ?? '');
    } else {
      // An older server (or a hand-pushed line) sends a bare string.
      text = String(item ?? '');
      const found = text.match(LEVEL_IN_TEXT);
      if (found) {
        level = found[1].toUpperCase();
        text = text.replace(found[0], '').trim();
      }
    }

    if (!text) continue;
    if (level === 'ERROR' || level === 'CRITICAL' || level === 'FATAL') {
      out.push({ level: 'ERROR', text });
    } else if (level === 'WARN' || level === 'WARNING') {
      out.push({ level: 'WARN', text });
    }
  }

  return out;
};


/** 2 x pi x r for the r=20 progress ring, the same number the desktop uses. */
const RING = 125.6;

const ROSE_EDGE = 'rgba(242, 85, 90, 0.35)';
const AMBER_EDGE = 'rgba(199, 132, 31, 0.35)';

export const TabBankAudit: React.FC<BankAuditProps> = ({ onRunReport, onUploadFiles, selectedBank }) => {

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
  const [progressStep, setProgressStep] = useState('Initializing…');
  const [cancelling, setCancelling] = useState(false);
  const [alerts, setAlerts] = useState<RunAlert[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

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

  // The console this screen used to carry kept its transcript in the browser.
  // The panel is gone; the saved transcript should go with it rather than sit
  // there forever in everyone's localStorage.
  useEffect(() => {
    localStorage.removeItem('bank_audit_logs');
  }, []);

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

  const currentBankMeta = BANKS.find((b) => b.name === selectedBank) || BANKS[0];
  const isArvog = selectedBank.includes('Arvog');
  const isEquitas = selectedBank.includes('Equitas');
  const isRebuildLeg = isArvog && arvogPanel === 'REBUILD';

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
    setIsDragging(false);
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
      setAlerts((prev) => [...prev, { level: 'WARN', text: 'The reports were generated but the output folder could not be listed.' }]);
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
    setCancelling(true);
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
          if (data.active_branch) {
            setProgressStep(String(data.active_branch));
          }
          // No console any more, so only the lines that report trouble are
          // kept — the whole point is that a failure still reaches the user.
          if (Array.isArray(data.logs)) {
            setAlerts(extractAlerts(data.logs));
          }

          if (data.is_running === false) {
            stopPolling();
            setIsProcessing(false);
            setCancelling(false);

            // The backend states this now. The label matching below is kept
            // only so an older server still works; on its own it missed the
            // directory whenever a label was reworded, and its "/var/" and
            // "/tmp/" sniffing never matched a Windows path at all.
            let foundDir: string | null = data.summary?.output_dir ?? null;
            if (!foundDir && data.summary && Array.isArray(data.summary.items)) {
              const dirItem = data.summary.items.find(
                (item: any) =>
                  item.label === 'Staging Directory' ||
                  item.label === 'Output Directory' ||
                  item.label === 'Output Folder' ||
                  item.label === 'Output Path'
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
    setCancelling(false);
    setError(null);
    setAlerts([]);
    setOutputDir(null);
    setOutputFiles([]);
    setProgressPct(5);
    setProgressStep(`Uploading ${stagedFiles.length} spreadsheet(s)…`);

    try {
      const filePaths = await onUploadFiles(stagedFiles);

      if (filePaths.length === 0) {
        throw new Error('Failed to upload source spreadsheet files.');
      }

      setProgressStep('Launching generation pipeline…');

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
      setIsProcessing(false);
      setCancelling(false);
    }
  };

  const pdfFiles = outputFiles.filter((f) => f.name.toLowerCase().endsWith('.pdf'));
  const handleResetAll = () => {
    setStagedFiles([]);
    setOutputDir(null);
    setOutputFiles([]);
    setAlerts([]);
    setError(null);
    setProgressPct(0);
    setProgressStep('Initializing…');
    localStorage.removeItem('bank_audit_outputDir');
    localStorage.removeItem('bank_audit_outputFiles');
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

  // A selected chip takes the current bank's own fill, which is what the
  // desktop's dynamic-accent-bg does to every chip on a Process screen. The
  // fills are the darkened variants -- white chip text on the lighter dot
  // colours does not clear the AA contrast floor.
  const selectedChip: React.CSSProperties = {
    background: currentBankMeta.fill,
    borderColor: currentBankMeta.fill,
    color: '#fff',
  };

  /** A labelled segmented control, the same one the desktop uses. */
  const chipRow = (
    label: string,
    options: { value: string; label: string }[],
    current: string,
    onSelect: (value: string) => void
  ) => (
    <div>
      <label className="field-label">{label}</label>
      <div className="chip-group">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onSelect(opt.value)}
            className={`chip-btn${current === opt.value ? ' selected' : ''}`}
            style={current === opt.value ? selectedChip : undefined}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <div className="tab-content process-layout space-y-5">
      {/* File Inspection Modal */}
      <FilePreviewModal file={previewFile} onClose={() => setPreviewFile(null)} />

      {/* Page header */}
      <div className="section-header">
        <div>
          <h2 className="section-title">Generate Reports</h2>
          <p className="text-sm text-slate-400 mt-1">{currentBankMeta.desc}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`section-badge ${currentBankMeta.badge}`}>{currentBankMeta.label}</span>
          <button
            onClick={handleResetAll}
            className="btn btn-ghost btn-sm"
            title="Clear staged files and generated outputs to start fresh"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Start New Batch</span>
          </button>
        </div>
      </div>


      {/* Anything that went wrong, and anything the run warned about */}
      {(error || alerts.length > 0) && (
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {error && (
            <div className="validation-box flex items-start gap-2" style={{ borderColor: ROSE_EDGE }}>
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: 'var(--accent-rose)' }} />
              <span style={{ color: 'var(--accent-rose)' }}>{error}</span>
            </div>
          )}
          {alerts.map((a, idx) => (
            <div
              key={idx}
              className="validation-box flex items-start gap-2"
              style={{ borderColor: a.level === 'ERROR' ? ROSE_EDGE : AMBER_EDGE }}
            >
              {a.level === 'ERROR' ? (
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: 'var(--accent-rose)' }} />
              ) : (
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: 'var(--accent-amber)' }} />
              )}
              <span style={{ color: a.level === 'ERROR' ? 'var(--accent-rose)' : 'var(--accent-amber)' }}>
                {a.text}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Equitas runs in two stages; the choice sits above everything else */}
      {isEquitas && (
        <div className="chip-group">
          {[
            { value: 'STAGE 1', label: 'Stage 1: Single-Packet Audit Report' },
            { value: 'STAGE 2', label: 'Stage 2: Consolidate Reports' },
          ].map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setEquitasStage(opt.value)}
              className={`chip-btn${equitasStage === opt.value ? ' selected' : ''}`}
              style={{ padding: '0.6rem 0.75rem', ...(equitasStage === opt.value ? selectedChip : {}) }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      {/* Which leg of the Arvog round trip: out to the branch, or back */}
      {isArvog && (
        <div className="chip-group w-max">
          {(['GENERATE', 'REBUILD'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => {
                setArvogPanel(mode);
                localStorage.setItem('bank_audit_arvogPanel', mode);
              }}
              className={`chip-btn whitespace-nowrap${arvogPanel === mode ? ' selected' : ''}`}
              style={{ padding: '0.5rem 0.9rem', ...(arvogPanel === mode ? selectedChip : {}) }}
            >
              {mode === 'GENERATE' ? 'Generate PDF / Excel' : 'Rebuild Master Sheet'}
            </button>
          ))}
        </div>
      )}

      {/* The return leg carries its own upload, so the staging grid steps
          aside for it rather than offering two conflicting ways in. */}
      {isRebuildLeg && (
        <div className="card" style={{ maxWidth: '32rem' }}>
          <ArvogRebuildPanel />
        </div>
      )}

      <div className={`process-grid${isRebuildLeg ? ' hidden' : ''}`}>
        {/* LEFT COLUMN: source files */}
        <div className="space-y-4">
          <div className="stats-row">
            <div className="stat-card">
              <span className="stat-label">Staged</span>
              <span className="stat-value text-sky-400">{stagedFiles.length}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Generated</span>
              <span className="stat-value text-emerald-400">{outputFiles.length}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">PDFs</span>
              <span className="stat-value" style={{ color: currentBankMeta.dot }}>{pdfFiles.length}</span>
            </div>
          </div>

          <div>
            <label className="field-label" htmlFor="bankFileInput">Source Master Excel</label>
            <div
              className={`drop-zone drag-zone-compact relative${isDragging ? ' is-dragging' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
            >
              <input
                type="file"
                id="bankFileInput"
                multiple
                accept=".xlsx,.XLSX,.xls"
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                onChange={handleFileChange}
              />
              <Upload className="drop-zone-icon w-8 h-8" />
              <span className="drop-zone-title">
                Drag &amp; drop or{' '}
                <span style={{ color: currentBankMeta.dot, fontWeight: 600 }}>browse</span>
              </span>
              <span className="drop-zone-sub">.xlsx, .xls</span>
            </div>
          </div>

          {stagedFiles.length > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between items-center text-2xs font-bold text-slate-400 uppercase tracking-wider">
                <span>Files ({stagedFiles.length})</span>
                <button
                  onClick={() => setStagedFiles([])}
                  className="text-2xs font-bold text-slate-400 hover:text-white cursor-pointer"
                >
                  Clear
                </button>
              </div>
              <div className="file-list-container space-y-1 p-1.5">
                {stagedFiles.map((f, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 px-2 py-1.5">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileSpreadsheet
                        className="w-3.5 h-3.5 shrink-0"
                        style={{ color: currentBankMeta.dot }}
                      />
                      <span className="text-xs text-slate-300 truncate">{f.name}</span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="text-2xs font-mono text-slate-500">
                        {(f.size / 1024).toFixed(1)} KB
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setPreviewFile(f);
                        }}
                        className="btn btn-ghost btn-sm cursor-pointer"
                        title="Inspect File"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveFile(i);
                        }}
                        className="btn btn-danger btn-sm cursor-pointer"
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

        {/* RIGHT COLUMN: run parameters */}
        <div className="card space-y-4">
          {selectedBank === 'IDFC First Bank' && (
            <>
              {chipRow(
                'Audit Type',
                [
                  { value: 'POA', label: 'POA' },
                  { value: 'TAF', label: 'TAF' },
                ],
                idfcAuditType,
                setIdfcAuditType
              )}
              {chipRow(
                'Packaging Mode',
                [
                  { value: 'FOLDER', label: 'Folder' },
                  { value: 'ZIP ONLY', label: 'Zip Only' },
                  { value: 'BOTH', label: 'Both' },
                ],
                idfcOutputMode,
                setIdfcOutputMode
              )}
            </>
          )}

          {isEquitas && (
            <>
              {chipRow(
                'Output Format',
                [
                  { value: 'PDF ONLY', label: 'PDF Only' },
                  { value: 'EXCEL ONLY', label: 'Excel Only' },
                  { value: 'BOTH', label: 'Both' },
                ],
                equitasFormat,
                setEquitasFormat
              )}
              <div>
                <label htmlFor="equitasPack" className="field-label">Packaging Mode</label>
                <select
                  id="equitasPack"
                  name="equitasPack"
                  value={equitasPack}
                  onChange={(e) => setEquitasPack(e.target.value)}
                  className="input-field"
                >
                  {EQUITAS_PACKS.map((mode) => (
                    <option key={mode} value={mode}>{mode}</option>
                  ))}
                </select>
              </div>
            </>
          )}

          {isArvog && (
            <>
              {chipRow(
                'Output Format',
                [
                  { value: 'PDF ONLY', label: 'PDF Only' },
                  { value: 'EXCEL ONLY', label: 'Excel Only' },
                  { value: 'BOTH', label: 'Both' },
                ],
                arvogFormat,
                setArvogFormat
              )}
              {chipRow(
                'Packaging Mode',
                [
                  { value: 'FOLDER', label: 'Folder' },
                  { value: 'ZIP ONLY', label: 'Zip Only' },
                  { value: 'BOTH', label: 'Both' },
                ],
                arvogMode,
                setArvogMode
              )}
            </>
          )}

          <p className="text-2xs text-slate-500 italic">
            Files are available for download once generation finishes.
          </p>

          <div style={{ borderTop: '1px solid var(--border-subtle)' }} />

          <div className="flex gap-2">
            <button
              onClick={handleExecute}
              disabled={isProcessing || stagedFiles.length === 0}
              className={`btn ${currentBankMeta.runClass} flex-1`}
              style={currentBankMeta.runStyle}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Generating… {progressPct}%</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Generate Reports ({stagedFiles.length})</span>
                </>
              )}
            </button>
            <button onClick={handleCancel} disabled={!isProcessing} className="btn btn-danger">
              Stop
            </button>
          </div>

          {isProcessing && (
            <div className="progress-container">
              <div className="progress-ring-wrap">
                <svg className="w-full h-full" viewBox="0 0 48 48">
                  <circle cx="24" cy="24" r="20" strokeWidth="4" stroke="#232a36" fill="transparent" />
                  <circle
                    cx="24"
                    cy="24"
                    r="20"
                    strokeWidth="4"
                    stroke={currentBankMeta.dot}
                    fill="transparent"
                    strokeDasharray={RING}
                    strokeDashoffset={RING - (RING * progressPct) / 100}
                    strokeLinecap="round"
                    className="transition-all duration-300"
                  />
                </svg>
                <span className="progress-pct">{progressPct}%</span>
              </div>
              <div className="space-y-1 min-w-0">
                <span className="block text-xs font-bold text-slate-300 truncate">
                  {cancelling ? 'Cancelling…' : progressStep}
                </span>
                <span className="block text-2xs text-slate-500 font-mono">Elapsed: {elapsedSec}s</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Generated Outputs */}
      {outputDir && (
        <div className="card space-y-4">
          <div
            // web.css redefines .flex-col, and being imported after Tailwind it
            // wins over a `sm:flex-row` -- so this row is never a column.
            className="flex flex-wrap items-center justify-between gap-4 pb-4"
            style={{ borderBottom: '1px solid var(--border-subtle)' }}
          >
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-6 h-6 shrink-0" style={{ color: 'var(--accent-emerald)' }} />
              <div>
                <h3 className="text-sm font-bold text-slate-200">Reports Generated</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  {outputFiles.length} file(s) ready — download them one by one, or take the whole folder as a ZIP.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button onClick={handleResetAll} className="btn btn-ghost btn-sm">
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Start New Batch</span>
              </button>
              <a
                href={`/api/download?path=${encodeURIComponent(outputDir)}`}
                download="audit_reports_all.zip"
                className="btn btn-success btn-sm"
              >
                <Archive className="w-3.5 h-3.5" />
                <span>Download All (ZIP)</span>
              </a>
            </div>
          </div>

          <div className="chip-group w-max">
            {([
              { value: 'ALL', label: `All (${outputFiles.length})` },
              { value: 'PDF', label: `PDFs (${pdfFiles.length})` },
              { value: 'ZIP', label: `ZIPs (${zipFiles.length})` },
              { value: 'EXCEL', label: `Excel (${excelFiles.length})` },
            ] as const).map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setFileFilter(opt.value)}
                className={`chip-btn whitespace-nowrap${fileFilter === opt.value ? ' selected' : ''}`}
                style={fileFilter === opt.value ? selectedChip : undefined}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="file-list-container" style={{ maxHeight: '20rem' }}>
            <table className="preview-table">
              <thead>
                <tr>
                  <th>File</th>
                  <th>Size</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filteredDisplayFiles.map((file, idx) => (
                  <tr key={idx}>
                    <td>
                      <span className="flex items-center gap-2">
                        {file.name.endsWith('.pdf') ? (
                          <FileText className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--accent-blue)' }} />
                        ) : file.name.endsWith('.zip') ? (
                          <Archive className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--accent-violet)' }} />
                        ) : (
                          <FileSpreadsheet className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--accent-emerald)' }} />
                        )}
                        <span className="truncate" style={{ maxWidth: '22rem' }}>{file.name}</span>
                      </span>
                    </td>
                    <td>{(file.size / 1024).toFixed(1)} KB</td>
                    <td>
                      <span className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setDocViewerState({ path: file.path, name: file.name })}
                          className="btn btn-ghost btn-sm cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Preview</span>
                        </button>
                        <a
                          href={`/api/download?path=${encodeURIComponent(file.path)}`}
                          download={file.name}
                          className="btn btn-primary btn-sm"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>Download</span>
                        </a>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
