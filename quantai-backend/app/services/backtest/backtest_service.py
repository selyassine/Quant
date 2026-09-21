"""
QuantAI — Backtest Service
Orchestre le moteur de backtest avec les données PostgreSQL.
"""
import pandas as pd
from typing import Dict, Optional
from sqlalchemy import text
import logging

from app.db.database import AsyncSessionLocal
from app.services.backtest.engine import BacktestEngine, BacktestResult

logger = logging.getLogger(__name__)


class BacktestService:

    def __init__(self):
        self.engine = BacktestEngine(initial_capital=100_000.0)

    # ------------------------------------------------------------------ #
    #  CHARGEMENT DES DONNÉES
    # ------------------------------------------------------------------ #

    async def _load_prices(self, ticker: str, days: int = 504) -> pd.Series:
        """Charge les prix de clôture depuis PostgreSQL."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT timestamp, close
                    FROM ohlcv
                    WHERE ticker = :ticker
                    ORDER BY timestamp ASC
                    LIMIT :days
                """),
                {"ticker": ticker, "days": days},
            )
            rows = result.fetchall()
            if not rows:
                raise ValueError(f"Aucune donnée pour {ticker}")

            df = pd.DataFrame(rows, columns=["date", "close"])
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            return df["close"].astype(float)

    # ------------------------------------------------------------------ #
    #  BACKTESTS
    # ------------------------------------------------------------------ #

    async def run_buy_hold(self, ticker: str, days: int = 504) -> Dict:
        """Backtest Buy & Hold — sert de benchmark."""
        prices = await self._load_prices(ticker, days)
        signals = self.engine._generate_signals_buy_hold(prices)
        result = self.engine.run(prices, signals, "buy_hold", ticker)
        return self._serialize(result)

    async def run_sma_crossover(
        self,
        ticker: str,
        short_window: int = 20,
        long_window: int = 50,
        days: int = 504,
    ) -> Dict:
        """Backtest SMA Crossover."""
        if short_window >= long_window:
            raise ValueError("short_window doit être < long_window")
        prices = await self._load_prices(ticker, days)
        signals = self.engine._generate_signals_sma_crossover(
            prices, short_window, long_window
        )
        name = f"sma_{short_window}_{long_window}"
        result = self.engine.run(prices, signals, name, ticker)
        return self._serialize(result)

    async def run_rsi(
        self,
        ticker: str,
        period: int = 14,
        oversold: float = 30,
        overbought: float = 70,
        days: int = 504,
    ) -> Dict:
        """Backtest RSI."""
        prices = await self._load_prices(ticker, days)
        signals = self.engine._generate_signals_rsi(
            prices, period, oversold, overbought
        )
        name = f"rsi_{period}_{oversold}_{overbought}"
        result = self.engine.run(prices, signals, name, ticker)
        return self._serialize(result)

    async def run_comparison(
        self,
        ticker: str,
        days: int = 504,
    ) -> Dict:
        """
        Compare toutes les stratégies sur le même ticker.
        Retourne un résumé côte à côte.
        """
        prices = await self._load_prices(ticker, days)

        strategies = {
            "buy_hold": self.engine._generate_signals_buy_hold(prices),
            "sma_20_50": self.engine._generate_signals_sma_crossover(prices, 20, 50),
            "sma_10_30": self.engine._generate_signals_sma_crossover(prices, 10, 30),
            "rsi_14":    self.engine._generate_signals_rsi(prices, 14, 30, 70),
        }

        results = {}
        for name, signals in strategies.items():
            r = self.engine.run(prices, signals, name, ticker)
            results[name] = {
                "total_return_pct":   r.total_return_pct,
                "annual_return_pct":  r.annual_return_pct,
                "sharpe_ratio":       r.sharpe_ratio,
                "max_drawdown_pct":   r.max_drawdown_pct,
                "num_trades":         r.num_trades,
                "win_rate_pct":       r.win_rate_pct,
                "final_value":        r.final_value,
                "volatility_pct":     r.volatility_pct,
                "calmar_ratio":       r.calmar_ratio,
            }

        # Classe par Sharpe ratio
        ranked = sorted(
            results.items(),
            key=lambda x: x[1]["sharpe_ratio"],
            reverse=True,
        )

        return {
            "ticker": ticker,
            "period_days": days,
            "initial_capital": 100_000,
            "comparison": results,
            "ranking": [
                {"rank": i + 1, "strategy": name, "sharpe": data["sharpe_ratio"]}
                for i, (name, data) in enumerate(ranked)
            ],
            "best_strategy": ranked[0][0] if ranked else "buy_hold",
        }

    # ------------------------------------------------------------------ #

    def _serialize(self, result: BacktestResult) -> Dict:
        """Convertit BacktestResult en dict JSON-serializable."""
        return {
            "strategy":             result.strategy,
            "ticker":               result.ticker,
            "period":               f"{result.start_date} → {result.end_date}",
            "initial_capital":      result.initial_capital,
            "final_value":          result.final_value,
            "total_return_pct":     result.total_return_pct,
            "annual_return_pct":    result.annual_return_pct,
            "benchmark_return_pct": result.benchmark_return_pct,
            "alpha":                round(result.annual_return_pct - result.benchmark_return_pct, 4),
            "sharpe_ratio":         result.sharpe_ratio,
            "sortino_ratio":        result.sortino_ratio,
            "max_drawdown_pct":     result.max_drawdown_pct,
            "calmar_ratio":         result.calmar_ratio,
            "volatility_pct":       result.volatility_pct,
            "num_trades":           result.num_trades,
            "win_rate_pct":         result.win_rate_pct,
            "avg_win_pct":          result.avg_win_pct,
            "avg_loss_pct":         result.avg_loss_pct,
            "profit_factor":        result.profit_factor,
            "equity_curve":         result.equity_curve,
            "drawdown_series":      result.drawdown_series,
            "trades":               result.trades,
        }


# Singleton
backtest_service = BacktestService()
