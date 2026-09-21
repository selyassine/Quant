"""
M9 — Paper Trading API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional

from app.db.database import get_db
from app.services.paper_trading.paper_trading_service import paper_trading_service

router = APIRouter(tags=["Paper Trading"])


# ── Schemas ────────────────────────────────────────────────────────────────

class OrderRequest(BaseModel):
    ticker:   str
    side:     str = Field(..., pattern="^(buy|sell)$")
    quantity: float = Field(..., gt=0)
    reason:   str = ""
    source:   str = "manual"


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/account")
async def get_account(db: AsyncSession = Depends(get_db)):
    """Get paper trading account summary."""
    try:
        return await paper_trading_service.get_account_summary(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_positions(db: AsyncSession = Depends(get_db)):
    """Get all open positions."""
    try:
        return await paper_trading_service.get_positions(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def get_orders(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get recent orders."""
    try:
        return await paper_trading_service.get_orders(db, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/order")
async def place_order(payload: OrderRequest, db: AsyncSession = Depends(get_db)):
    """
    Place a paper trading order.
    Fills immediately at last known close price.
    """
    try:
        return await paper_trading_service.place_order(
            ticker=payload.ticker,
            side=payload.side,
            quantity=payload.quantity,
            reason=payload.reason,
            source=payload.source,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance(db: AsyncSession = Depends(get_db)):
    """Get full performance report — account + positions + transactions."""
    try:
        return await paper_trading_service.get_performance(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_account(db: AsyncSession = Depends(get_db)):
    """Reset paper trading account to $100,000 initial capital."""
    try:
        return await paper_trading_service.reset_account(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price/{ticker}")
async def get_price(ticker: str, db: AsyncSession = Depends(get_db)):
    """Get current price for a ticker."""
    try:
        price = await paper_trading_service.get_current_price(ticker, db)
        return {"ticker": ticker.upper(), "price": price}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/health")
async def health():
    return {"status": "ok", "module": "paper_trading", "initial_capital": 100_000}
