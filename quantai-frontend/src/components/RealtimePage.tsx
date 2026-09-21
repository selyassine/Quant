'use client';
import { useEffect, useState, useRef } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';
import clsx from 'clsx';
import { Card, CardTitle, MetricCard, Badge, Button, Spinner, ErrorBox } from '@/components/ui';
import { ChartTooltip } from '@/components/charts/Tooltip';

const API = 'http://localhost:8000/api/v1/realtime';
const TICKERS = ['AAPL','MSFT','NVDA','TSLA','GOOGL','SPY','QQQ'];

async function apiFetch(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' }, ...options,
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(e.detail || 'API error');
  }
  return res.json();
}

export default function RealtimePage() {
  const [tab, setTab]             = useState('account');
  const [prices, setPrices]       = useState<Record<string, number>>({});
  const [prevPrices, setPrev]     = useState<Record<string, number>>({});
  const [account, setAccount]     = useState<any>(null);
  const [positions, setPositions] = useState<any[]>([]);
  const [orders, setOrders]       = useState<any[]>([]);
  const [history, setHistory]     = useState<any[]>([]);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);

  // Order form
  const [ticker, setTicker] = useState('AAPL');
  const [side, setSide]     = useState<'buy'|'sell'>('buy');
  const [qty, setQty]       = useState('5');
  const [placing, setPlacing] = useState(false);

  const esRef = useRef<EventSource | null>(null);

  // SSE — live price stream
  useEffect(() => {
    const es = new EventSource(`${API}/stream?tickers=${TICKERS.join(',')}`);
    esRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    es.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === 'prices') {
          setPrev((prev) => ({ ...prev, ...prices }));
          setPrices(msg.data);
        }
      } catch {}
    };

    return () => { es.close(); setConnected(false); };
  }, []);

  // Load account data
  const loadAccount = async () => {
    setLoading(true); setError(null);
    try {
      const [acc, pos, ord, hist] = await Promise.all([
        apiFetch('/account'),
        apiFetch('/positions'),
        apiFetch('/orders?status=all'),
        apiFetch('/portfolio/history?period=1M'),
      ]);
      setAccount(acc);
      setPositions(pos);
      setOrders(ord);
      setHistory(hist.equity_curve || []);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadAccount(); }, []);

  const placeOrder = async () => {
    setPlacing(true); setError(null);
    try {
      await apiFetch('/order', {
        method: 'POST',
        body: JSON.stringify({ ticker, side, qty: parseFloat(qty) }),
      });
      await loadAccount();
    } catch (e: any) { setError(e.message); }
    finally { setPlacing(false); }
  };

  const pnlColor = (v: number) => v >= 0 ? '#10b981' : '#ef4444';
  const priceChange = (ticker: string) => {
    const curr = prices[ticker] || 0;
    const prev = prevPrices[ticker] || curr;
    return curr - prev;
  };

  return (
    <div className="p-8 max-w-[1400px]">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Real-Time Trading</h1>
          <p className="text-sm text-muted mt-1">Live prices via Alpaca · Paper Trading account</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border ${connected ? 'border-accent-success/30 text-accent-success bg-accent-success/5' : 'border-accent-danger/30 text-accent-danger bg-accent-danger/5'}`}>
            <span className={connected ? 'live-dot' : ''} style={connected ? {} : { width: 6, height: 6, background: '#ef4444', borderRadius: '50%', display: 'inline-block' }} />
            {connected ? 'Live — prices updating' : 'Disconnected'}
          </div>
          <Button onClick={loadAccount} disabled={loading} variant="ghost">
            {loading ? <Spinner /> : '↻'} Refresh
          </Button>
        </div>
      </div>

      {error && <div className="mb-4"><ErrorBox message={error} /></div>}

      {/* Live prices grid */}
      <div className="grid grid-cols-7 gap-3 mb-6">
        {TICKERS.map((t) => {
          const price = prices[t];
          const change = priceChange(t);
          const up = change >= 0;
          return (
            <div
              key={t}
              onClick={() => setTicker(t)}
              className={`bg-surface border rounded-lg p-3 cursor-pointer transition-colors hover:border-border ${ticker === t ? 'border-accent-primary bg-accent-primary/5' : 'border-border'}`}
            >
              <p className="font-mono text-xs text-accent-primary font-medium mb-1">{t}</p>
              <p className="font-mono text-base font-medium">
                {price ? `$${price.toFixed(2)}` : '—'}
              </p>
              {price && (
                <p className={`text-xs font-mono mt-0.5 ${up ? 'text-accent-success' : 'text-accent-danger'}`}>
                  {up ? '▲' : '▼'} ${Math.abs(change).toFixed(2)}
                </p>
              )}
            </div>
          );
        })}
      </div>

      <div className="flex gap-2 border-b border-border mb-6">
        {[
          { id: 'account',     label: 'Account' },
          { id: 'trade',       label: 'Trade' },
          { id: 'positions',   label: `Positions (${positions.length})` },
          { id: 'orders',      label: `Orders (${orders.length})` },
          { id: 'performance', label: 'Performance' },
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

      {/* ACCOUNT */}
      {tab === 'account' && account && (
        <>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <MetricCard
              title="Portfolio value"
              value={`$${account.portfolio_value?.toLocaleString('en-US', { maximumFractionDigits: 0 })}`}
            />
            <MetricCard
              title="Cash available"
              value={`$${account.cash?.toLocaleString('en-US', { maximumFractionDigits: 0 })}`}
            />
            <MetricCard
              title="Total P&L"
              value={`${account.pnl >= 0 ? '+' : ''}$${account.pnl?.toFixed(0)}`}
              change={{ value: Math.abs(account.pnl_pct || 0), positive: account.pnl >= 0 }}
            />
            <MetricCard
              title="Return"
              value={`${account.pnl_pct >= 0 ? '+' : ''}${account.pnl_pct?.toFixed(2)}%`}
              change={{ value: Math.abs(account.pnl_pct || 0), positive: account.pnl_pct >= 0 }}
            />
          </div>

          {history.length > 0 && (
            <Card>
              <CardTitle>Portfolio value — 1 month</CardTitle>
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={history}>
                    <defs>
                      <linearGradient id="pg" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} axisLine={false} interval={4} />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} axisLine={false} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} domain={['auto','auto']} />
                    <ChartTooltip />
                    <Area type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={1.5} fill="url(#pg)" dot={false} name="Portfolio $" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}
        </>
      )}

      {/* TRADE */}
      {tab === 'trade' && (
        <div className="grid grid-cols-2 gap-5">
          <Card>
            <CardTitle>Place live order (Alpaca paper)</CardTitle>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-muted block mb-1">Ticker</label>
                <select className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-accent-primary"
                  value={ticker} onChange={e => setTicker(e.target.value)}>
                  {TICKERS.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>

              {prices[ticker] && (
                <div className="bg-surface border border-border rounded-lg px-4 py-3">
                  <p className="text-xs text-text-muted">Live price</p>
                  <p className="font-mono text-xl text-accent-primary">${prices[ticker]?.toFixed(2)}</p>
                  {qty && <p className="text-xs text-text-muted mt-1">Total ≈ ${(prices[ticker] * parseFloat(qty || '0')).toFixed(2)}</p>}
                  <div className="flex items-center gap-1 mt-1">
                    <span className="live-dot" />
                    <span className="text-xs text-accent-success">Live from Alpaca</span>
                  </div>
                </div>
              )}

              <div>
                <label className="text-xs text-muted block mb-1">Side</label>
                <div className="flex gap-2">
                  {(['buy','sell'] as const).map(s => (
                    <button key={s} onClick={() => setSide(s)}
                      className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${side === s
                        ? s === 'buy' ? 'bg-accent-success/20 text-accent-success border border-accent-success/30' : 'bg-accent-danger/20 text-accent-danger border border-accent-danger/30'
                        : 'bg-surface text-text-muted'}`}>
                      {s === 'buy' ? '▲ BUY' : '▼ SELL'}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs text-muted block mb-1">Quantity (shares)</label>
                <input type="number" min="1" value={qty} onChange={e => setQty(e.target.value)}
                  className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text-primary font-mono outline-none focus:border-accent-primary" />
              </div>

              <Button onClick={placeOrder} disabled={placing || !qty} className="w-full justify-center">
                {placing ? <><Spinner /> Placing...</> : `${side === 'buy' ? '▲ BUY' : '▼ SELL'} ${qty} ${ticker} @ live price`}
              </Button>
            </div>
          </Card>

          <Card>
            <CardTitle>How it works</CardTitle>
            <div className="space-y-3 text-sm text-text-muted">
              <p>Orders are sent to <span className="text-accent-primary font-medium">Alpaca Paper Trading</span> and fill at the <span className="text-text-primary">real market price</span>.</p>
              <p>This is not a simulation — it uses the actual Alpaca infrastructure with paper money.</p>
              <hr className="border-border" />
              <p className="font-medium text-text-primary">Market order</p>
              <p>Fills immediately at the best available price from the live market.</p>
              <hr className="border-border" />
              <p className="font-medium text-text-primary">Paper account</p>
              <p>Starting capital: <span className="font-mono text-accent-primary">$100,000</span><br/>No real money — safe to test.</p>
            </div>
          </Card>
        </div>
      )}

      {/* POSITIONS */}
      {tab === 'positions' && (
        <Card>
          <CardTitle>Open positions — live P&L</CardTitle>
          {positions.length === 0 ? (
            <p className="text-muted text-sm text-center py-10">No open positions</p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr>{['Ticker','Qty','Entry Price','Current Price','Market Value','Unrealized P&L','Today'].map(h => (
                  <th key={h} className="text-left pb-2 text-[11px] uppercase tracking-wider text-muted">{h}</th>
                ))}</tr>
              </thead>
              <tbody>
                {positions.map((p: any) => (
                  <tr key={p.ticker} className="border-t border-border">
                    <td className="py-2.5 font-mono text-accent-primary font-medium">{p.ticker}</td>
                    <td className="py-2.5 font-mono">{p.qty}</td>
                    <td className="py-2.5 font-mono">${p.avg_entry_price?.toFixed(2)}</td>
                    <td className="py-2.5 font-mono">${p.current_price?.toFixed(2)}</td>
                    <td className="py-2.5 font-mono">${p.market_value?.toLocaleString('en-US', { maximumFractionDigits: 0 })}</td>
                    <td className="py-2.5 font-mono" style={{ color: pnlColor(p.unrealized_pl) }}>
                      {p.unrealized_pl >= 0 ? '+' : ''}${p.unrealized_pl?.toFixed(0)} ({p.unrealized_plpc?.toFixed(1)}%)
                    </td>
                    <td className="py-2.5 font-mono" style={{ color: pnlColor(p.change_today) }}>
                      {p.change_today >= 0 ? '+' : ''}{p.change_today?.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {/* ORDERS */}
      {tab === 'orders' && (
        <Card>
          <CardTitle>Order history</CardTitle>
          {orders.length === 0 ? (
            <p className="text-muted text-sm text-center py-10">No orders yet</p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr>{['Date','Ticker','Side','Qty','Fill Price','Status'].map(h => (
                  <th key={h} className="text-left pb-2 text-[11px] uppercase tracking-wider text-muted">{h}</th>
                ))}</tr>
              </thead>
              <tbody>
                {orders.map((o: any, i: number) => (
                  <tr key={i} className="border-t border-border">
                    <td className="py-2.5 font-mono text-text-muted">{o.created_at?.slice(0, 16)}</td>
                    <td className="py-2.5 font-mono text-accent-primary">{o.ticker}</td>
                    <td className="py-2.5"><Badge variant={o.side === 'buy' ? 'success' : 'danger'}>{o.side?.toUpperCase()}</Badge></td>
                    <td className="py-2.5 font-mono">{o.filled_qty || o.qty}</td>
                    <td className="py-2.5 font-mono">{o.fill_price ? `$${o.fill_price?.toFixed(2)}` : '—'}</td>
                    <td className="py-2.5"><Badge variant={o.status === 'filled' ? 'success' : o.status === 'canceled' ? 'danger' : 'warning'}>{o.status}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {/* PERFORMANCE */}
      {tab === 'performance' && account && (
        <div className="grid grid-cols-2 gap-5">
          <Card>
            <CardTitle>Account performance</CardTitle>
            {[
              { label: 'Initial capital',  value: '$100,000' },
              { label: 'Current equity',   value: `$${account.equity?.toLocaleString('en-US', { maximumFractionDigits: 0 })}` },
              { label: 'Total P&L ($)',    value: `${account.pnl >= 0 ? '+' : ''}$${account.pnl?.toFixed(2)}`, color: pnlColor(account.pnl) },
              { label: 'Total P&L (%)',    value: `${account.pnl_pct >= 0 ? '+' : ''}${account.pnl_pct?.toFixed(2)}%`, color: pnlColor(account.pnl_pct) },
              { label: 'Buying power',     value: `$${account.buying_power?.toLocaleString('en-US', { maximumFractionDigits: 0 })}` },
              { label: 'Open positions',   value: positions.length },
              { label: 'Data source',      value: 'Alpaca Paper API', color: '#3b82f6' },
            ].map((row) => (
              <div key={row.label} className="flex justify-between py-2.5 border-b border-border last:border-0">
                <span className="text-sm text-text-muted">{row.label}</span>
                <span className="font-mono text-sm" style={{ color: row.color || '#f8fafc' }}>{row.value}</span>
              </div>
            ))}
          </Card>

          <Card>
            <CardTitle>Open positions summary</CardTitle>
            {positions.length === 0 ? (
              <p className="text-muted text-sm text-center py-10">No open positions</p>
            ) : (
              <div className="space-y-3">
                {positions.map((p: any) => (
                  <div key={p.ticker} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                    <div>
                      <p className="font-mono text-sm text-accent-primary">{p.ticker}</p>
                      <p className="text-xs text-text-muted">{p.qty} shares @ ${p.avg_entry_price?.toFixed(2)}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm" style={{ color: pnlColor(p.unrealized_pl) }}>
                        {p.unrealized_pl >= 0 ? '+' : ''}${p.unrealized_pl?.toFixed(0)}
                      </p>
                      <p className="font-mono text-xs" style={{ color: pnlColor(p.unrealized_plpc) }}>
                        {p.unrealized_plpc >= 0 ? '+' : ''}{p.unrealized_plpc?.toFixed(1)}%
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
