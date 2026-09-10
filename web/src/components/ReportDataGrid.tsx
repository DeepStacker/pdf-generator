import { memo, useCallback, useEffect, useRef, useState } from 'react'
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react'
import type { UploadResponse } from '../report-types'

// These are the fill colours the validator wrote into the workbook itself, so
// the grid shows the same colours the user will see when they open the file.
// They are data, not part of the app's palette.
const HIGHLIGHT_KEYS: Record<string, string> = {
  '#8B0000': 'bg-[#8B0000] text-white',
  '#FFC7CE': 'bg-[#FFC7CE] text-slate-900',
  '#FF8C00': 'bg-[#FF8C00] text-white',
  '#FFFF00': 'bg-[#FFFF00] text-slate-900',
  '#C6EFCE': 'bg-[#C6EFCE] text-slate-900',
  '#BDD7EE': 'bg-[#BDD7EE] text-slate-900',
}

const ROW_HEIGHT = 28
const OVERSCAN = 15
const CELL_BORDER = 'border-r border-b border-[var(--border-subtle)]'

function formatValue(value: unknown): string {
  return value != null
    ? typeof value === 'number'
      ? parseFloat(value.toFixed(4)).toString()
      : String(value)
    : ''
}

interface StaticCellProps {
  cellRef: string
  value: unknown
  hlClass: string
  onStartEdit: (ref: string) => void
}

const StaticCell = memo(function StaticCell({ cellRef, value, hlClass, onStartEdit }: StaticCellProps) {
  return (
    <td className={`p-0 relative ${CELL_BORDER} ${hlClass}`} onDoubleClick={() => onStartEdit(cellRef)}>
      <div className="px-1.5 py-0.5 h-7 truncate text-xs leading-[26px] cursor-cell whitespace-nowrap text-slate-300 hover:bg-[var(--bg-elevated)]">
        {formatValue(value)}
      </div>
    </td>
  )
})

interface EditingCellProps {
  cellRef: string
  initialValue: unknown
  onCommit: (ref: string, value: string) => void
  onCancel: () => void
}

function EditingCell({ cellRef, initialValue, onCommit, onCancel }: EditingCellProps) {
  const [value, setValue] = useState(() => (initialValue != null ? String(initialValue) : ''))
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.select()
  }, [])

  const commit = useCallback(() => onCommit(cellRef, value), [onCommit, cellRef, value])

  return (
    <td className={`p-0 relative ${CELL_BORDER}`}>
      <input
        ref={inputRef}
        autoFocus
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') commit()
          else if (e.key === 'Escape') onCancel()
        }}
        className="h-7 w-full rounded-none border border-[var(--accent-blue)] bg-[var(--bg-input)] text-[var(--text-primary)] font-mono text-xs px-1 outline-none"
      />
    </td>
  )
}

interface ReportDataGridProps {
  data: UploadResponse
  editedCells: Set<string>
  zoom: number
  onCellEdit: (ref: string, value: string) => void
  onZoomChange: (z: number) => void
}

export function ReportDataGrid({ data, editedCells, zoom, onCellEdit, onZoomChange }: ReportDataGridProps) {
  const { column_letters, columns, rows, highlights } = data
  const [isScrolledRight, setIsScrolledRight] = useState(false)
  const [editingCell, setEditingCell] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [viewportHeight, setViewportHeight] = useState(600)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    setViewportHeight(el.clientHeight)
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) setViewportHeight(entry.contentRect.height)
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const handleStartEdit = useCallback((ref: string) => setEditingCell(ref), [])
  const handleCommit = useCallback(
    (ref: string, value: string) => {
      onCellEdit(ref, value)
      setEditingCell(null)
    },
    [onCellEdit],
  )
  const handleCancel = useCallback(() => setEditingCell(null), [])

  const cellStyle = (ref: string) => {
    if (editedCells.has(ref)) return ''
    const color = highlights[ref]
    return color ? HIGHLIGHT_KEYS[color] || '' : ''
  }

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    setIsScrolledRight(el.scrollLeft > 20)
    setScrollTop(el.scrollTop)
  }, [])

  const visibleCount = Math.ceil(viewportHeight / ROW_HEIGHT) + OVERSCAN * 2
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN)
  const endIndex = Math.min(rows.length, startIndex + visibleCount)
  const visibleRows = rows.slice(startIndex, endIndex)
  const topSpacerHeight = startIndex * ROW_HEIGHT
  const bottomSpacerHeight = Math.max(0, (rows.length - endIndex) * ROW_HEIGHT)
  const colSpan = column_letters.length + 1
  const stickyShadow = isScrolledRight ? 'shadow-[2px_0_4px_-2px_rgba(0,0,0,0.6)]' : ''

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 140px)' }}>
      <div className="flex items-center gap-2 pb-2 shrink-0">
        <button onClick={() => onZoomChange(Math.max(zoom - 10, 30))} title="Zoom out" className="btn btn-ghost btn-sm">
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button onClick={() => onZoomChange(100)} title="Reset zoom" className="btn btn-ghost btn-sm">
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
        <button onClick={() => onZoomChange(Math.min(zoom + 10, 200))} title="Zoom in" className="btn btn-ghost btn-sm">
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <span className="w-10 text-xs font-mono text-slate-500">{zoom}%</span>
        <span className="ml-auto text-xs text-slate-500">
          {rows.length} rows &times; {columns.length} columns &middot; double-click a cell to edit
        </span>
      </div>

      <div
        ref={containerRef}
        className="flex-1 overflow-auto rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-deep)]"
        onScroll={handleScroll}
        style={{ fontSize: `${Math.round(zoom * 0.12)}px` }}
      >
        <table className="w-full border-collapse" style={{ minWidth: column_letters.length * 120 + 50 }}>
          <thead>
            <tr className="sticky top-0 z-10">
              <th
                className={`sticky left-0 z-20 bg-[var(--bg-surface)] ${CELL_BORDER} text-xs font-semibold text-slate-500 text-center ${stickyShadow}`}
                style={{ width: 50, minWidth: 50 }}
              >
                Row
              </th>
              {column_letters.map((letter, i) => (
                <th
                  key={letter}
                  className={`bg-[var(--bg-surface)] ${CELL_BORDER} text-xs font-semibold text-left px-1.5`}
                  title={columns[i] || letter}
                >
                  <div className="flex flex-col leading-tight py-0.5">
                    <span className="text-[9px] leading-none text-slate-600 font-mono">{letter}</span>
                    <span className="truncate max-w-[140px] leading-tight text-slate-400">{columns[i] || letter}</span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {topSpacerHeight > 0 && (
              <tr style={{ height: topSpacerHeight }} aria-hidden="true">
                <td colSpan={colSpan} style={{ padding: 0, border: 'none' }} />
              </tr>
            )}
            {visibleRows.map((row) => {
              const rowHighlightRef = column_letters
                .map((l) => `${l}${row.row}`)
                .find((ref) => highlights[ref] && !editedCells.has(ref))
              const rowDot = rowHighlightRef !== undefined
              const dotColor = rowHighlightRef ? highlights[rowHighlightRef] : ''
              return (
                <tr key={row.row} className="hover:bg-[var(--bg-elevated)]">
                  <td
                    className={`sticky left-0 z-10 bg-[var(--bg-deep)] ${CELL_BORDER} text-xs text-slate-500 text-center font-mono ${stickyShadow}`}
                    style={{ width: 50, minWidth: 50 }}
                  >
                    {rowDot && (
                      <span className="inline-block w-1.5 h-1.5 rounded-full mr-1 align-middle" style={{ backgroundColor: dotColor }} />
                    )}
                    {row.row}
                  </td>
                  {column_letters.map((letter) => {
                    const ref = `${letter}${row.row}`
                    const value = row.cells[letter]
                    if (editingCell === ref) {
                      return (
                        <EditingCell
                          key={ref}
                          cellRef={ref}
                          initialValue={value}
                          onCommit={handleCommit}
                          onCancel={handleCancel}
                        />
                      )
                    }
                    return (
                      <StaticCell
                        key={ref}
                        cellRef={ref}
                        value={value}
                        hlClass={cellStyle(ref)}
                        onStartEdit={handleStartEdit}
                      />
                    )
                  })}
                </tr>
              )
            })}
            {bottomSpacerHeight > 0 && (
              <tr style={{ height: bottomSpacerHeight }} aria-hidden="true">
                <td colSpan={colSpan} style={{ padding: 0, border: 'none' }} />
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
