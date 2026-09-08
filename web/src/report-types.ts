export interface UploadResponse {
  file_id: string
  file_name: string
  custom_filename: string
  columns: string[]
  column_letters: string[]
  rows: RowData[]
  highlights: Record<string, string>
  issues: IssueData[]
  summary: Record<string, number>
  summary_details: Record<string, string[]>
  total_issues: number
}

export interface RowData {
  row: number
  cells: Record<string, unknown>
}

export interface IssueData {
  ref: string
  row: number
  col: string
  color: string
}

export interface EditEntry {
  ref: string
  value: string
}

export type ReportView = 'validator'

export type JobStatus =
  | { status: 'processing'; file_id: string; pct?: number; message?: string }
  | { status: 'done'; file_id: string; result?: UploadResponse | null; pct?: number }
  | { status: 'error'; file_id: string; error?: string }
  | { status: 'unknown'; file_id?: string; detail?: string }