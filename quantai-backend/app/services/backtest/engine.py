"""
QuantAI — Backtesting Engine
Simule une stratégie de trading sur données historiques.
Supporte : Buy & Hold, SMA Crossover, RSI, ML Signal
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Représente un trade exécuté."""
    date: str
    action: str          # "BUY" | "SELL"
    price: float
    shares: float
    value: float
    cash_after: float
    portfolio_value: float


@dataclass
class BacktestResult:
    """Résultat complet d'un backtest."""
    strategy: str
    ticker: str
    start_date: str
    end_date: str

    # Performance
    initial_capital: float
    final_value: float
    total_return_pct: float
    annual_return_pct: float
    benchmark_return_pct: float   # Buy & Hold simple

    # Risque
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    calmar_ratio: float
    volatility_pct: float

    # Trades
    num_trades: int
    win_rate_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float

    # Séries temporelles (pour graphiques)
    equity_curve: List[Dict]      # [{date, value, benchmark}]
    drawdown_series: List[Dict]   # [{date, drawdown}]
    trades: List[Dict]            # liste des trades


class BacktestEngine:
    """
    Moteur de backtesting événementiel.
    Simule l'exécution d'une stratégie jour par jour.
    """

    def __init__(self, initial_capital: float = 100_000.0):
        self.initial_capital = initial_capital

    # ------------------------------------------------------------------ #
    #  STRATÉGIES
    # ------------------------------------------------------------------ #

    def _generate_signals_buy_hold(self, prices: pd.Series) -> pd.Series:
        """Achète au début, tient jusqu'à la fin."""
        signals = pd.Series(0, index=prices.index)
        signals.iloc[0] = 1   # BUY day 1
        signals.iloc[-1] = -1  # SELL last day
        return signals

    def _generate_signals_sma_crossover(
        self,
        prices: pd.Series,
        short_window: int = 20,
        long_window: int = 50,
    ) -> pd.Series:
        """
        SMA Crossover : achète quand SMA20 croise SMA50 à la hausse.
        Signal +1 = BUY, -1 = SELL, 0 = rien
        """
        sma_short = prices.rolling(short_window).mean()
        sma_long = prices.rolling(long_window).mean()

        signals = pd.Series(0, index=prices.index)
        # Croisement haussier → BUY
        signals[(sma_short > sma_long) & (sma_short.shift(1) <= sma_long.shift(1))] = 1
        # Croisement baissier → SELL
        signals[(sma_short < sma_long) & (sma_short.shift(1) >= sma_long.shift(1))] = -1
        return signals

    def _generate_signals_rsi(
        self,
        prices: pd.Series,
        period: int = 14,
        oversold: float = 30,
        overbought: float = 70,
    ) -> pd.Series:
        """
        RSI : achète en zone survendu (<30), vend en zone suracheté (>70).
        """
        delta = prices.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        signals = pd.Series(0, index=prices.index)
        # RSI sort de la zone survendu → BUY
        signals[(rsi > oversold) & (rsi.shift(1) <= oversold)] = 1
        # RSI entre en zone suracheté → SELL
        signals[(rsi > overbought) & (rsi.shift(1) <= overbought)] = -1
        return signals

    def _generate_signals_ml(
        self,
        prices: pd.Series,
        ml_signals: pd.Series,
        threshold: float = 0.55,
    ) -> pd.Series:
        """
        Signaux basés sur les prédictions ML.
        ml_signals : série de probabilités (0-1) de hausse
        threshold  : seuil pour déclencher un achat
        """
        signals = pd.Series(0, index=prices.index)
        aligned = ml_signals.reindex(prices.index).fillna(0.5)

        signals[aligned > threshold] = 1       # BUY
        signals[aligned < (1 - threshold)] = -1  # SELL
        return signals

    # ------------------------------------------------------------------ #
    #  MOTEUR D'EXÉCUTION
    # ------------------------------------------------------------------ #

    def run(
        self,
        prices: pd.Series,
        signals: pd.Series,
        strategy_name: str,
        ticker: str,
        commission: float = 0.001,   # 0.1% par trade
    ) -> BacktestResult:
        """
        Exécute le backtest sur les signaux fournis.

        prices   : série de prix de clôture
        signals  : +1 = BUY, -1 = SELL, 0 = rien
        commission: frais de courtage (0.001 = 0.1%)
        """
        cash = self.initial_capital
        shares = 0.0
        trades: List[Trade] = []
        equity_curve = []
        in_position = False

        prices = prices.dropna()
        signals = signals.reindex(prices.index).fillna(0)

        for date, price in prices.items():
            signal = signals.get(date, 0)
            portfolio_value = cash + shares * price

            # --- EXÉCUTION DES SIGNAUX ---
            if signal == 1 and not in_position and cash > 0:
                # BUY : investit tout le cash disponible
                cost = price * (1 + commission)
                shares_bought = cash / cost
                cash -= shares_bought * cost
                shares = shares_bought
                in_position = True
                trades.append(Trade(
                    date=str(date.date()),
                    action="BUY",
                    price=round(price, 4),
                    shares=round(shares, 6),
                    value=round(shares * price, 2),
                    cash_after=round(cash, 2),
                    portfolio_value=round(cash + shares * price, 2),
                ))

            elif signal == -1 and in_position and shares > 0:
                # SELL : vend toutes les actions
                proceeds = shares * price * (1 - commission)
                cash += proceeds
                trades.append(Trade(
                    date=str(date.date()),
                    action="SELL",
                    price=round(price, 4),
                    shares=round(shares, 6),
                    value=round(proceeds, 2),
                    cash_after=round(cash, 2),
                    portfolio_value=round(cash, 2),
                ))
                shares = 0.0
                in_position = False

            portfolio_value = cash + shares * price
            equity_curve.append({
                "date": str(date.date()),
                "value": round(portfolio_value, 2),
            })

        # Ferme la position si encore ouverte
        if shares > 0:
            last_price = prices.iloc[-1]
            cash += shares * last_price * (1 - commission)
            shares = 0.0

        final_value = cash
        returns = self._equity_to_returns(equity_curve)

        # Benchmark : Buy & Hold simple
        bh_return = (prices.iloc[-1] / prices.iloc[0] - 1) * 100

        # Drawdown series
        dd_series = self._compute_drawdown_series(equity_curve)

        # Stats trades
        trade_stats = self._compute_trade_stats(trades)

        # Risk metrics
        risk = self._compute_risk_metrics(returns)

        total_return = (final_value / self.initial_capital - 1) * 100
        n_years = len(prices) / 252
        annual_return = ((final_value / self.initial_capital) ** (1 / max(n_years, 0.1)) - 1) * 100

        return BacktestResult(
            strategy=strategy_name,
            ticker=ticker,
            start_date=str(prices.index[0].date()),
            end_date=str(prices.index[-1].date()),
            initial_capital=self.initial_capital,
            final_value=round(final_value, 2),
            total_return_pct=round(total_return, 4),
            annual_return_pct=round(annual_return, 4),
            benchmark_return_pct=round(bh_return, 4),
            sharpe_ratio=risk["sharpe"],
            sortino_ratio=risk["sortino"],
            max_drawdown_pct=risk["max_drawdown"],
            calmar_ratio=risk["calmar"],
            volatility_pct=risk["volatility"],
            num_trades=len(trades),
            win_rate_pct=trade_stats["win_rate"],
            avg_win_pct=trade_stats["avg_win"],
            avg_loss_pct=trade_stats["avg_loss"],
            profit_factor=trade_stats["profit_factor"],
            equity_curve=equity_curve,
            drawdown_series=dd_series,
            trades=[t.__dict__ for t in trades],
        )

    # ------------------------------------------------------------------ #
    #  HELPERS
    # ------------------------------------------------------------------ #

    def _equity_to_returns(self, equity_curve: List[Dict]) -> pd.Series:
        values = pd.Series([e["value"] for e in equity_curve])
        return values.pct_change().dropna()

    def _compute_drawdown_series(self, equity_curve: List[Dict]) -> List[Dict]:
        values = pd.Series(
            [e["value"] for e in equity_curve],
            index=[e["date"] for e in equity_curve],
        )
        rolling_max = values.cummax()
        drawdown = (values - rolling_max) / rolling_max * 100
        return [
            {"date": d, "drawdown": round(dd, 4)}
            for d, dd in drawdown.items()
        ]

    def _compute_trade_stats(self, trades: List[Trade]) -> Dict:
        if len(trades) < 2:
            return {"win_rate": 0, "avg_win": 0, "avg_loss": 0, "profit_factor": 0}

        # Apparie BUY/SELL
        pairs = []
        buys = [t for t in trades if t.action == "BUY"]
        sells = [t for t in trades if t.action == "SELL"]
        for buy, sell in zip(buys, sells):
            pnl_pct = (sell.price / buy.price - 1) * 100
            pairs.append(pnl_pct)

        if not pairs:
            return {"win_rate": 0, "avg_win": 0, "avg_loss": 0, "profit_factor": 0}

        wins = [p for p in pairs if p > 0]
        losses = [p for p in pairs if p <= 0]
        total_win = sum(wins) if wins else 0
        total_loss = abs(sum(losses)) if losses else 1

        return {
            "win_rate": round(len(wins) / len(pairs) * 100, 2),
            "avg_win": round(np.mean(wins), 4) if wins else 0,
            "avg_loss": round(np.mean(losses), 4) if losses else 0,
            "profit_factor": round(total_win / total_loss, 4) if total_loss > 0 else 0,
        }

    def _compute_risk_metrics(self, returns: pd.Series) -> Dict:
        if len(returns) < 5:
            return {"sharpe": 0, "sortino": 0, "max_drawdown": 0, "calmar": 0, "volatility": 0}

        rf_daily = 0.05 / 252
        ann_vol = returns.std() * np.sqrt(252) * 100
        ann_ret = returns.mean() * 252

        sharpe = (ann_ret - 0.05) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0

        downside = returns[returns < 0].std()
        sortino = (ann_ret - 0.05) / (downside * np.sqrt(252)) if downside > 0 else 0

        cum = (1 + returns).cumprod()
        rolling_max = cum.cummax()
        max_dd = ((cum - rolling_max) / rolling_max).min() * 100

        calmar = ann_ret * 100 / abs(max_dd) if max_dd != 0 else 0

        return {
            "sharpe": round(sharpe, 4),
            "sortino": round(sortino, 4),
            "max_drawdown": round(max_dd, 4),
            "calmar": round(calmar, 4),
            "volatility": round(ann_vol, 4),
        }
