'use client';
import { useState, useEffect } from 'react';

const BASE = 'http://localhost:8000/api/v1';
const TICKERS = ['Market', 'AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'SPY', 'BTC-USD', 'ETH-USD'];

interface Article {
  title: string;
  url: string;
  published_at: string;
  summary: string;
  source: string;
  sentiment: string;
  sentiment_scores: { positive: number; negative: number; neutral: number };
  impact_score: number;
  relevance?: string;
}

interface Aggregate {
  overall_sentiment: string;
  sentiment_score: number;
  positive_pct: number;
  negative_pct: number;
  neutral_pct: number;
  avg_impact: number;
  article_count: number;
}

const SENTIMENT_COLORS: Record<string, string> = {
  positive: '#1D9E75',
  negative: '#D85A30',
  neutral: '#888780',
};

const SENTIMENT_BG: Record<string, string> = {
  positive: 'bg-green-500/10 border-green-500/20 text-green-400',
  negative: 'bg-orange-500/10 border-orange-500/20 text-orange-400',
  neutral: 'bg-gray-500/10 border-gray-500/20 text-gray-400',
};

export default function NewsPage() {
  const [ticker, setTicker] = useState('Market');
  const [articles, setArticles] = useState<Article[]>([]);
  const [aggregate, setAggregate] = useState<Aggregate | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchNews = async (t: string) => {
    setLoading(true);
    setError('');
    try {
      const url = t === 'Market'
        ? `${BASE}/news/market?limit=30`
        : `${BASE}/news/ticker/${t}?limit=20`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setArticles(data.articles || []);
      setAggregate(data.aggregate || null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchNews(ticker); }, [ticker]);

  const sentimentColor = aggregate ? SENTIMENT_COLORS[aggregate.overall_sentiment] : '#888';

  return (
    <div className="p-6 space-y-5 max-w-[1100px]">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">News Intelligence</h1>
          <p className="text-sm text-muted mt-1">
            Actualités financières · Sentiment NLP · Impact estimé
          </p>
        </div>
        <button
          onClick={() => fetchNews(ticker)}
          disabled={loading}
          className="px-4 py-2 bg-accent/10 border border-accent/30 rounded text-sm text-accent hover:bg-accent/20 transition-all disabled:opacity-40"
        >
          {loading ? '...' : '↻ Refresh'}
        </button>
      </div>

      {/* Ticker selector */}
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

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Aggregate sentiment */}
      {aggregate && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-surface border border-border rounded-lg px-4 py-3 col-span-2 md:col-span-1">
            <div className="text-xs text-muted mb-1">Overall sentiment</div>
            <div className="text-lg font-semibold capitalize" style={{ color: sentimentColor }}>
              {aggregate.overall_sentiment}
            </div>
            <div className="text-xs text-muted mt-1">Score: {aggregate.sentiment_score > 0 ? '+' : ''}{aggregate.sentiment_score}</div>
          </div>

          <div className="bg-surface border border-border rounded-lg px-4 py-3">
            <div className="text-xs text-muted mb-2">Sentiment breakdown</div>
            <div className="space-y-1">
              {[
                { label: 'Positive', pct: aggregate.positive_pct, color: '#1D9E75' },
                { label: 'Neutral', pct: aggregate.neutral_pct, color: '#888' },
                { label: 'Negative', pct: aggregate.negative_pct, color: '#D85A30' },
              ].map(({ label, pct, color }) => (
                <div key={label} className="flex items-center gap-2">
                  <div className="w-16 text-xs text-muted">{label}</div>
                  <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
                  </div>
                  <div className="text-xs text-muted w-8 text-right">{pct}%</div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-surface border border-border rounded-lg px-4 py-3">
            <div className="text-xs text-muted mb-1">Articles analyzed</div>
            <div className="text-2xl font-semibold">{aggregate.article_count}</div>
            <div className="text-xs text-muted mt-1">Avg impact: {aggregate.avg_impact > 0 ? '+' : ''}{aggregate.avg_impact}</div>
          </div>

          <div className="bg-surface border border-border rounded-lg px-4 py-3">
            <div className="text-xs text-muted mb-1">Signal</div>
            <div className={`text-sm font-semibold px-2 py-1 rounded border inline-block mt-1 ${SENTIMENT_BG[aggregate.overall_sentiment]}`}>
              {aggregate.overall_sentiment === 'positive' ? '▲ Bullish' :
               aggregate.overall_sentiment === 'negative' ? '▼ Bearish' : '◆ Neutral'}
            </div>
            <div className="text-xs text-muted mt-2">{ticker === 'Market' ? 'General market' : ticker}</div>
          </div>
        </div>
      )}

      {/* Articles list */}
      {loading ? (
        <div className="text-center text-muted py-16 text-sm">Loading news...</div>
      ) : articles.length === 0 ? (
        <div className="text-center text-muted py-16 text-sm">No articles found</div>
      ) : (
        <div className="space-y-2">
          <div className="text-xs text-muted mb-3">{articles.length} articles</div>
          {articles.map((article, i) => (
            <div key={i} className="bg-surface border border-border rounded-lg px-4 py-3 hover:border-accent/20 transition-all">
              <div className="flex items-start gap-3">
                {/* Sentiment badge */}
                <span className={`shrink-0 text-[10px] font-medium px-2 py-0.5 rounded border mt-0.5 ${SENTIMENT_BG[article.sentiment] || SENTIMENT_BG.neutral}`}>
                  {article.sentiment === 'positive' ? '▲' : article.sentiment === 'negative' ? '▼' : '◆'} {article.sentiment}
                </span>

                <div className="flex-1 min-w-0">
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-[#e8edf5] hover:text-accent transition-colors line-clamp-2"
                  >
                    {article.title}
                  </a>
                  {article.summary && (
                    <p className="text-xs text-muted mt-1 line-clamp-2">{article.summary}</p>
                  )}
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-[10px] text-muted">{article.source}</span>
                    {article.published_at && (
                      <span className="text-[10px] text-muted">{article.published_at.substring(0, 16)}</span>
                    )}
                    {article.impact_score !== 0 && (
                      <span className={`text-[10px] font-mono ${article.impact_score > 0 ? 'text-green-400' : 'text-orange-400'}`}>
                        Impact: {article.impact_score > 0 ? '+' : ''}{article.impact_score}
                      </span>
                    )}
                  </div>
                </div>

                {/* Confidence bars */}
                <div className="shrink-0 w-20 space-y-1">
                  {Object.entries(article.sentiment_scores || {}).map(([k, v]) => (
                    <div key={k} className="flex items-center gap-1">
                      <div className="w-6 text-[9px] text-muted">{k.substring(0, 3)}</div>
                      <div className="flex-1 h-1 bg-border rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${(v as number) * 100}%`,
                            background: SENTIMENT_COLORS[k] || '#888',
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
