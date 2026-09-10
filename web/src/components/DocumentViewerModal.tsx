import React, { useEffect, useState, useMemo } from 'react';
import { X, FileText, FileSpreadsheet, Download, Loader2, Search, ChevronLeft, ChevronRight } from 'lucide-react';

interface DocumentViewerModalProps {
  filePath: string | null;
  fileName: string | null;
  onClose: () => void;
}

export const DocumentViewerModal: React.FC<DocumentViewerModalProps> = ({ filePath, fileName, onClose }) => {
  if (!filePath || !fileName) return null;

  const isPdf = fileName.toLowerCase().endsWith('.pdf');
  const isExcel = fileName.toLowerCase().endsWith('.xlsx') || fileName.toLowerCase().endsWith('.xls');

  const previewUrl = `/api/preview?path=${encodeURIComponent(filePath)}`;
  const downloadUrl = `/api/download?path=${encodeURIComponent(filePath)}`;

  const [activeSheet, setActiveSheet] = useState<string | null>(null);
  const [excelData, setExcelData] = useState<{ sheet_name: string; sheet_names: string[]; headers: string[]; rows: string[][]; total_rows: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Search, Copy & Pagination state
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedCell, setCopiedCell] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  // Accessibility: Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Fetch Excel sheet content
  const loadExcelSheet = (sheetName?: string) => {
    setLoading(true);
    setError(null);
    let url = `/api/preview/excel?path=${encodeURIComponent(filePath)}&max_rows=3000`;
    if (sheetName) {
      url += `&sheet=${encodeURIComponent(sheetName)}`;
    }
    fetch(url)
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setExcelData(data);
          setActiveSheet(data.sheet_name);
          setCurrentPage(1);
        } else {
          setError(data.error || 'Failed to preview Excel spreadsheet.');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (isExcel) {
      loadExcelSheet();
    }
  }, [filePath, isExcel]);

  const filteredRows = useMemo(() => {
    if (!excelData?.rows) return [];
    if (!searchTerm.trim()) return excelData.rows;
    const term = searchTerm.toLowerCase();
    return excelData.rows.filter((row) =>
      row.some((cell) => cell.toLowerCase().includes(term))
    );
  }, [excelData, searchTerm]);

  // Reset page when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  const totalFilteredRows = filteredRows.length;
  const totalPages = Math.ceil(totalFilteredRows / pageSize) || 1;

  const paginatedRows = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredRows.slice(start, start + pageSize);
  }, [filteredRows, currentPage, pageSize]);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCell(id);
    setTimeout(() => setCopiedCell(null), 1500);
  };

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="document-modal-title"
    >
      <div
        className="modal-box flex flex-col"
        style={{ maxWidth: '76rem', height: '90vh' }}
      >
        {/* Modal Header */}
        <div className="modal-header" style={{ flexShrink: 0 }}>
          <div className="flex items-center gap-3" style={{ minWidth: 0 }}>
            {isPdf
              ? <FileText className="w-5 h-5 text-blue-400" />
              : <FileSpreadsheet className="w-5 h-5 text-blue-400" />}
            <div style={{ minWidth: 0 }}>
              <h3 id="document-modal-title" className="truncate">{fileName}</h3>
              <p className="text-2xs font-mono text-slate-400 mt-1">
                {isPdf
                  ? 'Interactive PDF document viewer'
                  : `Sheet: ${activeSheet || 'Default'} • ${excelData?.total_rows?.toLocaleString() || 0} rows`}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <a
              href={downloadUrl}
              download={fileName}
              className="btn btn-primary btn-sm"
              aria-label="Download Document"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download</span>
            </a>
            <button onClick={onClose} className="btn btn-ghost btn-sm" aria-label="Close modal">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Excel Sub-Header: Sheet Selector & Search */}
        {isExcel && excelData && (
          <div
            className="flex flex-wrap items-center justify-between gap-3"
            style={{
              flexShrink: 0,
              padding: '0.65rem 1.5rem',
              borderBottom: '1px solid var(--border-subtle)',
            }}
          >
            {/* Sheet Tabs */}
            <div className="flex items-center gap-2 overflow-x-auto" style={{ maxWidth: '36rem' }}>
              {excelData.sheet_names && excelData.sheet_names.map((name) => (
                <button
                  key={name}
                  onClick={() => loadExcelSheet(name)}
                  className={`chip-btn font-mono ${activeSheet === name ? 'selected' : ''}`}
                  style={{ flex: '0 0 auto', whiteSpace: 'nowrap' }}
                >
                  {name}
                </button>
              ))}
            </div>

            {/* Live Search */}
            <div className="relative">
              <Search
                className="w-3.5 h-3.5 text-slate-500 pointer-events-none"
                style={{ position: 'absolute', left: '0.7rem', top: '50%', transform: 'translateY(-50%)' }}
              />
              <input
                type="text"
                id="docViewerSearchInput"
                name="docViewerSearchInput"
                aria-label="Search all rows in sheet"
                placeholder="Search all rows in sheet..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input-field"
                style={{ width: '17rem', paddingLeft: '2.1rem' }}
              />
            </div>
          </div>
        )}

        {/* Content Viewer Body */}
        <div
          className="flex-1 relative flex flex-col"
          style={{ minHeight: 0, overflow: 'hidden', background: 'var(--bg-deep)' }}
        >
          {isPdf ? (
            <object
              data={previewUrl}
              type="application/pdf"
              className="w-full h-full"
              style={{ border: 0 }}
            >
              <iframe
                src={previewUrl}
                className="w-full h-full"
                style={{ border: 0 }}
                title={fileName}
              />
            </object>
          ) : isExcel ? (
            loading ? (
              <div className="flex-1 flex flex-col items-center justify-center gap-3">
                <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
                <span className="text-xs text-slate-400 font-mono">Parsing workbook sheet...</span>
              </div>
            ) : error ? (
              <div className="flex-1 flex items-center justify-center text-xs text-rose-400 font-mono" style={{ padding: '1.5rem', textAlign: 'center' }}>
                {error}
              </div>
            ) : excelData ? (
              <div className="flex-1 overflow-auto">
                <table className="preview-table">
                  <thead>
                    <tr style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--bg-surface)' }}>
                      <th>#</th>
                      {excelData.headers.map((h, i) => (
                        <th key={i}>
                          {h || `Col ${i + 1}`}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedRows.length > 0 ? (
                      paginatedRows.map((row, rIdx) => {
                        const globalRowIdx = (currentPage - 1) * pageSize + rIdx + 1;
                        return (
                          <tr key={rIdx}>
                            <td>{globalRowIdx}</td>
                            {row.map((cell, cIdx) => {
                              const cellId = `${rIdx}-${cIdx}`;
                              const isCopied = copiedCell === cellId;
                              return (
                                <td
                                  key={cIdx}
                                  onClick={() => copyToClipboard(cell, cellId)}
                                  title="Click to copy cell value"
                                  className="relative cursor-pointer"
                                >
                                  <span>{cell}</span>
                                  {isCopied && (
                                    <span
                                      style={{
                                        position: 'absolute',
                                        right: '0.25rem',
                                        top: '0.15rem',
                                        background: 'var(--accent-emerald-fill)',
                                        color: '#fff',
                                        fontSize: '0.6rem',
                                        fontWeight: 700,
                                        padding: '0.1rem 0.35rem',
                                        borderRadius: 'var(--radius-sm)',
                                        zIndex: 20,
                                      }}
                                    >
                                      Copied
                                    </span>
                                  )}
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td colSpan={excelData.headers.length + 1} style={{ textAlign: 'center', padding: '2rem 1rem' }}>
                          No matching records found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            ) : null
          ) : (
            <div className="flex-1 flex items-center justify-center text-xs text-slate-400">
              Preview not available for this file type.
            </div>
          )}
        </div>

        {/* Excel Pagination Footer */}
        {isExcel && excelData && totalFilteredRows > 0 && (
          <div className="modal-footer justify-between" style={{ flexShrink: 0 }}>
            <span className="text-xs font-mono text-slate-400">
              Showing {(currentPage - 1) * pageSize + 1} to{' '}
              {Math.min(currentPage * pageSize, totalFilteredRows)} of{' '}
              {totalFilteredRows.toLocaleString()} rows
            </span>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Rows per page</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="input-field"
                  style={{ width: 'auto' }}
                  aria-label="Rows per page"
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={250}>250</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="btn btn-ghost btn-sm"
                  aria-label="Previous Page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-xs font-mono text-slate-300">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="btn btn-ghost btn-sm"
                  aria-label="Next Page"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
