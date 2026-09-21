'use client';
import { useState } from 'react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell } from 'recharts';
import clsx from 'clsx';
import { Card, CardTitle, MetricCard, Badge, Button, Spinner, TickerPills, ErrorBox } from '@/components/ui';
import { ChartTooltip } from '@/components/charts/Tooltip';
import { backtestCompare, backtestBuyHold, backtestSMA, backtestRSI, backtestMACD } from '@/lib/api';

const TICKERS = ['AAPL','MSFT','NVDA','TSLA','GOOGL','SPY','QQQ'];

const STRATEGY_ACTIONS: { id: string; label: string; fn: (t: string) => Promise<any> }[] = [
  { id: 'buy_hold', label: 'Buy & Hold',  fn: (t) => backtestBuyHold(t) },
  { id: 'sma',      label: 'SMA 10/30',  fn: (t) => backtestSMA(t, 10, 30) },
  { id: 'rsi',      label: 'RSI 14',     fn: (t) => backtestRSI(t) },
  { id: 'macd',     label: 'MACD',       fn: (t) => backtestMACD(t) },
];

export default function BacktestPage() {
  const [ticker, setTicker]   = useState('AAPL');
  const [tab, setTab]         = useState('compare');
  const [result, setResult]   = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const run = async (fn: () => Promise<any>) => {
    setLoading(true); setError(null); setResult(null);
    try { setResult(await fn()); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const equityData = result?.equity_curve
    ?.filter((_: any, i: number) => i % 3 === 0)
    .map((d: any) => ({ date: d.date?.slice(5), value: d.value })) || [];

  const compareData = result?.comparison
    ? Object.entries(result.comparison).map(([k, v]: any) => ({
        name: k.replace(/_/g, ' '),
        return: v.total_return_pct,
        sharpe: v.sharpe_ratio,
      }))
    : [];

  return (
    <div className="p-8 max-w-[1400px]">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary">Backtesting</h1>
        <p className="text-sm text-text-muted mt-1">Historical strategy simulation on real OHLCV data · $100k initial capital</p>
      </div>

      <TickerPills tickers={TICKERS} active={ticker} onSelect={setTicker} />

      <div className="flex gap-2 border-b border-border mb-6">
        {[
          { id: 'compare', label: 'Compare all' },
          { id: 'single', label: 'Single strategy' }
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

      {tab === 'compare' && (
        <Button onClick={() => run(() => backtestCompare(ticker))} disabled={loading} className="mb-5">
          {loading ? <><Spinner /> Running...</> : '⚡ Run comparison'}
        </Button>
      )}

      {tab === 'single' && (
        <div className="flex gap-3 mb-5 flex-wrap">
          {STRATEGY_ACTIONS.map((s) => (
            <Button key={s.id} variant="secondary" onClick={() => run(() => s.fn(ticker))} disabled={loading}>
              {loading ? <Spinner /> : s.label}
            </Button>
          ))}
        </div>
      )}

      {error && <ErrorBox message={error} />}

      {/* Compare results */}
      {result?.comparison && (
        <>
          <div className="grid grid-cols-5 gap-4 mb-5">
            {Object.entries(result.comparison).map(([k, v]: any) => (
              <div
                key={k}
                className={clsx('bg-surface border rounded-lg p-4', result.best_strategy === k ? 'border-accent-primary' : 'border-border')}
              >
                {result.best_strategy === k && (
                  <p className="text-[10px] text-accent-primary uppercase tracking-wider mb-1">★ Best</p>
                )}
                <p className="text-xs text-text-muted mb-2">{k.replace(/_/g, ' ')}</p>
                <p className={clsx('font-mono text-xl font-medium', v.total_return_pct >= 0 ? 'text-accent-success' : 'text-accent-danger')}>
                  {v.total_return_pct >= 0 ? '+' : ''}{v.total_return_pct?.toFixed(2)}%
                </p>
                <p className="text-xs text-text-muted mt-1">Sharpe: {v.sharpe_ratio?.toFixed(2)} · DD: {v.max_drawdown_pct?.toFixed(1)}%</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-5">
            <Card>
              <CardTitle>Return by strategy</CardTitle>
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={compareData} barSize={28}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} />
                    <ChartTooltip />
                    <Bar dataKey="return" name="Return %" radius={[4, 4, 0, 0]}>
                      {compareData.map((d, i) => <Cell key={i} fill={d.return >= 0 ? '#10b981' : '#ef4444'} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <CardTitle>Strategy ranking</CardTitle>
              <table className="w-full text-xs">
                <thead>
                  <tr>
                    {['#', 'Strategy', 'Return', 'Sharpe', 'Trades'].map((h) => (
                      <th key={h} className="text-left pb-2 text-[11px] uppercase tracking-wider text-text-muted">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.ranking.map((r: any) => {
                    const v = result.comparison[r.strategy];
                    return (
                      <tr key={r.strategy} className="border-t border-border">
                        <td className="py-2 font-mono font-bold" style={{ color: r.rank === 1 ? '#f59e0b' : '#64748b' }}>{r.rank}</td>
                        <td className="py-2">{r.strategy.replace(/_/g, ' ')}</td>
                        <td className={clsx('py-2 font-mono', v?.total_return_pct >= 0 ? 'text-accent-success' : 'text-accent-danger')}>
                          {v?.total_return_pct >= 0 ? '+' : ''}{v?.total_return_pct?.toFixed(2)}%
                        </td>
                        <td className="py-2 font-mono">{r.sharpe?.toFixed(2)}</td>
                        <td className="py-2 font-mono text-text-muted">{v?.num_trades}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Card>
          </div>
        </>
      )}

      {/* Single strategy result */}
      {result?.strategy && !result?.comparison && (
        <>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <MetricCard
              title="Total return"
              value={`${result.total_return_pct >= 0 ? '+' : ''}${result.total_return_pct?.toFixed(2)}%`}
              change={{ value: Math.abs(result.total_return_pct || 0), positive: result.total_return_pct >= 0 }}
            />
            <MetricCard
              title="Sharpe ratio"
              value={result.sharpe_ratio?.toFixed(4)}
            />
            <MetricCard
              title="Max drawdown"
              value={`${result.max_drawdown_pct?.toFixed(2)}%`}
            />
            <MetricCard
              title="Win rate"
              value={`${result.win_rate_pct?.toFixed(1)}%`}
            />
          </div>

          {equityData.length > 0 && (
            <Card className="mb-5">
              <CardTitle>Equity curve — {result.strategy} on {result.ticker}</CardTitle>
              <div className="h-60">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={equityData}>
                    <defs>
                      <linearGradient id="eg" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#10b981" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} domain={['auto','auto']} />
                    <ChartTooltip />
                    <Area type="monotone" dataKey="value" stroke="#10b981" strokeWidth={1.5} fill="url(#eg)" dot={false} name="Portfolio $" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {result.trades?.length > 0 && (
            <Card>
              <CardTitle>Trade log ({result.trades.length} trades)</CardTitle>
              <table className="w-full text-xs">
                <thead>
                  <tr>
                    {['Date', 'Action', 'Price', 'Shares', 'Value', 'Portfolio'].map((h) => (
                      <th key={h} className="text-left pb-2 text-[11px] uppercase tracking-wider text-text-muted">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.trades.slice(0, 20).map((t: any, i: number) => (
                    <tr key={i} className="border-t border-border">
                      <td className="py-2 font-mono text-text-muted">{t.date}</td>
                      <td className="py-2"><Badge variant={t.action === 'BUY' ? 'success' : 'danger'}>{t.action}</Badge></td>
                      <td className="py-2 font-mono">${t.price?.toFixed(2)}</td>
                      <td className="py-2 font-mono">{t.shares?.toFixed(4)}</td>
                      <td className="py-2 font-mono">${t.value?.toLocaleString('en-US', { maximumFractionDigits: 0 })}</td>
                      <td className="py-2 font-mono">${t.portfolio_value?.toLocaleString('en-US', { maximumFractionDigits: 0 })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
