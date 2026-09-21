const BASE = 'http://localhost:8000/api/v1';

async function req<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

// ── Market ────────────────────────────────────────────────────────────────
export const getAssets = () => req<any[]>('/market/assets');
export const getAsset  = (ticker: string) => req<any>(`/market/assets/${ticker}`);
export const getOHLCV  = (ticker: string, limit = 60) =>
  req<any[]>(`/market/ohlcv/${ticker}?limit=${limit}`);
export const getFeatures = (ticker: string, limit = 200) =>
  req<any>(`/market/features/${ticker}?limit=${limit}`);
export const collectSync = (ticker: string, period = '2y') =>
  req<any>(`/market/collect/sync/${ticker}?period=${period}`, { method: 'POST' });

// ── Predictions ───────────────────────────────────────────────────────────
export const trainModel = (ticker: string, models?: string[]) =>
  req<any>('/predict/train', {
    method: 'POST',
    body: JSON.stringify({ ticker, ...(models ? { models } : {}) }),
  });
export const getPrediction = (ticker: string) =>
  req<any>(`/predict/predict/${ticker}`);
export const getModelStatus = (ticker: string) =>
  req<any>(`/predict/status/${ticker}`);
export const getAllStatus = () => req<any>('/predict/status');

// ── Portfolio ─────────────────────────────────────────────────────────────
export const optimizeMarkowitz = (tickers: string[], objective = 'sharpe', days = 252) =>
  req<any>('/portfolio/optimize/markowitz', {
    method: 'POST',
    body: JSON.stringify({ tickers, objective, max_weight: 0.4, days }),
  });
export const optimizeBL = (tickers: string[], views: any[], days = 252) =>
  req<any>('/portfolio/optimize/black-litterman', {
    method: 'POST',
    body: JSON.stringify({ tickers, views, max_weight: 0.4, days }),
  });
export const analyzePortfolio = (tickers: string[], weights: Record<string, number>) =>
  req<any>('/portfolio/analyze', {
    method: 'POST',
    body: JSON.stringify({ tickers, weights }),
  });

// ── Backtesting ───────────────────────────────────────────────────────────
export const backtestBuyHold = (ticker: string, days = 252) =>
  req<any>('/backtest/buy-hold', { method: 'POST', body: JSON.stringify({ ticker, days }) });
export const backtestSMA = (ticker: string, short_window = 10, long_window = 30, days = 252) =>
  req<any>('/backtest/sma-crossover', {
    method: 'POST',
    body: JSON.stringify({ ticker, short_window, long_window, days }),
  });
export const backtestRSI = (ticker: string, period = 14, oversold = 30, overbought = 70, days = 252) =>
  req<any>('/backtest/rsi', {
    method: 'POST',
    body: JSON.stringify({ ticker, period, oversold, overbought, days }),
  });
export const backtestMACD = (ticker: string, days = 252) =>
  req<any>('/backtest/macd', { method: 'POST', body: JSON.stringify({ ticker, days }) });
export const backtestCompare = (ticker: string, days = 252) =>
  req<any>('/backtest/compare', { method: 'POST', body: JSON.stringify({ ticker, days }) });
