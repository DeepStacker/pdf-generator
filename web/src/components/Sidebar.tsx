import React from 'react';
import { ShieldCheck, FileStack, Combine, Users, LogOut } from 'lucide-react';
import { BANKS } from '../banks';

export type ActiveTab = 'audit' | 'consolidation' | 'flatten' | 'merge' | 'report' | 'users';

interface SidebarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  /** The banks are nav entries here, as on the desktop -- not a control inside the screen. */
  selectedBank: string;
  setSelectedBank: (bank: string) => void;
  version: string;
  /** Account management is an admin's screen; everyone else is not shown the
   *  door at all. The server refuses the endpoints regardless -- this only
   *  keeps the nav honest about what this account can do. */
  isAdmin?: boolean;
  status?: string;
  /** On a phone this is a drawer; on a desktop width it is always shown. */
  isOpen?: boolean;
  onNavigate?: () => void;
}

/**
 * The desktop app's navigation, rebuilt in React against the same stylesheet.
 * Every class here is defined in the shared web.css, so the two apps are not
 * "designed to match" -- they are drawing from one set of rules.
 */
export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, selectedBank, setSelectedBank, version, isAdmin, status, isOpen, onNavigate }) => {
  const go = (fn: () => void) => () => {
    fn();
    onNavigate?.();  // a drawer that stays open after you pick something is in the way
  };
  const tools: { id: ActiveTab; label: string; Icon: React.FC<{ className?: string }> }[] = [
    { id: 'report', label: 'Report Validator', Icon: ShieldCheck },
    { id: 'flatten', label: 'Flatten PDF', Icon: FileStack },
    { id: 'merge', label: 'Merge PDF', Icon: Combine },
  ];
  const item = (id: ActiveTab, label: string, Icon: React.FC<{ className?: string }>) => (
    <button
      key={id}
      onClick={go(() => setActiveTab(id))}
      className={`sidebar-item nav-btn${activeTab === id ? ' active' : ''}`}
    >
      <Icon />
      <span className="sidebar-item-label">{label}</span>
    </button>
  );

  return (
    <aside className={`sidebar${isOpen ? ' is-open' : ''}`}>
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
              onClick={go(() => {
                setSelectedBank(b.name);
                setActiveTab('audit');
              })}
              className={`sidebar-item bank-pill${activeTab === 'audit' && selectedBank === b.name ? ' active' : ''}`}
            >
              <span className="bank-dot" style={{ background: b.dot }} />
              <span className="sidebar-item-label">{b.nav}</span>
            </button>
          ))}
          <button
            onClick={go(() => setActiveTab('consolidation'))}
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
      </nav>

      <div className="sidebar-footer">
        {isAdmin && item('users', 'Users', Users)}
        <a href="/logout" className="sidebar-item nav-btn">
          <LogOut />
          <span className="sidebar-item-label">Sign out</span>
        </a>
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
