"""
QuantAI — Portfolio Service
Orchestre Markowitz, Black-Litterman et Risk Metrics.
Lit les données depuis PostgreSQL.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from sqlalchemy import text
import logging

from app.db.database import AsyncSessionLocal
from app.services.portfolio.markowitz import MarkowitzOptimizer
from app.services.portfolio.black_litterman import BlackLittermanOptimizer
from app.services.risk.risk_metrics import RiskMetrics

logger = logging.getLogger(__name__)


class PortfolioService:

    def __init__(self):
        self.risk = RiskMetrics(risk_free_rate=0.05)

    # ------------------------------------------------------------------ #
    #  LECTURE DES DONNÉES
    # ------------------------------------------------------------------ #

    async def _load_prices(
        self,
        tickers: List[str],
        days: int = 252,
    ) -> pd.DataFrame:
        """
        Charge les prix de clôture depuis PostgreSQL.
        Retourne un DataFrame : index=date, colonnes=tickers
        """
        async with AsyncSessionLocal() as session:
            prices = {}
            for ticker in tickers:
                result = await session.execute(
                    text("""
                        SELECT timestamp, close
                        FROM ohlcv
                        WHERE ticker = :ticker
                        ORDER BY timestamp DESC
                        LIMIT :days
                    """),
                    {"ticker": ticker, "days": days},
                )
                rows = result.fetchall()
                if rows:
                    df = pd.DataFrame(rows, columns=["date", "close"])
                    df = df.set_index("date").sort_index()
                    prices[ticker] = df["close"]

            if not prices:
                raise ValueError("Aucune donnée trouvée pour ces tickers")

            return pd.DataFrame(prices).dropna(how="all")

    # ------------------------------------------------------------------ #
    #  OPTIMISATION MARKOWITZ
    # ------------------------------------------------------------------ #

    async def optimize_markowitz(
        self,
        tickers: List[str],
        objective: str = "sharpe",
        max_weight: float = 0.4,
        days: int = 252,
    ) -> Dict:
        """
        Optimise un portfolio avec Markowitz.

        objective : "sharpe" | "min_vol" | "max_return"
        max_weight : poids maximum par actif (0.4 = 40%)
        days       : nombre de jours historiques utilisés
        """
        logger.info(f"Markowitz: {tickers}, objective={objective}")

        prices = await self._load_prices(tickers, days)

        optimizer = MarkowitzOptimizer(risk_free_rate=0.05)
        optimizer.fit(prices)
        if objective == "min_vol":
            result = optimizer.min_variance(max_weight=max_weight)
        elif objective == "max_return":
            result = optimizer.max_sharpe(max_weight=max_weight)
        else:  # default: sharpe
            result = optimizer.max_sharpe(max_weight=max_weight)

        # Ajoute les métriques de risque du portfolio optimisé
        if result.get("weights"):
            metrics = self.risk.portfolio_metrics(prices, result["weights"])
            result["risk_metrics"] = {
                k: v for k, v in metrics.items()
                if k not in ("weights",)
            }

        return result

    # ------------------------------------------------------------------ #
    #  OPTIMISATION BLACK-LITTERMAN
    # ------------------------------------------------------------------ #

    async def optimize_black_litterman(
        self,
        tickers: List[str],
        views: Optional[List[Dict]] = None,
        max_weight: float = 0.4,
        days: int = 252,
    ) -> Dict:
        """
        Optimise un portfolio avec Black-Litterman.

        views : liste de vues du trader (optionnel)
          [
            {"type": "absolute", "ticker": "AAPL", "return": 0.15, "confidence": 0.8},
            {"type": "relative", "long": "MSFT", "short": "GOOGL", "return": 0.05, "confidence": 0.6}
          ]
        """
        logger.info(f"Black-Litterman: {tickers}, {len(views or [])} vues")

        prices = await self._load_prices(tickers, days)

        optimizer = BlackLittermanOptimizer(risk_free_rate=0.05)
        optimizer.fit(prices)
        result = optimizer.optimize(views=views or [], max_weight=max_weight)

        # Ajoute les métriques de risque
        if result.get("weights"):
            metrics = self.risk.portfolio_metrics(prices, result["weights"])
            result["risk_metrics"] = {
                k: v for k, v in metrics.items()
                if k not in ("weights",)
            }

        return result

    # ------------------------------------------------------------------ #
    #  MÉTRIQUES D'UN PORTFOLIO EXISTANT
    # ------------------------------------------------------------------ #

    async def analyze_portfolio(
        self,
        weights: Dict[str, float],
        benchmark_ticker: Optional[str] = "SPY",
        days: int = 252,
    ) -> Dict:
        """
        Analyse un portfolio existant (poids fournis par l'utilisateur).
        Retourne toutes les métriques de risque.
        """
        tickers = list(weights.keys())
        if benchmark_ticker and benchmark_ticker not in tickers:
            tickers_to_load = tickers + [benchmark_ticker]
        else:
            tickers_to_load = tickers

        prices = await self._load_prices(tickers_to_load, days)

        bench_prices = None
        if benchmark_ticker and benchmark_ticker in prices.columns:
            bench_prices = prices[benchmark_ticker]
            portfolio_prices = prices[list(weights.keys())]
        else:
            portfolio_prices = prices[list(weights.keys())]

        metrics = self.risk.portfolio_metrics(
            portfolio_prices, weights, bench_prices
        )

        return {
            "weights": weights,
            "benchmark": benchmark_ticker,
            "period_days": days,
            "metrics": metrics,
        }

    # ------------------------------------------------------------------ #
    #  FRONTIÈRE EFFICIENTE (pour graphique)
    # ------------------------------------------------------------------ #

    async def efficient_frontier(
        self,
        tickers: List[str],
        n_points: int = 30,
        days: int = 252,
    ) -> Dict:
        """
        Calcule N points sur la frontière efficiente.
        Utile pour afficher le graphique rendement/risque.
        """
        prices = await self._load_prices(tickers, days)

        optimizer = MarkowitzOptimizer(risk_free_rate=0.05)
        optimizer.fit(prices)
        frontier = optimizer.efficient_frontier(n_points=n_points)

        return {
            "tickers": tickers,
            "frontier": frontier,
            "num_points": len(frontier),
        }


# Singleton
portfolio_service = PortfolioService()