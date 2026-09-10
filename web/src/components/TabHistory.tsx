import React, { useEffect, useState } from 'react';
import { Search, Download, Trash2 } from 'lucide-react';

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
      <div className="section-header">
        <div className="flex items-center gap-3">
          <h2 className="section-title">History Logs</h2>
          <span className="section-badge badge-blue">{history.length} runs</span>
        </div>

        <button onClick={handleClearHistory} className="btn btn-danger btn-sm">
          <Trash2 className="w-3.5 h-3.5" />
          <span>Clear History</span>
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search
          className="w-4 h-4 text-slate-500 pointer-events-none"
          style={{ position: 'absolute', left: '0.8rem', top: '50%', transform: 'translateY(-50%)' }}
        />
        <input
          type="text"
          placeholder="Type an institution or Excel filename to search past audit logs..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="input-field"
          style={{ paddingLeft: '2.4rem' }}
        />
      </div>

      {/* Log table. The empty state is deliberately not a row inside the table:
          five columns force the table wider than a phone, so a centred cell
          spanning them all sat off the right edge, unreadable until you
          scrolled sideways to find out there was nothing there. */}
      {filteredHistory.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '2.5rem 1rem' }}>
          <p className="text-slate-500 italic">No history records found.</p>
        </div>
      ) : (
      <div className="card card-flush">
        <div className="overflow-x-auto">
          <table className="history-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Institution</th>
                <th>Input Spreadsheet</th>
                <th style={{ textAlign: 'center' }}>Output Records</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredHistory.map((item, idx) => (
                  <tr key={idx}>
                    <td className="font-mono text-slate-400">{item.timestamp || 'Just now'}</td>
                    <td className="font-semibold">{item.bank_name || 'Consolidation'}</td>
                    <td className="font-mono truncate" style={{ maxWidth: '20rem' }}>
                      {item.input_file || 'Batch files'}
                    </td>
                    <td className="font-mono" style={{ textAlign: 'center' }}>{item.records || 1}</td>
                    <td style={{ textAlign: 'right' }}>
                      {item.output_path && (
                        <a
                          href={`/api/download?path=${encodeURIComponent(item.output_path)}`}
                          download
                          className="btn btn-ghost btn-sm"
                        >
                          <Download className="w-3 h-3" />
                          <span>Download</span>
                        </a>
                      )}
                    </td>
                  </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      )}
    </div>
  );
};
