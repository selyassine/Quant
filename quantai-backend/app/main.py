"""
QuantAI — FastAPI Main Application

Modules:
- Phase 1: Market Data
- Phase 2: Prediction Engine (LightGBM + LSTM + Transformer)
- Phase 3: Portfolio Management (Markowitz + Black-Litterman + Risk Metrics)
- Phase 4: Backtesting (Buy & Hold, SMA, RSI, Compare)

Additional Modules:
- M4: Strategy Builder
- M8: News Intelligence
- M9: Paper Trading
- M10: Explainable AI (SHAP)
- M11: AI Assistant (Groq + RAG)
- M12: MLOps & Monitoring
- M13: Portfolio Analytics
- M14: Report Generator PDF
- Live: Alpaca Real-Time Trading
- Agent: Autonomous Trading Agent
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.db.database import init_db

# ==========================
# Core Routers
# ==========================
from app.api.endpoints import market
from app.api.endpoints.predict import router as predict_router
from app.api.endpoints.portfolio import router as portfolio_router
from app.api.endpoints.backtest import router as backtest_router
from app.api.endpoints.strategy import router as strategy_router
from app.api.endpoints.news import router as news_router
from app.api.endpoints.paper_trading import router as paper_trading_router
from app.api.endpoints.explainability import router as explain_router
from app.api.endpoints.analytics import router as analytics_router
from app.api.endpoints.report import router as report_router
from app.api.endpoints.assistant import router as assistant_router
from app.api.endpoints.agent import router as agent_router

# ==========================
# Optional Routers
# ==========================
try:
    from app.api.endpoints.realtime import router as realtime_router
    HAS_REALTIME = True
except Exception:
    HAS_REALTIME = False

try:
    from app.api.endpoints.mlops import router as mlops_router
    HAS_MLOPS = True
except Exception:
    HAS_MLOPS = False


# ==========================
# Lifespan
# ==========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} [{settings.app_env}]")

    await init_db()

    logger.info("Database initialized successfully.")

    yield

    logger.info("Application shutdown.")


# ==========================
# FastAPI App
# ==========================
app = FastAPI(
    title=settings.app_name,
    description="AI Quantitative Trading & Portfolio Management Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ==========================
# CORS
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# Register Core Routers
# ==========================
app.include_router(market.router, prefix="/api/v1")

app.include_router(
    predict_router,
    prefix="/api/v1/predict",
    tags=["Prediction"],
)

app.include_router(
    portfolio_router,
    prefix="/api/v1/portfolio",
    tags=["Portfolio"],
)

app.include_router(
    backtest_router,
    prefix="/api/v1/backtest",
    tags=["Backtesting"],
)

app.include_router(
    strategy_router,
    prefix="/api/v1/strategy",
    tags=["Strategy"],
)

app.include_router(
    news_router,
    prefix="/api/v1/news",
    tags=["News"],
)

app.include_router(
    paper_trading_router,
    prefix="/api/v1/paper",
    tags=["Paper Trading"],
)

app.include_router(
    explain_router,
    prefix="/api/v1/explain",
    tags=["Explainability"],
)

app.include_router(
    analytics_router,
    prefix="/api/v1/analytics",
    tags=["Analytics"],
)

app.include_router(
    report_router,
    prefix="/api/v1/report",
    tags=["Reports"],
)

app.include_router(
    assistant_router,
    prefix="/api/v1/assistant",
    tags=["AI Assistant"],
)

app.include_router(
    agent_router,
    prefix="/api/v1/agent",
    tags=["Autonomous Agent"],
)

# ==========================
# Register Optional Routers
# ==========================
if HAS_REALTIME:
    app.include_router(
        realtime_router,
        prefix="/api/v1/realtime",
        tags=["Real-Time Trading"],
    )
    logger.info("Realtime module loaded.")
else:
    logger.warning("Realtime module not available.")

if HAS_MLOPS:
    app.include_router(
        mlops_router,
        prefix="/api/v1/mlops",
        tags=["MLOps"],
    )
    logger.info("MLOps module loaded.")
else:
    logger.warning("MLOps module not available.")


# ==========================
# Health Endpoints
# ==========================
@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "application": settings.app_name,
        "version": "0.1.0",
        "environment": settings.app_env,
    }


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "environment": settings.app_env,
    }