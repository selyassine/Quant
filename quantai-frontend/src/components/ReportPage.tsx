'use client';
import { useState } from 'react';

const BASE = 'http://localhost:8000/api/v1';

const TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'SPY', 'QQQ', 'BTC-USD', 'ETH-USD'];

type ReportType = 'portfolio' | 'backtest' | 'full';

interface ReportConfig {
  type: ReportType;
  tickers: string[];
  objective: string;
  days: number;
  backtest_ticker: string;
  include_predictions: boolean;
  include_attribution: boolean;
  include_drawdown: boolean;
}

const REPORT_TYPES = [
  {
    id: 'portfolio' as ReportType,
    label: 'Portfolio Report',
    icon: '◐',
    description: 'Allocation · Risk metrics · Attribution · Drawdown · Predictions',
    color: '#378ADD',
  },
  {
    id: 'backtest' as ReportType,
    label: 'Backtest Report',
    icon: '⌬',
    description: 'Strategy comparison · Buy&Hold · SMA · RSI · Ranking',
    color: '#1D9E75',
  },
  {
    id: 'full' as ReportType,
    label: 'Full Platform Report',
    icon: '◈',
    description: 'Complete report · Portfolio + Predictions + Backtest',
    color: '#EF9F27',
  },
];

export default function ReportPage() {
  const [config, setConfig] = useState<ReportConfig>({
    type: 'portfolio',
    tickers: ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'SPY'],
    objective: 'sharpe',
    days: 252,
    backtest_ticker: 'AAPL',
    include_predictions: true,
    include_attribution: true,
    include_drawdown: true,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const toggleTicker = (t: string) => {
    setConfig(prev => ({
      ...prev,
      tickers: prev.tickers.includes(t)
        ? prev.tickers.filter(x => x !== t)
        : [...prev.tickers, t],
    }));
  };

  const generateReport = async () => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      let url = '';
      let body: any = {};

      if (config.type === 'portfolio') {
        url = `${BASE}/report/portfolio`;
        body = {
          tickers: config.tickers,
          objective: config.objective,
          days: config.days,
          include_predictions: config.include_predictions,
          include_attribution: config.include_attribution,
          include_drawdown: config.include_drawdown,
        };
      } else if (config.type === 'backtest') {
        url = `${BASE}/report/backtest`;
        body = { ticker: config.backtest_ticker, days: config.days };
      } else {
        url = `${BASE}/report/full`;
        body = {
          tickers: config.tickers,
          backtest_ticker: config.backtest_ticker,
          days: config.days,
        };
      }

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      // Download PDF
      const blob = await res.blob();
      const filename = `quantai_${config.type}_report.pdf`;
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);

      setSuccess(`✓ ${filename} downloaded successfully`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const selectedType = REPORT_TYPES.find(r => r.id === config.type)!;

  return (
    <div className="p-6 space-y-6 max-w-[900px]">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Report Generator</h1>
        <p className="text-sm text-muted mt-1">
          Génération automatique de rapports PDF professionnels
        </p>
      </div>

      {/* Report type selector */}
      <div className="grid grid-cols-3 gap-3">
        {REPORT_TYPES.map(rt => (
          <button
            key={rt.id}
            onClick={() => setConfig(prev => ({ ...prev, type: rt.id }))}
            className={`p-4 rounded-xl border text-left transition-all ${
              config.type === rt.id
                ? 'border-accent/40 bg-accent/5'
                : 'border-border bg-surface hover:border-accent/20'
            }`}
          >
            <div className="text-2xl mb-2" style={{ color: rt.color }}>{rt.icon}</div>
            <div className="text-sm font-semibold text-[#e8edf5] mb-1">{rt.label}</div>
            <div className="text-xs text-muted leading-relaxed">{rt.description}</div>
          </button>
        ))}
      </div>

      {/* Config */}
      <div className="bg-surface border border-border rounded-xl p-5 space-y-5">
        <div className="text-sm font-medium text-[#e8edf5]">Configuration</div>

        {/* Tickers — for portfolio & full */}
        {(config.type === 'portfolio' || config.type === 'full') && (
          <div>
            <div className="text-xs text-muted mb-2">Assets à inclure</div>
            <div className="flex flex-wrap gap-1.5">
              {TICKERS.map(t => (
                <button
                  key={t}
                  onClick={() => toggleTicker(t)}
                  className={`px-3 py-1 rounded text-xs font-mono transition-all ${
                    config.tickers.includes(t)
                      ? 'bg-accent/20 text-accent border border-accent/40'
                      : 'text-muted border border-border hover:border-accent/30'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
            <div className="text-xs text-muted mt-1">{config.tickers.length} assets sélectionnés</div>
          </div>
        )}

        {/* Backtest ticker */}
        {(config.type === 'backtest' || config.type === 'full') && (
          <div>
            <div className="text-xs text-muted mb-2">Ticker pour le backtest</div>
            <div className="flex flex-wrap gap-1.5">
              {['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'SPY'].map(t => (
                <button
                  key={t}
                  onClick={() => setConfig(prev => ({ ...prev, backtest_ticker: t }))}
                  className={`px-3 py-1 rounded text-xs font-mono transition-all ${
                    config.backtest_ticker === t
                      ? 'bg-green-500/20 text-green-400 border border-green-500/40'
                      : 'text-muted border border-border hover:border-accent/30'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Period */}
        <div>
          <div className="text-xs text-muted mb-2">Période</div>
          <div className="flex gap-2">
            {[
              { label: '3 mois', value: 63 },
              { label: '6 mois', value: 126 },
              { label: '1 an', value: 252 },
              { label: '2 ans', value: 504 },
            ].map(p => (
              <button
                key={p.value}
                onClick={() => setConfig(prev => ({ ...prev, days: p.value }))}
                className={`px-3 py-1.5 rounded text-xs transition-all ${
                  config.days === p.value
                    ? 'bg-accent/20 text-accent border border-accent/40'
                    : 'text-muted border border-border hover:border-accent/30'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Options — portfolio only */}
        {config.type === 'portfolio' && (
          <div>
            <div className="text-xs text-muted mb-2">Sections à inclure</div>
            <div className="flex flex-col gap-2">
              {[
                { key: 'include_predictions', label: 'AI Predictions' },
                { key: 'include_attribution', label: 'Performance Attribution' },
                { key: 'include_drawdown', label: 'Drawdown Analysis' },
              ].map(opt => (
                <label key={opt.key} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config[opt.key as keyof ReportConfig] as boolean}
                    onChange={e => setConfig(prev => ({ ...prev, [opt.key]: e.target.checked }))}
                    className="w-3.5 h-3.5 accent-blue-500"
                  />
                  <span className="text-sm text-[#e8edf5]">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Objective — portfolio only */}
        {config.type === 'portfolio' && (
          <div>
            <div className="text-xs text-muted mb-2">Objectif d'optimisation</div>
            <div className="flex gap-2">
              {[
                { label: 'Max Sharpe', value: 'sharpe' },
                { label: 'Min Volatility', value: 'min_vol' },
                { label: 'Max Return', value: 'max_return' },
              ].map(o => (
                <button
                  key={o.value}
                  onClick={() => setConfig(prev => ({ ...prev, objective: o.value }))}
                  className={`px-3 py-1.5 rounded text-xs transition-all ${
                    config.objective === o.value
                      ? 'bg-accent/20 text-accent border border-accent/40'
                      : 'text-muted border border-border hover:border-accent/30'
                  }`}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Preview */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <div className="text-xs text-muted mb-3 uppercase tracking-wider">Aperçu du rapport</div>
        <div className="flex items-center gap-3 mb-3">
          <span className="text-2xl" style={{ color: selectedType.color }}>{selectedType.icon}</span>
          <div>
            <div className="text-sm font-semibold text-[#e8edf5]">{selectedType.label}</div>
            <div className="text-xs text-muted">{selectedType.description}</div>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-xs text-muted">
          {config.type !== 'backtest' && (
            <div className="bg-bg rounded px-3 py-2">
              <div className="text-[#e8edf5] font-medium mb-0.5">Assets</div>
              <div>{config.tickers.join(', ')}</div>
            </div>
          )}
          <div className="bg-bg rounded px-3 py-2">
            <div className="text-[#e8edf5] font-medium mb-0.5">Période</div>
            <div>{config.days} jours trading</div>
          </div>
          <div className="bg-bg rounded px-3 py-2">
            <div className="text-[#e8edf5] font-medium mb-0.5">Format</div>
            <div>PDF professionnel</div>
          </div>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-4 py-3 text-sm text-green-400">
          {success}
        </div>
      )}

      {/* Generate button */}
      <button
        onClick={generateReport}
        disabled={loading || (config.type !== 'backtest' && config.tickers.length === 0)}
        className="w-full py-4 bg-accent/10 border border-accent/30 rounded-xl text-accent font-semibold text-sm hover:bg-accent/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="animate-spin">↻</span>
            Génération en cours...
          </span>
        ) : (
          `⬇ Générer ${selectedType.label}`
        )}
      </button>

      <p className="text-xs text-muted text-center">
        Le rapport PDF sera téléchargé automatiquement · Powered by ReportLab
      </p>
    </div>
  );
}
