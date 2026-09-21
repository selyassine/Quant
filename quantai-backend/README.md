# quantai-backend

FastAPI backend for the QuantAI platform — Market Data Collector + Feature Engineering.

## Stack

- **FastAPI** — REST API
- **PostgreSQL** — time-series storage
- **Redis** — cache + Celery broker
- **Celery** — async tasks & scheduled jobs
- **yfinance** — free market data (stocks, ETFs, crypto, indices)
- **pandas-ta** — 100+ technical indicators

---

## Setup (Windows)

### 1. Clone the repo

```powershell
git clone https://github.com/YOUR_USERNAME/quantai-backend.git
cd quantai-backend
```

### 2. Copy the env file

```powershell
copy .env.example .env
```

> You can leave the default values for local development.

### 3. Start all services with Docker

```powershell
docker compose up --build
```

This starts:
- `quantai_db` — PostgreSQL on port 5432
- `quantai_redis` — Redis on port 6379
- `quantai_api` — FastAPI on port 8000 (with hot reload)
- `quantai_worker` — Celery worker
- `quantai_beat` — Celery beat (scheduled tasks)

### 4. Open Swagger docs

```
http://localhost:8000/docs
```

---

## API Endpoints

### Health
```
GET /             → status ok
GET /health       → health check
```

### Market Data
```
GET  /api/v1/market/assets                    → list all tracked assets
GET  /api/v1/market/assets/{ticker}           → get asset info
GET  /api/v1/market/ohlcv/{ticker}            → get OHLCV data
POST /api/v1/market/collect                   → queue collection (async)
POST /api/v1/market/collect/sync/{ticker}     → collect now (sync)
GET  /api/v1/market/features/{ticker}         → OHLCV + all features
```

### Example: Collect Apple data

```bash
curl -X POST "http://localhost:8000/api/v1/market/collect/sync/AAPL?period=2y"
```

### Example: Get features for Tesla

```bash
curl "http://localhost:8000/api/v1/market/features/TSLA"
```

---

## Seed initial data

```powershell
docker exec quantai_api python scripts/seed_data.py
```

This collects 2 years of daily data for AAPL, MSFT, GOOGL, NVDA, TSLA, SPY, QQQ, BTC-USD and more.

---

## Project Structure

```
quantai-backend/
├── app/
│   ├── main.py                          # FastAPI app entry point
│   ├── core/
│   │   └── config.py                    # Settings (pydantic-settings)
│   ├── db/
│   │   ├── database.py                  # Engine, session, Base
│   │   └── models/
│   │       ├── asset.py                 # Asset model
│   │       └── ohlcv.py                 # OHLCV model
│   ├── schemas/
│   │   └── market.py                    # Pydantic schemas
│   ├── services/
│   │   ├── data/
│   │   │   └── market_data.py           # yfinance collector + DB storage
│   │   └── features/
│   │       └── feature_engineering.py   # 100+ technical indicators
│   ├── tasks/
│   │   ├── celery_app.py                # Celery config + beat schedule
│   │   └── market_tasks.py              # Async collection tasks
│   └── api/
│       └── endpoints/
│           └── market.py                # REST endpoints
├── scripts/
│   └── seed_data.py                     # Seed initial tickers
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```
