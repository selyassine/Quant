# quantai-frontend

Next.js 14 dashboard for the QuantAI platform.

## Stack
- **Next.js 14** + TypeScript
- **Tailwind CSS** — dark trading terminal theme
- **Recharts** — charts (area, bar, pie)
- **JetBrains Mono** + **Inter** fonts

## Pages
| Page | Route | Description |
|------|-------|-------------|
| Overview | dashboard | KPIs, assets, sparklines |
| Market Data | market | OHLCV charts + volume |
| Predictions | predict | Ensemble ML signals |
| Portfolio | portfolio | Markowitz + Black-Litterman |
| Backtesting | backtest | Strategy comparison + equity curve |

## Setup

```powershell
cd quantai-frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Open http://localhost:3000

> Make sure `quantai-backend` is running on http://localhost:8000 first.

## API proxy
All `/api/*` calls are proxied to `http://localhost:8000/api/*` via `next.config.js`.
