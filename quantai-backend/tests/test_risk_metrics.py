"""Tests des mesures de risque (VaR, CVaR, drawdown, ratios, bêta)."""
import numpy as np
import pandas as pd
import pytest

from app.services.risk.risk_metrics import RiskMetrics


@pytest.fixture
def rm():
    return RiskMetrics(risk_free_rate=0.0)


def test_pas_assez_de_donnees(rm):
    assert "error" in rm.compute_all(pd.Series([0.01] * 5))


def test_rendement_constant(rm):
    r = pd.Series([0.001] * 252)
    m = rm.compute_all(r)
    assert m["annual_return"] == pytest.approx(1.001 ** 252 - 1, abs=1e-6)
    assert m["max_drawdown"] == 0.0
    assert m["sharpe_ratio"] == 0.0          # volatilité nulle (bug corrigé : valait ~7e16)
    assert m["sortino_ratio"] == 0.0         # aucune baisse
    assert m["calmar_ratio"] == 0.0          # aucun drawdown
    assert m["num_observations"] == 252


def test_max_drawdown(rm):
    # 1 → 1,1 → 0,55 → 0,66 : pire chute -50 % depuis le sommet
    r = pd.Series([0.1, -0.5, 0.2])
    assert rm._max_drawdown(r) == pytest.approx(-0.5)


def test_var_et_cvar_historiques(rm):
    r = pd.Series(np.linspace(-0.05, 0.05, 101))     # pas de 0,001
    assert rm._var(r, 0.95) == pytest.approx(-0.045)
    # moyenne des 6 pires rendements : -0,050 … -0,045
    assert rm._cvar(r, 0.95) == pytest.approx(-0.0475)
    assert rm._cvar(r, 0.95) <= rm._var(r, 0.95)


def test_beta_double_du_marche(rm):
    rng = np.random.default_rng(0)
    bench = pd.Series(rng.normal(0, 0.01, 300))
    beta, _ = rm._beta_alpha(2 * bench, bench)
    assert beta == pytest.approx(2.0)


def test_sortino_superieur_au_sharpe_si_baisses_rares(rm):
    r = pd.Series([0.02] * 20 + [-0.01, -0.02] + [0.015] * 20)
    m = rm.compute_all(r)
    assert m["sortino_ratio"] > m["sharpe_ratio"] > 0
