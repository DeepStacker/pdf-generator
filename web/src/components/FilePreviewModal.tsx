import React from 'react';
import { X, FileSpreadsheet, Info } from 'lucide-react';

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
    <div className="modal-overlay">
      <div className="modal-box" style={{ maxWidth: '36rem' }}>
        <div className="modal-header">
          <div className="flex items-center gap-3" style={{ minWidth: 0 }}>
            <FileSpreadsheet className="w-5 h-5 text-blue-400" />
            <div style={{ minWidth: 0 }}>
              <h3 className="truncate">{file.name}</h3>
              <p className="text-2xs font-mono text-slate-400 mt-1">
                {displaySize} • Excel Spreadsheet
              </p>
            </div>
          </div>

          <button onClick={onClose} className="btn btn-ghost btn-sm" aria-label="Close">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="modal-body space-y-4">
          <div className="grid grid-3 gap-3">
            <div className="stat-card">
              <span className="stat-label">File Type</span>
              <span className="text-xs font-mono font-bold mt-1 block">.XLSX Workbook</span>
            </div>

            <div className="stat-card">
              <span className="stat-label">File Name</span>
              <span className="text-xs font-mono font-bold mt-1 block truncate">As uploaded</span>
            </div>

            <div className="stat-card">
              <span className="stat-label">Memory Storage</span>
              <span className="text-xs font-mono font-bold mt-1 block">In-memory stream</span>
            </div>
          </div>

          <div className="validation-box space-y-2">
            <div className="flex items-center gap-2 text-blue-400 font-semibold">
              <Info className="w-4 h-4" />
              <span>Inspection Overview</span>
            </div>
            <p className="text-slate-400">
              This workbook is parsed in memory during audit generation. The required columns
              (Prospectno, CUID, CurrentBranch, Tare Weight) are matched and reformatted
              automatically.
            </p>
          </div>
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-primary">
            Close Inspection
          </button>
        </div>
      </div>
    </div>
  );
};
