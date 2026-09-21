"""
M13 — Portfolio Analytics Endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from app.db.database import AsyncSessionLocal
from app.services.analytics.analytics_service import analytics_service

router = APIRouter(tags=["Portfolio Analytics"])


# ------------------------------------------------------------------ #
#  SCHEMAS
# ------------------------------------------------------------------ #

class CorrRequest(BaseModel):
    tickers: List[str] = Field(default=["AAPL", "MSFT", "NVDA", "GOOGL", "SPY", "QQQ"])
    days: int = Field(default=252)


class RollingRequest(BaseModel):
    tickers: List[str] = Field(default=["AAPL", "MSFT", "NVDA", "SPY"])
    weights: Dict[str, float] = Field(default={"AAPL": 0.3, "MSFT": 0.3, "NVDA": 0.2, "SPY": 0.2})
    days: int = Field(default=252)
    window: int = Field(default=30, description="Rolling window in days")


class AttributionRequest(BaseModel):
    weights: Dict[str, float] = Field(default={"AAPL": 0.3, "MSFT": 0.25, "NVDA": 0.25, "SPY": 0.2})
    days: int = Field(default=252)


class DrawdownRequest(BaseModel):
    tickers: List[str] = Field(default=["AAPL", "MSFT", "NVDA", "SPY"])
    weights: Dict[str, float] = Field(default={"AAPL": 0.3, "MSFT": 0.3, "NVDA": 0.2, "SPY": 0.2})
    days: int = Field(default=252)


class DashboardRequest(BaseModel):
    weights: Dict[str, float] = Field(
        default={"AAPL": 0.3, "MSFT": 0.25, "NVDA": 0.25, "SPY": 0.2}
    )
    days: int = Field(default=252)


# ------------------------------------------------------------------ #
#  ENDPOINTS
# ------------------------------------------------------------------ #

@router.post("/correlation")
async def get_correlation(req: CorrRequest):
    """
    Compute **correlation matrix** between assets.
    Returns data formatted for a heatmap visualization.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await analytics_service.correlation_matrix(
                req.tickers, req.days, session
            )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rolling")
async def get_rolling_metrics(req: RollingRequest):
    """
    Compute **rolling metrics** : Sharpe, volatility, return.
    Returns time series for charts.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await analytics_service.rolling_metrics(
                req.tickers, req.weights, req.days, req.window, session
            )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/attribution")
async def get_attribution(req: AttributionRequest):
    """
    **Performance attribution** : contribution of each asset to total return.
    Shows which assets drove performance and which dragged it down.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await analytics_service.performance_attribution(
                req.weights, req.days, session
            )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drawdown")
async def get_drawdown(req: DrawdownRequest):
    """
    **Drawdown analysis** : worst periods, recovery times, underwater chart.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await analytics_service.drawdown_analysis(
                req.tickers, req.weights, req.days, session
            )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sector")
async def get_sector(weights: Dict[str, float]):
    """
    **Sector exposure** based on portfolio weights.
    """
    try:
        return analytics_service.sector_exposure(weights)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dashboard")
async def get_dashboard(req: DashboardRequest):
    """
    **Full analytics dashboard** — all metrics in one call.
    Includes: correlation, rolling metrics, attribution, drawdown, sector.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await analytics_service.full_dashboard(
                req.weights, req.days, session
            )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def analytics_health():
    return {"status": "ok", "module": "Portfolio Analytics M13"}
