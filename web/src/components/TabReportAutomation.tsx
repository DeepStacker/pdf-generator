import { useState, useCallback, useEffect } from 'react'
import { Upload, FileSpreadsheet, Download, Loader2, AlertCircle, ShieldCheck, CheckCircle2, X } from 'lucide-react'
import { uploadReport, getReportStatus, downloadReport } from '../report-api'
import { ReportDataGrid } from './ReportDataGrid'
import { ReportIssuesPanel } from './ReportIssuesPanel'
import type { UploadResponse, EditEntry, ReportView } from '../report-types'

interface Toast {
  message: string
  description?: string
  kind: 'success' | 'error' | 'info'
}

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
  const [uploadPct, setUploadPct] = useState(0)
  const [uploadMessage, setUploadMessage] = useState('')

  const showToast = useCallback((t: Toast) => {
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
  }, [])

  const toastBg =
    toast?.kind === 'success'
      ? 'border-emerald-600/60 bg-emerald-950/90'
      : toast?.kind === 'error'
        ? 'border-red-600/60 bg-red-950/90'
        : 'border-blue-600/60 bg-blue-950/90'

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-100 tracking-tight flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-blue-400" />
          <span>Report Validator</span>
        </h2>
        {data && view === 'validator' && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleReset}
              className="px-3.5 py-1.5 rounded-lg bg-[#0d1322] border border-slate-700 text-slate-300 hover:border-slate-600 text-xs font-semibold transition cursor-pointer"
            >
              New File
            </button>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50 shadow-lg shadow-blue-600/20"
            >
              {downloading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              Download
              {edits.size > 0 && (
                <span className="ml-1 text-[10px] bg-white/20 px-1.5 py-0.5 rounded-full">{edits.size}</span>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Sub-nav */}
      <div className="flex items-center gap-1.5 bg-[#070a12] p-1.5 rounded-2xl border border-slate-800/80 w-fit">
        <button
          onClick={() => setView('validator')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
            view === 'validator'
              ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-600/25'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <FileSpreadsheet className="w-4 h-4" />
          Report Validator
        </button>
      </div>

      {/* Validator: upload */}
      {view === 'validator' && (!data || data == null) && (
        <div className="flex-1 flex items-start justify-center p-4">
          <div className="glass-panel w-full max-w-xl p-6 space-y-4">
            <div className="text-center">
              <div className="flex justify-center mb-2">
                <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                  <FileSpreadsheet className="w-6 h-6 text-blue-400" />
                </div>
              </div>
              <h3 className="text-lg font-bold text-slate-100">Report Validator</h3>
              <p className="text-xs text-slate-500 mt-1">
                Upload a gold loan purity verification Excel report to validate, review, and correct.
              </p>
            </div>

            <div className="space-y-4">
              {/* Excel */}
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Excel Report (Required)</label>
                <div
                  className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer ${
                    dragOver
                      ? 'border-blue-500 bg-blue-500/5'
                      : 'border-slate-700 hover:border-slate-600'
                  } ${excelFile ? 'border-emerald-500/50 bg-emerald-500/5' : ''}`}
                  onDragOver={(e) => {
                    e.preventDefault()
                    setDragOver(true)
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleExcelDrop}
                  onClick={() => document.getElementById('report-excel-input')?.click()}
                >
                  <div className="flex flex-col items-center gap-2">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${excelFile ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-500'}`}>
                      <FileSpreadsheet className="w-4 h-4" />
                    </div>
                    <div className="max-w-xs truncate">
                      <p className="text-xs font-medium truncate text-slate-300">
                        {excelFile ? excelFile.name : 'Drop Excel report (.xlsx) here or click to browse'}
                      </p>
                      {!excelFile && <p className="text-[10px] text-slate-600 mt-0.5">.xlsx files only</p>}
                    </div>
                  </div>
                </div>
                <input id="report-excel-input" type="file" accept=".xlsx" className="hidden" onChange={handleExcelSelect} disabled={loading} />
              </div>

              {/* PDF */}
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">PDF Sequence (Optional)</label>
                <div
                  className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer ${
                    pdfDragOver
                      ? 'border-blue-500 bg-blue-500/5'
                      : 'border-slate-700 hover:border-slate-600'
                  } ${pdfFile ? 'border-sky-500/50 bg-sky-500/5' : ''}`}
                  onDragOver={(e) => {
                    e.preventDefault()
                    setPdfDragOver(true)
                  }}
                  onDragLeave={() => setPdfDragOver(false)}
                  onDrop={handlePdfDrop}
                  onClick={() => document.getElementById('report-pdf-input')?.click()}
                >
                  <div className="flex flex-col items-center gap-2">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${pdfFile ? 'bg-sky-500/20 text-sky-400' : 'bg-slate-800 text-slate-500'}`}>
                      <Upload className="w-4 h-4" />
                    </div>
                    <div className="max-w-xs truncate">
                      <p className="text-xs font-medium truncate text-slate-300">
                        {pdfFile ? pdfFile.name : 'Drop sequence PDF (.pdf) here or click to browse'}
                      </p>
                      {!pdfFile && <p className="text-[10px] text-slate-600 mt-0.5">.pdf files only</p>}
                    </div>
                  </div>
                </div>
                <input id="report-pdf-input" type="file" accept=".pdf" className="hidden" onChange={handlePdfSelect} disabled={loading} />
              </div>

              {/* Buttons */}
              <div className="flex items-center gap-2 mt-2">
                <button
                  onClick={handleUpload}
                  disabled={!excelFile || loading}
                  className="flex-1 py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold flex items-center justify-center gap-2 transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-600/20"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {uploadMessage || 'Validating…'} {uploadPct > 0 ? `${Math.round(uploadPct)}%` : ''}
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
                    className="px-4 py-2.5 rounded-xl bg-[#0d1322] border border-slate-700 text-slate-300 hover:border-slate-600 text-xs font-semibold transition cursor-pointer"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>
            {loading && uploadPct > 0 && (
              <div className="space-y-1">
                <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full transition-all duration-300"
                    style={{ width: `${Math.min(100, Math.max(2, uploadPct))}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-500 text-center">
                  {uploadMessage || 'Validating…'} {uploadPct > 0 ? `— ${Math.round(uploadPct)}%` : ''}
                </p>
              </div>
            )}
            <div className="mt-2 flex items-center gap-2 text-[10px] text-slate-600">
              <AlertCircle className="w-3 h-3" />
              <span>Files are processed locally. No data is stored permanently.</span>
            </div>
          </div>
        </div>
      )}

      {/* Validator: preview */}
      {view === 'validator' && data && (
        <div className="flex flex-1 overflow-hidden gap-4">
          <main className="flex-1 p-0 overflow-hidden">
            <ReportDataGrid data={data} editedCells={editedCells} zoom={zoom} onCellEdit={handleCellEdit} onZoomChange={setZoom} />
          </main>
          <aside className="w-80 border-l border-slate-800 shrink-0 overflow-y-auto p-4 custom-scrollbar hidden lg:block">
            <ReportIssuesPanel data={data} />
          </aside>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-[60] max-w-sm border rounded-xl shadow-2xl p-4 text-slate-100 ${toastBg} animate-in fade-in slide-in-from-bottom-4`}>
          <div className="flex items-start gap-3">
            <div className="shrink-0 pt-0.5">
              {toast.kind === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : toast.kind === 'error' ? (
                <AlertCircle className="w-4 h-4 text-red-400" />
              ) : (
                <Loader2 className="w-4 h-4 text-blue-400" />
              )}
            </div>
            <div className="flex-1">
              <p className="text-xs font-bold">{toast.message}</p>
              {toast.description && <p className="text-[11px] text-slate-400 mt-0.5 break-words">{toast.description}</p>}
            </div>
            <button onClick={() => setToast(null)} className="text-slate-500 hover:text-slate-200 transition cursor-pointer">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}