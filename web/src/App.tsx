import { useState, useEffect } from 'react';
import { Menu } from 'lucide-react';
import { Sidebar, ActiveTab } from './components/Sidebar';

// Served by audit_engine_web, which substitutes the real number into the meta
// tag. In `vite dev` the placeholder is still there, so show nothing rather
// than the literal "{{VERSION}}".
const rawVersion = document.querySelector('meta[name="app-version"]')?.getAttribute('content') ?? '';
const SCREEN_TITLES: Record<ActiveTab, string> = {
  audit: 'Generate Reports',
  consolidation: 'Consolidation',
  report: 'Report Validator',
  flatten: 'Flatten PDF',
  merge: 'Merge PDF',
  stats: 'Analytics',
  history: 'History',
  users: 'Users',
  settings: 'Settings',
};

const APP_VERSION = rawVersion.startsWith('{{') ? '' : rawVersion;
import { TabBankAudit } from './components/TabBankAudit';
import { TabConsolidation } from './components/TabConsolidation';
import { TabStats } from './components/TabStats';
import { TabReportAutomation } from './components/TabReportAutomation';
import { TabFlatten } from './components/TabFlatten';
import { TabMerge } from './components/TabMerge';
import { TabHistory } from './components/TabHistory';
import { TabSettings } from './components/TabSettings';
import { TabUsers } from './components/TabUsers';

export default function App() {
  // Every valid tab, in one place. TabHistory and TabSettings were written but
  // never reachable because this list and the nav were maintained separately.
  const TABS: ActiveTab[] = [
    'audit', 'consolidation', 'report', 'flatten', 'merge', 'stats', 'history', 'users', 'settings',
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

  const [activeTab, setActiveTabState] = useState<ActiveTab>(getInitialTab);

  // The sidebar selects the bank, so it is owned here rather than inside the
  // audit screen -- the same shape as the desktop, where the bank is a nav item.
  const [selectedBank, setSelectedBankState] = useState<string>(
    () => localStorage.getItem('bank_audit_selectedBank') || 'IDFC First Bank'
  );
  // Drawer state. Only reachable below the mobile breakpoint, where the
  // sidebar is off-canvas; at desktop widths the CSS shows it regardless.
  const [navOpen, setNavOpen] = useState(false);

  // Who is signed in. Until this answers we know neither the name nor whether
  // the Users screen exists for this account, so the nav entry stays absent
  // rather than appearing and then being taken away again.
  const [me, setMe] = useState<{ username: string | null; is_admin: boolean } | null>(null);

  const setSelectedBank = (bank: string) => {
    setSelectedBankState(bank);
    localStorage.setItem('bank_audit_selectedBank', bank);
  };

  // Sync tab changes with URL hash & localStorage
  const setActiveTab = (tab: ActiveTab) => {
    setActiveTabState(tab);
    setNavOpen(false);
    window.location.hash = tab;
    localStorage.setItem('audit_engine_active_tab', tab);
  };

  useEffect(() => {
    let cancelled = false;
    fetch('/api/me')
      .then((res) => res.json())
      .then((data) => {
        if (cancelled) return;
        setMe({ username: data?.username ?? null, is_admin: !!data?.is_admin });
      })
      .catch(() => {
        if (!cancelled) setMe({ username: null, is_admin: false });
      });
    return () => { cancelled = true; };
  }, []);

  // A saved tab or a #users link can outlive the account that could use it --
  // the screen is admin-only, so send everyone else back to the default rather
  // than leaving them on a page of permission errors.
  useEffect(() => {
    if (me && !me.is_admin && activeTab === 'users') setActiveTab('audit');
  }, [me, activeTab]);

  // Listen for browser Back / Forward / Refresh navigation
  useEffect(() => {
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
  }, []);

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
    <div className="app-shell">
      <header className="mobile-topbar">
        <button
          className="mobile-navbtn"
          onClick={() => setNavOpen(true)}
          aria-label="Open navigation"
          aria-expanded={navOpen}
        >
          <Menu />
        </button>
        <span className="mobile-topbar-title">
          {activeTab === 'audit' ? selectedBank : SCREEN_TITLES[activeTab]}
        </span>
      </header>

      {navOpen && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setNavOpen(false)}
        />
      )}

      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        selectedBank={selectedBank}
        setSelectedBank={setSelectedBank}
        version={APP_VERSION}
        isAdmin={!!me?.is_admin}
        isOpen={navOpen}
        onNavigate={() => setNavOpen(false)}
      />

      <div className="app-main">
        <main className="main-content">
          <div className={activeTab === 'audit' ? 'block' : 'hidden'}>
            <TabBankAudit onRunReport={handleRunReport} onUploadFiles={handleUploadFiles} selectedBank={selectedBank} />
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
          <div className={activeTab === 'merge' ? 'block' : 'hidden'}>
            <TabMerge />
          </div>
          <div className={activeTab === 'history' ? 'block' : 'hidden'}>
            <TabHistory />
          </div>
          {me?.is_admin && (
            <div className={activeTab === 'users' ? 'block' : 'hidden'}>
              <TabUsers currentUser={me.username} />
            </div>
          )}
          <div className={activeTab === 'settings' ? 'block' : 'hidden'}>
            <TabSettings />
          </div>
        </main>
      </div>
    </div>
  );
}
