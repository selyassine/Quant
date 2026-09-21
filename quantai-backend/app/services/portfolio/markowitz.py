"""
Markowitz Mean-Variance Portfolio Optimization.
Finds the optimal portfolio weights that maximize Sharpe ratio
or minimize variance for a given set of assets.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MarkowitzOptimizer:
    """
    Classical Markowitz mean-variance optimizer.
    
    Supports:
    - Maximum Sharpe Ratio portfolio
    - Minimum Variance portfolio
    - Efficient Frontier computation
    - Custom target return optimization
    """

    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate  # Annual risk-free rate
        self.returns: pd.DataFrame = None
        self.mean_returns: pd.Series = None
        self.cov_matrix: pd.DataFrame = None
        self.tickers: List[str] = []

    # ---------------------------------------------------------------- #

    def fit(self, prices: pd.DataFrame):
        """
        Fit optimizer on historical price data.
        prices: DataFrame with dates as index and tickers as columns
        """
        self.tickers = list(prices.columns)
        self.returns = prices.pct_change().dropna()
        self.mean_returns = self.returns.mean() * 252  # Annualized
        self.cov_matrix = self.returns.cov() * 252     # Annualized
        logger.info(f"[Markowitz] Fitted on {len(self.tickers)} assets, {len(self.returns)} periods")

    # ---------------------------------------------------------------- #

    def _portfolio_performance(self, weights: np.ndarray) -> Tuple[float, float, float]:
        """Returns (annual_return, annual_volatility, sharpe_ratio)"""
        ret = np.dot(weights, self.mean_returns)
        vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix.values, weights)))
        sharpe = (ret - self.risk_free_rate) / vol if vol > 0 else 0
        return ret, vol, sharpe

    def _neg_sharpe(self, weights: np.ndarray) -> float:
        _, _, sharpe = self._portfolio_performance(weights)
        return -sharpe

    def _portfolio_variance(self, weights: np.ndarray) -> float:
        return np.dot(weights.T, np.dot(self.cov_matrix.values, weights))

    def _get_constraints_and_bounds(
        self,
        allow_short: bool = False,
        max_weight: float = 1.0,
    ):
        n = len(self.tickers)
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        if allow_short:
            bounds = tuple((-max_weight, max_weight) for _ in range(n))
        else:
            bounds = tuple((0.0, max_weight) for _ in range(n))
        return constraints, bounds

    # ---------------------------------------------------------------- #

    def max_sharpe(
        self,
        allow_short: bool = False,
        max_weight: float = 0.4,
    ) -> Dict:
        """Find portfolio with maximum Sharpe ratio."""
        n = len(self.tickers)
        w0 = np.ones(n) / n
        constraints, bounds = self._get_constraints_and_bounds(allow_short, max_weight)

        result = minimize(
            self._neg_sharpe,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-9},
        )

        weights = result.x
        ret, vol, sharpe = self._portfolio_performance(weights)

        return self._format_result(weights, ret, vol, sharpe, "max_sharpe")

    def min_variance(
        self,
        allow_short: bool = False,
        max_weight: float = 0.4,
    ) -> Dict:
        """Find minimum variance portfolio."""
        n = len(self.tickers)
        w0 = np.ones(n) / n
        constraints, bounds = self._get_constraints_and_bounds(allow_short, max_weight)

        result = minimize(
            self._portfolio_variance,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-9},
        )

        weights = result.x
        ret, vol, sharpe = self._portfolio_performance(weights)

        return self._format_result(weights, ret, vol, sharpe, "min_variance")

    def equal_weight(self) -> Dict:
        """Equal weight (1/N) portfolio — benchmark."""
        n = len(self.tickers)
        weights = np.ones(n) / n
        ret, vol, sharpe = self._portfolio_performance(weights)
        return self._format_result(weights, ret, vol, sharpe, "equal_weight")

    # ---------------------------------------------------------------- #

    def efficient_frontier(self, n_points: int = 50) -> List[Dict]:
        """
        Compute the efficient frontier.
        Returns list of portfolios along the frontier.
        """
        # Find min and max return
        min_ret = self.mean_returns.min()
        max_ret = self.mean_returns.max()
        target_returns = np.linspace(min_ret * 0.8, max_ret * 0.9, n_points)

        frontier = []
        n = len(self.tickers)
        bounds = tuple((0.0, 1.0) for _ in range(n))

        for target in target_returns:
            constraints = [
                {"type": "eq", "fun": lambda w: np.sum(w) - 1},
                {"type": "eq", "fun": lambda w, t=target: np.dot(w, self.mean_returns) - t},
            ]
            result = minimize(
                self._portfolio_variance,
                np.ones(n) / n,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": 500, "ftol": 1e-9},
            )
            if result.success:
                w = result.x
                ret, vol, sharpe = self._portfolio_performance(w)
                frontier.append({
                    "expected_return": float(ret),
                    "volatility": float(vol),
                    "sharpe_ratio": float(sharpe),
                })

        return frontier

    # ---------------------------------------------------------------- #

    def _format_result(
        self,
        weights: np.ndarray,
        ret: float,
        vol: float,
        sharpe: float,
        strategy: str,
    ) -> Dict:
        allocation = {
            ticker: float(round(w, 6))
            for ticker, w in zip(self.tickers, weights)
            if abs(w) > 0.001  # Drop near-zero weights
        }
        # Re-normalize after filtering
        total = sum(allocation.values())
        if total > 0:
            allocation = {k: round(v / total, 6) for k, v in allocation.items()}

        return {
            "strategy": strategy,
            "weights": allocation,
            "expected_annual_return": float(round(ret * 100, 2)),
            "annual_volatility": float(round(vol * 100, 2)),
            "sharpe_ratio": float(round(sharpe, 4)),
            "risk_free_rate": self.risk_free_rate,
            "num_assets": len(allocation),
        }