'use client';
import { useState, useEffect, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { Card, CardTitle, MetricCard, Badge, Spinner } from '@/components/ui';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'SPY', 'QQQ', 'BTC-USD', 'ETH-USD'];

type Tab = 'health' | 'registry' | 'drift' | 'accuracy' | 'retraining';

const PSI_COLOR = (v: number) =>
  v > 0.2 ? '#ef4444' : v > 0.1 ? '#f97316' : '#34d399';

const GRADE_COLOR: Record<string, string> = {
  A: '#34d399', B: '#38bdf8', C: '#f97316', D: '#ef4444',
};

export default function MLOpsPage() {
  const [tab, setTab]         = useState<Tab>('health');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');
  const [ticker, setTicker]   = useState('AAPL');

  const [healthData,    setHealthData]    = useState<any>(null);
  const [registryData,  setRegistryData]  = useState<any>(null);
  const [driftData,     setDriftData]     = useState<any>(null);
  const [accuracyData,  setAccuracyData]  = useState<any>(null);
  const [retrainData,   setRetrainData]   = useState<any>(null);

  const get = async (path: string) => {
    const r = await fetch(`${API}/api/v1/mlops/${path}`);
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  };

  const run = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      if (tab === 'health')      setHealthData(await get('health'));
      else if (tab === 'registry')   setRegistryData(await get('registry'));
      else if (tab === 'drift')      setDriftData(await get(`drift/${ticker}`));
      else if (tab === 'accuracy')   setAccuracyData(await get(`accuracy/${ticker}`));
      else if (tab === 'retraining') setRetrainData(await get('retraining'));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [tab, ticker]);

  // auto-load health on mount
  useEffect(() => { run(); }, []);

  const TABS: { id: Tab; label: string }[] = [
    { id: 'health',     label: 'System Health' },
    { id: 'registry',   label: 'Model Registry' },
    { id: 'drift',      label: 'Data Drift' },
    { id: 'accuracy',   label: 'Accuracy' },
    { id: 'retraining', label: 'Retraining' },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">MLOps & Monitoring</h1>
        <p className="text-sm text-text-muted mt-1">
          Model health · Data drift · Prediction accuracy · Retraining alerts
        </p>
      </div>

      {/* tab bar */}
      <div className="flex gap-1 bg-surface rounded-lg p-1 w-fit flex-wrap">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              tab === t.id ? 'bg-accent-primary text-black' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* controls */}
      <div className="flex items-center gap-3 flex-wrap">
        {(tab === 'drift' || tab === 'accuracy') && (
          <select
            value={ticker}
            onChange={e => setTicker(e.target.value)}
            className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
          >
            {TICKERS.map(t => <option key={t}>{t}</option>)}
          </select>
        )}
        <button
          onClick={run}
          disabled={loading}
          className="bg-accent-primary text-black font-bold px-5 py-1.5 rounded hover:bg-accent-primary/80 disabled:opacity-50 transition-colors text-sm"
        >
          {loading ? '⏳ Loading…' : '⚡ Run'}
        </button>
        {error && (
          <span className="text-accent-danger text-xs bg-accent-danger/10 rounded px-2 py-1">{error}</span>
        )}
      </div>

      {loading && (
        <div className="flex items-center justify-center h-48"><Spinner /></div>
      )}

      {/* ─── SYSTEM HEALTH ────────────────────────────────────────────────── */}
      {tab === 'health' && healthData && !loading && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricCard
              title="Status"
              value={healthData.status.toUpperCase()}
            />
            <MetricCard title="DB rows" value={healthData.database.total_rows.toLocaleString()} />
            <MetricCard
              title="Fresh tickers"
              value={`${healthData.data_freshness.fresh_tickers} / ${healthData.data_freshness.total_tickers}`}
            />
            <MetricCard title="Model files" value={healthData.models.total_files} />
          </div>

          <Card>
            <CardTitle>Data freshness per ticker</CardTitle>
            <div className="space-y-2">
              {healthData.data_freshness.tickers.map((t: any) => (
                <div key={t.ticker} className="flex items-center justify-between py-1 border-b border-border/30">
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold text-white w-16">{t.ticker}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${t.fresh ? 'bg-accent-success/20 text-accent-success' : 'bg-accent-danger/20 text-accent-danger'}`}>
                      {t.fresh ? '✓ Fresh' : '⚠ Stale'}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-text-muted">
                    <span>{t.data_points.toLocaleString()} pts</span>
                    <span>{t.days_since_update}d ago</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {healthData.models.files.length > 0 && (
            <Card>
              <CardTitle>Saved model files</CardTitle>
              <div className="flex flex-wrap gap-2">
                {healthData.models.files.map((f: string) => (
                  <span key={f} className="text-xs font-mono bg-surface px-2 py-1 rounded text-text-muted">
                    {f}
                  </span>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ─── MODEL REGISTRY ───────────────────────────────────────────────── */}
      {tab === 'registry' && registryData && !loading && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <MetricCard title="Total tickers" value={registryData.total_tickers} />
            <MetricCard title="Trained" value={registryData.trained_tickers} />
            <MetricCard
              title="Not trained"
              value={registryData.total_tickers - registryData.trained_tickers}
            />
          </div>

          <Card>
            <CardTitle>Model status per ticker</CardTitle>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-muted border-b border-border">
                  {['Ticker','Status','Models','Last trained','Data points','Needs retrain'].map(h => (
                    <th key={h} className="text-left py-2 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {registryData.models.map((m: any) => (
                  <tr key={m.ticker} className="border-b border-border/30 hover:bg-surface/50">
                    <td className="py-2 pr-4 font-mono font-bold text-text-primary">{m.ticker}</td>
                    <td className="py-2 pr-4">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        m.status === 'trained' ? 'bg-accent-success/20 text-accent-success' : 'bg-surface text-text-muted'
                      }`}>
                        {m.status}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-text-muted">
                      {m.trained_models.length > 0
                        ? m.trained_models.join(', ')
                        : '—'}
                    </td>
                    <td className="py-2 pr-4 text-text-muted">
                      {m.last_trained
                        ? new Date(m.last_trained).toLocaleDateString()
                        : '—'}
                    </td>
                    <td className="py-2 pr-4 text-text-muted">{m.data_points.toLocaleString()}</td>
                    <td className="py-2">
                      {m.needs_retraining
                        ? <span className="text-accent-warning">⚠ Yes</span>
                        : <span className="text-accent-success">✓ No</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}

      {/* ─── DATA DRIFT ───────────────────────────────────────────────────── */}
      {tab === 'drift' && driftData && !loading && !driftData.error && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricCard
              title="Overall PSI"
              value={driftData.overall_psi}
            />
            <MetricCard
              title="Severity"
              value={driftData.severity.toUpperCase()}
            />
            <MetricCard title="Reference" value={driftData.reference_period.split(' → ')[0]} />
            <MetricCard title="Current" value={driftData.current_period.split(' → ')[0]} />
          </div>

          <Card>
            <CardTitle>Recommendation</CardTitle>
            <p className={`text-sm font-medium ${
              driftData.severity === 'high' ? 'text-accent-danger' :
              driftData.severity === 'medium' ? 'text-accent-warning' : 'text-accent-success'
            }`}>
              {driftData.severity === 'high' ? '🔴' : driftData.severity === 'medium' ? '🟡' : '🟢'}{' '}
              {driftData.recommendation}
            </p>
          </Card>

          <Card>
            <CardTitle>Feature drift (PSI per feature)</CardTitle>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={driftData.features} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis dataKey="feature" type="category"
                  tick={{ fontSize: 11, fill: '#f8fafc', fontFamily: 'monospace' }} width={80} />
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid #334155' }}
                  formatter={(v: any) => [v.toFixed(4), 'PSI']}
                />
                <Bar dataKey="psi" radius={[0, 3, 3, 0]}>
                  {driftData.features.map((f: any, i: number) => (
                    <Cell key={i} fill={PSI_COLOR(f.psi)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card>
            <CardTitle>Feature detail</CardTitle>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-muted border-b border-border">
                  {['Feature','PSI','Drift','Ref mean','Curr mean','Ref std','Curr std'].map(h => (
                    <th key={h} className="text-left py-2 pr-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {driftData.features.map((f: any, i: number) => (
                  <tr key={i} className="border-b border-border/30 hover:bg-surface/50">
                    <td className="py-2 pr-3 font-mono text-text-primary">{f.feature}</td>
                    <td className="py-2 pr-3" style={{ color: PSI_COLOR(f.psi) }}>{f.psi}</td>
                    <td className="py-2 pr-3">
                      <span className={`px-1.5 py-0.5 rounded text-xs ${
                        f.drift_level === 'high' ? 'bg-accent-danger/20 text-accent-danger' :
                        f.drift_level === 'medium' ? 'bg-accent-warning/20 text-accent-warning' :
                        'bg-accent-success/20 text-accent-success'
                      }`}>{f.drift_level}</span>
                    </td>
                    <td className="py-2 pr-3 text-text-muted">{f.ref_mean}</td>
                    <td className="py-2 pr-3 text-text-muted">{f.curr_mean}</td>
                    <td className="py-2 pr-3 text-text-muted">{f.ref_std}</td>
                    <td className="py-2 text-text-muted">{f.curr_std}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}

      {/* ─── ACCURACY ─────────────────────────────────────────────────────── */}
      {tab === 'accuracy' && accuracyData && !loading && !accuracyData.error && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricCard
              title="Accuracy"
              value={`${accuracyData.accuracy}%`}
            />
            <MetricCard title="Precision" value={`${accuracyData.precision}%`} />
            <MetricCard title="Recall" value={`${accuracyData.recall}%`} />
            <MetricCard
              title="Grade"
              value={accuracyData.grade}
            />
          </div>

          {/* confusion matrix */}
          <Card>
            <CardTitle>Confusion matrix</CardTitle>
            <div className="grid grid-cols-2 gap-2 w-48">
              {[
                { label: 'True Positive', value: accuracyData.confusion_matrix.true_positive,  color: 'text-accent-success' },
                { label: 'False Positive', value: accuracyData.confusion_matrix.false_positive, color: 'text-accent-danger' },
                { label: 'False Negative', value: accuracyData.confusion_matrix.false_negative, color: 'text-accent-danger' },
                { label: 'True Negative', value: accuracyData.confusion_matrix.true_negative,  color: 'text-accent-success' },
              ].map(c => (
                <div key={c.label} className="bg-surface rounded p-3 text-center">
                  <div className={`text-2xl font-bold ${c.color}`}>{c.value}</div>
                  <div className="text-xs text-text-muted mt-1">{c.label}</div>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <CardTitle>Metrics</CardTitle>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-text-muted text-xs">F1 Score</div>
                <div className="text-text-primary font-bold text-lg">{accuracyData.f1_score}</div>
              </div>
              <div>
                <div className="text-text-muted text-xs">Total predictions</div>
                <div className="text-text-primary font-bold text-lg">{accuracyData.total_predictions}</div>
              </div>
              <div>
                <div className="text-text-muted text-xs">Correct</div>
                <div className="text-text-primary font-bold text-lg">{accuracyData.correct_predictions}</div>
              </div>
            </div>
            <p className="text-xs text-text-muted mt-4">
              Note: accuracy is computed using a momentum proxy (5-day return direction). 
              Train models via Predictions page for real ML accuracy.
            </p>
          </Card>
        </div>
      )}

      {/* ─── RETRAINING ───────────────────────────────────────────────────── */}
      {tab === 'retraining' && retrainData && !loading && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard title="Alerts" value={retrainData.total_alerts} />
            <MetricCard title="Summary" value={retrainData.total_alerts === 0 ? 'All good' : 'Action needed'} />
          </div>

          {retrainData.total_alerts === 0 ? (
            <Card>
              <div className="flex items-center gap-3 py-4">
                <span className="text-3xl">✅</span>
                <span className="text-accent-success font-medium">{retrainData.summary}</span>
              </div>
            </Card>
          ) : (
            <Card>
              <CardTitle>{`${retrainData.total_alerts} tickers need attention`}</CardTitle>
              <div className="space-y-3">
                {retrainData.alerts.map((a: any, i: number) => (
                  <div key={i} className="border border-border rounded p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-text-primary">{a.ticker}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        a.priority === 'high'
                          ? 'bg-accent-danger/20 text-accent-danger'
                          : 'bg-accent-warning/20 text-accent-warning'
                      }`}>
                        {a.priority} priority
                      </span>
                    </div>
                    <ul className="text-xs text-text-muted space-y-1">
                      {a.reasons.map((r: string, j: number) => (
                        <li key={j}>• {r}</li>
                      ))}
                    </ul>
                    <code className="text-xs text-accent-primary bg-surface px-2 py-1 rounded block">
                      {a.action}
                    </code>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* empty state */}
      {!loading && !error && (
        (tab === 'health'     && !healthData) ||
        (tab === 'registry'   && !registryData) ||
        (tab === 'drift'      && !driftData) ||
        (tab === 'accuracy'   && !accuracyData) ||
        (tab === 'retraining' && !retrainData)
      ) && (
        <div className="flex flex-col items-center justify-center h-48 text-text-muted gap-2">
          <span className="text-4xl">◎</span>
          <p className="text-sm">Click ⚡ Run to load data</p>
        </div>
      )}
    </div>
  );
}
