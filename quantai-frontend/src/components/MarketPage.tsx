'use client';
import { useEffect, useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, ResponsiveContainer, Cell,
} from 'recharts';
import clsx from 'clsx';
import { Card, CardTitle, MetricCard, TickerPills, LoadingBox, Badge } from '@/components/ui';
import { ChartTooltip } from '@/components/charts/Tooltip';
import { getOHLCV } from '@/lib/api';

const TICKERS = ['AAPL','MSFT','NVDA','TSLA','GOOGL','SPY','QQQ','BTC-USD','ETH-USD'];

export default function MarketPage() {
  const [ticker, setTicker] = useState('AAPL');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getOHLCV(ticker, 60)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [ticker]);

  const chartData = data.slice(-50).map((r) => ({
    date: r.timestamp?.slice(5, 10) || '',
    open: r.open, high: r.high, low: r.low, close: r.close,
    volume: Math.round((r.volume || 0) / 1000),
  }));

  const latest = data[data.length - 1];
  const prev   = data[data.length - 2];
  const change = latest && prev ? ((latest.close - prev.close) / prev.close * 100) : null;

  return (
    <div className="p-6 max-w-[1600px]">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary">Market Data</h1>
        <p className="text-sm text-text-muted mt-1">OHLCV historical data from PostgreSQL</p>
      </div>

      <TickerPills tickers={TICKERS} active={ticker} onSelect={setTicker} />

      {latest && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <MetricCard
            title="Last Close"
            value={`$${latest.close?.toFixed(2)}`}
            change={change ? { value: Math.abs(change), positive: change >= 0 } : undefined}
          />
          <MetricCard
            title="Day Change"
            value={change != null ? `${change >= 0 ? '+' : ''}${change.toFixed(2)}%` : '—'}
          />
          <MetricCard
            title="Day High"
            value={`$${latest.high?.toFixed(2)}`}
          />
          <MetricCard
            title="Volume"
            value={`${((latest.volume || 0) / 1e6).toFixed(1)}M`}
          />
        </div>
      )}

      {loading ? <LoadingBox label="Loading..." /> : (
        <>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <Card className="col-span-2">
              <CardTitle>Price Chart — {ticker}</CardTitle>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} interval={9} />
                    <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} domain={['auto','auto']} tickFormatter={(v) => `$${v}`} />
                    <ChartTooltip />
                    <Area type="monotone" dataKey="close" stroke="#3b82f6" strokeWidth={1.5} fill="url(#cg)" dot={false} name="Close" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <CardTitle>Price Summary</CardTitle>
              <div className="space-y-3">
                <div className="flex justify-between items-center py-2 border-b border-border">
                  <span className="text-sm text-text-muted">Open</span>
                  <span className="font-mono text-sm text-text-primary">${latest?.open?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-border">
                  <span className="text-sm text-text-muted">High</span>
                  <span className="font-mono text-sm text-accent-success">${latest?.high?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-border">
                  <span className="text-sm text-text-muted">Low</span>
                  <span className="font-mono text-sm text-accent-danger">${latest?.low?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-border">
                  <span className="text-sm text-text-muted">Close</span>
                  <span className="font-mono text-sm text-accent-primary">${latest?.close?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-sm text-text-muted">Volume</span>
                  <span className="font-mono text-sm text-text-secondary">{((latest?.volume || 0) / 1e6).toFixed(2)}M</span>
                </div>
              </div>
            </Card>
          </div>

          <Card>
            <CardTitle>Volume — {ticker}</CardTitle>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} barSize={4}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} interval={9} />
                  <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}k`} />
                  <ChartTooltip />
                  <Bar dataKey="volume" name="Volume (k)" radius={[2, 2, 0, 0]}>
                    {chartData.map((d, i) => (
                      <Cell key={i} fill={d.close >= d.open ? '#10b981' : '#ef4444'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
