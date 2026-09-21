from sqlalchemy import Column, String, Float, DateTime, Boolean, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.database import Base


class AssetType(str, enum.Enum):
    STOCK = "stock"
    ETF = "etf"
    CRYPTO = "crypto"
    FOREX = "forex"
    INDEX = "index"
    COMMODITY = "commodity"


class Asset(Base):
    __tablename__ = "assets"

    ticker = Column(String(20), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False, default=AssetType.STOCK)
    exchange = Column(String(50), nullable=True)
    currency = Column(String(10), default="USD")
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    market_cap = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    ohlcv_data = relationship("OHLCV", back_populates="asset", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Asset {self.ticker} ({self.asset_type})>"
