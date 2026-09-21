from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.db.models.asset import AssetType
from app.db.models.ohlcv import Timeframe


# ---------- Asset ----------

class AssetBase(BaseModel):
    ticker: str
    name: str
    asset_type: AssetType = AssetType.STOCK
    exchange: Optional[str] = None
    currency: str = "USD"
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    is_active: bool
    last_updated: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- OHLCV ----------

class OHLCVBase(BaseModel):
    ticker: str
    timeframe: Timeframe = Timeframe.D1
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None
    adj_close: Optional[float] = None
    dividends: float = 0.0
    stock_splits: float = 0.0

class OHLCVResponse(OHLCVBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Collection request ----------

class CollectRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=1, max_length=50)
    period: str = Field(default="2y", description="1d 5d 1mo 3mo 6mo 1y 2y 5y 10y ytd max")
    timeframe: Timeframe = Timeframe.D1

class CollectResponse(BaseModel):
    status: str
    tickers_queued: list[str]
    task_ids: list[str]
