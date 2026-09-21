"""
M14 — Report Generator API endpoints
Generates PDF reports for portfolio, backtest, and full platform.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional, Dict
import httpx
import logging
import io

from app.db.database import get_db
from app.services.reports.report_service import report_service

logger = logging.getLogger(__name__)
router = APIRouter()

BASE = "http://localhost:8000/api/v1"


# ------------------------------------------------------------------ #
#  Schemas                                                             #
# ------------------------------------------------------------------ #

class PortfolioReportRequest(BaseModel):
    tickers: List[str] = ["AAPL", "MSFT", "NVDA", "GOOGL", "SPY"]
    objective: str = "sharpe"
    days: int = 252
    include_predictions: bool = True
    include_attribution: bool = True
    include_drawdown: bool = True

class BacktestReportRequest(BaseModel):
    ticker: str = "AAPL"
    days: int = 252

class FullReportRequest(BaseModel):
    tickers: List[str] = ["AAPL", "MSFT", "NVDA", "GOOGL", "SPY"]
    backtest_ticker: str = "AAPL"
    days: int = 252


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

async def _fetch(client: httpx.AsyncClient, url: str, method: str = "GET", json: dict = None):
    try:
        if method == "POST":
            r = await client.post(url, json=json, timeout=30)
        else:
            r = await client.get(url, timeout=30)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.warning(f"Fetch failed {url}: {e}")
    return None


def _pdf_response(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ------------------------------------------------------------------ #
#  Endpoints                                                           #
# ------------------------------------------------------------------ #

@router.post("/portfolio", tags=["Report Generator"])
async def generate_portfolio_report(request: PortfolioReportRequest):
    """
    Generate a professional PDF portfolio report.
    Includes: allocation, risk metrics, attribution, drawdown, predictions.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Portfolio optimization
            markowitz = await _fetch(client, f"{BASE}/portfolio/optimize/markowitz",
                                     method="POST", json={
                                         "tickers": request.tickers,
                                         "objective": request.objective,
                                         "days": request.days,
                                     })
            if not markowitz:
                raise HTTPException(status_code=400, detail="Portfolio optimization failed")

            # Attribution
            attribution = None
            if request.include_attribution:
                weights = markowitz.get("weights", {})
                attribution = await _fetch(client, f"{BASE}/analytics/attribution",
                                           method="POST", json={
                                               "tickers": list(weights.keys()),
                                               "weights": weights,
                                               "days": request.days,
                                           })

            # Drawdown
            drawdown = None
            if request.include_drawdown:
                weights = markowitz.get("weights", {})
                drawdown = await _fetch(client, f"{BASE}/analytics/drawdown",
                                        method="POST", json={
                                            "tickers": list(weights.keys()),
                                            "weights": weights,
                                            "days": request.days,
                                        })

            # Predictions
            predictions = []
            if request.include_predictions:
                for ticker in request.tickers[:5]:
                    pred = await _fetch(client, f"{BASE}/predict/predict/{ticker}")
                    if pred:
                        pred["ticker"] = ticker
                        predictions.append(pred)

        pdf_bytes = report_service.generate_portfolio_report(
            markowitz_data=markowitz,
            attribution_data=attribution,
            drawdown_data=drawdown,
            predictions=predictions if predictions else None,
        )

        return _pdf_response(pdf_bytes, "quantai_portfolio_report.pdf")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portfolio report failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backtest", tags=["Report Generator"])
async def generate_backtest_report(request: BacktestReportRequest):
    """Generate a PDF backtest comparison report for a ticker."""
    try:
        async with httpx.AsyncClient() as client:
            compare = await _fetch(client, f"{BASE}/backtest/compare",
                                   method="POST", json={
                                       "ticker": request.ticker.upper(),
                                       "days": request.days,
                                   })
            if not compare:
                raise HTTPException(status_code=400, detail="Backtest failed")

        pdf_bytes = report_service.generate_backtest_report(
            ticker=request.ticker.upper(),
            compare_data=compare,
        )
        return _pdf_response(pdf_bytes, f"quantai_backtest_{request.ticker}.pdf")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest report failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/full", tags=["Report Generator"])
async def generate_full_report(request: FullReportRequest):
    """
    Generate a complete platform PDF report.
    Combines portfolio + predictions + backtest into one document.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Portfolio
            portfolio = await _fetch(client, f"{BASE}/portfolio/optimize/markowitz",
                                     method="POST", json={
                                         "tickers": request.tickers,
                                         "objective": "sharpe",
                                         "days": request.days,
                                     })

            # Attribution
            attribution = None
            if portfolio:
                weights = portfolio.get("weights", {})
                attribution = await _fetch(client, f"{BASE}/analytics/attribution",
                                           method="POST", json={
                                               "tickers": list(weights.keys()),
                                               "weights": weights,
                                               "days": request.days,
                                           })

            # Backtest
            backtest = await _fetch(client, f"{BASE}/backtest/compare",
                                    method="POST", json={
                                        "ticker": request.backtest_ticker.upper(),
                                        "days": request.days,
                                    })

            # Predictions
            predictions = []
            for ticker in request.tickers[:5]:
                pred = await _fetch(client, f"{BASE}/predict/predict/{ticker}")
                if pred:
                    pred["ticker"] = ticker
                    predictions.append(pred)

        data = {
            "portfolio": portfolio,
            "attribution": attribution,
            "backtest": backtest,
            "predictions": predictions,
        }

        pdf_bytes = report_service.generate_full_report(data)
        return _pdf_response(pdf_bytes, "quantai_full_report.pdf")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Full report failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", tags=["Report Generator"])
async def report_health():
    return {"status": "ok", "engine": "reportlab", "formats": ["pdf"]}
