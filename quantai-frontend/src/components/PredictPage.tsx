'use client';
import { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';
import clsx from 'clsx';
import { Card, CardTitle, MetricCard, Badge, Button, Spinner, TickerPills, ErrorBox, LoadingBox } from '@/components/ui';
import { ChartTooltip } from '@/components/charts/Tooltip';
import { getPrediction, trainModel, getOHLCV } from '@/lib/api';

const TICKERS = ['AAPL','MSFT','NVDA','TSLA','GOOGL','SPY','QQQ','BTC-USD','ETH-USD'];

export default function PredictPage() {
  const [ticker, setTicker]     = useState('AAPL');
  const [pred, setPred]         = useState<any>(null);
  const [ohlcv, setOhlcv]       = useState<any[]>([]);
  const [loading, setLoading]   = useState(false);
  const [training, setTraining] = useState(false);
  const [error, setError]       = useState<string | null>(null);

  const load = async (t: string) => {
    setLoading(true); setError(null);
    try {
      const [p, o] = await Promise.all([getPrediction(t), getOHLCV(t, 60)]);
      setPred(p); setOhlcv(o);
    } catch (e: any) {
      setError(e.message);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(ticker); }, [ticker]);

  const train = async () => {
    setTraining(true); setError(null);
    try {
      await trainModel(ticker);
      await load(ticker);
    } catch (e: any) {
      setError(e.message);
    } finally { setTraining(false); }
  };

  const chartData = ohlcv.slice(-40).map((r) => ({
    date: r.timestamp?.slice(0, 10) || '',
    close: r.close,
  }));

  const dir    = pred?.ensemble_direction;
  const prob   = pred ? (pred.ensemble_probability * 100).toFixed(1) : '—';
  const conf   = pred ? (pred.ensemble_confidence * 100).toFixed(1) : '—';
  const agree  = pred ? (pred.agreement_score * 100).toFixed(1) : '—';
  const signal = pred?.signal || '—';

  return (
    <div className="p-6 max-w-[1600px]">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary">AI Predictions</h1>
        <p className="text-sm text-text-muted mt-1">Ensemble — LightGBM + LSTM + Transformer</p>
      </div>

      <TickerPills tickers={TICKERS} active={ticker} onSelect={setTicker} />

      <div className="flex gap-3 mb-6">
        <Button onClick={() => load(ticker)} disabled={loading}>
          {loading && <Spinner />} Refresh
        </Button>
        <Button variant="secondary" onClick={train} disabled={training}>
          {training && <Spinner />} Train Models
        </Button>
      </div>

      {error && <ErrorBox message={`${error} — Try training the model first.`} />}

      {loading && <LoadingBox label="Loading..." />}

      {pred && !loading && (
        <>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <MetricCard title="Signal" value={signal} />
            <MetricCard title="Probability" value={`${prob}%`} />
            <MetricCard title="Confidence" value={`${conf}%`} />
            <MetricCard title="Model Agreement" value={`${agree}%`} />
          </div>

          <div className="grid grid-cols-3 gap-4 mb-4">
            <Card className="col-span-2">
              <CardTitle>Individual Model Predictions</CardTitle>
              <div className="overflow-hidden rounded">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      {['Model', 'Direction', 'Probability', 'Weight'].map((h) => (
                        <th key={h} className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(pred.individual_predictions || {}).map(([model, p]: any) => (
                      <tr key={model} className="border-b border-border last:border-0 hover:bg-surface-hover">
                        <td className="py-2 px-3 font-medium text-text-primary">{model}</td>
                        <td>
                          <Badge variant={p.direction === 'up' ? 'success' : 'danger'}>
                            {p.direction === 'up' ? 'UP' : 'DOWN'}
                          </Badge>
                        </td>
                        <td className="font-mono text-text-secondary">{(p.probability * 100).toFixed(1)}%</td>
                        <td className="font-mono text-text-muted">{((pred.weights_used?.[model] || 0) * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card>
              <CardTitle>Model Performance</CardTitle>
              <div className="space-y-4">
                <div className="flex justify-between items-center py-2 border-b border-border">
                  <span className="text-sm text-text-muted">Ensemble Probability</span>
                  <span className="font-mono text-sm text-text-primary">{prob}%</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-border">
                  <span className="text-sm text-text-muted">Confidence Score</span>
                  <span className="font-mono text-sm text-text-primary">{conf}%</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-border">
                  <span className="text-sm text-text-muted">Model Agreement</span>
                  <span className="font-mono text-sm text-text-primary">{agree}%</span>
                </div>
                <div className="pt-2">
                  <div className="flex justify-between items-center py-1">
                    <span className="text-sm text-text-muted">Total Models</span>
                    <span className="font-mono text-sm text-text-primary">3</span>
                  </div>
                  <div className="flex justify-between items-center py-1">
                    <span className="text-sm text-text-muted">Active Models</span>
                    <span className="font-mono text-sm text-accent-success">3</span>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          <Card>
            <CardTitle>Price Chart — {ticker}</CardTitle>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="pg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} interval={9} />
                  <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} domain={['auto','auto']} tickFormatter={(v) => `$${v}`} />
                  <ChartTooltip />
                  <Area type="monotone" dataKey="close" stroke="#3b82f6" strokeWidth={1.5} fill="url(#pg)" dot={false} name="Close" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
