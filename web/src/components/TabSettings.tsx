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
    <div className="space-y-6 max-w-3xl">
      <div className="border-b border-[#1f2937] pb-5">
        <h2 className="text-xl font-bold text-slate-100 tracking-tight">
          Application Preferences & System Configuration
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Configure default file output paths and operational preferences.
        </p>
      </div>

      {isSaved && (
        <div className="p-4 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Configuration updated successfully!</span>
        </div>
      )}

      <div className="app-card p-6 space-y-5">
        <div className="space-y-2">
          <label className="block text-xs font-semibold text-slate-200">Default Output Directory Path</label>
          <input
            type="text"
            placeholder="Auto (System temporary directory)"
            value={outputDir}
            onChange={(e) => setOutputDir(e.target.value)}
            className="app-input font-mono"
          />
          <p className="text-[11px] text-slate-500">Leave empty to use temporary system folder.</p>
        </div>

        <div className="flex items-center space-x-3 pt-2">
          <input
            type="checkbox"
            id="chkAutoOpen"
            checked={autoOpen}
            onChange={(e) => setAutoOpen(e.target.checked)}
            className="w-4 h-4 rounded border-slate-700 bg-[#090d16] text-blue-600 focus:ring-blue-500 cursor-pointer"
          />
          <label htmlFor="chkAutoOpen" className="text-xs text-slate-300 cursor-pointer font-medium">
            Automatically open output folder after PDF report generation completes
          </label>
        </div>

        <div className="pt-4 border-t border-[#1f2937] flex justify-end">
          <button
            onClick={handleSave}
            className="px-5 py-2 rounded-md bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-sm flex items-center space-x-2 transition cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>Save Preferences</span>
          </button>
        </div>
      </div>
    </div>
  );
};
