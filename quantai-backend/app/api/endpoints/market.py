from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models.ohlcv import Timeframe
from app.schemas.market import (
    AssetResponse,
    OHLCVResponse,
    CollectRequest,
    CollectResponse,
)
from app.services.data.market_data import market_data_service
from app.services.features.feature_engineering import feature_service
from app.tasks.market_tasks import collect_ticker_task

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get("/assets", response_model=list[AssetResponse])
async def list_assets(db: AsyncSession = Depends(get_db)):
    """List all tracked assets."""
    return await market_data_service.get_assets(db)


@router.get("/assets/{ticker}", response_model=AssetResponse)
async def get_asset(ticker: str, db: AsyncSession = Depends(get_db)):
    """Get a single asset by ticker."""
    from sqlalchemy import select
    from app.db.models.asset import Asset
    result = await db.execute(select(Asset).where(Asset.ticker == ticker.upper()))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {ticker} not found")
    return asset


@router.get("/ohlcv/{ticker}", response_model=list[OHLCVResponse])
async def get_ohlcv(
    ticker: str,
    timeframe: Timeframe = Query(default=Timeframe.D1),
    limit: int = Query(default=500, le=5000),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get OHLCV data for a ticker."""
    data = await market_data_service.get_ohlcv(db, ticker, timeframe, limit, date_from, date_to)
    if not data:
        raise HTTPException(status_code=404, detail=f"No OHLCV data for {ticker}")
    return data


@router.post("/collect", response_model=CollectResponse)
async def collect_data(payload: CollectRequest):
    """Queue data collection for one or more tickers (async via Celery)."""
    task_ids = []
    for ticker in payload.tickers:
        task = collect_ticker_task.delay(
            ticker.upper(),
            payload.period,
            payload.timeframe.value,
        )
        task_ids.append(task.id)

    return CollectResponse(
        status="queued",
        tickers_queued=payload.tickers,
        task_ids=task_ids,
    )


@router.post("/collect/sync/{ticker}")
async def collect_sync(
    ticker: str,
    period: str = Query(default="2y"),
    timeframe: Timeframe = Query(default=Timeframe.D1),
    db: AsyncSession = Depends(get_db),
):
    """Collect data synchronously (for testing — use async /collect in prod)."""
    try:
        result = await market_data_service.collect_ticker(db, ticker, period, timeframe)
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/{ticker}")
async def get_features(
    ticker: str,
    timeframe: Timeframe = Query(default=Timeframe.D1),
    limit: int = Query(default=300, le=2000),
    db: AsyncSession = Depends(get_db),
):
    """Get OHLCV data enriched with all technical features."""
    import pandas as pd

    data = await market_data_service.get_ohlcv(db, ticker, timeframe, limit)
    if not data:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    # Build DataFrame
    rows = [
        {
            "timestamp": r.timestamp,
            "open": r.open, "high": r.high, "low": r.low,
            "close": r.close, "volume": r.volume,
        }
        for r in reversed(data)  # oldest first
    ]
    df = pd.DataFrame(rows).set_index("timestamp")

    # Generate features
    df_feat = feature_service.generate_all_features(df)

    # Return last N rows as JSON (drop NaN for cleanliness)
    df_out = df_feat.tail(200).dropna(how="all", axis=1)
    return {
        "ticker": ticker.upper(),
        "timeframe": timeframe.value,
        "rows": len(df_out),
        "features": df_out.columns.tolist(),
        "data": df_out.reset_index().to_dict(orient="records"),
    }
