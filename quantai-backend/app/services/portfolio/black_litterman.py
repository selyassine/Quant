"""
Black-Litterman Portfolio Optimization.
Combines market equilibrium returns with investor views
to produce a posterior estimate of expected returns.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from scipy.optimize import minimize
import logging

logger = logging.getLogger(__name__)


class BlackLittermanOptimizer:
    """
    Black-Litterman model implementation.
    
    The BL model:
    1. Starts from market equilibrium (CAPM implied returns)
    2. Incorporates investor views (absolute or relative)
    3. Produces posterior expected returns
    4. Optimizes portfolio on posterior returns
    
    Views format:
    - Absolute: "AAPL will return 15% annually"
    - Relative: "AAPL will outperform MSFT by 5%"
    """

    def __init__(
        self,
        risk_free_rate: float = 0.05,
        risk_aversion: float = 2.5,   # Market risk aversion (lambda)
        tau: float = 0.05,            # Uncertainty in prior (small = trust prior more)
    ):
        self.risk_free_rate = risk_free_rate
        self.risk_aversion = risk_aversion
        self.tau = tau

        self.tickers: List[str] = []
        self.cov_matrix: np.ndarray = None
        self.market_caps: np.ndarray = None
        self.equilibrium_returns: np.ndarray = None
        self.posterior_returns: np.ndarray = None
        self.posterior_cov: np.ndarray = None

    # ---------------------------------------------------------------- #

    def fit(
        self,
        prices: pd.DataFrame,
        market_caps: Optional[Dict[str, float]] = None,
    ):
        """
        Fit BL model on historical prices.
        market_caps: dict of {ticker: market_cap} for equilibrium weights.
                     If None, uses equal weights.
        """
        self.tickers = list(prices.columns)
        n = len(self.tickers)

        returns = prices.pct_change().dropna()
        self.cov_matrix = returns.cov().values * 252  # Annualized

        # Market cap weights (equilibrium)
        if market_caps:
            caps = np.array([market_caps.get(t, 1e9) for t in self.tickers], dtype=float)
        else:
            caps = np.ones(n)
        self.market_caps = caps / caps.sum()

        # CAPM equilibrium returns: π = λ * Σ * w_mkt
        self.equilibrium_returns = (
            self.risk_aversion * self.cov_matrix @ self.market_caps
        )

        logger.info(f"[BL] Fitted on {n} assets")

    # ---------------------------------------------------------------- #

    def set_views(
        self,
        views: List[Dict],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Parse investor views into BL matrices P, Q, Omega.
        
        views format:
        [
          {"type": "absolute", "ticker": "AAPL", "return": 0.15, "confidence": 0.8},
          {"type": "relative", "long": "MSFT", "short": "GOOGL", "return": 0.05, "confidence": 0.6},
        ]
        confidence: 0-1 (1 = very confident)
        """
        n = len(self.tickers)
        k = len(views)

        P = np.zeros((k, n))   # Pick matrix
        Q = np.zeros(k)        # View returns
        omega_diag = []        # View uncertainty

        for i, view in enumerate(views):
            if view["type"] == "absolute":
                idx = self.tickers.index(view["ticker"])
                P[i, idx] = 1.0
                Q[i] = view["return"]
            elif view["type"] == "relative":
                long_idx = self.tickers.index(view["long"])
                short_idx = self.tickers.index(view["short"])
                P[i, long_idx] = 1.0
                P[i, short_idx] = -1.0
                Q[i] = view["return"]

            # Omega: uncertainty inversely proportional to confidence
            confidence = view.get("confidence", 0.5)
            variance = (1 - confidence) * (self.tau * P[i] @ self.cov_matrix @ P[i].T)
            omega_diag.append(max(variance, 1e-6))

        Omega = np.diag(omega_diag)
        return P, Q, Omega

    # ---------------------------------------------------------------- #

    def compute_posterior(self, views: List[Dict]) -> Dict:
        """
        Compute posterior expected returns using BL formula.
        Returns posterior returns and covariance.
        """
        if not views:
            # No views → use equilibrium
            self.posterior_returns = self.equilibrium_returns
            self.posterior_cov = self.cov_matrix
            return {"message": "No views provided — using equilibrium returns"}

        P, Q, Omega = self.set_views(views)

        # BL posterior formula:
        # μ_BL = [(τΣ)^-1 + P'Ω^-1 P]^-1 * [(τΣ)^-1 π + P'Ω^-1 Q]
        tau_cov = self.tau * self.cov_matrix
        tau_cov_inv = np.linalg.inv(tau_cov)
        omega_inv = np.linalg.inv(Omega)

        M = np.linalg.inv(tau_cov_inv + P.T @ omega_inv @ P)
        self.posterior_returns = M @ (tau_cov_inv @ self.equilibrium_returns + P.T @ omega_inv @ Q)

        # Posterior covariance
        self.posterior_cov = self.cov_matrix + M

        return {
            "equilibrium_returns": {
                t: float(round(r * 100, 2))
                for t, r in zip(self.tickers, self.equilibrium_returns)
            },
            "posterior_returns": {
                t: float(round(r * 100, 2))
                for t, r in zip(self.tickers, self.posterior_returns)
            },
        }

    # ---------------------------------------------------------------- #

    def optimize(
        self,
        views: List[Dict] = None,
        max_weight: float = 0.4,
    ) -> Dict:
        """
        Full BL optimization pipeline.
        Returns optimal portfolio weights based on posterior returns.
        """
        if views is None:
            views = []

        posterior_info = self.compute_posterior(views)

        n = len(self.tickers)
        bounds = tuple((0.0, max_weight) for _ in range(n))
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]

        # Maximize: w'μ_BL - (λ/2) * w'Σw
        def neg_utility(w):
            ret = np.dot(w, self.posterior_returns)
            risk = self.risk_aversion / 2 * w @ self.posterior_cov @ w
            return -(ret - risk)

        result = minimize(
            neg_utility,
            np.ones(n) / n,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-9},
        )

        weights = result.x
        ret = float(np.dot(weights, self.posterior_returns))
        vol = float(np.sqrt(weights @ self.cov_matrix @ weights))
        sharpe = (ret - self.risk_free_rate) / vol if vol > 0 else 0

        allocation = {
            t: float(round(w, 6))
            for t, w in zip(self.tickers, weights)
            if w > 0.001
        }
        total = sum(allocation.values())
        if total > 0:
            allocation = {k: round(v / total, 6) for k, v in allocation.items()}

        return {
            "strategy": "black_litterman",
            "weights": allocation,
            "expected_annual_return": float(round(ret * 100, 2)),
            "annual_volatility": float(round(vol * 100, 2)),
            "sharpe_ratio": float(round(sharpe, 4)),
            "views_applied": len(views),
            "posterior_info": posterior_info,
            "num_assets": len(allocation),
        }