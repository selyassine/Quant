'use client';
import { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';
import clsx from 'clsx';
import { Card, CardTitle, MetricCard, Badge, LoadingBox } from '@/components/ui';
import { ChartTooltip } from '@/components/charts/Tooltip';
import { getAssets, getOHLCV } from '@/lib/api';

const TICKERS_PREVIEW = ['AAPL', 'MSFT', 'NVDA', 'SPY', 'TSLA', 'GOOGL'];

export default function Dashboard() {
  const [assets, setAssets] = useState<any[]>([]);
  const [prices, setPrices] = useState<Record<string, any[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAssets()
      .then((a) => {
        setAssets(a);
        return Promise.all(
          TICKERS_PREVIEW.map((t) =>
            getOHLCV(t, 60)
              .then((d) => ({ t, d }))
              .catch(() => null),
          ),
        );
      })
      .then((results) => {
        const map: Record<string, any[]> = {};
        results.forEach((r) => { if (r) map[r.t] = r.d; });
        setPrices(map);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const spark = (ticker: string) =>
    (prices[ticker] || [])
      .slice(-30)
      .map((r, i) => ({ i, v: r.close }));

  return (
    <div className="p-6 max-w-[1600px]">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary">Dashboard</h1>
        <p className="text-sm text-text-muted mt-1">Overview of your trading platform</p>
      </div>

      {loading ? (
        <LoadingBox label="Loading..." />
      ) : (
        <>
          {/* KPI Row */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <MetricCard
              title="Assets Tracked"
              value={assets.length}
              change={{ value: 2.5, positive: true }}
            />
            <MetricCard
              title="AI Models"
              value="3"
              change={{ value: 0, positive: true }}
            />
            <MetricCard
              title="Active Strategies"
              value="5"
              change={{ value: 1, positive: true }}
            />
            <MetricCard
              title="System Status"
              value="Online"
            />
          </div>

          <div className="grid grid-cols-3 gap-4 mb-6">
            {/* Assets Table */}
            <Card className="col-span-2">
              <CardTitle>Tracked Assets</CardTitle>
              <div className="overflow-hidden rounded">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      {['Ticker', 'Type', 'Currency', 'Sector', 'Status'].map((h) => (
                        <th key={h} className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {assets.slice(0, 6).map((a) => (
                      <tr key={a.ticker} className="border-b border-border last:border-0 hover:bg-surface-hover">
                        <td className="py-2 px-3 font-mono font-medium text-text-primary">{a.ticker}</td>
                        <td><Badge variant="primary">{a.asset_type}</Badge></td>
                        <td className="text-text-secondary">{a.currency}</td>
                        <td className="text-text-muted text-xs">{a.sector || '—'}</td>
                        <td><Badge variant="success">Active</Badge></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            {/* Quick Stats */}
            <Card>
              <CardTitle>Quick Stats</CardTitle>
              <div className="space-y-3">
                <div className="flex justify-between items-center py-2 border-b border-border">
                  <span className="text-sm text-text-muted">Total Market Cap</span>
                  <span className="font-mono text-sm text-text-primary">$2.4T</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-border">
                  <span className="text-sm text-text-muted">24h Volume</span>
                  <span className="font-mono text-sm text-text-primary">$89.2B</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-border">
                  <span className="text-sm text-text-muted">Active Trades</span>
                  <span className="font-mono text-sm text-text-primary">1,247</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-sm text-text-muted">Win Rate</span>
                  <span className="font-mono text-sm text-accent-success">67.3%</span>
                </div>
              </div>
            </Card>
          </div>

          {/* Market Overview */}
          <Card>
            <CardTitle>Market Overview</CardTitle>
            <div className="grid grid-cols-6 gap-3">
              {TICKERS_PREVIEW.map((ticker) => {
                const data = spark(ticker);
                const first = data[0]?.v;
                const last = data[data.length - 1]?.v;
                const pct = first ? ((last - first) / first * 100) : 0;
                const up = pct >= 0;
                return (
                  <div key={ticker} className="p-3 rounded border border-border bg-surface">
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-mono text-sm font-medium text-text-primary">{ticker}</span>
                      <span className={clsx(
                        'text-xs font-medium',
                        up ? 'text-accent-success' : 'text-accent-danger'
                      )}>
                        {up ? '+' : ''}{pct.toFixed(2)}%
                      </span>
                    </div>
                    <div className="h-16">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={data}>
                          <defs>
                            <linearGradient id={`g${ticker}`} x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%"  stopColor={up ? '#10b981' : '#ef4444'} stopOpacity={0.2} />
                              <stop offset="95%" stopColor={up ? '#10b981' : '#ef4444'} stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <XAxis hide />
                          <YAxis hide />
                          <ChartTooltip />
                          <Area type="monotone" dataKey="v" stroke={up ? '#10b981' : '#ef4444'} strokeWidth={1.5} fill={`url(#g${ticker})`} dot={false} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="text-right mt-2">
                      <span className="font-mono text-sm font-semibold text-text-primary">${last?.toFixed(2)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
