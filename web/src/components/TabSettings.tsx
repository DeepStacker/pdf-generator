import React, { useState } from 'react';
import { Save, CheckCircle2 } from 'lucide-react';

export const TabSettings: React.FC = () => {
  const [outputDir, setOutputDir] = useState<string>('');
  const [autoOpen, setAutoOpen] = useState<boolean>(false);
  const [isSaved, setIsSaved] = useState(false);

  const handleSave = async () => {
    try {
      await fetch('/api/config/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          out_path: outputDir,
          auto_open: autoOpen ? 'True' : 'False',
        }),
      });
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 3000);
    } catch (err) {
      console.error('Failed to save settings:', err);
    }
  };

  return (
    <div className="space-y-6" style={{ maxWidth: '48rem' }}>
      <div className="section-header">
        <div>
          <h2 className="section-title">Settings</h2>
          <p className="text-sm text-slate-400 mt-1">
            Default output path and operational preferences for every screen.
          </p>
        </div>
        {isSaved && (
          <span className="section-badge badge-emerald flex items-center gap-2">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Configuration saved</span>
          </span>
        )}
      </div>

      {/* Output location */}
      <div className="card space-y-4">
        <div>
          <h3 className="stat-label">Output Location</h3>
          <p className="text-2xs text-slate-500 mt-1">
            Where every bank's generated reports are written. Every screen shares this one folder.
          </p>
        </div>

        <div>
          <label className="field-label" htmlFor="settingsOutputDir">
            Default output directory path
          </label>
          <input
            id="settingsOutputDir"
            type="text"
            placeholder="Auto (system temporary directory)"
            value={outputDir}
            onChange={(e) => setOutputDir(e.target.value)}
            className="input-field"
          />
          <p className="text-2xs text-slate-500 mt-2">Leave empty to use the temporary system folder.</p>
        </div>

        <label htmlFor="chkAutoOpen" className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            id="chkAutoOpen"
            checked={autoOpen}
            onChange={(e) => setAutoOpen(e.target.checked)}
          />
          <span className="text-xs text-slate-300">
            Open the output folder automatically once a run finishes
          </span>
        </label>

        <div
          className="flex justify-end"
          style={{ paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}
        >
          <button onClick={handleSave} className="btn btn-primary btn-sm">
            <Save className="w-4 h-4" />
            <span>Save Preferences</span>
          </button>
        </div>
      </div>
    </div>
  );
};
