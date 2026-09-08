import type { EditEntry, UploadResponse, JobStatus } from './report-types'

const BASE = '/api/report'

/**
 * Start a validation job. Returns a file_id immediately; the heavy validation
 * runs server-side in a background thread. Poll {@link getReportStatus} for
 * progress and completion.
 */
export async function uploadReport(
  excelFile: File,
  pdfFile?: File | null,
): Promise<{ file_id: string }> {
  const formData = new FormData()
  formData.append('file', excelFile)
  if (pdfFile) formData.append('pdf_file', pdfFile)
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: formData })
  if (!res.ok) {
    let detail = `Upload failed (${res.status})`
    try {
      const err = await res.json()
      detail = err.detail || detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return await res.json()
}

/** Poll a running validation job. Resolves the final {@link UploadResponse} on completion. */
export async function getReportStatus(fileId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE}/status/${fileId}`, { method: 'GET' })
  if (!res.ok) {
    let detail = `Status check failed (${res.status})`
    try {
      const err = await res.json()
      detail = err.detail || detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return await res.json()
}

export async function downloadReport(
  fileId: string,
  edits: EditEntry[],
  fallbackName = 'validated_report.xlsx',
): Promise<void> {
  const res = await fetch(`${BASE}/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId, edits }),
  })
  if (!res.ok) {
    let detail = `Download failed (${res.status})`
    try {
      const err = await res.json()
      detail = err.detail || detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fallbackName
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
