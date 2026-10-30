"""Tests du moteur de stratégies sans code."""
import numpy as np
import pandas as pd
import pytest

from app.services.strategy.strategy_engine import Rule, Strategy, StrategyEngine


@pytest.fixture
def engine():
    return StrategyEngine()


def ohlcv(closes):
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="D")
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 1_000.0})


def test_croisement_a_la_hausse(engine):
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [2.0, 2.0, 2.0]})
    rule = Rule("a", "cross_above", "b")
    assert not engine._evaluate_rule(df, 1, rule)   # 2 n'est pas > 2
    assert engine._evaluate_rule(df, 2, rule)       # 2 ≤ 2 puis 3 > 2


def test_logique_et_ou(engine):
    df = pd.DataFrame({"x": [5.0]})
    vrai, faux = Rule("x", ">", 1), Rule("x", "<", 1)
    assert not engine._evaluate_rules(df, 0, [vrai, faux], "AND")
    assert engine._evaluate_rules(df, 0, [vrai, faux], "OR")


def test_indicateurs_calcules(engine):
    df = engine.build_features(ohlcv(np.linspace(100, 160, 60)))
    assert df["sma_5"].iloc[-1] == pytest.approx(df["close"].iloc[-5:].mean())
    assert df["rsi_14"].iloc[-1] > 90           # tendance purement haussière


def test_achat_tenu_jusqua_la_fin(engine):
    strat = Strategy("toujours acheteur", "", [Rule("close", ">", 0)], [])
    res = engine.run(ohlcv(np.linspace(100, 150, 60)), strat)
    assert res["num_trades"] == 1
    assert res["trades"][-1]["reason"] == "end_of_period"
    assert res["final_value"] > 100_000


def test_stop_loss(engine):
    prix = [100.0] * 5 + [90.0] * 5             # chute de 10 %
    strat = Strategy("stop", "", [Rule("close", ">", 0)], [], stop_loss_pct=0.05)
    res = engine.run(ohlcv(prix), strat)
    assert any(t.get("reason") == "stop_loss" for t in res["trades"])


def test_validation(engine):
    ok = engine.validate_strategy([{"indicator": "rsi_14", "operator": "<", "value": 30}], [])
    assert ok["valid"] and ok["warnings"]
    ko = engine.validate_strategy([{"indicator": "inconnu", "operator": "?", "value": 1}], [])
    assert not ko["valid"] and len(ko["errors"]) == 2


def test_strategies_predefinies_valides(engine):
    for p in engine.get_preset_strategies():
        assert engine.validate_strategy(p["buy_rules"], p["sell_rules"])["valid"], p["name"]
