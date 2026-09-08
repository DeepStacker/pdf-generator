import { useState, useEffect } from 'react';
import { Header, ActiveTab } from './components/Header';
import { TabBankAudit } from './components/TabBankAudit';
import { TabConsolidation } from './components/TabConsolidation';
import { TabStats } from './components/TabStats';
import { TabReportAutomation } from './components/TabReportAutomation';
import { TabFlatten } from './components/TabFlatten';
import { TabHistory } from './components/TabHistory';
import { TabSettings } from './components/TabSettings';

export default function App() {
  // Every valid tab, in one place. TabHistory and TabSettings were written but
  // never reachable because this list and the nav were maintained separately.
  const TABS: ActiveTab[] = [
    'audit', 'consolidation', 'report', 'flatten', 'stats', 'history', 'settings',
  ];
  const isTab = (value: string | null): value is ActiveTab =>
    !!value && (TABS as string[]).includes(value);

  // Read initial tab from URL hash or localStorage, default to 'audit'
  const getInitialTab = (): ActiveTab => {
    const hash = window.location.hash.replace('#', '');
    if (isTab(hash)) return hash;
    const saved = localStorage.getItem('audit_engine_active_tab');
    if (isTab(saved)) return saved;
    return 'audit';
  };

  const getInitialTheme = (): 'dark' | 'light' => {
    const saved = localStorage.getItem('audit_engine_theme');
    return saved === 'light' ? 'light' : 'dark';
  };

  const [activeTab, setActiveTabState] = useState<ActiveTab>(getInitialTab);
  const [theme, setTheme] = useState<'dark' | 'light'>(getInitialTheme);

  // Sync tab changes with URL hash & localStorage
  const setActiveTab = (tab: ActiveTab) => {
    setActiveTabState(tab);
    window.location.hash = tab;
    localStorage.setItem('audit_engine_active_tab', tab);
  };

  // Sync theme changes with localStorage & body class
  const handleThemeChange = (newTheme: 'dark' | 'light') => {
    setTheme(newTheme);
    localStorage.setItem('audit_engine_theme', newTheme);
    if (newTheme === 'light') {
      document.documentElement.classList.add('light-mode');
    } else {
      document.documentElement.classList.remove('light-mode');
    }
  };

  // Listen for browser Back / Forward / Refresh navigation
  useEffect(() => {
    // Initial theme setup
    if (theme === 'light') {
      document.documentElement.classList.add('light-mode');
    }

    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '');
      if (isTab(hash)) {
        setActiveTabState(hash);
        localStorage.setItem('audit_engine_active_tab', hash);
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    window.addEventListener('popstate', handleHashChange);
    return () => {
      window.removeEventListener('hashchange', handleHashChange);
      window.removeEventListener('popstate', handleHashChange);
    };
  }, [theme]);

  const handleUploadFiles = async (files: File[]): Promise<string[]> => {
    // Uploads run together rather than one after another, and a file that
    // fails is named. Previously any file whose response lacked a path was
    // dropped in silence, so a batch could come back short with no clue why.
    const results = await Promise.all(
      files.map(async (f) => {
        const formData = new FormData();
        formData.append('file', f);
        try {
          const res = await fetch('/api/upload', { method: 'POST', body: formData });
          const data = await res.json();
          if (data.success && data.path) return { name: f.name, path: data.path as string };
          return { name: f.name, error: data.error || `HTTP ${res.status}` };
        } catch {
          return { name: f.name, error: 'could not reach the server' };
        }
      })
    );

    const failed = results.filter((r) => !('path' in r));
    if (failed.length) {
      const detail = failed.map((r: any) => `${r.name} (${r.error})`).join(', ');
      throw new Error(`${failed.length} file(s) could not be uploaded: ${detail}`);
    }
    return results.map((r: any) => r.path);
  };

  const handleRunReport = async (bankName: string, filePaths: string[], options: any) => {
    const payload = {
      bank: bankName,
      filepath: filePaths.length === 1 ? filePaths[0] : filePaths,
      ...options,
    };

    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    return await res.json();
  };

  const handleConsolidateRun = async (filePaths: string[]) => {
    const res = await fetch('/api/consolidate/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files: filePaths }),
    });

    return await res.json();
  };

  return (
    <div className={`min-h-screen flex flex-col font-sans transition-colors duration-300 ${theme === 'light' ? 'bg-slate-100 text-slate-900' : 'bg-[#0b0f17] text-slate-100'}`}>
      <Header activeTab={activeTab} setActiveTab={setActiveTab} theme={theme} setTheme={handleThemeChange} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        <div className={activeTab === 'audit' ? 'block' : 'hidden'}>
          <TabBankAudit onRunReport={handleRunReport} onUploadFiles={handleUploadFiles} />
        </div>
        <div className={activeTab === 'consolidation' ? 'block' : 'hidden'}>
          <TabConsolidation onConsolidateRun={handleConsolidateRun} onUploadFiles={handleUploadFiles} />
        </div>
        <div className={activeTab === 'stats' ? 'block' : 'hidden'}>
          <TabStats />
        </div>
        <div className={activeTab === 'report' ? 'block' : 'hidden'}>
          <TabReportAutomation />
        </div>
        <div className={activeTab === 'flatten' ? 'block' : 'hidden'}>
          <TabFlatten />
        </div>
        <div className={activeTab === 'history' ? 'block' : 'hidden'}>
          <TabHistory />
        </div>
        <div className={activeTab === 'settings' ? 'block' : 'hidden'}>
          <TabSettings />
        </div>
      </main>

      <footer className="bg-[#070a12] border-t border-slate-800/80 py-4 px-6 text-center text-xs text-slate-500 mt-auto font-medium">
        FinConsolidate Pro Operations Suite • Enterprise Financial Consolidation System
      </footer>
    </div>
  );
}
