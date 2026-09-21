"""
QuantAI — Backtest Endpoints
Phase 4 : Buy & Hold, SMA Crossover, RSI, Comparaison
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.services.backtest.backtest_service import backtest_service

router = APIRouter(tags=["Backtesting"])


# ------------------------------------------------------------------ #
#  SCHÉMAS
# ------------------------------------------------------------------ #

class BuyHoldRequest(BaseModel):
    ticker: str = Field(default="AAPL")
    days: int = Field(default=504, description="Nombre de jours (504 ≈ 2 ans)")


class SMARequest(BaseModel):
    ticker: str = Field(default="AAPL")
    short_window: int = Field(default=20, description="Fenêtre courte (ex: 20 jours)")
    long_window: int = Field(default=50, description="Fenêtre longue (ex: 50 jours)")
    days: int = Field(default=504)


class RSIRequest(BaseModel):
    ticker: str = Field(default="AAPL")
    period: int = Field(default=14, description="Période RSI")
    oversold: float = Field(default=30, description="Seuil survendu → BUY")
    overbought: float = Field(default=70, description="Seuil suracheté → SELL")
    days: int = Field(default=504)


class CompareRequest(BaseModel):
    ticker: str = Field(default="AAPL")
    days: int = Field(default=504)


# ------------------------------------------------------------------ #
#  ENDPOINTS
# ------------------------------------------------------------------ #

@router.post("/buy-hold")
async def backtest_buy_hold(req: BuyHoldRequest):
    """
    Backtest **Buy & Hold** — achète au début et tient jusqu'à la fin.
    Sert de benchmark pour comparer les autres stratégies.
    """
    try:
        result = await backtest_service.run_buy_hold(req.ticker, req.days)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sma-crossover")
async def backtest_sma(req: SMARequest):
    """
    Backtest **SMA Crossover**.

    - Achète quand la SMA courte croise la SMA longue **à la hausse**
    - Vend quand la SMA courte croise la SMA longue **à la baisse**

    Paramètres classiques : short=20, long=50 (swing trading)
    ou short=50, long=200 (Golden Cross / Death Cross)
    """
    try:
        result = await backtest_service.run_sma_crossover(
            req.ticker, req.short_window, req.long_window, req.days
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rsi")
async def backtest_rsi(req: RSIRequest):
    """
    Backtest **RSI (Relative Strength Index)**.

    - Achète quand RSI remonte au-dessus du seuil survendu (ex: 30)
    - Vend quand RSI dépasse le seuil suracheté (ex: 70)
    """
    try:
        result = await backtest_service.run_rsi(
            req.ticker, req.period, req.oversold, req.overbought, req.days
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
async def backtest_compare(req: CompareRequest):
    """
    **Compare toutes les stratégies** sur le même ticker.

    Teste simultanément :
    - Buy & Hold
    - SMA 20/50
    - SMA 10/30
    - RSI 14 (30/70)

    Retourne un classement par Sharpe Ratio et la meilleure stratégie.
    """
    try:
        result = await backtest_service.run_comparison(req.ticker, req.days)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def backtest_health():
    return {"status": "ok", "module": "Backtesting Phase 4"}
