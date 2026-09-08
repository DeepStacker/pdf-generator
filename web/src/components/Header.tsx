import React from 'react';
import { Layers, BarChart3, History, Settings, FileText, Sun, Moon, ShieldCheck, FileStack } from 'lucide-react';

export type ActiveTab = 'audit' | 'consolidation' | 'flatten' | 'stats' | 'report' | 'history' | 'settings';

interface HeaderProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  theme: 'dark' | 'light';
  setTheme: (t: 'dark' | 'light') => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab, theme, setTheme }) => {
  const tabs: { id: ActiveTab; label: string; icon: React.FC<{ className?: string }> }[] = [
    { id: 'audit', label: 'Bank Audit', icon: FileText },
    { id: 'consolidation', label: 'Consolidation', icon: Layers },
    { id: 'report', label: 'Report Validator', icon: ShieldCheck },
    { id: 'flatten', label: 'Flatten PDF', icon: FileStack },
    { id: 'stats', label: 'Analytics', icon: BarChart3 },
    { id: 'history', label: 'History', icon: History },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  return (
    <header className="bg-[#0b0f19]/90 backdrop-blur-xl border-b border-slate-800/80 sticky top-0 z-50 px-6 py-3.5 shadow-xl transition-all">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
        {/* Brand Header */}
        <div className="flex items-center space-x-3.5">
          <div className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500 rounded-2xl blur-md opacity-75 group-hover:opacity-100 transition duration-300"></div>
            <img
              src="/logo.png"
              alt="FinConsolidate Pro Logo"
              className="relative w-11 h-11 rounded-2xl object-cover border border-cyan-400/40 shadow-xl"
            />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-cyan-100 to-blue-300">
                FinConsolidate <span className="text-cyan-400 font-black">PRO</span>
              </h1>
              <span className="text-[10px] font-mono font-extrabold text-cyan-300 bg-cyan-950/80 border border-cyan-700/60 px-2.5 py-0.5 rounded-full uppercase tracking-wider shadow-inner">
                v5.2
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">
              Multi-Bank Audit & Financial Reconciliation Suite
            </p>
          </div>
        </div>

        {/* Tab Navigation & Theme Toggle */}
        <div className="flex items-center space-x-3">
          <nav className="flex items-center space-x-1.5 bg-[#070a12] p-1.5 rounded-2xl border border-slate-800/80 shadow-inner">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition duration-200 flex items-center space-x-2 cursor-pointer ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-600/25 border border-blue-400/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>

          <button
            onClick={toggleTheme}
            className="p-2.5 rounded-2xl bg-[#070a12] border border-slate-800/80 text-slate-400 hover:text-slate-200 hover:border-slate-700 transition cursor-pointer shadow-inner"
            title="Toggle Theme"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-blue-400" />}
          </button>
        </div>
      </div>
    </header>
  );
};
