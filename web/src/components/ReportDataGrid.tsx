import { memo, useCallback, useEffect, useRef, useState } from 'react'
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react'
import type { UploadResponse } from '../report-types'

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
    <td
      className={`p-0 relative border-r border-b border-slate-800/40 ${hlClass}`}
      onDoubleClick={() => onStartEdit(cellRef)}
    >
      <div className="px-1.5 py-0.5 h-7 truncate text-xs leading-[26px] cursor-cell hover:bg-slate-500/20 whitespace-nowrap text-slate-200">
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
    <td className="p-0 relative border-r border-b border-slate-800/40">
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
        className="h-7 w-full rounded-none border-2 border-blue-500 bg-[#0b0f19] text-slate-100 text-xs px-1 outline-none"
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

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 140px)' }}>
      <div className="flex items-center gap-1.5 pb-2 shrink-0">
        <button
          onClick={() => onZoomChange(Math.max(zoom - 10, 30))}
          title="Zoom out"
          className="p-1.5 rounded-lg bg-[#090d16] border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700 transition cursor-pointer"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => onZoomChange(100)}
          title="Reset zoom"
          className="p-1.5 rounded-lg bg-[#090d16] border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700 transition cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => onZoomChange(Math.min(zoom + 10, 200))}
          title="Zoom in"
          className="p-1.5 rounded-lg bg-[#090d16] border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700 transition cursor-pointer"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <span className="text-xs text-slate-500 font-mono w-10">{zoom}%</span>
        <span className="text-xs text-slate-500 ml-auto">
          {rows.length} rows &times; {columns.length} cols &middot; Double-click cell to edit
        </span>
      </div>

      <div
        ref={containerRef}
        className="flex-1 border border-slate-800 rounded-lg overflow-auto custom-scrollbar bg-[#0b0f19]"
        onScroll={handleScroll}
        style={{ fontSize: `${Math.round(zoom * 0.12)}px` }}
      >
        <table className="w-full border-collapse" style={{ minWidth: column_letters.length * 120 + 50 }}>
          <thead>
            <tr className="sticky top-0 z-10 bg-[#0d1322]">
              <th
                className={`sticky left-0 z-20 border-r border-b border-slate-800/40 text-xs font-medium text-slate-500 text-center ${
                  isScrolledRight ? 'shadow-[2px_0_4px_-2px_rgba(0,0,0,0.6)]' : ''
                }`}
                style={{ width: 50, minWidth: 50 }}
              >
                Row
              </th>
              {column_letters.map((letter, i) => (
                <th
                  key={letter}
                  className="border-r border-b border-slate-800/40 text-xs font-medium text-slate-500 text-left px-1.5"
                  title={columns[i] || letter}
                >
                  <div className="flex flex-col leading-tight py-0.5">
                    <span className="text-[9px] text-slate-600 leading-none">{letter}</span>
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
                <tr key={row.row} className="hover:bg-slate-500/10">
                  <td
                    className={`sticky left-0 z-10 bg-[#0b0f19] border-r border-b border-slate-800/40 text-xs text-slate-500 text-center font-mono ${
                      isScrolledRight ? 'shadow-[2px_0_4px_-2px_rgba(0,0,0,0.6)]' : ''
                    }`}
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