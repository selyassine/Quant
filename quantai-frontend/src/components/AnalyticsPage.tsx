'use client';
import { useState, useCallback } from 'react';
import {
  LineChart, Line, AreaChart, Area,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Legend,
} from 'recharts';
import { Card, CardTitle, MetricCard, Badge, Spinner } from '@/components/ui';
import clsx from 'clsx';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'SPY', 'QQQ'];

const DEFAULT_WEIGHTS: Record<string, number> = {
  AAPL: 0.30,
  MSFT: 0.25,
  NVDA: 0.25,
  SPY:  0.20,
};

// ─── colour helpers ──────────────────────────────────────────────────────────
const CORR_COLOR = (v: number) => {
  if (v >= 0.8)  return '#ef4444';
  if (v >= 0.6)  return '#f97316';
  if (v >= 0.4)  return '#eab308';
  if (v >= 0.2)  return '#22c55e';
  if (v >= 0)    return '#3b82f6';
  if (v >= -0.2) return '#6366f1';
  return '#8b5cf6';
};

const SECTOR_COLORS = ['#38bdf8','#818cf8','#34d399','#fbbf24','#f87171','#a78bfa'];

type Tab = 'correlation' | 'rolling' | 'attribution' | 'drawdown' | 'sector';

export default function AnalyticsPage() {
  const [tab, setTab]             = useState<Tab>('correlation');
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');

  // selected tickers for correlation
  const [selTickers, setSelTickers] = useState<string[]>(['AAPL','MSFT','NVDA','GOOGL','SPY']);
  const [days, setDays]             = useState(252);
  const [window, setWindow]         = useState(30);

  // portfolio weights
  const [weights, setWeights] = useState<Record<string,number>>(DEFAULT_WEIGHTS);

  // results
  const [corrData,   setCorrData]   = useState<any>(null);
  const [rollingData, setRollingData] = useState<any>(null);
  const [attrData,   setAttrData]   = useState<any>(null);
  const [ddData,     setDdData]     = useState<any>(null);
  const [sectorData, setSectorData] = useState<any>(null);

  // ── fetch helpers ────────────────────────────────────────────────────────
  const post = async (path: string, body: object) => {
    const r = await fetch(`${API}/api/v1/analytics/${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  };

  const run = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const tickers = Object.keys(weights).filter(t => weights[t] > 0);

      if (tab === 'correlation') {
        const d = await post('correlation', { tickers: selTickers, days });
        setCorrData(d);
      } else if (tab === 'rolling') {
        const d = await post('rolling', { tickers, weights, days, window });
        setRollingData(d);
      } else if (tab === 'attribution') {
        const d = await post('attribution', { weights, days });
        setAttrData(d);
      } else if (tab === 'drawdown') {
        const d = await post('drawdown', { tickers, weights, days });
        setDdData(d);
      } else if (tab === 'sector') {
        const r = await fetch(`${API}/api/v1/analytics/sector`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(weights),
        });
        if (!r.ok) throw new Error((await r.json()).detail);
        setSectorData(await r.json());
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [tab, selTickers, weights, days, window]);

  // ── weight editor ────────────────────────────────────────────────────────
  const toggleTicker = (t: string) => {
    setWeights(prev => {
      const next = { ...prev };
      if (next[t]) delete next[t]; else next[t] = 0.25;
      return next;
    });
  };
  const setWeight = (t: string, v: number) =>
    setWeights(prev => ({ ...prev, [t]: v }));

  const totalW = Object.values(weights).reduce((a, b) => a + b, 0);

  // ── tabs ─────────────────────────────────────────────────────────────────
  const TABS: { id: Tab; label: string }[] = [
    { id: 'correlation', label: 'Correlation' },
    { id: 'rolling',     label: 'Rolling Metrics' },
    { id: 'attribution', label: 'Attribution' },
    { id: 'drawdown',    label: 'Drawdown' },
    { id: 'sector',      label: 'Sector' },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Portfolio Analytics</h1>
        <p className="text-sm text-text-muted mt-1">
          Correlation · Rolling metrics · Performance attribution · Drawdown · Sector exposure
        </p>
      </div>

      {/* tab bar */}
      <div className="flex gap-1 bg-surface rounded-lg p-1 w-fit">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => { setTab(t.id); }}
            className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              tab === t.id
                ? 'bg-accent-primary text-black'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* ── LEFT PANEL: controls ──────────────────────────────────────── */}
        <div className="space-y-4">
          {/* portfolio weights — shown for all tabs except correlation */}
          {tab !== 'correlation' && (
            <Card>
              <CardTitle>Portfolio weights</CardTitle>
              <div className="space-y-3">
                {TICKERS.map(t => {
                  const active = t in weights;
                  return (
                    <div key={t}>
                      <div className="flex items-center justify-between mb-1">
                        <button
                          onClick={() => toggleTicker(t)}
                          className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                            active ? 'bg-accent-primary text-black' : 'bg-surface text-text-muted'
                          }`}
                        >
                          {t}
                        </button>
                        {active && (
                          <span className="text-xs text-text-muted">
                            {Math.round((weights[t] / totalW) * 100)}%
                          </span>
                        )}
                      </div>
                      {active && (
                        <input
                          type="range" min={0.05} max={0.6} step={0.05}
                          value={weights[t]}
                          onChange={e => setWeight(t, parseFloat(e.target.value))}
                          className="w-full accent-accent-primary"
                        />
                      )}
                    </div>
                  );
                })}
                <div className={`text-xs text-center mt-2 ${Math.abs(totalW - 1) > 0.01 ? 'text-accent-danger' : 'text-accent-success'}`}>
                  Total: {Math.round(totalW * 100)}% {Math.abs(totalW - 1) > 0.01 ? '⚠ not 100%' : '✓'}
                </div>
              </div>
            </Card>
          )}

          {/* ticker picker — correlation only */}
          {tab === 'correlation' && (
            <Card>
              <CardTitle>Select assets</CardTitle>
              <div className="flex flex-wrap gap-1">
                {TICKERS.map(t => (
                  <button
                    key={t}
                    onClick={() =>
                      setSelTickers(prev =>
                        prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]
                      )
                    }
                    className={`text-xs font-mono px-2 py-1 rounded ${
                      selTickers.includes(t) ? 'bg-accent-primary text-black' : 'bg-surface text-text-muted'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </Card>
          )}

          {/* period */}
          <Card>
            <CardTitle>Period</CardTitle>
            <select
              value={days}
              onChange={e => setDays(+e.target.value)}
              className="w-full bg-surface border border-border rounded px-2 py-1 text-sm text-text-primary"
            >
              <option value={63}>3 months</option>
              <option value={126}>6 months</option>
              <option value={252}>1 year</option>
              <option value={504}>2 years</option>
            </select>
          </Card>

          {/* window — rolling only */}
          {tab === 'rolling' && (
            <Card>
              <CardTitle>Rolling window</CardTitle>
              <select
                value={window}
                onChange={e => setWindow(+e.target.value)}
                className="w-full bg-surface border border-border rounded px-2 py-1 text-sm text-text-primary"
              >
                <option value={10}>10 days</option>
                <option value={20}>20 days</option>
                <option value={30}>30 days</option>
                <option value={60}>60 days</option>
              </select>
            </Card>
          )}

          <button
            onClick={run}
            disabled={loading}
            className="w-full bg-accent-primary text-black font-bold py-2 rounded hover:bg-accent-primary/80 disabled:opacity-50 transition-colors"
          >
            {loading ? '⏳ Computing…' : '⚡ Run'}
          </button>

          {error && (
            <div className="text-accent-danger text-xs bg-accent-danger/10 rounded p-2">{error}</div>
          )}
        </div>

        {/* ── RIGHT PANEL: results ──────────────────────────────────────── */}
        <div className="xl:col-span-3 space-y-4">

          {/* ─── CORRELATION ─────────────────────────────────────────────── */}
          {tab === 'correlation' && corrData && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <MetricCard title="Assets" value={corrData.tickers.length} />
                <MetricCard title="Period" value={`${corrData.period_days}d`} />
                <MetricCard
                  title="Top pair"
                  value={corrData.top_correlated[0]?.pair ?? '—'}
                />
              </div>

              {/* heatmap */}
              <Card>
                <CardTitle>Correlation heatmap</CardTitle>
                <div
                  className="grid gap-1"
                  style={{
                    gridTemplateColumns: `80px repeat(${corrData.tickers.length}, 1fr)`,
                  }}
                >
                  {/* header row */}
                  <div />
                  {corrData.tickers.map((t: string) => (
                    <div key={t} className="text-center text-xs text-text-muted font-mono py-1">{t}</div>
                  ))}
                  {/* rows */}
                  {corrData.tickers.map((row: string) => (
                    <>
                      <div key={row} className="text-xs text-text-muted font-mono flex items-center">{row}</div>
                      {corrData.tickers.map((col: string) => {
                        const cell = corrData.matrix.find((m: any) => m.x === col && m.y === row);
                        const v = cell?.value ?? 0;
                        return (
                          <div
                            key={col}
                            title={`${row}/${col}: ${v.toFixed(2)}`}
                            className="aspect-square rounded flex items-center justify-center text-xs font-bold text-text-primary"
                            style={{ backgroundColor: CORR_COLOR(v) + 'cc' }}
                          >
                            {v.toFixed(2)}
                          </div>
                        );
                      })}
                    </>
                  ))}
                </div>
              </Card>

              {/* top pairs */}
              <Card>
                <CardTitle>Most correlated pairs</CardTitle>
                <div className="space-y-2">
                  {corrData.top_correlated.map((p: any, i: number) => (
                    <div key={i} className="flex items-center justify-between">
                      <span className="text-sm font-mono text-text-primary">{p.pair}</span>
                      <div className="flex items-center gap-2">
                        <div className="h-2 rounded" style={{
                          width: `${Math.abs(p.correlation) * 120}px`,
                          backgroundColor: CORR_COLOR(p.correlation),
                        }} />
                        <span className="text-xs text-text-muted w-10 text-right">
                          {(p.correlation * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </>
          )}

          {/* ─── ROLLING ─────────────────────────────────────────────────── */}
          {tab === 'rolling' && rollingData && (
            <>
              <Card>
                <CardTitle>Rolling Sharpe ({rollingData.window_days}d window)</CardTitle>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={rollingData.rolling_sharpe}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }}
                      tickFormatter={d => d.slice(5)} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', border: '1px solid #334155' }}
                      formatter={(v: any) => [v.toFixed(2), 'Sharpe']}
                    />
                    <Line dataKey="value" stroke="#38bdf8" dot={false} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </Card>

              <Card>
                <CardTitle>Cumulative return</CardTitle>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={rollingData.cumulative_return}>
                    <defs>
                      <linearGradient id="cumGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }}
                      tickFormatter={d => d.slice(5)} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }}
                      tickFormatter={v => `${v.toFixed(1)}%`} />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', border: '1px solid #334155' }}
                      formatter={(v: any) => [`${v.toFixed(2)}%`, 'Return']}
                    />
                    <Area dataKey="value" stroke="#38bdf8" fill="url(#cumGrad)" dot={false} strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </Card>

              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardTitle>Rolling volatility (ann.)</CardTitle>
                  <ResponsiveContainer width="100%" height={160}>
                    <LineChart data={rollingData.rolling_vol}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#64748b' }}
                        tickFormatter={d => d.slice(5)} interval="preserveStartEnd" />
                      <YAxis tick={{ fontSize: 9, fill: '#64748b' }}
                        tickFormatter={v => `${v.toFixed(0)}%`} />
                      <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }}
                        formatter={(v: any) => [`${v.toFixed(1)}%`, 'Vol']} />
                      <Line dataKey="value" stroke="#f97316" dot={false} strokeWidth={1.5} />
                    </LineChart>
                  </ResponsiveContainer>
                </Card>

                <Card>
                  <CardTitle>Rolling return (ann.)</CardTitle>
                  <ResponsiveContainer width="100%" height={160}>
                    <LineChart data={rollingData.rolling_return}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#64748b' }}
                        tickFormatter={d => d.slice(5)} interval="preserveStartEnd" />
                      <YAxis tick={{ fontSize: 9, fill: '#64748b' }}
                        tickFormatter={v => `${v.toFixed(0)}%`} />
                      <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }}
                        formatter={(v: any) => [`${v.toFixed(1)}%`, 'Return']} />
                      <Line dataKey="value" stroke="#34d399" dot={false} strokeWidth={1.5} />
                    </LineChart>
                  </ResponsiveContainer>
                </Card>
              </div>
            </>
          )}

          {/* ─── ATTRIBUTION ─────────────────────────────────────────────── */}
          {tab === 'attribution' && attrData && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <MetricCard
                  title="Total return"
                  value={`${attrData.total_return_pct > 0 ? '+' : ''}${attrData.total_return_pct}%`}
                  change={{ value: Math.abs(attrData.total_return_pct || 0), positive: attrData.total_return_pct > 0 }}
                />
                <MetricCard title="Best contributor" value={attrData.best_contributor ?? '—'} />
                <MetricCard title="Worst contributor" value={attrData.worst_contributor ?? '—'} />
              </div>

              <Card>
                <CardTitle>Contribution by asset</CardTitle>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={attrData.attribution} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }}
                      tickFormatter={v => `${v.toFixed(1)}%`} />
                    <YAxis dataKey="ticker" type="category" tick={{ fontSize: 11, fill: '#f8fafc', fontFamily: 'monospace' }} width={60} />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', border: '1px solid #334155' }}
                      formatter={(v: any) => [`${v.toFixed(2)}%`, 'Contribution']}
                    />
                    <Bar dataKey="contribution" radius={[0, 3, 3, 0]}>
                      {attrData.attribution.map((a: any, i: number) => (
                        <Cell key={i} fill={a.contribution >= 0 ? '#34d399' : '#f87171'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              <Card>
                <CardTitle>Attribution detail</CardTitle>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-muted border-b border-border">
                      {['Ticker','Weight','Return','Contribution','Volatility','Sharpe'].map(h => (
                        <th key={h} className="text-left py-2 pr-4">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {attrData.attribution.map((a: any, i: number) => (
                      <tr key={i} className="border-b border-border/30 hover:bg-surface/50">
                        <td className="py-2 pr-4 font-mono font-bold text-text-primary">{a.ticker}</td>
                        <td className="py-2 pr-4 text-text-muted">{a.weight_pct}%</td>
                        <td className={`py-2 pr-4 ${a.asset_return >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
                          {a.asset_return > 0 ? '+' : ''}{a.asset_return}%
                        </td>
                        <td className={`py-2 pr-4 font-semibold ${a.contribution >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
                          {a.contribution > 0 ? '+' : ''}{a.contribution}%
                        </td>
                        <td className="py-2 pr-4 text-text-muted">{a.volatility}%</td>
                        <td className="py-2 text-text-muted">{a.sharpe}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </>
          )}

          {/* ─── DRAWDOWN ────────────────────────────────────────────────── */}
          {tab === 'drawdown' && ddData && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <MetricCard title="Max drawdown" value={`${ddData.max_drawdown_pct}%`} />
                <MetricCard title="Current drawdown" value={`${ddData.current_drawdown_pct}%`} />
                <MetricCard title="Avg drawdown" value={`${ddData.avg_drawdown_pct}%`} />
              </div>

              <Card>
                <CardTitle>Underwater chart</CardTitle>
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={ddData.drawdown_series}>
                    <defs>
                      <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }}
                      tickFormatter={d => d.slice(5)} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }}
                      tickFormatter={v => `${v.toFixed(1)}%`} />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', border: '1px solid #334155' }}
                      formatter={(v: any) => [`${v.toFixed(2)}%`, 'Drawdown']}
                    />
                    <Area dataKey="drawdown" stroke="#ef4444" fill="url(#ddGrad)" dot={false} strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </Card>

              {ddData.worst_periods.length > 0 && (
                <Card>
                  <CardTitle>Worst drawdown periods</CardTitle>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-text-muted border-b border-border">
                        {['Start','End','Duration','Max drawdown'].map(h => (
                          <th key={h} className="text-left py-2 pr-4">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {ddData.worst_periods.map((p: any, i: number) => (
                        <tr key={i} className="border-b border-border/30 hover:bg-surface/50">
                          <td className="py-2 pr-4 text-text-primary">{p.start}</td>
                          <td className="py-2 pr-4 text-text-primary">{p.end}</td>
                          <td className="py-2 pr-4 text-text-muted">{p.duration_days}d</td>
                          <td className="py-2 text-accent-danger font-bold">{p.max_drawdown_pct}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
              )}
            </>
          )}

          {/* ─── SECTOR ──────────────────────────────────────────────────── */}
          {tab === 'sector' && sectorData && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <MetricCard title="Sectors" value={sectorData.num_sectors} />
                <MetricCard title="Most exposed" value={sectorData.most_exposed ?? '—'} />
              </div>

              <Card>
                <CardTitle>Sector allocation</CardTitle>
                <div className="space-y-3">
                  {sectorData.sector_exposure.map((s: any, i: number) => (
                    <div key={i}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-text-primary">{s.sector}</span>
                        <span className="text-text-muted font-mono">{s.pct}%</span>
                      </div>
                      <div className="h-2 bg-surface rounded overflow-hidden">
                        <div
                          className="h-full rounded"
                          style={{
                            width: `${s.pct}%`,
                            backgroundColor: SECTOR_COLORS[i % SECTOR_COLORS.length],
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              <Card>
                <CardTitle>Breakdown</CardTitle>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={sectorData.sector_exposure}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="sector" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }}
                      tickFormatter={v => `${v}%`} />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', border: '1px solid #334155' }}
                      formatter={(v: any) => [`${v.toFixed(1)}%`, 'Exposure']}
                    />
                    <Bar dataKey="pct" radius={[3, 3, 0, 0]}>
                      {sectorData.sector_exposure.map((_: any, i: number) => (
                        <Cell key={i} fill={SECTOR_COLORS[i % SECTOR_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </>
          )}

          {/* empty state */}
          {!loading && !error && (
            (tab === 'correlation' && !corrData) ||
            (tab === 'rolling'     && !rollingData) ||
            (tab === 'attribution' && !attrData) ||
            (tab === 'drawdown'    && !ddData) ||
            (tab === 'sector'      && !sectorData)
          ) && (
            <div className="flex flex-col items-center justify-center h-64 text-text-muted gap-3">
              <span className="text-4xl">◎</span>
              <p className="text-sm">Configure your portfolio and click ⚡ Run</p>
            </div>
          )}

          {loading && (
            <div className="flex items-center justify-center h-64">
              <Spinner />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
