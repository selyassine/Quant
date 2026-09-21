'use client';
import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend } from 'recharts';
import clsx from 'clsx';
import {
  Card, CardTitle, MetricCard, Badge, Button, Spinner,
  ErrorBox, LoadingBox, Table,
} from '@/components/ui';

const API = 'http://localhost:8000/api/v1/paper';
const COLORS = ['#3b82f6','#6366f1','#10b981','#f59e0b','#ef4444','#0ea5e9'];
const TICKERS = ['AAPL','MSFT','NVDA','TSLA','GOOGL','SPY','QQQ','BTC-USD','ETH-USD'];

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

export default function PaperTradingPage() {
  const [tab, setTab]           = useState('account');
  const [account, setAccount]   = useState<any>(null);
  const [positions, setPositions] = useState<any[]>([]);
  const [orders, setOrders]     = useState<any[]>([]);
  const [perf, setPerf]         = useState<any>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);

  // Order form
  const [ticker, setTicker]     = useState('AAPL');
  const [side, setSide]         = useState<'buy'|'sell'>('buy');
  const [qty, setQty]           = useState('10');
  const [reason, setReason]     = useState('');
  const [placing, setPlacing]   = useState(false);
  const [price, setPrice]       = useState<number | null>(null);

  const loadAll = async () => {
    setLoading(true); setError(null);
    try {
      const [acc, pos, ord, pf] = await Promise.all([
        apiFetch('/account'),
        apiFetch('/positions'),
        apiFetch('/orders?limit=30'),
        apiFetch('/performance'),
      ]);
      setAccount(acc); setPositions(pos); setOrders(ord); setPerf(pf);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const loadPrice = async (t: string) => {
    try {
      const d = await apiFetch(`/price/${t}`);
      setPrice(d.price);
    } catch { setPrice(null); }
  };

  useEffect(() => { loadAll(); }, []);
  useEffect(() => { loadPrice(ticker); }, [ticker]);

  const placeOrder = async () => {
    setPlacing(true); setError(null);
    try {
      await apiFetch('/order', {
        method: 'POST',
        body: JSON.stringify({ ticker, side, quantity: parseFloat(qty), reason }),
      });
      await loadAll();
    } catch (e: any) { setError(e.message); }
    finally { setPlacing(false); }
  };

  const resetAccount = async () => {
    if (!confirm('Reset account to $100,000? All trades will be lost.')) return;
    try {
      await apiFetch('/reset', { method: 'POST' });
      await loadAll();
    } catch (e: any) { setError(e.message); }
  };

  const pieData = positions.map((p) => ({ name: p.ticker, value: p.market_value }));
  const pnlColor = (v: number) => v >= 0 ? '#10b981' : '#ef4444';

  return (
    <div className="p-8 max-w-[1400px]">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Paper Trading</h1>
          <p className="text-sm text-muted mt-1">Virtual account · $100,000 initial capital · zero commission</p>
        </div>
        <div className="flex gap-3">
          <Button onClick={loadAll} disabled={loading} variant="ghost">
            {loading ? <Spinner /> : '↻'} Refresh
          </Button>
          <Button onClick={resetAccount} variant="ghost">Reset account</Button>
        </div>
      </div>

      {error && <div className="mb-4"><ErrorBox message={error} /></div>}

      {/* KPI row */}
      {account && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <MetricCard
            title="Total value"
            value={`$${account.total_value?.toLocaleString('en-US', { maximumFractionDigits: 0 })}`}
          />
          <MetricCard
            title="Cash available"
            value={`$${account.cash_balance?.toLocaleString('en-US', { maximumFractionDigits: 0 })}`}
          />
          <MetricCard
            title="Total P&L"
            value={`${account.total_pnl >= 0 ? '+' : ''}$${account.total_pnl?.toFixed(0)}`}
            change={{ value: Math.abs(account.total_pnl_pct || 0), positive: account.total_pnl >= 0 }}
          />
          <MetricCard
            title="Return"
            value={`${account.total_pnl_pct >= 0 ? '+' : ''}${account.total_pnl_pct?.toFixed(2)}%`}
            change={{ value: Math.abs(account.total_pnl_pct || 0), positive: account.total_pnl_pct >= 0 }}
          />
        </div>
      )}

      <div className="flex gap-2 border-b border-border mb-6">
        {[
          { id: 'account',   label: 'Account' },
          { id: 'trade',     label: 'Place Order' },
          { id: 'orders',    label: `Orders (${orders.length})` },
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

      {/* ── ACCOUNT tab ─────────────────────────────────────────────── */}
      {tab === 'account' && (
        loading ? <LoadingBox /> : (
          <div className="grid grid-cols-2 gap-5">
            {/* Pie chart */}
            <Card>
              <CardTitle>Portfolio allocation</CardTitle>
              {pieData.length > 0 ? (
                <>
                  <div className="h-52 mb-4">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} paddingAngle={2}>
                          {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                        </Pie>
                        <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <Table
                    headers={['Ticker', 'Qty', 'Avg Cost', 'Current', 'Value', 'P&L']}
                    rows={positions.map((p) => [
                      <span className="text-accent-primary font-medium">{p.ticker}</span>,
                      p.quantity,
                      `$${p.avg_cost}`,
                      `$${p.current_price}`,
                      `$${p.market_value?.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
                      <span style={{ color: pnlColor(p.unrealized_pnl) }}>
                        {p.unrealized_pnl >= 0 ? '+' : ''}${p.unrealized_pnl?.toFixed(0)} ({p.unrealized_pnl_pct?.toFixed(1)}%)
                      </span>,
                    ])}
                  />
                </>
              ) : (
                <div className="flex items-center justify-center h-40 text-text-muted text-sm">
                  No open positions — place an order to start
                </div>
              )}
            </Card>

            {/* Account info */}
            <Card>
              <CardTitle>Account details</CardTitle>
              {account && [
                { label: 'Initial capital',  value: `$${account.initial_capital?.toLocaleString()}` },
                { label: 'Cash balance',     value: `$${account.cash_balance?.toFixed(2)}` },
                { label: 'Positions value',  value: `$${account.positions_value?.toFixed(2)}` },
                { label: 'Total value',      value: `$${account.total_value?.toFixed(2)}`, color: '#3b82f6' },
                { label: 'Total P&L ($)',    value: `${account.total_pnl >= 0 ? '+' : ''}$${account.total_pnl?.toFixed(2)}`, color: pnlColor(account.total_pnl) },
                { label: 'Total P&L (%)',    value: `${account.total_pnl_pct >= 0 ? '+' : ''}${account.total_pnl_pct?.toFixed(2)}%`, color: pnlColor(account.total_pnl_pct) },
                { label: 'Open positions',   value: account.positions_count },
              ].map((row) => (
                <div key={row.label} className="flex justify-between py-2.5 border-b border-border last:border-0">
                  <span className="text-sm text-text-muted">{row.label}</span>
                  <span className="font-mono text-sm" style={{ color: row.color || '#f8fafc' }}>{row.value}</span>
                </div>
              ))}
            </Card>
          </div>
        )
      )}

      {/* ── TRADE tab ───────────────────────────────────────────────── */}
      {tab === 'trade' && (
        <div className="grid grid-cols-2 gap-5">
          <Card>
            <CardTitle>Place market order</CardTitle>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-muted block mb-1">Ticker</label>
                <select
                  className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-[#e8edf5] outline-none focus:border-accent"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                >
                  {TICKERS.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>

              {price && (
                <div className="bg-surface border border-border rounded-lg px-4 py-3">
                  <p className="text-xs text-text-muted">Current price</p>
                  <p className="font-mono text-lg text-accent-primary">${price?.toFixed(2)}</p>
                  {qty && <p className="text-xs text-text-muted mt-1">Total: ${(price * parseFloat(qty || '0')).toFixed(2)}</p>}
                </div>
              )}

              <div>
                <label className="text-xs text-text-muted block mb-1">Side</label>
                <div className="flex gap-2">
                  {(['buy', 'sell'] as const).map((s) => (
                    <button
                      key={s}
                      onClick={() => setSide(s)}
                      className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                        side === s
                          ? s === 'buy' ? 'bg-accent-success/20 text-accent-success border border-accent-success/30' : 'bg-accent-danger/20 text-accent-danger border border-accent-danger/30'
                          : 'bg-surface text-text-muted'
                      }`}
                    >
                      {s === 'buy' ? '▲ BUY' : '▼ SELL'}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs text-text-muted block mb-1">Quantity (shares)</label>
                <input
                  type="number"
                  min="1"
                  value={qty}
                  onChange={(e) => setQty(e.target.value)}
                  className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text-primary font-mono outline-none focus:border-accent-primary"
                />
              </div>

              <div>
                <label className="text-xs text-text-muted block mb-1">Reason (optional)</label>
                <input
                  type="text"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="e.g. RSI oversold signal"
                  className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-[#e8edf5] outline-none focus:border-accent"
                />
              </div>

              <Button
                onClick={placeOrder}
                disabled={placing || !qty || parseFloat(qty) <= 0}
                className="w-full justify-center"
              >
                {placing ? <><Spinner /> Placing...</> : `${side === 'buy' ? '▲ BUY' : '▼ SELL'} ${qty} shares of ${ticker}`}
              </Button>
            </div>
          </Card>

          <Card>
            <CardTitle>Quick guide</CardTitle>
            <div className="space-y-3 text-sm text-text-muted">
              <p>All orders fill instantly at the last known <span className="text-text-primary">closing price</span> from PostgreSQL.</p>
              <p>Zero commission — like Robinhood paper trading.</p>
              <p>Initial capital: <span className="font-mono text-accent-primary">$100,000</span></p>
              <hr className="border-border my-4" />
              <p className="font-medium text-text-primary">BUY order</p>
              <p>Deducts cash · Creates or increases position</p>
              <p className="font-medium text-text-primary mt-3">SELL order</p>
              <p>Requires existing position · Adds cash back</p>
              <hr className="border-border my-4" />
              <p>If quantity exceeds available cash, it is automatically adjusted to the maximum affordable.</p>
            </div>
          </Card>
        </div>
      )}

      {/* ── ORDERS tab ──────────────────────────────────────────────── */}
      {tab === 'orders' && (
        <Card>
          <CardTitle>Order history ({orders.length})</CardTitle>
          {orders.length === 0 ? (
            <div className="text-center py-10 text-text-muted text-sm">No orders yet</div>
          ) : (
            <Table
              headers={['Date', 'Ticker', 'Side', 'Qty', 'Fill Price', 'Total', 'Status', 'Reason']}
              rows={orders.map((o) => [
                <span className="text-text-muted">{o.created_at?.slice(0, 16)}</span>,
                <span className="text-accent-primary font-medium">{o.ticker}</span>,
                <Badge variant={o.side === 'buy' ? 'success' : 'danger'}>{o.side.toUpperCase()}</Badge>,
                o.quantity,
                `$${o.fill_price?.toFixed(2)}`,
                `$${(o.fill_price * o.quantity).toFixed(0)}`,
                <Badge variant={o.status === 'filled' ? 'success' : 'muted'}>{o.status}</Badge>,
                <span className="text-text-muted">{o.reason || '—'}</span>,
              ])}
            />
          )}
        </Card>
      )}

      {/* ── PERFORMANCE tab ─────────────────────────────────────────── */}
      {tab === 'performance' && perf && (
        <div className="grid grid-cols-2 gap-5">
          <Card>
            <CardTitle>Performance metrics</CardTitle>
            {[
              { label: 'Total return',  value: `${perf.performance.total_return_pct >= 0 ? '+' : ''}${perf.performance.total_return_pct?.toFixed(2)}%`, color: pnlColor(perf.performance.total_return_pct) },
              { label: 'Total P&L',     value: `${perf.performance.total_pnl_usd >= 0 ? '+' : ''}$${perf.performance.total_pnl_usd?.toFixed(2)}`, color: pnlColor(perf.performance.total_pnl_usd) },
              { label: 'Total trades',  value: perf.performance.total_trades },
              { label: 'Buy trades',    value: perf.performance.buy_trades,  color: '#10b981' },
              { label: 'Sell trades',   value: perf.performance.sell_trades, color: '#ef4444' },
            ].map((row) => (
              <div key={row.label} className="flex justify-between py-2.5 border-b border-border last:border-0">
                <span className="text-sm text-muted">{row.label}</span>
                <span className="font-mono text-sm" style={{ color: row.color || '#e8edf5' }}>{row.value}</span>
              </div>
            ))}
          </Card>

          <Card>
            <CardTitle>Recent transactions</CardTitle>
            {perf.recent_transactions?.length === 0 ? (
              <p className="text-text-muted text-sm text-center py-8">No transactions yet</p>
            ) : (
              <Table
                headers={['Date', 'Ticker', 'Side', 'Qty', 'Price', 'Cash after']}
                rows={(perf.recent_transactions || []).map((t: any) => [
                  <span className="text-text-muted">{t.date?.slice(5, 16)}</span>,
                  <span className="text-accent-primary">{t.ticker}</span>,
                  <Badge variant={t.side === 'buy' ? 'success' : 'danger'}>{t.side.toUpperCase()}</Badge>,
                  t.quantity,
                  `$${t.price?.toFixed(2)}`,
                  `$${t.cash_after?.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
                ])}
              />
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
