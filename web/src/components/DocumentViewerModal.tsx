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
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="document-modal-title"
    >
      <div className="glass-panel w-full max-w-6xl h-[90vh] flex flex-col overflow-hidden rounded-2xl border border-slate-700 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="p-4 border-b border-slate-800 bg-[#0f172a] flex items-center justify-between flex-shrink-0">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              {isPdf ? <FileText className="w-5 h-5" /> : <FileSpreadsheet className="w-5 h-5" />}
            </div>
            <div>
              <h3 id="document-modal-title" className="text-sm font-bold text-slate-100 truncate max-w-lg">
                {fileName}
              </h3>
              <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                {isPdf
                  ? 'Interactive PDF Document Viewer'
                  : `Excel Sheet: ${activeSheet || 'Default'} • Total Rows: ${excelData?.total_rows?.toLocaleString() || 0}`}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <a
              href={downloadUrl}
              download={fileName}
              className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer"
              aria-label="Download Document"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download</span>
            </a>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition cursor-pointer"
              aria-label="Close modal"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Excel Sub-Header: Sheet Selector & Search */}
        {isExcel && excelData && (
          <div className="bg-[#0b0f17] border-b border-slate-800 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 flex-shrink-0">
            {/* Sheet Tabs */}
            <div className="flex items-center space-x-1.5 overflow-x-auto custom-scrollbar max-w-xl">
              {excelData.sheet_names && excelData.sheet_names.map((name) => (
                <button
                  key={name}
                  onClick={() => loadExcelSheet(name)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold font-mono transition cursor-pointer whitespace-nowrap ${
                    activeSheet === name
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      : 'bg-slate-800/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  {name}
                </button>
              ))}
            </div>

            {/* Live Search */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                id="docViewerSearchInput"
                name="docViewerSearchInput"
                aria-label="Search all rows in sheet"
                placeholder="Search all rows in sheet..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-[#090d16] border border-slate-800 text-slate-200 text-xs rounded-lg pl-8 pr-3 py-1.5 focus:outline-none focus:border-blue-500 font-mono w-64"
              />
            </div>
          </div>
        )}

        {/* Content Viewer Body */}
        <div className="flex-1 bg-[#080c14] relative overflow-hidden flex flex-col">
          {isPdf ? (
            <object
              data={previewUrl}
              type="application/pdf"
              className="w-full h-full border-0"
            >
              <iframe
                src={previewUrl}
                className="w-full h-full border-0"
                title={fileName}
              />
            </object>
          ) : isExcel ? (
            loading ? (
              <div className="flex-1 flex flex-col items-center justify-center space-y-3">
                <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
                <span className="text-xs text-slate-400 font-mono">Parsing Entire Excel Workbook Sheet...</span>
              </div>
            ) : error ? (
              <div className="flex-1 flex items-center justify-center p-6 text-center text-xs text-red-400 font-mono">
                {error}
              </div>
            ) : excelData ? (
              <div className="flex-1 overflow-auto custom-scrollbar p-4 bg-[#090d16]">
                <table className="w-full text-left text-xs border-collapse font-mono">
                  <thead className="bg-[#0f172a] text-slate-300 font-bold sticky top-0 border-b border-slate-800 z-10">
                    <tr>
                      <th className="py-2.5 px-3 border border-slate-800 bg-[#0f172a]">#</th>
                      {excelData.headers.map((h, i) => (
                        <th key={i} className="py-2.5 px-3 border border-slate-800 bg-[#0f172a] whitespace-nowrap text-blue-400">
                          {h || `Col ${i + 1}`}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {paginatedRows.length > 0 ? (
                      paginatedRows.map((row, rIdx) => {
                        const globalRowIdx = (currentPage - 1) * pageSize + rIdx + 1;
                        return (
                          <tr key={rIdx} className="hover:bg-slate-800/40 group transition">
                            <td className="py-2 px-3 border border-slate-800 text-slate-500 font-mono text-[10px] bg-[#0b0f17]">
                              {globalRowIdx}
                            </td>
                            {row.map((cell, cIdx) => {
                              const cellId = `${rIdx}-${cIdx}`;
                              const isCopied = copiedCell === cellId;
                              return (
                                <td
                                  key={cIdx}
                                  onClick={() => copyToClipboard(cell, cellId)}
                                  title="Click to copy cell value"
                                  className="py-2 px-3 border border-slate-800 text-slate-300 whitespace-nowrap text-[11px] cursor-pointer hover:bg-blue-600/10 hover:text-white transition relative"
                                >
                                  <span>{cell}</span>
                                  {isCopied && (
                                    <span className="absolute right-1 top-1 bg-emerald-500 text-black text-[9px] font-bold px-1.5 py-0.5 rounded shadow z-20">
                                      Copied!
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
                        <td colSpan={excelData.headers.length + 1} className="py-8 text-center text-slate-500 text-xs">
                          No matching records found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            ) : null
          ) : (
            <div className="p-8 text-center text-slate-400 text-xs">
              Preview not available for this file type.
            </div>
          )}
        </div>

        {/* Excel Pagination Footer */}
        {isExcel && excelData && totalFilteredRows > 0 && (
          <div className="bg-[#0f172a] border-t border-slate-800 px-4 py-2.5 flex items-center justify-between text-xs font-mono text-slate-400 flex-shrink-0">
            <div>
              Showing <span className="text-slate-200 font-bold">{(currentPage - 1) * pageSize + 1}</span> to{' '}
              <span className="text-slate-200 font-bold">{Math.min(currentPage * pageSize, totalFilteredRows)}</span> of{' '}
              <span className="text-slate-200 font-bold">{totalFilteredRows.toLocaleString()}</span> rows
            </div>

            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <span>Rows per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-[#090d16] border border-slate-800 text-slate-200 text-xs rounded px-2 py-1 focus:outline-none"
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={250}>250</option>
                </select>
              </div>

              <div className="flex items-center space-x-1">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-1 rounded bg-slate-800 disabled:opacity-40 hover:bg-slate-700 transition cursor-pointer"
                  aria-label="Previous Page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="px-2 text-slate-300 font-bold">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-1 rounded bg-slate-800 disabled:opacity-40 hover:bg-slate-700 transition cursor-pointer"
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
