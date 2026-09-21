'use client';
import { LayoutDashboard, TrendingUp, Brain, Briefcase, LineChart, Settings, Target, Zap, Search, Newspaper, BarChart3, RefreshCw, FileText, MessageSquare, Bot, LogOut, User } from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '@/contexts/AuthContext';

const NAV = [
  { id: 'dashboard', label: 'Overview',    icon: LayoutDashboard, group: 'Main' },
  { id: 'market',    label: 'Market Data', icon: TrendingUp, group: 'Main' },
  { id: 'predict',   label: 'Predictions', icon: Brain, group: 'AI' },
  { id: 'portfolio', label: 'Portfolio',   icon: Briefcase, group: 'Trading' },
  { id: 'backtest',  label: 'Backtesting', icon: LineChart, group: 'Trading' },
  { id: 'strategy', label: 'Strategy Builder', icon: Settings, group: 'Trading' },
  { id: 'paper', label: 'Paper Trading', icon: Target, group: 'Trading' },
  { id: 'realtime', label: 'Live Trading', icon: Zap, group: 'Trading' },
  { id: 'explain', label: 'Explainable AI', icon: Search, group: 'AI' },
  { id: 'news', label: 'News Intelligence', icon: Newspaper, group: 'Data' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, group: 'Data' },
  { id: 'mlops', label: 'MLOps', icon: RefreshCw, group: 'System' },
  { id: 'report', label: 'Reports', icon: FileText, group: 'System' },
  { id: 'assistant', label: 'AI Assistant', icon: MessageSquare, group: 'AI' },
  { id: 'agent',     label: 'Agent',        icon: Bot, group: 'AI' },
];

const GROUPS = ['Main', 'Trading', 'AI', 'Data', 'System'];

export function Sidebar({
  page, setPage,
}: {
  page: string;
  setPage: (p: string) => void;
}) {
  const { user, logout } = useAuth();

  return (
    <aside className="w-64 min-w-64 bg-surface border-r border-border flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-6 pt-6 pb-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-primary flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="font-semibold text-text-primary">QuantAI</div>
            <div className="text-[10px] uppercase tracking-wider text-text-muted">
              Quant Trading Platform
            </div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-3 overflow-y-auto">
        {GROUPS.map((group) => {
          const groupItems = NAV.filter(n => n.group === group);
          if (groupItems.length === 0) return null;
          
          return (
            <div key={group} className="mb-4">
              <div className="px-3 mb-2 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                {group}
              </div>
              {groupItems.map((n) => {
                const Icon = n.icon;
                return (
                  <button
                    key={n.id}
                    onClick={() => setPage(n.id)}
                    className={clsx(
                      'w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors',
                      page === n.id
                        ? 'bg-accent-primary text-white'
                        : 'text-text-muted hover:text-text-primary hover:bg-surface-hover',
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{n.label}</span>
                  </button>
                );
              })}
            </div>
          );
        })}
      </nav>

      {/* User Section */}
      <div className="px-3 py-4 border-t border-border">
        <div className="bg-bg rounded-lg p-3 mb-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-accent-primary/20 flex items-center justify-center">
              <User className="w-4 h-4 text-accent-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-text-primary truncate">
                {user?.name || 'User'}
              </div>
              <div className="text-xs text-text-muted truncate">
                {user?.email || ''}
              </div>
            </div>
          </div>
        </div>

        {/* Logout Button */}
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-text-muted hover:text-accent-danger hover:bg-accent-danger/10 rounded-md transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>

      {/* Status */}
      <div className="px-6 py-3 border-t border-border">
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <div className="w-2 h-2 rounded-full bg-accent-success" />
          <span>API Connected</span>
        </div>
        <div className="text-[10px] text-text-muted mt-1">localhost:8000</div>
      </div>
    </aside>
  );
}
