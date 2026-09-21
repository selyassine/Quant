"""
M9 — Paper Trading Service
Virtual account with $100k initial capital.
Handles: orders, positions, P&L tracking, performance metrics.
"""
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from loguru import logger

from app.services.paper_trading.models import (
    PaperAccount, PaperOrder, PaperPosition, PaperTransaction,
    OrderSide, OrderStatus, OrderType,
)

INITIAL_CAPITAL = 100_000.0


class PaperTradingService:

    # ── Account ───────────────────────────────────────────────────────
    async def get_or_create_account(self, db: AsyncSession) -> PaperAccount:
        result = await db.execute(select(PaperAccount).where(PaperAccount.id == 1))
        account = result.scalar_one_or_none()
        if not account:
            account = PaperAccount(
                id=1, name="Main Account",
                initial_capital=INITIAL_CAPITAL,
                cash_balance=INITIAL_CAPITAL,
                total_value=INITIAL_CAPITAL,
            )
            db.add(account)
            await db.commit()
            await db.refresh(account)
        return account

    async def get_account_summary(self, db: AsyncSession) -> Dict:
        account  = await self.get_or_create_account(db)
        positions = await self.get_positions(db)

        positions_value = sum(p["market_value"] for p in positions)
        total_value     = account.cash_balance + positions_value
        total_pnl       = total_value - INITIAL_CAPITAL
        total_pnl_pct   = (total_pnl / INITIAL_CAPITAL) * 100

        # Persist updated values
        account.total_value   = total_value
        account.total_pnl     = total_pnl
        account.total_pnl_pct = total_pnl_pct
        account.updated_at    = datetime.utcnow()
        await db.commit()

        return {
            "id":               account.id,
            "name":             account.name,
            "initial_capital":  account.initial_capital,
            "cash_balance":     round(account.cash_balance, 2),
            "positions_value":  round(positions_value, 2),
            "total_value":      round(total_value, 2),
            "total_pnl":        round(total_pnl, 2),
            "total_pnl_pct":    round(total_pnl_pct, 2),
            "positions_count":  len(positions),
        }

    # ── Price ─────────────────────────────────────────────────────────
    async def get_current_price(self, ticker: str, db: AsyncSession) -> float:
        result = await db.execute(text("""
            SELECT close FROM ohlcv
            WHERE ticker = :ticker
            ORDER BY timestamp DESC
            LIMIT 1
        """), {"ticker": ticker.upper()})
        row = result.fetchone()
        if not row:
            raise ValueError(f"No price data for {ticker}. Import data first.")
        return float(row[0])

    # ── Orders ────────────────────────────────────────────────────────
    async def place_order(
        self,
        ticker: str,
        side: str,
        quantity: float,
        reason: str = "",
        source: str = "manual",
        db: AsyncSession = None,
    ) -> Dict:
        ticker  = ticker.upper()
        side_e  = OrderSide(side.lower())
        account = await self.get_or_create_account(db)
        price   = await self.get_current_price(ticker, db)
        total   = price * quantity

        # ── Validation ──────────────────────────────────────────────
        if side_e == OrderSide.BUY:
            if total > account.cash_balance:
                max_qty = int(account.cash_balance / price)
                if max_qty <= 0:
                    raise ValueError(f"Insufficient cash: ${account.cash_balance:.2f} needed ${price:.2f}")
                quantity = max_qty
                total    = price * quantity

        elif side_e == OrderSide.SELL:
            pos = await self._get_position(ticker, db)
            if not pos or pos.quantity < quantity:
                held = pos.quantity if pos else 0
                raise ValueError(f"Insufficient position: holding {held:.2f}, tried to sell {quantity}")

        # ── Create order ────────────────────────────────────────────
        order = PaperOrder(
            account_id=1, ticker=ticker, side=side_e,
            order_type=OrderType.MARKET, quantity=quantity,
            fill_price=price, status=OrderStatus.FILLED,
            reason=reason, source=source,
            filled_at=datetime.utcnow(),
        )
        db.add(order)
        await db.flush()

        # ── Update position ─────────────────────────────────────────
        await self._update_position(ticker, side_e, quantity, price, db)

        # ── Update cash ─────────────────────────────────────────────
        cash_before = account.cash_balance
        account.cash_balance = cash_before - total if side_e == OrderSide.BUY else cash_before + total

        # ── Record transaction ──────────────────────────────────────
        txn = PaperTransaction(
            account_id=1, order_id=order.id,
            ticker=ticker, side=side_e, quantity=quantity,
            price=price, total_value=total,
            cash_before=cash_before, cash_after=account.cash_balance,
        )
        db.add(txn)
        await db.commit()

        logger.info(f"[PaperTrading] {side.upper()} {quantity} {ticker} @ ${price:.2f} | cash: ${account.cash_balance:.2f}")

        return {
            "order_id":       order.id,
            "ticker":         ticker,
            "side":           side,
            "quantity":       quantity,
            "fill_price":     round(price, 2),
            "total_value":    round(total, 2),
            "status":         "filled",
            "cash_remaining": round(account.cash_balance, 2),
            "reason":         reason,
        }

    async def get_orders(self, db: AsyncSession, limit: int = 50) -> List[Dict]:
        result = await db.execute(
            select(PaperOrder).order_by(PaperOrder.created_at.desc()).limit(limit)
        )
        orders = result.scalars().all()
        return [
            {
                "id":         o.id,
                "ticker":     o.ticker,
                "side":       o.side.value,
                "quantity":   o.quantity,
                "fill_price": o.fill_price,
                "status":     o.status.value,
                "reason":     o.reason,
                "source":     o.source,
                "filled_at":  str(o.filled_at)[:19] if o.filled_at else None,
                "created_at": str(o.created_at)[:19],
            }
            for o in orders
        ]

    # ── Positions ─────────────────────────────────────────────────────
    async def get_positions(self, db: AsyncSession) -> List[Dict]:
        result = await db.execute(
            select(PaperPosition)
            .where(PaperPosition.account_id == 1)
            .where(PaperPosition.quantity > 0)
        )
        positions = []
        for pos in result.scalars().all():
            try:
                current_price = await self.get_current_price(pos.ticker, db)
            except Exception:
                current_price = pos.avg_cost

            market_value     = current_price * pos.quantity
            cost_basis       = pos.avg_cost   * pos.quantity
            unrealized_pnl   = market_value - cost_basis
            unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0

            positions.append({
                "ticker":             pos.ticker,
                "quantity":           round(pos.quantity, 4),
                "avg_cost":           round(pos.avg_cost, 2),
                "current_price":      round(current_price, 2),
                "market_value":       round(market_value, 2),
                "unrealized_pnl":     round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
            })
        return positions

    async def _get_position(self, ticker: str, db: AsyncSession) -> Optional[PaperPosition]:
        result = await db.execute(
            select(PaperPosition)
            .where(PaperPosition.ticker == ticker)
            .where(PaperPosition.account_id == 1)
        )
        return result.scalar_one_or_none()

    async def _update_position(self, ticker: str, side: OrderSide, quantity: float, price: float, db: AsyncSession):
        existing = await self._get_position(ticker, db)

        if side == OrderSide.BUY:
            if existing:
                new_qty  = existing.quantity + quantity
                new_avg  = (existing.avg_cost * existing.quantity + price * quantity) / new_qty
                existing.quantity      = new_qty
                existing.avg_cost      = new_avg
                existing.current_price = price
                existing.market_value  = new_qty * price
            else:
                db.add(PaperPosition(
                    account_id=1, ticker=ticker, quantity=quantity,
                    avg_cost=price, current_price=price, market_value=price * quantity,
                ))

        elif side == OrderSide.SELL and existing:
            realized = (price - existing.avg_cost) * quantity
            existing.realized_pnl += realized
            new_qty = existing.quantity - quantity
            if new_qty <= 0:
                await db.delete(existing)
            else:
                existing.quantity     = new_qty
                existing.market_value = new_qty * price

    # ── Performance ───────────────────────────────────────────────────
    async def get_performance(self, db: AsyncSession) -> Dict:
        account  = await self.get_account_summary(db)
        positions = await self.get_positions(db)

        result = await db.execute(
            select(PaperTransaction).where(PaperTransaction.account_id == 1).order_by(PaperTransaction.created_at.asc())
        )
        txns = result.scalars().all()

        buys  = [t for t in txns if t.side == OrderSide.BUY]
        sells = [t for t in txns if t.side == OrderSide.SELL]

        return {
            "account":   account,
            "positions": positions,
            "performance": {
                "total_return_pct": account["total_pnl_pct"],
                "total_pnl_usd":    account["total_pnl"],
                "total_trades":     len(txns),
                "buy_trades":       len(buys),
                "sell_trades":      len(sells),
            },
            "recent_transactions": [
                {
                    "ticker":      t.ticker,
                    "side":        t.side.value,
                    "quantity":    t.quantity,
                    "price":       t.price,
                    "total_value": t.total_value,
                    "cash_after":  t.cash_after,
                    "date":        str(t.created_at)[:19],
                }
                for t in list(reversed(txns))[:20]
            ],
        }

    async def reset_account(self, db: AsyncSession) -> Dict:
        await db.execute(text("DELETE FROM paper_transactions WHERE account_id = 1"))
        await db.execute(text("DELETE FROM paper_positions    WHERE account_id = 1"))
        await db.execute(text("DELETE FROM paper_orders       WHERE account_id = 1"))
        account = await self.get_or_create_account(db)
        account.cash_balance    = INITIAL_CAPITAL
        account.total_value     = INITIAL_CAPITAL
        account.total_pnl       = 0.0
        account.total_pnl_pct   = 0.0
        await db.commit()
        return {"message": "Account reset to $100,000", "cash_balance": INITIAL_CAPITAL}


paper_trading_service = PaperTradingService()
