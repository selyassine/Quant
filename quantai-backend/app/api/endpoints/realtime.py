"""
Alpaca Real-time API Endpoints
Live prices · Paper trading orders · Portfolio · SSE stream
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional

from app.services.alpaca.alpaca_service import alpaca_service
from app.services.alpaca.realtime_service import price_stream

router = APIRouter(tags=["Real-Time (Alpaca)"])


# ── Schemas ────────────────────────────────────────────────────────────────

class AlpacaOrderRequest(BaseModel):
    ticker:     str
    side:       str = Field(..., pattern="^(buy|sell)$")
    qty:        float = Field(..., gt=0)
    order_type: str = "market"


# ── Account ────────────────────────────────────────────────────────────────

@router.get("/account")
async def get_account():
    """Get Alpaca paper trading account info."""
    try:
        data = await alpaca_service.get_account()
        return {
            "buying_power":    float(data.get("buying_power", 0)),
            "cash":            float(data.get("cash", 0)),
            "portfolio_value": float(data.get("portfolio_value", 0)),
            "equity":          float(data.get("equity", 0)),
            "initial_capital": 100_000,
            "pnl":             float(data.get("equity", 0)) - 100_000,
            "pnl_pct":        (float(data.get("equity", 0)) - 100_000) / 100_000 * 100,
            "status":          data.get("status"),
            "account_number":  data.get("account_number"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Live prices ────────────────────────────────────────────────────────────

@router.get("/price/{ticker}")
async def get_live_price(ticker: str):
    """Get latest real-time price for a ticker."""
    try:
        return await alpaca_service.get_latest_price(ticker.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices")
async def get_multiple_prices(
    tickers: str = Query(default="AAPL,MSFT,NVDA,TSLA,GOOGL,SPY,QQQ"),
):
    """Get latest prices for multiple tickers."""
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
        prices = await alpaca_service.get_multiple_prices(ticker_list)
        return {"prices": prices, "count": len(prices)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream")
async def live_price_stream(
    tickers: str = Query(default="AAPL,MSFT,NVDA,TSLA,GOOGL,SPY,QQQ"),
):
    """
    SSE endpoint — streams live prices every 2 seconds.
    Frontend: const es = new EventSource('/api/v1/realtime/stream')
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    return StreamingResponse(
        price_stream(ticker_list),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ── Historical ─────────────────────────────────────────────────────────────

@router.get("/history/{ticker}")
async def get_history(
    ticker: str,
    timeframe: str = Query(default="1Day"),
    days: int = Query(default=365),
):
    """Get historical bars from Alpaca."""
    try:
        from datetime import datetime, timedelta
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        bars  = await alpaca_service.get_historical_bars(
            ticker.upper(), timeframe=timeframe, start=start
        )
        return {"ticker": ticker.upper(), "bars": bars, "count": len(bars)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Orders ─────────────────────────────────────────────────────────────────

@router.post("/order")
async def place_order(payload: AlpacaOrderRequest):
    """
    Place a paper trading order via Alpaca.
    Fills at REAL market price — not DB price.
    """
    try:
        result = await alpaca_service.place_order(
            ticker=payload.ticker,
            side=payload.side,
            qty=payload.qty,
            order_type=payload.order_type,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders")
async def get_orders(status: str = Query(default="all")):
    """Get paper trading orders from Alpaca."""
    try:
        return await alpaca_service.get_orders(status=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Positions ──────────────────────────────────────────────────────────────

@router.get("/positions")
async def get_positions():
    """Get open positions with real-time P&L."""
    try:
        return await alpaca_service.get_positions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio/history")
async def get_portfolio_history(period: str = Query(default="1M")):
    """Get portfolio value history (1W, 1M, 3M, 6M, 1A)."""
    try:
        return await alpaca_service.get_portfolio_history(period)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    try:
        account = await alpaca_service.get_account()
        return {
            "status":          "connected",
            "account_status":  account.get("status"),
            "portfolio_value": float(account.get("portfolio_value", 0)),
            "data_source":     "Alpaca Paper Trading",
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}
