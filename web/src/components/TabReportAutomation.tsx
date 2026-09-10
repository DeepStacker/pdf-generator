import { useState, useCallback, useEffect } from 'react'
import { Upload, FileSpreadsheet, FileText, Download, Loader2, AlertCircle, CheckCircle2, X } from 'lucide-react'
import { uploadReport, getReportStatus, downloadReport } from '../report-api'
import { ReportDataGrid } from './ReportDataGrid'
import { ReportIssuesPanel } from './ReportIssuesPanel'
import type { UploadResponse, EditEntry, ReportView } from '../report-types'

interface Toast {
  message: string
  description?: string
  kind: 'success' | 'error' | 'info'
}

/** A failure the user must still be able to read after the toast has gone. */
interface Failure {
  message: string
  description?: string
}

// Geometry of the progress ring drawn below. .progress-ring-wrap is 72x72.
const RING_RADIUS = 30
const RING_LENGTH = 2 * Math.PI * RING_RADIUS

export const TabReportAutomation: React.FC = () => {
  const [view, setView] = useState<ReportView>('validator')
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [data, setData] = useState<UploadResponse | null>(null)
  const [editedCells, setEditedCells] = useState<Set<string>>(new Set())
  const [edits, setEdits] = useState<Map<string, string>>(new Map())
  const [zoom, setZoom] = useState(100)
  const [dragOver, setDragOver] = useState(false)
  const [excelFile, setExcelFile] = useState<File | null>(null)
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [pdfDragOver, setPdfDragOver] = useState(false)
  const [toast, setToast] = useState<Toast | null>(null)
  const [failure, setFailure] = useState<Failure | null>(null)
  const [uploadPct, setUploadPct] = useState(0)
  const [uploadMessage, setUploadMessage] = useState('')

  // A toast disappears after a few seconds. A validation run can take minutes,
  // so an error announced only that way is an error the user can miss entirely
  // -- every error also lands in the banner below, which stays until dismissed.
  const showToast = useCallback((t: Toast) => {
    if (t.kind === 'error') setFailure({ message: t.message, description: t.description })
    setToast(t)
    window.setTimeout(() => setToast((cur) => (cur === t ? null : cur)), 3500)
  }, [])

  useEffect(() => {
    if (!toast) return
    const t = window.setTimeout(() => setToast(null), 3500)
    return () => window.clearTimeout(t)
  }, [toast])

  const handleCellEdit = useCallback((ref: string, value: string) => {
    setEditedCells((prev) => {
      const next = new Set(prev)
      next.add(ref)
      return next
    })
    setEdits((prev) => {
      const next = new Map(prev)
      next.set(ref, value)
      return next
    })
  }, [])

  const triggerDownload = useCallback(
    async (fileId: string, editsMap: Map<string, string>, customFilename?: string) => {
      const editEntries: EditEntry[] = []
      for (const [ref, value] of editsMap) {
        editEntries.push({ ref, value })
      }
      try {
        await downloadReport(fileId, editEntries, customFilename || 'validated_report.xlsx')
      } catch (err) {
        showToast({ kind: 'error', message: 'Download Error', description: err instanceof Error ? err.message : 'Unknown error' })
      }
    },
    [showToast],
  )

  const handleUpload = useCallback(async () => {
    if (!excelFile) return
    setLoading(true)
    setFailure(null)
    setUploadPct(0)
    setUploadMessage('Uploading…')
    try {
      // Upload is instant — returns a file_id immediately.
      const { file_id } = await uploadReport(excelFile, pdfFile)
      setUploadMessage('Validating…')

      // Poll the background job until it completes.
      let attempts = 0
      const maxAttempts = 600 // ~2 minutes at 200ms, extended lazily below
      while (attempts < maxAttempts) {
        const status = await getReportStatus(file_id)
        if (status.status === 'done') {
          const result = status.result
          if (!result) throw new Error('Processing finished without a result')
          setData(result)
          setEditedCells(new Set())
          setEdits(new Map())
          setZoom(100)
          setView('validator')
          setUploadPct(100)

          showToast(
            result.total_issues > 0
              ? { kind: 'info', message: `${result.total_issues} issues found — auto-downloading corrected file`, description: `${result.file_name} — ${result.total_issues} issues fixed` }
              : { kind: 'success', message: 'No issues found — auto-downloading file', description: `${result.file_name} — file is clean` },
          )
          triggerDownload(result.file_id, new Map(), result.custom_filename)
          return
        }
        if (status.status === 'error') {
          throw new Error(status.error || 'Validation failed')
        }
        if (status.status === 'processing') {
          if (status.pct != null) setUploadPct(status.pct)
          if (status.message) setUploadMessage(status.message)
        } else {
          throw new Error(status.detail || 'Validation failed')
        }
        await new Promise((r) => setTimeout(r, 600))
        attempts += 1
      }
      throw new Error('Processing timed out. Please try again.')
    } catch (err) {
      showToast({ kind: 'error', message: 'Upload Error', description: err instanceof Error ? err.message : 'Unknown error' })
    } finally {
      setLoading(false)
    }
  }, [excelFile, pdfFile, triggerDownload, showToast])

  const handleExcelDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const file = e.dataTransfer.files?.[0]
      if (file && file.name.endsWith('.xlsx')) {
        setExcelFile(file)
      } else {
        showToast({ kind: 'error', message: 'Invalid file', description: 'Please upload an .xlsx file (.xls is not supported)' })
      }
    },
    [showToast],
  )

  const handlePdfDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setPdfDragOver(false)
      const file = e.dataTransfer.files?.[0]
      if (file && file.name.endsWith('.pdf')) {
        setPdfFile(file)
      } else {
        showToast({ kind: 'error', message: 'Invalid file', description: 'Please upload a .pdf file' })
      }
    },
    [showToast],
  )

  const handleExcelSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) setExcelFile(file)
  }, [])

  const handlePdfSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) setPdfFile(file)
  }, [])

  const handleDownload = useCallback(async () => {
    if (!data) return
    setDownloading(true)
    try {
      const editEntries: EditEntry[] = []
      for (const [ref, value] of edits) {
        editEntries.push({ ref, value })
      }
      await downloadReport(data.file_id, editEntries, data.custom_filename || 'validated_report.xlsx')
      showToast({ kind: 'success', message: 'Downloaded', description: `${edits.size} edits applied` })
    } catch (err) {
      showToast({ kind: 'error', message: 'Download Error', description: err instanceof Error ? err.message : 'Unknown error' })
    } finally {
      setDownloading(false)
    }
  }, [data, edits, showToast])

  const handleReset = useCallback(() => {
    setData(null)
    setExcelFile(null)
    setPdfFile(null)
    setEditedCells(new Set())
    setEdits(new Map())
    setZoom(100)
    setUploadPct(0)
    setUploadMessage('')
    setFailure(null)
  }, [])

  const openPicker = (id: string) => document.getElementById(id)?.click()
  const pickerKeys = (id: string) => (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      openPicker(id)
    }
  }

  const pct = Math.min(100, Math.max(0, uploadPct))

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="section-header">
        <div className="min-w-0">
          <h2 className="section-title">Report Validator</h2>
          {data ? (
            <p className="text-xs text-slate-500 mt-1 truncate">{data.custom_filename || data.file_name}</p>
          ) : (
            <p className="text-xs text-slate-500 mt-1">
              Checks a Purity Verification Format workbook, marks every finding and hands back a corrected copy.
            </p>
          )}
        </div>
        {data && view === 'validator' && (
          <div className="flex items-center gap-2">
            <span className={`section-badge ${data.total_issues > 0 ? 'badge-amber' : 'badge-emerald'}`}>
              {data.total_issues > 0 ? `${data.total_issues} findings` : 'No findings'}
            </span>
            <button onClick={handleReset} className="btn btn-ghost btn-sm">
              New File
            </button>
            <button onClick={handleDownload} disabled={downloading} className="btn btn-primary btn-sm">
              {downloading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              {edits.size > 0 ? `Download (${edits.size})` : 'Download'}
            </button>
          </div>
        )}
      </div>

      {/* A failure stays on screen until it is dismissed or the next run starts. */}
      {failure && (
        <div className="validation-box flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-rose-400">{failure.message}</p>
            {failure.description && <p className="text-xs text-slate-400 mt-0.5 break-words">{failure.description}</p>}
          </div>
          <button onClick={() => setFailure(null)} className="cursor-pointer text-slate-500" aria-label="Dismiss error">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Validator: upload */}
      {view === 'validator' && !data && (
        <div className="max-w-3xl space-y-4">
          {/* Step 1 — inputs */}
          <div className="card space-y-4">
            <span className="stat-label">Step 1 · Select Report</span>

            <div>
              <label className="field-label">
                Report Workbook <span className="text-rose-400">*</span>
              </label>
              <div
                className={`drop-zone${dragOver ? ' is-dragging' : ''}`}
                role="button"
                tabIndex={0}
                onKeyDown={pickerKeys('report-excel-input')}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragOver(true)
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleExcelDrop}
                onClick={() => openPicker('report-excel-input')}
              >
                <FileSpreadsheet className="drop-zone-icon w-6 h-6" />
                <p className={`drop-zone-title truncate max-w-full ${excelFile ? 'text-emerald-400' : ''}`}>
                  {excelFile ? excelFile.name : 'Drop the Excel report here, or click to browse'}
                </p>
                <p className="drop-zone-sub">
                  {excelFile ? 'Ready to validate' : '.xlsx only — must contain the “Purity Verification Format” sheet'}
                </p>
              </div>
              <input id="report-excel-input" type="file" accept=".xlsx" className="hidden" onChange={handleExcelSelect} disabled={loading} />
            </div>

            <div>
              <label className="field-label">
                Sequence PDF <span className="text-slate-500 font-normal">(optional)</span>
              </label>
              <div
                className={`drop-zone${pdfDragOver ? ' is-dragging' : ''}`}
                role="button"
                tabIndex={0}
                onKeyDown={pickerKeys('report-pdf-input')}
                onDragOver={(e) => {
                  e.preventDefault()
                  setPdfDragOver(true)
                }}
                onDragLeave={() => setPdfDragOver(false)}
                onDrop={handlePdfDrop}
                onClick={() => openPicker('report-pdf-input')}
              >
                <FileText className="drop-zone-icon w-6 h-6" />
                <p className={`drop-zone-title truncate max-w-full ${pdfFile ? 'text-emerald-400' : ''}`}>
                  {pdfFile ? pdfFile.name : 'Drop the sequence PDF here, or click to browse'}
                </p>
                <p className="drop-zone-sub">
                  {pdfFile ? 'Rows will be reordered to match this PDF' : 'If supplied, rows are reordered to match the account sequence in the PDF'}
                </p>
              </div>
              <input id="report-pdf-input" type="file" accept=".pdf" className="hidden" onChange={handlePdfSelect} disabled={loading} />
            </div>
          </div>

          {/* Step 2 — run */}
          <div className="card space-y-4">
            <span className="stat-label">Step 2 · Run Validation</span>

            <div className="flex items-center gap-2">
              <button onClick={handleUpload} disabled={!excelFile || loading} className="btn btn-primary flex-1">
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {uploadMessage || 'Validating…'}
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    {pdfFile ? 'Validate & Rearrange' : 'Validate Report'}
                  </>
                )}
              </button>
              {(excelFile || pdfFile) && (
                <button
                  onClick={() => {
                    setExcelFile(null)
                    setPdfFile(null)
                  }}
                  disabled={loading}
                  className="btn btn-ghost"
                >
                  Clear
                </button>
              )}
            </div>

            {loading && (
              <div className="progress-container">
                <div className="progress-ring-wrap">
                  <svg width="72" height="72">
                    <circle cx="36" cy="36" r={RING_RADIUS} strokeWidth="5" fill="transparent" style={{ stroke: 'var(--border-subtle)' }} />
                    <circle
                      cx="36"
                      cy="36"
                      r={RING_RADIUS}
                      strokeWidth="5"
                      fill="transparent"
                      strokeLinecap="round"
                      strokeDasharray={RING_LENGTH}
                      strokeDashoffset={RING_LENGTH - (pct / 100) * RING_LENGTH}
                      style={{ stroke: 'var(--accent-blue)', transition: 'stroke-dashoffset 300ms ease' }}
                    />
                  </svg>
                  <span className="progress-pct">{Math.round(pct)}%</span>
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-300">{uploadMessage || 'Validating…'}</p>
                  <p className="text-xs text-slate-500 mt-0.5 truncate">{excelFile ? excelFile.name : '--'}</p>
                </div>
              </div>
            )}

            <div className="flex items-center gap-2 text-xs text-slate-600">
              <AlertCircle className="w-3 h-3 shrink-0" />
              <span>Files are processed locally. No data is stored permanently.</span>
            </div>
          </div>
        </div>
      )}

      {/* Validator: results */}
      {view === 'validator' && data && (
        <div className="flex gap-4 items-start">
          <main className="flex-1 min-w-0">
            <ReportDataGrid data={data} editedCells={editedCells} zoom={zoom} onCellEdit={handleCellEdit} onZoomChange={setZoom} />
          </main>
          {/* max-lg:hidden, not "hidden lg:block": the shared sheet declares
              .hidden with !important, so lg:block could never win it back. */}
          <aside className="w-96 shrink-0 overflow-y-auto max-lg:hidden" style={{ maxHeight: 'calc(100vh - 140px)' }}>
            <ReportIssuesPanel data={data} />
          </aside>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="card card-compact animate-fade-in fixed bottom-6 right-6 z-50 max-w-sm flex items-start gap-3">
          <div className="shrink-0 pt-0.5">
            {toast.kind === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            ) : toast.kind === 'error' ? (
              <AlertCircle className="w-4 h-4 text-rose-400" />
            ) : (
              <Loader2 className="w-4 h-4 text-blue-400" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-slate-300">{toast.message}</p>
            {toast.description && <p className="text-xs text-slate-500 mt-0.5 break-words">{toast.description}</p>}
          </div>
          <button onClick={() => setToast(null)} className="cursor-pointer text-slate-500" aria-label="Dismiss">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}
