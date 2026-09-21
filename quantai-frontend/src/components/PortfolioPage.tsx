'use client';
import { useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend } from 'recharts';
import clsx from 'clsx';
import { Card, CardTitle, MetricCard, Badge, Button, Spinner, TickerPills, ErrorBox } from '@/components/ui';
import { optimizeMarkowitz, optimizeBL } from '@/lib/api';

const TICKERS = ['AAPL','MSFT','NVDA','TSLA','GOOGL','SPY','QQQ'];
const COLORS  = ['#3b82f6','#6366f1','#10b981','#f59e0b','#ef4444','#0ea5e9','#8b5cf6'];

export default function PortfolioPage() {
  const [tab, setTab]                   = useState('markowitz');
  const [result, setResult]             = useState<any>(null);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState<string | null>(null);
  const [objective, setObjective]       = useState('sharpe');
  const [selected, setSelected]         = useState(['AAPL','MSFT','NVDA','GOOGL','SPY']);
  const [blView, setBlView]             = useState('{"type":"absolute","ticker":"NVDA","return":0.20,"confidence":0.8}');

  const toggleTicker = (t: string) =>
    setSelected((prev) => prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]);

  const runMarkowitz = async () => {
    setLoading(true); setError(null);
    try { setResult({ type: 'mz', ...await optimizeMarkowitz(selected, objective) }); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const runBL = async () => {
    setLoading(true); setError(null);
    try {
      let views: any[] = [];
      try { views = [JSON.parse(blView)]; } catch { setError('Invalid JSON'); return; }
      setResult({ type: 'bl', ...await optimizeBL(selected, views) });
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const pieData = result?.weights
    ? Object.entries(result.weights).map(([k, v]: any) => ({ name: k, value: +(v * 100).toFixed(1) }))
    : [];

  const rm = result?.risk_metrics;

  return (
    <div className="p-8 max-w-[1400px]">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary">Portfolio Optimization</h1>
        <p className="text-sm text-text-muted mt-1">Markowitz mean-variance · Black-Litterman with investor views</p>
      </div>

      <div className="flex gap-2 border-b border-border mb-6">
        {[
          { id: 'markowitz', label: 'Markowitz' },
          { id: 'bl', label: 'Black-Litterman' }
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => { setTab(t.id); setResult(null); setError(null); }}
            className={clsx(
              'px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
              tab === t.id
                ? 'text-accent-primary border-accent-primary'
                : 'text-text-muted border-transparent hover:text-text-secondary'
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <Card className="mb-5">
        <CardTitle>Select assets</CardTitle>
        <TickerPills tickers={TICKERS} active={selected} onSelect={toggleTicker} multi />

        {tab === 'markowitz' && (
          <div className="flex gap-3 items-end mt-2">
            <div>
              <label className="text-xs text-text-muted block mb-1">Objective</label>
              <select
                className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-accent-primary"
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
              >
                <option value="sharpe">Max Sharpe Ratio</option>
                <option value="min_vol">Min Volatility</option>
                <option value="max_return">Max Return</option>
              </select>
            </div>
            <Button onClick={runMarkowitz} disabled={loading || selected.length < 2}>
              {loading ? <><Spinner /> Running...</> : '⚡ Optimize'}
            </Button>
          </div>
        )}

        {tab === 'bl' && (
          <div className="mt-3">
            <label className="text-xs text-text-muted block mb-1">View (JSON)</label>
            <textarea
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-xs font-mono text-text-primary outline-none focus:border-accent-primary resize-none"
              rows={3}
              value={blView}
              onChange={(e) => setBlView(e.target.value)}
            />
            <Button className="mt-3" onClick={runBL} disabled={loading || selected.length < 2}>
              {loading ? <><Spinner /> Running...</> : '⚡ Optimize with views'}
            </Button>
          </div>
        )}
      </Card>

      {error && <ErrorBox message={error} />}

      {result && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <MetricCard
              title="Expected annual return"
              value={`${result.expected_annual_return > 0 ? '+' : ''}${result.expected_annual_return?.toFixed(2)}%`}
              change={{ value: Math.abs(result.expected_annual_return || 0), positive: result.expected_annual_return >= 0 }}
            />
            <MetricCard
              title="Annual volatility"
              value={`${result.annual_volatility?.toFixed(2)}%`}
            />
            <MetricCard
              title="Sharpe ratio"
              value={result.sharpe_ratio?.toFixed(4)}
            />
          </div>

          <div className="grid grid-cols-2 gap-5">
            {/* Pie + weights */}
            <Card>
              <CardTitle>Optimal allocation</CardTitle>
              {pieData.length > 0 && (
                <div className="h-44 mb-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={65} paddingAngle={2}>
                        {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
              {Object.entries(result.weights || {}).map(([k, v]: any) => (
                <div key={k} className="mb-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-mono text-accent-primary">{k}</span>
                    <span className="font-mono">{(v * 100).toFixed(1)}%</span>
                  </div>
                  <div className="h-1.5 bg-border rounded-full overflow-hidden">
                    <div className="h-full bg-accent-primary rounded-full transition-all duration-500" style={{ width: `${v * 100}%` }} />
                  </div>
                </div>
              ))}
            </Card>

            {/* Risk metrics */}
            <Card>
              <CardTitle>Risk metrics</CardTitle>
              {rm && [
                { label: 'Max drawdown',    value: `${(rm.max_drawdown * 100).toFixed(2)}%`,    color: '#ef4444' },
                { label: 'VaR 95%',         value: `${(rm.var_95 * 100).toFixed(2)}%`,          color: '#ef4444' },
                { label: 'CVaR 95%',        value: `${(rm.cvar_95 * 100).toFixed(2)}%`,         color: '#ef4444' },
                { label: 'Sortino ratio',   value: rm.sortino_ratio?.toFixed(4),                color: '#10b981' },
                { label: 'Calmar ratio',    value: rm.calmar_ratio?.toFixed(4),                 color: '#3b82f6' },
                { label: 'Positive days',   value: `${rm.positive_days_pct?.toFixed(1)}%`,      color: '#10b981' },
                { label: 'Skewness',        value: rm.skewness?.toFixed(4),                     color: '#64748b' },
              ].map((m) => (
                <div key={m.label} className="flex justify-between py-2 border-b border-border last:border-0">
                  <span className="text-xs text-text-muted">{m.label}</span>
                  <span className="font-mono text-xs" style={{ color: m.color }}>{m.value}</span>
                </div>
              ))}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
