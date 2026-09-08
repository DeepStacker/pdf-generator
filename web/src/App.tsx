import { useState, useEffect } from 'react';
import { Header, ActiveTab } from './components/Header';
import { TabBankAudit } from './components/TabBankAudit';
import { TabConsolidation } from './components/TabConsolidation';
import { TabStats } from './components/TabStats';
import { TabReportAutomation } from './components/TabReportAutomation';

export default function App() {
  // Read initial tab from URL hash or localStorage, default to 'audit'
  const getInitialTab = (): ActiveTab => {
    const hash = window.location.hash.replace('#', '');
    if (hash === 'audit' || hash === 'consolidation' || hash === 'stats' || hash === 'report') {
      return hash as ActiveTab;
    }
    const saved = localStorage.getItem('audit_engine_active_tab');
    if (saved === 'audit' || saved === 'consolidation' || saved === 'stats' || saved === 'report') {
      return saved as ActiveTab;
    }
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
      if (hash === 'audit' || hash === 'consolidation' || hash === 'stats' || hash === 'report') {
        setActiveTabState(hash as ActiveTab);
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
    const uploadedPaths: string[] = [];
    for (const f of files) {
      const formData = new FormData();
      formData.append('file', f);
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (data.success && data.path) {
        uploadedPaths.push(data.path);
      }
    }
    return uploadedPaths;
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
      </main>

      <footer className="bg-[#070a12] border-t border-slate-800/80 py-4 px-6 text-center text-xs text-slate-500 mt-auto font-medium">
        FinConsolidate Pro Operations Suite • Enterprise Financial Consolidation System
      </footer>
    </div>
  );
}
