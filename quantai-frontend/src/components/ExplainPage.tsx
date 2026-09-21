'use client';
import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';

const BASE = 'http://localhost:8000/api/v1';

const TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'SPY', 'QQQ', 'BTC-USD', 'ETH-USD'];

interface Contributor {
  feature: string;
  shap_value: number;
  feature_value: number;
  impact: string;
}

interface ExplainResult {
  ticker: string;
  prediction: { direction: string; probability: number; predicted_return_pct: number };
  explanation: string;
  top_contributors: Contributor[];
  global_feature_importance: { feature: string; importance: number }[];
  waterfall: { label: string; value: number; cumulative: number; type: string }[];
  base_value: number;
  num_features_analyzed: number;
}

export default function ExplainPage() {
  const [ticker, setTicker] = useState('AAPL');
  const [result, setResult] = useState<ExplainResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<'shap' | 'importance'>('shap');

  const explain = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${BASE}/explain/explain/${ticker}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed');
      }
      setResult(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const shapData = result?.top_contributors.map(c => ({
    feature: c.feature.replace(/_/g, ' ').substring(0, 16),
    value: parseFloat(c.shap_value.toFixed(4)),
    fill: c.shap_value > 0 ? '#1D9E75' : '#D85A30',
  })) || [];

  const importanceData = result?.global_feature_importance.slice(0, 15).map(f => ({
    feature: f.feature.replace(/_/g, ' ').substring(0, 16),
    value: parseFloat(f.importance.toFixed(4)),
  })) || [];

  return (
    <div className="p-6 space-y-5 max-w-[1100px]">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Explainable AI</h1>
        <p className="text-sm text-muted mt-1">SHAP values — pourquoi le modèle prend cette décision</p>
      </div>

      {/* Controls */}
      <div className="flex gap-3 items-center">
        <div className="flex gap-1 flex-wrap">
          {TICKERS.map(t => (
            <button
              key={t}
              onClick={() => setTicker(t)}
              className={`px-3 py-1.5 rounded text-xs font-mono transition-all ${
                ticker === t
                  ? 'bg-accent/20 text-accent border border-accent/40'
                  : 'text-muted border border-border hover:border-accent/30 hover:text-[#e8edf5]'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <button
          onClick={explain}
          disabled={loading}
          className="ml-auto px-5 py-2 bg-accent/10 border border-accent/30 rounded text-sm text-accent font-medium hover:bg-accent/20 transition-all disabled:opacity-40"
        >
          {loading ? 'Analyzing...' : '⚡ Explain'}
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400">
          {error} — Make sure the model is trained first (POST /predict/train)
        </div>
      )}

      {result && (
        <>
          {/* Prediction summary */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Direction', value: result.prediction.direction, color: result.prediction.direction === 'UP' ? '#1D9E75' : '#D85A30' },
              { label: 'Probability', value: `${result.prediction.probability}%` },
              { label: 'Expected return', value: `${result.prediction.predicted_return_pct > 0 ? '+' : ''}${result.prediction.predicted_return_pct}%` },
              { label: 'Features analyzed', value: result.num_features_analyzed },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-surface border border-border rounded-lg px-4 py-3">
                <div className="text-xs text-muted mb-1">{label}</div>
                <div className="text-lg font-semibold" style={color ? { color } : {}}>{value}</div>
              </div>
            ))}
          </div>

          {/* Explanation text */}
          <div className="bg-surface border border-border rounded-lg px-4 py-4">
            <div className="text-xs text-muted mb-2 font-medium uppercase tracking-wider">AI Explanation</div>
            <pre className="text-sm text-[#e8edf5] whitespace-pre-wrap font-sans leading-relaxed">
              {result.explanation}
            </pre>
          </div>

          {/* Tabs */}
          <div className="flex gap-1">
            {(['shap', 'importance'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 rounded text-sm transition-all ${
                  tab === t
                    ? 'bg-accent/15 text-accent border border-accent/30'
                    : 'text-muted border border-transparent hover:text-[#e8edf5]'
                }`}
              >
                {t === 'shap' ? 'SHAP Values (local)' : 'Feature Importance (global)'}
              </button>
            ))}
          </div>

          {/* Charts */}
          <div className="bg-surface border border-border rounded-lg p-4">
            {tab === 'shap' ? (
              <>
                <div className="text-xs text-muted mb-4">
                  SHAP values — contribution de chaque feature à la prédiction actuelle.
                  <span className="text-green-400 ml-2">● Positif = pousse vers UP</span>
                  <span className="text-orange-400 ml-2">● Négatif = pousse vers DOWN</span>
                </div>
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={shapData} layout="vertical" margin={{ left: 120, right: 30 }}>
                    <XAxis type="number" tick={{ fontSize: 11, fill: '#888' }} />
                    <YAxis type="category" dataKey="feature" tick={{ fontSize: 11, fill: '#aaa' }} width={115} />
                    <ReferenceLine x={0} stroke="#444" strokeWidth={1} />
                    <Tooltip
                      contentStyle={{ background: '#0f1623', border: '1px solid #2a3441', borderRadius: 8, fontSize: 12 }}
                      formatter={(v: number) => [v.toFixed(4), 'SHAP value']}
                    />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                      {shapData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} opacity={0.85} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </>
            ) : (
              <>
                <div className="text-xs text-muted mb-4">
                  Feature importance globale — quelles variables le modèle utilise le plus en général.
                </div>
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={importanceData} layout="vertical" margin={{ left: 120, right: 30 }}>
                    <XAxis type="number" tick={{ fontSize: 11, fill: '#888' }} />
                    <YAxis type="category" dataKey="feature" tick={{ fontSize: 11, fill: '#aaa' }} width={115} />
                    <Tooltip
                      contentStyle={{ background: '#0f1623', border: '1px solid #2a3441', borderRadius: 8, fontSize: 12 }}
                      formatter={(v: number) => [v.toFixed(4), 'Importance']}
                    />
                    <Bar dataKey="value" fill="#378ADD" opacity={0.8} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </>
            )}
          </div>

          {/* Waterfall table */}
          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="text-xs text-muted mb-3 font-medium uppercase tracking-wider">Waterfall — décomposition de la prédiction</div>
            <div className="space-y-1">
              {result.waterfall.map((w, i) => (
                <div key={i} className="flex items-center gap-3 text-sm py-1 border-b border-border/50 last:border-0">
                  <span className="text-muted w-28 text-xs font-mono truncate">{w.label}</span>
                  <div className="flex-1 relative h-4 bg-border/30 rounded overflow-hidden">
                    <div
                      className="absolute top-0 h-full rounded"
                      style={{
                        width: `${Math.min(Math.abs(w.value) * 500, 100)}%`,
                        background: w.type === 'positive' ? '#1D9E75' : w.type === 'negative' ? '#D85A30' : '#888',
                        opacity: 0.7,
                        left: w.value >= 0 ? '50%' : `calc(50% - ${Math.min(Math.abs(w.value) * 500, 50)}%)`,
                      }}
                    />
                  </div>
                  <span className={`w-20 text-right text-xs font-mono ${
                    w.value > 0 ? 'text-green-400' : w.value < 0 ? 'text-orange-400' : 'text-muted'
                  }`}>
                    {w.value > 0 ? '+' : ''}{w.value.toFixed(4)}
                  </span>
                  <span className="w-20 text-right text-xs font-mono text-muted">
                    → {w.cumulative.toFixed(4)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {!result && !loading && (
        <div className="text-center text-muted py-16 text-sm">
          Sélectionne un ticker et clique sur Explain pour voir les explications SHAP
        </div>
      )}
    </div>
  );
}
