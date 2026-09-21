'use client';
import { useEffect, useState } from 'react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell } from 'recharts';
import clsx from 'clsx';
import { Card, CardTitle, MetricCard, Badge, Button, Spinner, ErrorBox } from '@/components/ui';
import { ChartTooltip } from '@/components/charts/Tooltip';

const API = 'http://localhost:8000/api/v1/strategy';
const TICKERS = ['AAPL','MSFT','NVDA','TSLA','GOOGL','SPY','QQQ'];

const INDICATOR_GROUPS = [
  { label: 'Price',           items: ['close','open','high','low','volume'] },
  { label: 'Moving Average',  items: ['sma_20','sma_50','sma_200','ema_20','ema_50','ema_200'] },
  { label: 'Momentum',        items: ['rsi_14','macd','macd_signal','macd_hist','stoch_k','stoch_d','mom_10','roc_10'] },
  { label: 'Volatility',      items: ['bb_upper_20','bb_lower_20','bb_mid_20','bb_width_20','atr_14','hvol_20'] },
  { label: 'Volume',          items: ['vol_sma_20','vol_ratio_20','vwap_20'] },
];
const OPERATORS = ['>', '<', '>=', '<=', '==', 'cross_above', 'cross_below'];

async function apiFetch(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
  if (!res.ok) { const e = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(e.detail || 'API error'); }
  return res.json();
}

interface RuleForm { indicator: string; operator: string; value: string; }

const defaultRule = (): RuleForm => ({ indicator: 'rsi_14', operator: '<', value: '30' });

export default function StrategyPage() {
  const [tab, setTab]         = useState('builder');
  const [ticker, setTicker]   = useState('AAPL');
  const [name, setName]       = useState('My Strategy');
  const [logic, setLogic]     = useState('AND');
  const [days, setDays]       = useState(252);
  const [buyRules, setBuyRules]   = useState<RuleForm[]>([defaultRule()]);
  const [sellRules, setSellRules] = useState<RuleForm[]>([{ indicator: 'rsi_14', operator: '>', value: '70' }]);
  const [stopLoss, setStopLoss]   = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [presets, setPresets] = useState<any[]>([]);
  const [result, setResult]   = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    apiFetch('/presets').then(setPresets).catch(console.error);
  }, []);

  const updateRule = (rules: RuleForm[], setRules: any, idx: number, field: string, value: string) => {
    const updated = [...rules];
    updated[idx] = { ...updated[idx], [field]: value };
    setRules(updated);
  };

  const runStrategy = async () => {
    setLoading(true); setError(null);
    try {
      const payload = {
        ticker, name, logic, days,
        buy_rules:  buyRules.map(r => ({ indicator: r.indicator, operator: r.operator, value: isNaN(Number(r.value)) ? r.value : Number(r.value) })),
        sell_rules: sellRules.map(r => ({ indicator: r.indicator, operator: r.operator, value: isNaN(Number(r.value)) ? r.value : Number(r.value) })),
        stop_loss_pct:   stopLoss    ? parseFloat(stopLoss) / 100    : null,
        take_profit_pct: takeProfit  ? parseFloat(takeProfit) / 100  : null,
      };
      setResult(await apiFetch('/run', { method: 'POST', body: JSON.stringify(payload) }));
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const runPreset = async (idx: number) => {
    setLoading(true); setError(null);
    try {
      setResult(await apiFetch('/run/preset', { method: 'POST', body: JSON.stringify({ ticker, preset_idx: idx, days }) }));
      setTab('builder');
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const equityData = result?.equity_curve?.filter((_: any, i: number) => i % 3 === 0)
    .map((d: any) => ({ date: d.date?.slice(5), value: d.value })) || [];

  const pnlColor = (v: number) => v >= 0 ? '#10b981' : '#ef4444';

  const RuleRow = ({ rules, setRules, label, color }: { rules: RuleForm[]; setRules: any; label: string; color: string }) => (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium" style={{ color }}>{label}</span>
        <Button variant="ghost" onClick={() => setRules([...rules, defaultRule()])} className="text-xs py-1 px-2">+ Add rule</Button>
      </div>
      {rules.map((rule, i) => (
        <div key={i} className="flex gap-2 mb-2 items-center">
          <select className="flex-1 bg-surface border border-border rounded-lg px-2 py-1.5 text-xs text-text-primary outline-none focus:border-accent-primary"
            value={rule.indicator} onChange={e => updateRule(rules, setRules, i, 'indicator', e.target.value)}>
            {INDICATOR_GROUPS.map(g => (
              <optgroup key={g.label} label={g.label}>
                {g.items.map(item => <option key={item} value={item}>{item}</option>)}
              </optgroup>
            ))}
          </select>
          <select className="w-32 bg-surface border border-border rounded-lg px-2 py-1.5 text-xs text-text-primary outline-none focus:border-accent-primary"
            value={rule.operator} onChange={e => updateRule(rules, setRules, i, 'operator', e.target.value)}>
            {OPERATORS.map(op => <option key={op} value={op}>{op}</option>)}
          </select>
          <input className="w-28 bg-surface border border-border rounded-lg px-2 py-1.5 text-xs font-mono text-text-primary outline-none focus:border-accent-primary"
            value={rule.value} onChange={e => updateRule(rules, setRules, i, 'value', e.target.value)}
            placeholder="30 or sma_50" />
          {rules.length > 1 && (
            <button onClick={() => setRules(rules.filter((_, j) => j !== i))} className="text-text-muted hover:text-accent-danger text-sm w-6">×</button>
          )}
        </div>
      ))}
    </div>
  );

  return (
    <div className="p-8 max-w-[1400px]">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary">Strategy Builder</h1>
        <p className="text-sm text-text-muted mt-1">Create trading strategies from rules — no coding required</p>
      </div>

      <div className="flex gap-2 border-b border-border mb-6">
        {[
          { id: 'builder', label: 'Custom Strategy' },
          { id: 'presets', label: 'Presets' }
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
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

      {/* ── PRESETS ─────────────────────────────────────────────── */}
      {tab === 'presets' && (
        <div className="grid grid-cols-2 gap-4">
          {presets.map((p, i) => (
            <Card key={i}>
              <div className="flex justify-between items-start mb-2">
                <div>
                  <p className="font-medium text-sm">{p.name}</p>
                  <p className="text-xs text-text-muted mt-1">{p.description}</p>
                </div>
                <Button onClick={() => runPreset(i)} disabled={loading} className="ml-4 shrink-0">
                  {loading ? <Spinner /> : '▶ Run'}
                </Button>
              </div>
              <div className="mt-3 space-y-1">
                {p.buy_rules.map((r: any, j: number) => (
                  <p key={j} className="text-xs font-mono"><span className="text-accent-success">BUY:</span> {r.indicator} {r.operator} {r.value}</p>
                ))}
                {p.sell_rules.map((r: any, j: number) => (
                  <p key={j} className="text-xs font-mono"><span className="text-accent-danger">SELL:</span> {r.indicator} {r.operator} {r.value}</p>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* ── BUILDER ─────────────────────────────────────────────── */}
      {tab === 'builder' && (
        <div className="grid grid-cols-3 gap-5">
          <div className="col-span-1">
            <Card>
              <CardTitle>Strategy setup</CardTitle>

              <div className="mb-3">
                <label className="text-xs text-text-muted block mb-1">Strategy name</label>
                <input className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-accent-primary"
                  value={name} onChange={e => setName(e.target.value)} />
              </div>

              <div className="mb-3">
                <label className="text-xs text-text-muted block mb-1">Ticker</label>
                <select className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-accent-primary"
                  value={ticker} onChange={e => setTicker(e.target.value)}>
                  {TICKERS.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="text-xs text-text-muted block mb-1">Days</label>
                  <input type="number" className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-accent-primary"
                    value={days} onChange={e => setDays(Number(e.target.value))} />
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">Rule logic</label>
                  <select className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-accent-primary"
                    value={logic} onChange={e => setLogic(e.target.value)}>
                    <option value="AND">AND</option>
                    <option value="OR">OR</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-4">
                <div>
                  <label className="text-xs text-text-muted block mb-1">Stop loss %</label>
                  <input type="number" placeholder="e.g. 5" className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-accent-primary"
                    value={stopLoss} onChange={e => setStopLoss(e.target.value)} />
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">Take profit %</label>
                  <input type="number" placeholder="e.g. 15" className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-accent-primary"
                    value={takeProfit} onChange={e => setTakeProfit(e.target.value)} />
                </div>
              </div>

              <RuleRow rules={buyRules}  setRules={setBuyRules}  label="BUY conditions"  color="#10b981" />
              <RuleRow rules={sellRules} setRules={setSellRules} label="SELL conditions" color="#ef4444" />

              {error && <ErrorBox message={error} />}

              <Button onClick={runStrategy} disabled={loading} className="w-full justify-center mt-2">
                {loading ? <><Spinner /> Running...</> : '⚡ Run strategy'}
              </Button>
            </Card>
          </div>

          {/* Results */}
          <div className="col-span-2">
            {!result && !loading && (
              <div className="flex items-center justify-center h-full text-text-muted text-sm">
                Configure your strategy and click Run
              </div>
            )}
            {loading && <div className="flex items-center justify-center h-64 text-text-muted text-sm gap-3"><Spinner /> Running strategy...</div>}

            {result && !loading && (
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

                <Card className="mb-5">
                  <CardTitle>Equity curve — {result.strategy_name} on {result.ticker}</CardTitle>
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={equityData}>
                        <defs>
                          <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor={pnlColor(result.total_return_pct)} stopOpacity={0.2} />
                            <stop offset="95%" stopColor={pnlColor(result.total_return_pct)} stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} axisLine={false} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} domain={['auto','auto']} />
                        <ChartTooltip />
                        <Area type="monotone" dataKey="value" stroke={pnlColor(result.total_return_pct)} strokeWidth={1.5} fill="url(#sg)" dot={false} name="Portfolio $" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </Card>

                {result.trades?.length > 0 && (
                  <Card>
                    <CardTitle>Trade log ({result.trades.length} trades)</CardTitle>
                    <table className="w-full text-xs">
                      <thead>
                        <tr>{['Date','Action','Price','Shares','P&L','Reason'].map(h => (
                          <th key={h} className="text-left pb-2 text-[11px] uppercase tracking-wider text-muted">{h}</th>
                        ))}</tr>
                      </thead>
                      <tbody>
                        {result.trades.slice(0, 20).map((t: any, i: number) => (
                          <tr key={i} className="border-t border-border">
                            <td className="py-2 font-mono text-text-muted">{t.date}</td>
                            <td className="py-2"><Badge variant={t.action === 'BUY' ? 'success' : 'danger'}>{t.action}</Badge></td>
                            <td className="py-2 font-mono">${t.price?.toFixed(2)}</td>
                            <td className="py-2 font-mono">{t.shares?.toFixed(2)}</td>
                            <td className="py-2 font-mono" style={{ color: t.pnl >= 0 ? '#10b981' : '#ef4444' }}>
                              {t.pnl != null ? `${t.pnl >= 0 ? '+' : ''}$${t.pnl?.toFixed(0)}` : '—'}
                            </td>
                            <td className="py-2 text-text-muted">{t.reason || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </Card>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
