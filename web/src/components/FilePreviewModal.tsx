import React from 'react';
import { X, FileSpreadsheet, CheckCircle2, AlertCircle, Info, Hash, Layers } from 'lucide-react';

interface FilePreviewModalProps {
  file: File | null;
  onClose: () => void;
}

export const FilePreviewModal: React.FC<FilePreviewModalProps> = ({ file, onClose }) => {
  if (!file) return null;

  const fileSizeKB = (file.size / 1024).toFixed(1);
  const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
  const displaySize = file.size > 1024 * 1024 ? `${fileSizeMB} MB` : `${fileSizeKB} KB`;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="glass-panel w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-700 shadow-2xl space-y-0 animate-in fade-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800 bg-[#0f172a] flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 truncate max-w-md">{file.name}</h3>
              <p className="text-[11px] text-slate-400 font-mono mt-0.5">Size: {displaySize} • Format: Excel Spreadsheet</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3.5 rounded-xl bg-[#090d16] border border-slate-800 text-center space-y-1">
              <span className="text-[10px] uppercase font-semibold text-slate-400 block">File Type</span>
              <span className="text-xs font-mono font-bold text-blue-400">.XLSX Workbook</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#090d16] border border-slate-800 text-center space-y-1">
              <span className="text-[10px] uppercase font-semibold text-slate-400 block">File Name</span>
              <span className="text-xs font-mono font-bold text-emerald-400 flex items-center justify-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>As uploaded</span>
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#090d16] border border-slate-800 text-center space-y-1">
              <span className="text-[10px] uppercase font-semibold text-slate-400 block">Memory Storage</span>
              <span className="text-xs font-mono font-bold text-purple-400">In-Memory Stream</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-blue-950/20 border border-blue-800/40 text-xs text-slate-300 space-y-2">
            <div className="flex items-center space-x-2 font-semibold text-blue-400">
              <Info className="w-4 h-4" />
              <span>Inspection Overview</span>
            </div>
            <p className="text-slate-400 leading-relaxed text-[11px]">
              This workbook will be parsed in-memory during audit generation. Standard required columns (Prospectno, CUID, CurrentBranch, Tare Weight) will be dynamically matched and reformatted.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-[#0f172a] flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-sm transition cursor-pointer"
          >
            Close Inspection
          </button>
        </div>
      </div>
    </div>
  );
};
