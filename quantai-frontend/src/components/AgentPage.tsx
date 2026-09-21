'use client';
import { useState, useCallback, useEffect } from 'react';
import { Card, CardTitle, MetricCard, Spinner } from '@/components/ui';
import clsx from 'clsx';

const API = 'http://localhost:8000';

const SIDE_COLOR = (s: string) => s === 'buy' ? 'text-accent-success' : 'text-accent-danger';
const STATUS_STYLE: Record<string, string> = {
  pending:  'bg-accent-warning/20 text-accent-warning',
  accepted: 'bg-accent-success/20 text-accent-success',
  refused:  'bg-accent-danger/20 text-accent-danger',
  executed: 'bg-accent-primary/20 text-accent-primary',
};

type Tab = 'pending' | 'all' | 'performance';

export default function AgentPage() {
  const [tab, setTab]         = useState<Tab>('pending');
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError]     = useState('');
  const [success, setSuccess] = useState('');

  const [pendingOrders, setPendingOrders] = useState<any[]>([]);
  const [allOrders, setAllOrders]         = useState<any[]>([]);
  const [perfData, setPerfData]           = useState<any>(null);
  const [cycleResult, setCycleResult]     = useState<any>(null);
  const [actioning, setActioning]         = useState<Record<number, string>>({});

  const get = async (path: string) => {
    const r = await fetch(`${API}/api/v1/agent/${path}`);
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  };

  const post = async (path: string) => {
    const r = await fetch(`${API}/api/v1/agent/${path}`, { method: 'POST' });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  };

  const loadData = useCallback(async () => {
    setLoading(true); setError('');
    try {
      if (tab === 'pending') {
        const d = await get('orders/pending');
        const orders = Array.isArray(d.orders) ? d.orders : Array.isArray(d) ? d : [];
        setPendingOrders(orders);
      } else if (tab === 'all') {
        const d = await get('orders');
        const orders = Array.isArray(d.orders) ? d.orders : Array.isArray(d) ? d : [];
        setAllOrders(orders);
      } else {
        setPerfData(await get('performance'));
      }
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [tab]);

  useEffect(() => { loadData(); }, [tab]);

  useEffect(() => {
    if (tab !== 'pending') return;
    const id = setInterval(loadData, 30000);
    return () => clearInterval(id);
  }, [tab, loadData]);

  const runCycle = async () => {
    setRunning(true); setError(''); setSuccess(''); setCycleResult(null);
    try {
      const r = await post('run');
      setCycleResult(r);
      const ordersCount = typeof r.orders_created === 'number' ? r.orders_created : 
                          Array.isArray(r.orders_created) ? r.orders_created.length : 0;
      setSuccess(`Agent cycle complete — ${ordersCount} new orders created`);
      if (tab === 'pending') loadData();
    } catch (e: any) { setError(e.message); }
    finally { setRunning(false); }
  };

  const handleOrder = async (orderId: number, action: 'accept' | 'refuse') => {
    setActioning(prev => ({ ...prev, [orderId]: action }));
    setError(''); setSuccess('');
    try {
      const r = await post(`orders/${orderId}/${action}`);
      setSuccess(action === 'accept'
        ? `✅ Order #${orderId} accepted`
        : `❌ Order #${orderId} refused`
      );
      loadData();
    } catch (e: any) { setError(e.message); }
    finally { setActioning(prev => { const n = { ...prev }; delete n[orderId]; return n; }); }
  };

  return (
    <div className="p-6 space-y-5 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Autonomous Trading Agent</h1>
          <p className="text-sm text-text-muted mt-1">AI-driven decisions · You review and accept or refuse each order</p>
        </div>
        <button
          onClick={runCycle}
          disabled={running}
          className="bg-accent-primary text-bg font-bold px-5 py-2.5 rounded-lg hover:bg-accent-primary/80 disabled:opacity-50 transition-colors text-sm flex items-center gap-2"
        >
          {running ? <><Spinner /><span>Running…</span></> : '⚡ Run Agent Cycle'}
        </button>
      </div>

      {/* Risk rules */}
      <div className="bg-surface border border-border rounded-lg px-4 py-3 flex flex-wrap gap-4 text-xs text-text-muted">
        <span>🛡 Max position: <span className="text-text-primary">10%</span></span>
        <span>🛑 Stop-loss: <span className="text-text-primary">5%</span></span>
        <span>📊 Min confidence: <span className="text-text-primary">55%</span></span>
        <span>🔢 Max trades/day: <span className="text-text-primary">3</span></span>
        <span>💡 Models: <span className="text-text-primary">LightGBM + LSTM + Transformer</span></span>
      </div>

      {error   && <div className="text-accent-danger text-sm bg-accent-danger/10 rounded-lg p-3">{error}</div>}
      {success && <div className="text-accent-success text-sm bg-accent-success/10 rounded-lg p-3">{success}</div>}

      {/* Cycle result */}
      {cycleResult && (
        <Card>
          <CardTitle>Last cycle result</CardTitle>
          <div className="grid grid-cols-4 gap-3 text-sm">
            {[
              { label: 'Tickers analyzed', value: typeof cycleResult.tickers_analyzed === 'number' ? cycleResult.tickers_analyzed : 0 },
              { label: 'Orders created',   value: Array.isArray(cycleResult.orders_created) ? cycleResult.orders_created.length : (typeof cycleResult.orders_created === 'number' ? cycleResult.orders_created : 0) },
              { label: 'Skipped',          value: typeof cycleResult.skipped === 'number' ? cycleResult.skipped : 0 },
              { label: 'Status',           value: typeof cycleResult.status === 'string' ? cycleResult.status : '—' },
            ].map(item => (
              <div key={item.label}>
                <div className="text-text-muted text-xs">{item.label}</div>
                <div className="text-text-primary font-bold text-lg">{item.value}</div>
              </div>
            ))}
          </div>
          {cycleResult.message && typeof cycleResult.message === 'string' && (
            <p className="text-xs text-text-muted mt-3 italic">{cycleResult.message}</p>
          )}
        </Card>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {(['pending','all','performance'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm border-b-2 -mb-px transition-colors ${
              tab === t ? 'text-accent-primary border-accent-primary' : 'text-text-muted border-transparent hover:text-text-primary'
            }`}
          >
            {t === 'pending' ? 'Pending Orders' : t === 'all' ? 'Order History' : 'Performance'}
            {t === 'pending' && pendingOrders.length > 0 && (
              <span className="ml-2 bg-accent-danger text-white text-xs px-1.5 py-0.5 rounded-full">
                {pendingOrders.length}
              </span>
            )}
          </button>
        ))}
        <button onClick={loadData} disabled={loading} className="px-3 py-2 text-text-muted hover:text-text-primary text-sm ml-auto">
          {loading ? <Spinner /> : '↻'}
        </button>
      </div>

      {/* PENDING */}
      {tab === 'pending' && !loading && (
        pendingOrders.length === 0 ? (
          <Card>
            <div className="flex flex-col items-center justify-center h-40 text-text-muted gap-3">
              <span className="text-4xl">✅</span>
              <p className="text-sm">No pending orders — run an agent cycle to generate signals</p>
            </div>
          </Card>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-text-muted">{pendingOrders.length} order(s) waiting for approval</p>
            {pendingOrders.map((order: any, idx: number) => (
              <div key={typeof order.id === 'number' ? order.id : idx} className="bg-surface border border-border rounded-xl p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`text-2xl font-bold font-mono ${SIDE_COLOR(typeof order.side === 'string' ? order.side : 'buy')}`}>
                      {typeof order.side === 'string' ? order.side.toUpperCase() : 'BUY'}
                    </span>
                    <div>
                      <span className="text-text-primary font-bold text-xl font-mono">{typeof order.ticker === 'string' ? order.ticker : '—'}</span>
                      <div className="text-xs text-text-muted">
                        {typeof order.quantity === 'number' ? order.quantity : '—'} shares · ${typeof order.suggested_price === 'number' ? order.suggested_price.toFixed(2) : '—'} ·
                        Est. ${typeof order.quantity === 'number' && typeof order.suggested_price === 'number' ? ((order.quantity || 0) * (order.suggested_price || 0)).toFixed(0) : '—'}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-text-muted">Confidence</div>
                    <div className={`text-lg font-bold ${
                      (typeof order.confidence === 'number' ? order.confidence : 0) > 0.65 ? 'text-accent-success' :
                      (typeof order.confidence === 'number' ? order.confidence : 0) > 0.55 ? 'text-accent-warning' : 'text-accent-warning'
                    }`}>
                      {((typeof order.confidence === 'number' ? order.confidence : 0) * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>

                {order.reason && typeof order.reason === 'string' && (
                  <div className="bg-surface border border-border rounded-lg px-3 py-2">
                    <p className="text-xs text-text-muted font-mono leading-relaxed">💡 {order.reason}</p>
                  </div>
                )}

                <div className="flex flex-wrap gap-3 text-xs text-text-muted">
                  {order.signal && typeof order.signal === 'string' && <span>Signal: <span className="text-text-primary">{order.signal}</span></span>}
                  {order.probability && typeof order.probability === 'number' && <span>Probability: <span className="text-text-primary">{(order.probability * 100).toFixed(1)}%</span></span>}
                  {order.created_at && <span>Created: <span className="text-text-primary">{new Date(order.created_at).toLocaleTimeString()}</span></span>}
                </div>

                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => handleOrder(order.id, 'accept')}
                    disabled={!!actioning[order.id]}
                    className="flex-1 bg-accent-success/20 hover:bg-accent-success/30 text-accent-success font-bold py-2.5 rounded-lg transition-colors text-sm disabled:opacity-50 border border-accent-success/30"
                  >
                    {actioning[order.id] === 'accept' ? '⏳ Executing…' : '✅ Accept & Execute'}
                  </button>
                  <button
                    onClick={() => handleOrder(order.id, 'refuse')}
                    disabled={!!actioning[order.id]}
                    className="flex-1 bg-accent-danger/10 hover:bg-accent-danger/20 text-accent-danger font-bold py-2.5 rounded-lg transition-colors text-sm disabled:opacity-50 border border-accent-danger/20"
                  >
                    {actioning[order.id] === 'refuse' ? '⏳ Refusing…' : '❌ Refuse'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {/* ALL ORDERS */}
      {tab === 'all' && !loading && (
        allOrders.length === 0 ? (
          <Card>
            <div className="flex flex-col items-center justify-center h-32 text-text-muted gap-2">
              <span className="text-3xl">◎</span>
              <p className="text-sm">No orders yet — run an agent cycle first</p>
            </div>
          </Card>
        ) : (
          <Card>
            <CardTitle>All orders ({allOrders.length})</CardTitle>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-text-muted border-b border-border">
                  {['#','Ticker','Side','Qty','Price','Confidence','Status','Date'].map(h => (
                    <th key={h} className="text-left py-2 pr-4 text-[11px] uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {allOrders.map((o: any, idx: number) => (
                  <tr key={typeof o.id === 'number' ? o.id : idx} className="border-b border-border/30 hover:bg-white/[0.02]">
                    <td className="py-2.5 pr-4 text-text-muted font-mono">#{typeof o.id === 'number' ? o.id : '—'}</td>
                    <td className="py-2.5 pr-4 font-mono font-bold text-accent-primary">{typeof o.ticker === 'string' ? o.ticker : '—'}</td>
                    <td className={`py-2.5 pr-4 font-bold ${SIDE_COLOR(typeof o.side === 'string' ? o.side : 'buy')}`}>{typeof o.side === 'string' ? o.side.toUpperCase() : 'BUY'}</td>
                    <td className="py-2.5 pr-4 text-text-muted font-mono">{typeof o.quantity === 'number' ? o.quantity : '—'}</td>
                    <td className="py-2.5 pr-4 text-text-muted font-mono">
                      {typeof o.fill_price === 'number' ? `$${o.fill_price}` : typeof o.suggested_price === 'number' ? `~$${o.suggested_price.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-2.5 pr-4 text-text-muted font-mono">
                      {typeof o.confidence === 'number' ? `${(o.confidence * 100).toFixed(1)}%` : '—'}
                    </td>
                    <td className="py-2.5 pr-4">
                      <span className={`px-2 py-0.5 rounded text-xs ${STATUS_STYLE[typeof o.status === 'string' ? o.status : 'pending'] || 'text-text-muted'}`}>
                        {typeof o.status === 'string' ? o.status : 'pending'}
                      </span>
                    </td>
                    <td className="py-2.5 text-text-muted font-mono whitespace-nowrap">
                      {o.created_at ? new Date(o.created_at).toLocaleDateString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )
      )}

      {/* PERFORMANCE */}
      {tab === 'performance' && !loading && perfData && (
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-4">
            <MetricCard title="Total orders"    value={String(perfData.total_orders ?? 0)} />
            <MetricCard title="Accepted"        value={String(perfData.accepted ?? 0)} />
            <MetricCard title="Refused"         value={String(perfData.refused ?? 0)} />
            <MetricCard title="Acceptance rate" value={`${perfData.acceptance_rate_pct ?? 0}%`} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardTitle>Order breakdown</CardTitle>
              {[
                ['Total orders',   typeof perfData.total_orders === 'number' ? perfData.total_orders : 0,    '#f8fafc'],
                ['Accepted',       typeof perfData.accepted === 'number' ? perfData.accepted : 0,        '#10b981'],
                ['Refused',        typeof perfData.refused === 'number' ? perfData.refused : 0,         '#ef4444'],
                ['Pending',        typeof perfData.pending === 'number' ? perfData.pending : 0,         '#f59e0b'],
                ['Buy orders',     typeof perfData.buy_orders === 'number' ? perfData.buy_orders : (Array.isArray(perfData.buy_orders) ? perfData.buy_orders.length : 0),      '#3b82f6'],
                ['Sell orders',    typeof perfData.sell_orders === 'number' ? perfData.sell_orders : (Array.isArray(perfData.sell_orders) ? perfData.sell_orders.length : 0),     '#f97316'],
                ['Avg confidence', typeof perfData.avg_confidence === 'number'
                  ? `${perfData.avg_confidence > 1
                      ? perfData.avg_confidence.toFixed(1)
                      : (perfData.avg_confidence * 100).toFixed(1)}%`
                  : '—', '#3b82f6'],
              ].map(([label, value, color]) => (
                <div key={String(label)} className="flex justify-between py-2 border-b border-border last:border-0">
                  <span className="text-sm text-text-muted">{label}</span>
                  <span className="font-mono text-sm font-medium" style={{ color: String(color) }}>{String(value)}</span>
                </div>
              ))}
            </Card>
            <Card>
              <CardTitle>Risk management</CardTitle>
              {[
                ['Max position size', '10% of portfolio'],
                ['Stop loss',         '5%'],
                ['Min confidence',    '55%'],
                ['Max trades/day',    '3'],
                ['Decision engine',   'Ensemble ML'],
                ['Execution',         'Paper Trading'],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between py-2 border-b border-border last:border-0">
                  <span className="text-sm text-text-muted">{k}</span>
                  <span className="text-sm text-text-primary font-medium">{v}</span>
                </div>
              ))}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
