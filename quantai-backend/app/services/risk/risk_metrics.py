"""
QuantAI — Risk Metrics
VaR, CVaR, Sharpe, Sortino, Max Drawdown, Calmar, Beta
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class RiskMetrics:
    """
    Calcule toutes les métriques de risque d'un portfolio ou d'un actif.
    """

    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate  # Taux sans risque annualisé

    # ------------------------------------------------------------------ #
    #  MÉTRIQUES PRINCIPALES
    # ------------------------------------------------------------------ #

    def compute_all(
        self,
        returns: pd.Series,
        weights: Optional[Dict[str, float]] = None,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> Dict:
        """
        Calcule toutes les métriques d'un coup.
        returns : série de rendements journaliers (ex: 0.012, -0.003 ...)
        """
        if returns.empty or len(returns) < 10:
            return {"error": "Pas assez de données (minimum 10 jours)"}

        r = returns.dropna()
        daily_rf = self.risk_free_rate / 252  # Taux journalier

        metrics = {
            # Rendement
            "annual_return":        self._annual_return(r),
            "total_return":         float(round((1 + r).prod() - 1, 6)),
            "daily_mean_return":    float(round(r.mean(), 6)),

            # Risque
            "annual_volatility":    self._annual_volatility(r),
            "daily_volatility":     float(round(r.std(), 6)),
            "max_drawdown":         self._max_drawdown(r),
            "var_95":               self._var(r, confidence=0.95),
            "var_99":               self._var(r, confidence=0.99),
            "cvar_95":              self._cvar(r, confidence=0.95),
            "cvar_99":              self._cvar(r, confidence=0.99),

            # Ratios
            "sharpe_ratio":         self._sharpe(r, daily_rf),
            "sortino_ratio":        self._sortino(r, daily_rf),
            "calmar_ratio":         self._calmar(r),

            # Stats
            "skewness":             float(round(r.skew(), 4)),
            "kurtosis":             float(round(r.kurtosis(), 4)),
            "positive_days_pct":    float(round((r > 0).mean() * 100, 2)),
            "num_observations":     int(len(r)),
        }

        # Beta & Alpha si benchmark fourni
        if benchmark_returns is not None:
            beta, alpha = self._beta_alpha(r, benchmark_returns)
            metrics["beta"] = beta
            metrics["alpha"] = alpha

        return metrics

    # ------------------------------------------------------------------ #
    #  MÉTHODES INDIVIDUELLES
    # ------------------------------------------------------------------ #

    def _annual_return(self, r: pd.Series) -> float:
        """Rendement annualisé (CAGR)."""
        total = (1 + r).prod()
        n_years = len(r) / 252
        if n_years <= 0:
            return 0.0
        return float(round(total ** (1 / n_years) - 1, 6))

    def _annual_volatility(self, r: pd.Series) -> float:
        """Volatilité annualisée."""
        return float(round(r.std() * np.sqrt(252), 6))

    def _max_drawdown(self, r: pd.Series) -> float:
        """
        Max Drawdown : pire chute depuis un sommet.
        Ex: -0.35 = -35%
        """
        cum = (1 + r).cumprod()
        rolling_max = cum.cummax()
        drawdown = (cum - rolling_max) / rolling_max
        return float(round(drawdown.min(), 6))

    def _var(self, r: pd.Series, confidence: float = 0.95) -> float:
        """
        Value at Risk historique.
        Ex: var_95 = -0.025 → dans 95% des cas, on perd moins de 2.5%/jour
        """
        return float(round(np.percentile(r, (1 - confidence) * 100), 6))

    def _cvar(self, r: pd.Series, confidence: float = 0.95) -> float:
        """
        Conditional VaR (Expected Shortfall).
        Moyenne des pertes au-delà de la VaR.
        """
        var = self._var(r, confidence)
        return float(round(r[r <= var].mean(), 6))

    def _sharpe(self, r: pd.Series, daily_rf: float) -> float:
        """
        Sharpe Ratio annualisé.
        > 1 = bon, > 2 = très bon, > 3 = excellent
        """
        excess = r - daily_rf
        if r.std() == 0:
            return 0.0
        return float(round(excess.mean() / r.std() * np.sqrt(252), 4))

    def _sortino(self, r: pd.Series, daily_rf: float) -> float:
        """
        Sortino Ratio : comme Sharpe mais pénalise seulement les baisses.
        Plus pertinent que Sharpe pour les stratégies asymétriques.
        """
        excess = r - daily_rf
        downside = r[r < 0].std()
        if downside == 0:
            return 0.0
        return float(round(excess.mean() / downside * np.sqrt(252), 4))

    def _calmar(self, r: pd.Series) -> float:
        """
        Calmar Ratio : rendement annualisé / max drawdown.
        Mesure combien de rendement tu obtiens par unité de drawdown.
        """
        ann_ret = self._annual_return(r)
        mdd = abs(self._max_drawdown(r))
        if mdd == 0:
            return 0.0
        return float(round(ann_ret / mdd, 4))

    def _beta_alpha(
        self,
        r: pd.Series,
        benchmark: pd.Series,
    ):
        """Beta et Alpha par rapport à un benchmark (ex: SPY)."""
        aligned = pd.concat([r, benchmark], axis=1).dropna()
        if len(aligned) < 10:
            return 1.0, 0.0
        cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
        beta = float(round(cov[0, 1] / cov[1, 1], 4))
        alpha = float(round(
            self._annual_return(aligned.iloc[:, 0])
            - beta * self._annual_return(aligned.iloc[:, 1]),
            6
        ))
        return beta, alpha

    # ------------------------------------------------------------------ #
    #  PORTFOLIO MULTI-ACTIFS
    # ------------------------------------------------------------------ #

    def portfolio_returns(
        self,
        prices: pd.DataFrame,
        weights: Dict[str, float],
    ) -> pd.Series:
        """
        Calcule les rendements journaliers d'un portfolio pondéré.
        prices  : DataFrame avec une colonne par ticker
        weights : {"AAPL": 0.3, "MSFT": 0.25, ...}
        """
        returns = prices.pct_change().dropna()
        w = pd.Series(weights).reindex(returns.columns).fillna(0)
        w = w / w.sum()  # Normalise à 1
        return (returns * w.values).sum(axis=1)

    def portfolio_metrics(
        self,
        prices: pd.DataFrame,
        weights: Dict[str, float],
        benchmark_prices: Optional[pd.Series] = None,
    ) -> Dict:
        """
        Métriques complètes d'un portfolio.
        """
        port_returns = self.portfolio_returns(prices, weights)

        bench_returns = None
        if benchmark_prices is not None:
            bench_returns = benchmark_prices.pct_change().dropna()

        metrics = self.compute_all(port_returns, weights, bench_returns)
        metrics["weights"] = weights
        return metrics
