"""
M9 — Paper Trading Models
Virtual account, orders, positions, transactions.
"""
from sqlalchemy import Column, String, Float, DateTime, BigInteger, Boolean, Integer, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.database import Base


class OrderSide(str, enum.Enum):
    BUY  = "buy"
    SELL = "sell"

class OrderStatus(str, enum.Enum):
    PENDING   = "pending"
    FILLED    = "filled"
    CANCELLED = "cancelled"
    REJECTED  = "rejected"

class OrderType(str, enum.Enum):
    MARKET = "market"
    LIMIT  = "limit"


class PaperAccount(Base):
    __tablename__ = "paper_accounts"

    id              = Column(Integer, primary_key=True, default=1)
    name            = Column(String(100), default="Main Account")
    initial_capital = Column(Float, default=100_000.0)
    cash_balance    = Column(Float, default=100_000.0)
    total_value     = Column(Float, default=100_000.0)
    total_pnl       = Column(Float, default=0.0)
    total_pnl_pct   = Column(Float, default=0.0)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders       = relationship("PaperOrder",       back_populates="account")
    positions    = relationship("PaperPosition",    back_populates="account")
    transactions = relationship("PaperTransaction", back_populates="account")


class PaperOrder(Base):
    __tablename__ = "paper_orders"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("paper_accounts.id"), default=1)
    ticker     = Column(String(20), nullable=False)
    side       = Column(Enum(OrderSide), nullable=False)
    order_type = Column(Enum(OrderType), default=OrderType.MARKET)
    quantity   = Column(Float, nullable=False)
    fill_price = Column(Float, nullable=True)
    status     = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    reason     = Column(Text, nullable=True)
    source     = Column(String(50), default="manual")  # manual / agent / signal
    filled_at  = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    account      = relationship("PaperAccount",     back_populates="orders")
    transactions = relationship("PaperTransaction", back_populates="order")


class PaperPosition(Base):
    __tablename__ = "paper_positions"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    account_id    = Column(Integer, ForeignKey("paper_accounts.id"), default=1)
    ticker        = Column(String(20), nullable=False)
    quantity      = Column(Float, default=0.0)
    avg_cost      = Column(Float, default=0.0)
    current_price = Column(Float, default=0.0)
    market_value  = Column(Float, default=0.0)
    realized_pnl  = Column(Float, default=0.0)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    account = relationship("PaperAccount", back_populates="positions")


class PaperTransaction(Base):
    __tablename__ = "paper_transactions"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    account_id  = Column(Integer, ForeignKey("paper_accounts.id"), default=1)
    order_id    = Column(Integer, ForeignKey("paper_orders.id"), nullable=True)
    ticker      = Column(String(20), nullable=False)
    side        = Column(Enum(OrderSide), nullable=False)
    quantity    = Column(Float, nullable=False)
    price       = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    cash_before = Column(Float, nullable=False)
    cash_after  = Column(Float, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    account = relationship("PaperAccount", back_populates="transactions")
    order   = relationship("PaperOrder",   back_populates="transactions")
