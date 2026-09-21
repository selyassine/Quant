"""
Agent Autonome — Autonomous Trading Agent
Celery Beat loop (every hour 09:30–16:00 ET).

Pipeline:
1. Collect market data for each ticker
2. Generate ML predictions (ensemble)
3. Optimize portfolio (Markowitz)
4. Decide BUY/SELL/HOLD with risk management
5. Create PENDING order → user accepts or refuses
6. If accepted → execute via Alpaca Paper API
"""
import httpx
import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy import text

from app.db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

BACKEND_URL = "http://localhost:8000/api/v1"

# Risk management rules
MAX_POSITION_PCT  = 0.10   # max 10% per position
MAX_TRADES_PER_DAY = 3
STOP_LOSS_PCT     = 0.05   # 5% stop loss
MIN_CONFIDENCE    = 0.55   # minimum ML probability to act

TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "SPY"]


async def _ensure_agent_table():
    """Create agent_orders table if not exists."""
    async with AsyncSessionLocal() as session:
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_orders (
                id          SERIAL PRIMARY KEY,
                ticker      VARCHAR(20) NOT NULL,
                side        VARCHAR(10) NOT NULL,
                quantity    FLOAT NOT NULL,
                reason      TEXT,
                confidence  FLOAT,
                prediction  FLOAT,
                sharpe      FLOAT,
                status      VARCHAR(20) DEFAULT 'pending',
                alpaca_id   VARCHAR(100),
                created_at  TIMESTAMP DEFAULT NOW(),
                decided_at  TIMESTAMP,
                decided_by  VARCHAR(50)
            )
        """))
        await session.commit()


class TradingAgent:
    """
    Autonomous trading agent.
    Runs the full decision pipeline and creates PENDING orders.
    """

    # ------------------------------------------------------------------ #
    #  STEP 1 — COLLECT DATA
    # ------------------------------------------------------------------ #

    async def get_prediction(self, ticker: str) -> Optional[Dict]:
        """Get ML ensemble prediction for a ticker."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.get(f"{BACKEND_URL}/predict/predict/{ticker}")
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                logger.error(f"[Agent] prediction failed for {ticker}: {e}")
        return None

    async def get_portfolio_optimization(self, tickers: List[str]) -> Optional[Dict]:
        """Get Markowitz portfolio weights."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.post(
                    f"{BACKEND_URL}/portfolio/optimize/markowitz",
                    json={"tickers": tickers, "objective": "sharpe", "max_weight": MAX_POSITION_PCT * 4, "days": 252},
                )
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                logger.error(f"[Agent] portfolio optimization failed: {e}")
        return None

    async def get_current_price(self, ticker: str) -> Optional[float]:
        """Get latest price from our DB."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT close FROM ohlcv WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1"),
                {"ticker": ticker},
            )
            row = result.fetchone()
            return float(row[0]) if row else None

    async def get_paper_account(self) -> Optional[Dict]:
        """Get current paper trading account balance."""
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                r = await client.get(f"{BACKEND_URL}/paper/account")
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                logger.error(f"[Agent] account fetch failed: {e}")
        return None

    # ------------------------------------------------------------------ #
    #  STEP 2 — DECISION ENGINE
    # ------------------------------------------------------------------ #

    def decide(
        self,
        ticker: str,
        prediction: Dict,
        portfolio_weight: float,
        cash_available: float,
        current_price: float,
    ) -> Optional[Dict]:
        """
        Decision logic with risk management.
        Returns order dict or None if HOLD.
        """
        direction    = prediction.get("ensemble_direction", "")
        probability  = prediction.get("ensemble_probability", 0.5)
        signal       = prediction.get("signal", "NEUTRAL")
        agreement    = prediction.get("agreement_score", 0)

        # Check how many models are active (single model = lower bar)
        weights_used  = prediction.get("weights_used", {})
        num_models    = len([v for v in weights_used.values() if v > 0]) if weights_used else 1
        single_model  = num_models <= 1

        # --- Risk filters (relaxed when only 1 model trained) ---
        min_prob      = 0.50 if single_model else MIN_CONFIDENCE   # 50% vs 55%
        min_agreement = 0.0  if single_model else 0.6              # no agreement filter with 1 model
        min_signal_p  = 0.51 if single_model else 0.58             # lower bar for NEUTRAL

        if direction == "up" and probability < min_prob:
            logger.info(f"[Agent] {ticker}: confidence too low ({probability:.1%}) → HOLD")
            return None

        if direction == "down" and probability > (1 - min_prob):
            # keep direction = down if model is confident enough
            pass

        if signal == "NEUTRAL" and probability < min_signal_p:
            logger.info(f"[Agent] {ticker}: signal NEUTRAL + low prob → HOLD")
            return None

        if not single_model and agreement < min_agreement:
            logger.info(f"[Agent] {ticker}: low model agreement ({agreement:.1%}) → HOLD")
            return None

        # --- Position sizing ---
        max_position_value = cash_available * MAX_POSITION_PCT
        target_value = min(
            cash_available * portfolio_weight,
            max_position_value,
        )

        if target_value < current_price:
            logger.info(f"[Agent] {ticker}: not enough cash → HOLD")
            return None

        quantity = int(target_value / current_price)
        if quantity < 1:
            return None

        # --- BUY signal ---
        if direction == "up" and probability >= MIN_CONFIDENCE:
            return {
                "ticker":     ticker,
                "side":       "buy",
                "quantity":   quantity,
                "confidence": probability,
                "prediction": probability,
                "reason":     (
                    f"ML ensemble predicts UP with {probability:.1%} probability "
                    f"(signal={signal}, agreement={agreement:.1%}). "
                    f"Portfolio weight: {portfolio_weight:.1%}. "
                    f"Stop loss: {STOP_LOSS_PCT:.0%}."
                ),
            }

        # --- SELL signal ---
        if direction == "down" and probability >= MIN_CONFIDENCE:
            return {
                "ticker":     ticker,
                "side":       "sell",
                "quantity":   quantity,
                "confidence": probability,
                "prediction": probability,
                "reason":     (
                    f"ML ensemble predicts DOWN with {probability:.1%} probability "
                    f"(signal={signal}, agreement={agreement:.1%}). "
                    f"Risk management: reducing exposure."
                ),
            }

        return None

    # ------------------------------------------------------------------ #
    #  STEP 3 — CREATE PENDING ORDER
    # ------------------------------------------------------------------ #

    async def create_pending_order(self, order: Dict) -> int:
        """Save a PENDING order to the database."""
        await _ensure_agent_table()
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    INSERT INTO agent_orders
                        (ticker, side, quantity, reason, confidence, prediction, status)
                    VALUES
                        (:ticker, :side, :qty, :reason, :conf, :pred, 'pending')
                    RETURNING id
                """),
                {
                    "ticker": order["ticker"],
                    "side":   order["side"],
                    "qty":    order["quantity"],
                    "reason": order["reason"],
                    "conf":   order.get("confidence", 0),
                    "pred":   order.get("prediction", 0),
                },
            )
            order_id = result.fetchone()[0]
            await session.commit()
            logger.info(f"[Agent] Created PENDING order #{order_id}: {order['side'].upper()} {order['quantity']} {order['ticker']}")
            return order_id

    # ------------------------------------------------------------------ #
    #  STEP 4 — ACCEPT / REFUSE
    # ------------------------------------------------------------------ #

    async def accept_order(self, order_id: int) -> Dict:
        """
        User accepts the order → execute via Paper Trading API.
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT * FROM agent_orders WHERE id = :id AND status = 'pending'"),
                {"id": order_id},
            )
            row = result.fetchone()
            if not row:
                return {"error": f"Order #{order_id} not found or not pending"}

            order = dict(row._mapping)

        # Execute via paper trading
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.post(
                    f"{BACKEND_URL}/paper/order",
                    json={
                        "ticker":   order["ticker"],
                        "side":     order["side"],
                        "quantity": order["quantity"],
                        "reason":   f"Agent order #{order_id} — accepted by user",
                        "source":   "agent",
                    },
                )
                if r.status_code == 200:
                    fill = r.json()
                    async with AsyncSessionLocal() as session:
                        await session.execute(
                            text("""
                                UPDATE agent_orders
                                SET status='accepted', decided_at=NOW(), decided_by='user'
                                WHERE id = :id
                            """),
                            {"id": order_id},
                        )
                        await session.commit()
                    return {
                        "order_id":   order_id,
                        "status":     "accepted",
                        "fill_price": fill.get("fill_price"),
                        "total_value": fill.get("total_value"),
                        "cash_remaining": fill.get("cash_remaining"),
                    }
                else:
                    return {"error": f"Execution failed: {r.status_code} {r.text}"}
            except Exception as e:
                return {"error": str(e)}

    async def refuse_order(self, order_id: int) -> Dict:
        """User refuses the order → mark as refused."""
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    UPDATE agent_orders
                    SET status='refused', decided_at=NOW(), decided_by='user'
                    WHERE id = :id AND status = 'pending'
                """),
                {"id": order_id},
            )
            await session.commit()
        return {"order_id": order_id, "status": "refused"}

    # ------------------------------------------------------------------ #
    #  STEP 5 — FULL AGENT LOOP
    # ------------------------------------------------------------------ #

    async def run_cycle(self) -> Dict:
        """
        Full agent cycle:
        1. Get account balance
        2. For each ticker: get prediction
        3. Get portfolio optimization
        4. Apply decision engine
        5. Create PENDING orders
        """
        await _ensure_agent_table()
        logger.info("[Agent] Starting trading cycle...")

        # Check trades today
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM agent_orders
                    WHERE DATE(created_at) = CURRENT_DATE
                    AND status = 'accepted'
                """)
            )
            trades_today = result.fetchone()[0]

        if trades_today >= MAX_TRADES_PER_DAY:
            return {
                "status": "skipped",
                "reason": f"Max trades per day reached ({MAX_TRADES_PER_DAY})",
                "trades_today": trades_today,
            }

        # Get account
        account = await self.get_paper_account()
        cash = account.get("cash_balance", 100_000) if account else 100_000

        # Get portfolio weights
        portfolio = await self.get_portfolio_optimization(TICKERS)
        weights = portfolio.get("weights", {}) if portfolio else {}
        sharpe = portfolio.get("sharpe_ratio", 0) if portfolio else 0

        # Process each ticker
        orders_created = []
        for ticker in TICKERS:
            if trades_today + len(orders_created) >= MAX_TRADES_PER_DAY:
                break

            prediction = await self.get_prediction(ticker)
            if not prediction:
                continue

            current_price = await self.get_current_price(ticker)
            if not current_price:
                continue

            weight = weights.get(ticker, 1 / len(TICKERS))

            order = self.decide(ticker, prediction, weight, cash, current_price)
            if order:
                order["sharpe"] = sharpe
                order_id = await self.create_pending_order(order)
                orders_created.append({
                    "id":       order_id,
                    "ticker":   order["ticker"],
                    "side":     order["side"],
                    "quantity": order["quantity"],
                    "reason":   order["reason"],
                })

        return {
            "status":         "completed",
            "timestamp":      datetime.now().isoformat(),
            "cash_available": cash,
            "tickers_analyzed": len(TICKERS),
            "orders_created": orders_created,
            "trades_today":   trades_today,
        }

    # ------------------------------------------------------------------ #
    #  GET PENDING ORDERS
    # ------------------------------------------------------------------ #

    async def get_pending_orders(self) -> List[Dict]:
        """Get all pending orders waiting for user approval."""
        await _ensure_agent_table()
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM agent_orders
                    WHERE status = 'pending'
                    ORDER BY created_at DESC
                """)
            )
            return [dict(r._mapping) for r in result.fetchall()]

    async def get_all_orders(self, limit: int = 50) -> List[Dict]:
        """Get all agent orders (pending, accepted, refused)."""
        await _ensure_agent_table()
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM agent_orders
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            )
            return [dict(r._mapping) for r in result.fetchall()]

    async def get_performance(self) -> Dict:
        """Get agent performance statistics."""
        await _ensure_agent_table()
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("""
                SELECT
                    COUNT(*) as total_orders,
                    COUNT(*) FILTER (WHERE status='accepted') as accepted,
                    COUNT(*) FILTER (WHERE status='refused') as refused,
                    COUNT(*) FILTER (WHERE status='pending') as pending,
                    COUNT(*) FILTER (WHERE side='buy' AND status='accepted') as buy_orders,
                    COUNT(*) FILTER (WHERE side='sell' AND status='accepted') as sell_orders,
                    AVG(confidence) FILTER (WHERE status='accepted') as avg_confidence
                FROM agent_orders
            """))
            row = result.fetchone()
            if row:
                d = dict(row._mapping)
                return {
                    "total_orders":  d["total_orders"] or 0,
                    "accepted":      d["accepted"] or 0,
                    "refused":       d["refused"] or 0,
                    "pending":       d["pending"] or 0,
                    "buy_orders":    d["buy_orders"] or 0,
                    "sell_orders":   d["sell_orders"] or 0,
                    "avg_confidence": round(float(d["avg_confidence"] or 0) * 100, 2),
                    "acceptance_rate": round(
                        (d["accepted"] or 0) / max(d["total_orders"] or 1, 1) * 100, 2
                    ),
                }
        return {}


trading_agent = TradingAgent()