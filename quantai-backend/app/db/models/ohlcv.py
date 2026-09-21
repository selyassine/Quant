from sqlalchemy import Column, String, Float, DateTime, BigInteger, ForeignKey, Index, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.database import Base


class Timeframe(str, enum.Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    D1 = "1d"
    W1 = "1wk"
    MO1 = "1mo"


class OHLCV(Base):
    __tablename__ = "ohlcv"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String(20), ForeignKey("assets.ticker", ondelete="CASCADE"), nullable=False)
    timeframe = Column(Enum(Timeframe), nullable=False, default=Timeframe.D1)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=True)
    adj_close = Column(Float, nullable=True)
    dividends = Column(Float, default=0.0)
    stock_splits = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    asset = relationship("Asset", back_populates="ohlcv_data")

    # Composite unique index: one record per ticker/timeframe/timestamp
    __table_args__ = (
        Index("ix_ohlcv_ticker_timeframe_ts", "ticker", "timeframe", "timestamp", unique=True),
        Index("ix_ohlcv_ticker_ts", "ticker", "timestamp"),
    )

    def __repr__(self):
        return f"<OHLCV {self.ticker} {self.timeframe} {self.timestamp}>"
