import React, { useEffect, useState } from 'react';
import { History, Search, Download, Trash2 } from 'lucide-react';

export const TabHistory: React.FC = () => {
  const [history, setHistory] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState('');

  const loadHistory = () => {
    fetch('/api/history')
      .then((res) => res.json())
      .then((data) => setHistory(Array.isArray(data) ? data : []))
      .catch(() => setHistory([]));
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleClearHistory = async () => {
    await fetch('/api/history/clear', { method: 'POST' });
    setHistory([]);
  };

  const filteredHistory = history.filter(
    (item) =>
      (item.bank_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.input_file || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-800 pb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-100 tracking-tight flex items-center space-x-2">
          <History className="w-5 h-5 text-blue-400" />
          <span>Audit History</span>
        </h2>

        <button
          onClick={handleClearHistory}
          className="px-3.5 py-1.5 rounded-md bg-[#090d16] hover:bg-[#1f2937] border border-[#1f2937] text-xs font-medium text-slate-400 hover:text-red-400 flex items-center space-x-1.5 transition cursor-pointer"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>Clear History</span>
        </button>
      </div>

      <div className="app-card rounded-xl overflow-hidden">
        <div className="p-4 border-b border-[#1f2937] flex items-center justify-between bg-[#0f172a]">
          <div className="flex items-center space-x-2">
            <History className="w-4 h-4 text-blue-400" />
            <h4 className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
              Execution Logs ({history.length})
            </h4>
          </div>

          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search history..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="app-input pl-9"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#090d16] text-slate-400 uppercase font-semibold text-[10px] tracking-wider border-b border-[#1f2937]">
              <tr>
                <th className="py-2.5 px-4">Timestamp</th>
                <th className="py-2.5 px-4">Institution</th>
                <th className="py-2.5 px-4">Input Spreadsheet</th>
                <th className="py-2.5 px-4 text-center">Output Records</th>
                <th className="py-2.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f2937]">
              {filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500 italic">
                    No history records found.
                  </td>
                </tr>
              ) : (
                filteredHistory.map((item, idx) => (
                  <tr key={idx} className="hover:bg-[#161e2e]">
                    <td className="py-2.5 px-4 font-mono text-slate-400 text-[11px]">{item.timestamp || 'Just now'}</td>
                    <td className="py-2.5 px-4 font-medium text-slate-200">{item.bank_name || 'Consolidation'}</td>
                    <td className="py-2.5 px-4 text-slate-300 font-mono text-[11px] truncate max-w-xs">{item.input_file || 'Batch files'}</td>
                    <td className="py-2.5 px-4 text-center font-mono text-slate-300">{item.records || 1}</td>
                    <td className="py-2.5 px-4 text-right">
                      {item.output_path && (
                        <a
                          href={`/api/download?path=${encodeURIComponent(item.output_path)}`}
                          download
                          className="px-2.5 py-1 rounded bg-[#090d16] hover:bg-[#1f2937] border border-[#1f2937] text-blue-400 text-[11px] font-medium inline-flex items-center space-x-1"
                        >
                          <Download className="w-3 h-3" />
                          <span>Download</span>
                        </a>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
