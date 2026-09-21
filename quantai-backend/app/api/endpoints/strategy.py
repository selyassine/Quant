"""
M4 — Strategy Builder API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel, Field
from typing import List, Any, Optional

from app.db.database import get_db
from app.db.models.ohlcv import OHLCV, Timeframe
from app.services.strategy.strategy_engine import (
    strategy_engine, Strategy, Rule, SUPPORTED_INDICATORS, OPERATORS
)
import pandas as pd

router = APIRouter(tags=["Strategy Builder"])


# ── Schemas ────────────────────────────────────────────────────────────────

class RuleSchema(BaseModel):
    indicator:   str
    operator:    str
    value:       Any          # float or indicator name
    description: str = ""

class RunStrategyRequest(BaseModel):
    ticker:           str = "AAPL"
    name:             str = "My Strategy"
    description:      str = ""
    buy_rules:        List[RuleSchema]
    sell_rules:       List[RuleSchema]
    logic:            str = Field(default="AND", pattern="^(AND|OR)$")
    days:             int = Field(default=252, ge=60, le=5000)
    stop_loss_pct:    Optional[float] = Field(default=None, ge=0.01, le=0.5)
    take_profit_pct:  Optional[float] = Field(default=None, ge=0.01, le=2.0)

class ValidateRequest(BaseModel):
    buy_rules:  List[RuleSchema]
    sell_rules: List[RuleSchema]

class PresetRunRequest(BaseModel):
    ticker:     str = "AAPL"
    preset_idx: int = Field(default=0, ge=0, le=10)
    days:       int = Field(default=252, ge=60, le=5000)


# ── Helper ─────────────────────────────────────────────────────────────────

async def load_ohlcv(ticker: str, days: int, db: AsyncSession) -> pd.DataFrame:
    result = await db.execute(
        select(OHLCV)
        .where(OHLCV.ticker == ticker.upper())
        .where(OHLCV.timeframe == Timeframe.D1)
        .order_by(OHLCV.timestamp.desc())
        .limit(days)
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}. Import data first.")

    data = [{"timestamp": r.timestamp, "open": r.open, "high": r.high, "low": r.low, "close": r.close, "volume": r.volume or 0}
            for r in reversed(rows)]
    return pd.DataFrame(data).set_index("timestamp")


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/indicators")
async def list_indicators():
    """List all supported indicators and operators."""
    return {
        "indicators": SUPPORTED_INDICATORS,
        "operators":  OPERATORS,
        "total":      len(SUPPORTED_INDICATORS),
    }

@router.get("/presets")
async def get_presets():
    """Get built-in strategy presets."""
    return strategy_engine.get_preset_strategies()

@router.post("/validate")
async def validate_strategy(payload: ValidateRequest):
    """Validate strategy rules without running."""
    result = strategy_engine.validate_strategy(
        [r.model_dump() for r in payload.buy_rules],
        [r.model_dump() for r in payload.sell_rules],
    )
    return result

@router.post("/run")
async def run_strategy(payload: RunStrategyRequest, db: AsyncSession = Depends(get_db)):
    """
    Run a custom strategy on historical data.
    Returns trades, equity curve, and performance metrics.
    """
    # Validate first
    validation = strategy_engine.validate_strategy(
        [r.model_dump() for r in payload.buy_rules],
        [r.model_dump() for r in payload.sell_rules],
    )
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail={"errors": validation["errors"]})

    # Load data
    df = await load_ohlcv(payload.ticker, payload.days, db)

    # Build strategy object
    strategy = Strategy(
        name=payload.name,
        description=payload.description,
        buy_rules=[Rule(**r.model_dump()) for r in payload.buy_rules],
        sell_rules=[Rule(**r.model_dump()) for r in payload.sell_rules],
        logic=payload.logic,
        stop_loss_pct=payload.stop_loss_pct,
        take_profit_pct=payload.take_profit_pct,
    )

    try:
        result = strategy_engine.run(df, strategy)
        result["ticker"] = payload.ticker.upper()
        result["days"]   = len(df)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run/preset")
async def run_preset(payload: PresetRunRequest, db: AsyncSession = Depends(get_db)):
    """Run one of the built-in preset strategies."""
    presets = strategy_engine.get_preset_strategies()
    if payload.preset_idx >= len(presets):
        raise HTTPException(status_code=404, detail="Preset not found")

    p = presets[payload.preset_idx]
    df = await load_ohlcv(payload.ticker, payload.days, db)

    strategy = Strategy(
        name=p["name"],
        description=p["description"],
        buy_rules=[Rule(**r) for r in p["buy_rules"]],
        sell_rules=[Rule(**r) for r in p["sell_rules"]],
        logic=p.get("logic", "AND"),
    )

    try:
        result = strategy_engine.run(df, strategy)
        result["ticker"] = payload.ticker.upper()
        result["days"]   = len(df)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health():
    return {"status": "ok", "module": "strategy_builder", "indicators": len(SUPPORTED_INDICATORS)}
