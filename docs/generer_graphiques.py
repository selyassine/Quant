"""Régénère les graphiques du README à partir des données incluses.

À lancer depuis la racine du dépôt : python docs/generer_graphiques.py
(dépendances : pandas, numpy, matplotlib, loguru).
"""
import sys, pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, "quantai-backend")
from app.services.strategy.strategy_engine import StrategyEngine, Strategy, Rule
from app.services.risk.risk_metrics import RiskMetrics

df = pd.read_csv("quantai-backend/scripts/market_data_csv/AAPL.csv", parse_dates=["timestamp"]).set_index("timestamp")
eng = StrategyEngine()
fig, ax = plt.subplots(figsize=(11, 5.2), dpi=150)
res_all = {}
for p in eng.get_preset_strategies()[:4]:
    s = Strategy(p["name"], p["description"], [Rule(**r) for r in p["buy_rules"]], [Rule(**r) for r in p["sell_rules"]], p.get("logic", "AND"))
    r = eng.run(df, s); res_all[p["name"]] = r
    eq = pd.DataFrame(r["equity_curve"]); ax.plot(pd.to_datetime(eq["date"]), eq["value"] / 1000, lw=1.8,
        label=f'{p["name"]}  ({r["total_return_pct"]:+.1f} %, Sharpe {r["sharpe_ratio"]:.2f})')
bh = df["close"] / df["close"].iloc[0] * 100
ax.plot(bh.index, bh, color="#888", lw=1.4, ls="--", label=f'Achat-conservation  ({(bh.iloc[-1]/100-1)*100:+.1f} %)')
ax.set_title("Backtest des stratégies prédéfinies — AAPL, 2 ans de données journalières", fontsize=13, weight="bold")
ax.set_ylabel("Valeur du portefeuille (k$)"); ax.grid(alpha=.3); ax.legend(fontsize=8.5, loc="upper left", frameon=False)
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig("docs/images/backtest_aapl.png")

rm = RiskMetrics(risk_free_rate=0.04)
tick = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "SPY", "QQQ"]
rows = []
for t in tick:
    c = pd.read_csv(f"quantai-backend/scripts/market_data_csv/{t}.csv", parse_dates=["timestamp"]).set_index("timestamp")["close"]
    m = rm.compute_all(c.pct_change().dropna()); rows.append((t, m["annual_volatility"]*100, m["annual_return"]*100, m["var_95"]*100, m["sharpe_ratio"]))
fig, ax = plt.subplots(figsize=(11, 5.2), dpi=150)
for t, vol, ret, var, sh in rows:
    ax.scatter(vol, ret, s=60 + 140 * abs(var), alpha=.75)
    ax.annotate(f"{t}\nSharpe {sh:.2f}", (vol, ret), textcoords="offset points", xytext=(8, 4), fontsize=8.5)
ax.axhline(0, color="#999", lw=.8)
ax.set_xlabel("Volatilité annualisée (%)"); ax.set_ylabel("Rendement annualisé (%)")
ax.set_title("Rendement / risque calculés par le module de risque — taille des points = VaR 95 % journalière", fontsize=12, weight="bold")
ax.grid(alpha=.3)
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig("docs/images/risque_rendement.png")
