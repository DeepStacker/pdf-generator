import React from 'react';
import { ShieldCheck, FileStack, BarChart3, History, Settings } from 'lucide-react';
import { BANKS } from '../banks';

export type ActiveTab = 'audit' | 'consolidation' | 'flatten' | 'stats' | 'report' | 'history' | 'settings';

interface SidebarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  /** The banks are nav entries here, as on the desktop -- not a control inside the screen. */
  selectedBank: string;
  setSelectedBank: (bank: string) => void;
  version: string;
  status?: string;
}

/**
 * The desktop app's navigation, rebuilt in React against the same stylesheet.
 * Every class here is defined in the shared web.css, so the two apps are not
 * "designed to match" -- they are drawing from one set of rules.
 */
export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, selectedBank, setSelectedBank, version, status }) => {
  const tools: { id: ActiveTab; label: string; Icon: React.FC<{ className?: string }> }[] = [
    { id: 'report', label: 'Report Validator', Icon: ShieldCheck },
    { id: 'flatten', label: 'Flatten PDF', Icon: FileStack },
  ];
  const insights: { id: ActiveTab; label: string; Icon: React.FC<{ className?: string }> }[] = [
    { id: 'stats', label: 'Analytics', Icon: BarChart3 },
    { id: 'history', label: 'History', Icon: History },
  ];

  const item = (id: ActiveTab, label: string, Icon: React.FC<{ className?: string }>) => (
    <button
      key={id}
      onClick={() => setActiveTab(id)}
      className={`sidebar-item nav-btn${activeTab === id ? ' active' : ''}`}
    >
      <Icon />
      <span className="sidebar-item-label">{label}</span>
    </button>
  );

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="logo-mark">
          <svg viewBox="0 0 32 32" fill="none">
            <rect x="2" y="2" width="28" height="28" rx="8" fill="url(#logo-grad)" />
            <text x="16" y="21" textAnchor="middle" fill="#fff" fontSize="12" fontWeight="800" fontFamily="system-ui">GM</text>
            <defs>
              <linearGradient id="logo-grad" x1="0" y1="0" x2="32" y2="32">
                <stop offset="0%" stopColor="#4c6fff" />
                <stop offset="100%" stopColor="#5c7cfa" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div className="flex flex-col leading-tight">
          <span className="navbar-logo-text">GSS-MIS</span>
          <span className="navbar-logo-sub">v{version}</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="sidebar-group">
          <span className="sidebar-group-label">Reports</span>
          {BANKS.map((b) => (
            <button
              key={b.name}
              onClick={() => {
                setSelectedBank(b.name);
                setActiveTab('audit');
              }}
              className={`sidebar-item bank-pill${activeTab === 'audit' && selectedBank === b.name ? ' active' : ''}`}
            >
              <span className="bank-dot" style={{ background: b.dot }} />
              <span className="sidebar-item-label">{b.nav}</span>
            </button>
          ))}
          <button
            onClick={() => setActiveTab('consolidation')}
            className={`sidebar-item bank-pill${activeTab === 'consolidation' ? ' active' : ''}`}
          >
            <span className="bank-dot" style={{ background: '#8b7fe8' }} />
            <span className="sidebar-item-label">Consolidation</span>
          </button>
        </div>

        <div className="sidebar-group">
          <span className="sidebar-group-label">Tools</span>
          {tools.map((t) => item(t.id, t.label, t.Icon))}
        </div>

        <div className="sidebar-group">
          <span className="sidebar-group-label">Insights</span>
          {insights.map((t) => item(t.id, t.label, t.Icon))}
        </div>
      </nav>

      <div className="sidebar-footer">
        {item('settings', 'Settings', Settings)}
        <div className="sidebar-status">
          <span className="sidebar-status-text">
            <span className="status-dot" />
            {status || 'Idle. Ready.'}
          </span>
        </div>
      </div>
    </aside>
  );
};
