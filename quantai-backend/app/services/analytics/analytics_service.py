"""
M13 — Portfolio Analytics Service
Correlation matrix, rolling metrics, performance attribution,
sector exposure, drawdown analysis.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


class PortfolioAnalyticsService:

    # ------------------------------------------------------------------ #
    #  DATA LOADING
    # ------------------------------------------------------------------ #

    async def _load_returns(
        self,
        tickers: List[str],
        days: int,
        session,
    ) -> pd.DataFrame:
        """Load daily returns for multiple tickers from PostgreSQL."""
        prices = {}
        for ticker in tickers:
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
            if rows:
                df = pd.DataFrame(rows, columns=["date", "close"])
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
                prices[ticker] = df["close"].astype(float)

        if not prices:
            raise ValueError("No data found for the provided tickers")

        price_df = pd.DataFrame(prices).dropna(how="all")
        return price_df.pct_change().dropna()

    # ------------------------------------------------------------------ #
    #  CORRELATION MATRIX
    # ------------------------------------------------------------------ #

    async def correlation_matrix(
        self,
        tickers: List[str],
        days: int,
        session,
    ) -> Dict:
        """
        Compute correlation matrix between assets.
        Returns matrix as list of rows for frontend heatmap.
        """
        returns = await self._load_returns(tickers, days, session)

        # Keep only tickers with data
        available = [t for t in tickers if t in returns.columns]
        corr = returns[available].corr().round(4)

        # Format for heatmap
        matrix = []
        for i, row_ticker in enumerate(available):
            for j, col_ticker in enumerate(available):
                matrix.append({
                    "x": col_ticker,
                    "y": row_ticker,
                    "value": float(corr.loc[row_ticker, col_ticker]),
                })

        # Most correlated pairs
        pairs = []
        for i in range(len(available)):
            for j in range(i + 1, len(available)):
                t1, t2 = available[i], available[j]
                pairs.append({
                    "pair": f"{t1}/{t2}",
                    "correlation": float(corr.loc[t1, t2]),
                })
        pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)

        return {
            "tickers": available,
            "matrix": matrix,
            "top_correlated": pairs[:5],
            "period_days": days,
        }

    # ------------------------------------------------------------------ #
    #  ROLLING METRICS
    # ------------------------------------------------------------------ #

    async def rolling_metrics(
        self,
        tickers: List[str],
        weights: Dict[str, float],
        days: int,
        window: int,
        session,
    ) -> Dict:
        """
        Compute rolling Sharpe, volatility, and returns.
        window: rolling window in days (e.g. 30)
        """
        returns = await self._load_returns(tickers, days, session)

        # Portfolio returns
        available = {t: w for t, w in weights.items() if t in returns.columns}
        total_w = sum(available.values())
        norm_w = {t: w / total_w for t, w in available.items()}

        port_returns = sum(
            returns[t] * w for t, w in norm_w.items()
        )

        # Rolling metrics
        rolling_sharpe = (
            port_returns.rolling(window).mean() /
            port_returns.rolling(window).std() *
            np.sqrt(252)
        ).round(4)

        rolling_vol = (
            port_returns.rolling(window).std() * np.sqrt(252) * 100
        ).round(4)

        rolling_return = (
            port_returns.rolling(window).mean() * 252 * 100
        ).round(4)

        # Cumulative return
        cum_return = ((1 + port_returns).cumprod() - 1) * 100

        # Format for charts
        def to_chart(series):
            return [
                {"date": str(d.date()), "value": round(float(v), 4)}
                for d, v in series.items()
                if pd.notna(v)
            ]

        return {
            "window_days": window,
            "rolling_sharpe":  to_chart(rolling_sharpe),
            "rolling_vol":     to_chart(rolling_vol),
            "rolling_return":  to_chart(rolling_return),
            "cumulative_return": to_chart(cum_return),
            "period_days": days,
        }

    # ------------------------------------------------------------------ #
    #  PERFORMANCE ATTRIBUTION
    # ------------------------------------------------------------------ #

    async def performance_attribution(
        self,
        weights: Dict[str, float],
        days: int,
        session,
    ) -> Dict:
        """
        Brinson attribution: contribution of each asset to total return.
        """
        tickers = list(weights.keys())
        returns = await self._load_returns(tickers, days, session)

        available = {t: w for t, w in weights.items() if t in returns.columns}
        total_w = sum(available.values())
        norm_w = {t: w / total_w for t, w in available.items()}

        attribution = []
        total_port_return = 0.0

        for ticker, weight in norm_w.items():
            asset_return = float((1 + returns[ticker]).prod() - 1)
            contribution = weight * asset_return
            total_port_return += contribution

            vol = float(returns[ticker].std() * np.sqrt(252))
            sharpe_asset = (
                asset_return - 0.05
            ) / vol if vol > 0 else 0

            attribution.append({
                "ticker":        ticker,
                "weight_pct":    round(weight * 100, 2),
                "asset_return":  round(asset_return * 100, 2),
                "contribution":  round(contribution * 100, 2),
                "volatility":    round(vol * 100, 2),
                "sharpe":        round(sharpe_asset, 4),
            })

        attribution.sort(key=lambda x: abs(x["contribution"]), reverse=True)

        # Best and worst contributors
        positive = [a for a in attribution if a["contribution"] > 0]
        negative = [a for a in attribution if a["contribution"] <= 0]

        return {
            "total_return_pct":  round(total_port_return * 100, 2),
            "attribution":       attribution,
            "best_contributor":  positive[0]["ticker"] if positive else None,
            "worst_contributor": negative[0]["ticker"] if negative else None,
            "period_days":       days,
        }

    # ------------------------------------------------------------------ #
    #  DRAWDOWN ANALYSIS
    # ------------------------------------------------------------------ #

    async def drawdown_analysis(
        self,
        tickers: List[str],
        weights: Dict[str, float],
        days: int,
        session,
    ) -> Dict:
        """
        Detailed drawdown analysis: max drawdown, recovery, underwater periods.
        """
        returns = await self._load_returns(tickers, days, session)

        available = {t: w for t, w in weights.items() if t in returns.columns}
        total_w = sum(available.values())
        norm_w = {t: w / total_w for t, w in available.items()}

        port_returns = sum(returns[t] * w for t, w in norm_w.items())
        cum = (1 + port_returns).cumprod()
        rolling_max = cum.cummax()
        drawdown = (cum - rolling_max) / rolling_max * 100

        # Find drawdown periods
        in_drawdown = False
        periods = []
        start_date = None
        peak_value = 1.0

        for date, dd in drawdown.items():
            if dd < -1 and not in_drawdown:
                in_drawdown = True
                start_date = date
                peak_value = float(rolling_max[date])
            elif dd >= -0.1 and in_drawdown:
                in_drawdown = False
                trough = float(drawdown[start_date:date].min())
                periods.append({
                    "start": str(start_date.date()),
                    "end":   str(date.date()),
                    "max_drawdown_pct": round(trough, 2),
                    "duration_days": (date - start_date).days,
                })

        periods.sort(key=lambda x: x["max_drawdown_pct"])

        drawdown_series = [
            {"date": str(d.date()), "drawdown": round(float(v), 4)}
            for d, v in drawdown.items()
        ]

        return {
            "max_drawdown_pct":     round(float(drawdown.min()), 2),
            "current_drawdown_pct": round(float(drawdown.iloc[-1]), 2),
            "avg_drawdown_pct":     round(float(drawdown[drawdown < 0].mean()), 2) if (drawdown < 0).any() else 0,
            "worst_periods":        periods[:5],
            "drawdown_series":      drawdown_series,
            "period_days":          days,
        }

    # ------------------------------------------------------------------ #
    #  SECTOR EXPOSURE
    # ------------------------------------------------------------------ #

    def sector_exposure(self, weights: Dict[str, float]) -> Dict:
        """
        Estimate sector exposure based on known ticker classifications.
        """
        SECTORS = {
            "AAPL":    "Technology",
            "MSFT":    "Technology",
            "NVDA":    "Technology",
            "GOOGL":   "Technology",
            "TSLA":    "Consumer Discretionary",
            "SPY":     "Broad Market ETF",
            "QQQ":     "Tech ETF",
            "BTC-USD": "Crypto",
            "ETH-USD": "Crypto",
            "AMZN":    "Consumer Discretionary",
            "META":    "Technology",
            "JPM":     "Financials",
            "GS":      "Financials",
            "XOM":     "Energy",
        }

        total_w = sum(weights.values())
        exposure = {}

        for ticker, weight in weights.items():
            sector = SECTORS.get(ticker.upper(), "Other")
            norm = weight / total_w if total_w > 0 else 0
            exposure[sector] = round(exposure.get(sector, 0) + norm * 100, 2)

        return {
            "sector_exposure": [
                {"sector": k, "pct": v}
                for k, v in sorted(exposure.items(), key=lambda x: x[1], reverse=True)
            ],
            "num_sectors": len(exposure),
            "most_exposed": max(exposure, key=exposure.get) if exposure else None,
        }

    # ------------------------------------------------------------------ #
    #  FULL DASHBOARD
    # ------------------------------------------------------------------ #

    async def full_dashboard(
        self,
        weights: Dict[str, float],
        days: int,
        session,
    ) -> Dict:
        """
        Single call that returns all analytics for the dashboard.
        """
        tickers = list(weights.keys())

        corr    = await self.correlation_matrix(tickers, days, session)
        rolling = await self.rolling_metrics(tickers, weights, days, 30, session)
        attrib  = await self.performance_attribution(weights, days, session)
        dd      = await self.drawdown_analysis(tickers, weights, days, session)
        sector  = self.sector_exposure(weights)

        return {
            "weights":      weights,
            "period_days":  days,
            "correlation":  corr,
            "rolling":      rolling,
            "attribution":  attrib,
            "drawdown":     dd,
            "sector":       sector,
        }


analytics_service = PortfolioAnalyticsService()
