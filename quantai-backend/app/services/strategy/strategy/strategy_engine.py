"""
M4 — Strategy Builder Engine
Allows creating trading strategies from rules without coding.

Rule format:
  {"indicator": "rsi_14", "operator": ">", "value": 30}
  {"indicator": "macd", "operator": "cross_above", "value": "macd_signal"}
  {"indicator": "close", "operator": ">", "value": "sma_20"}

Logic: AND / OR between rules
Action: BUY / SELL / HOLD
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from loguru import logger


SUPPORTED_INDICATORS = [
    # Price
    "close", "open", "high", "low", "volume",
    # Moving averages
    "sma_5", "sma_10", "sma_20", "sma_50", "sma_200",
    "ema_5", "ema_10", "ema_20", "ema_50", "ema_200",
    # Momentum
    "rsi_7", "rsi_14", "rsi_21",
    "macd", "macd_signal", "macd_hist",
    "stoch_k", "stoch_d",
    "mom_5", "mom_10", "mom_20",
    "roc_5", "roc_10", "roc_20",
    # Volatility
    "bb_upper_20", "bb_lower_20", "bb_mid_20", "bb_width_20", "bb_pct_20",
    "atr_7", "atr_14", "atr_21",
    "hvol_10", "hvol_20",
    # Volume
    "vol_sma_20", "vol_ratio_20", "vwap_20",
    # Stats
    "daily_return", "zscore_20", "hl_range",
]

OPERATORS = [">", "<", ">=", "<=", "==", "cross_above", "cross_below"]


@dataclass
class Rule:
    indicator: str
    operator: str
    value: Any          # float or another indicator name
    description: str = ""


@dataclass
class Strategy:
    name: str
    description: str
    buy_rules: List[Rule]
    sell_rules: List[Rule]
    logic: str = "AND"   # AND / OR
    stop_loss_pct: Optional[float] = None   # e.g. 0.05 = 5%
    take_profit_pct: Optional[float] = None


class StrategyEngine:

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all supported indicators on OHLCV dataframe."""
        df = df.copy().sort_index()
        close  = df["close"]
        high   = df["high"]
        low    = df["low"]
        volume = df.get("volume", pd.Series(0, index=df.index))

        # Moving averages
        for w in [5, 10, 20, 50, 200]:
            df[f"sma_{w}"] = close.rolling(w).mean()
            df[f"ema_{w}"] = close.ewm(span=w, adjust=False).mean()

        # RSI
        for p in [7, 14, 21]:
            delta = close.diff()
            gain  = delta.clip(lower=0).rolling(p).mean()
            loss  = (-delta.clip(upper=0)).rolling(p).mean()
            df[f"rsi_{p}"] = 100 - (100 / (1 + gain / (loss + 1e-9)))

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["macd"]        = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"]   = df["macd"] - df["macd_signal"]

        # Stochastic
        ll14 = low.rolling(14).min()
        hh14 = high.rolling(14).max()
        df["stoch_k"] = 100 * (close - ll14) / (hh14 - ll14 + 1e-9)
        df["stoch_d"] = df["stoch_k"].rolling(3).mean()

        # Momentum & ROC
        for p in [5, 10, 20]:
            df[f"mom_{p}"] = close - close.shift(p)
            df[f"roc_{p}"] = close.pct_change(p) * 100

        # Bollinger Bands
        mid = close.rolling(20).mean()
        std = close.rolling(20).std()
        df["bb_upper_20"] = mid + 2 * std
        df["bb_lower_20"] = mid - 2 * std
        df["bb_mid_20"]   = mid
        df["bb_width_20"] = (df["bb_upper_20"] - df["bb_lower_20"]) / (mid + 1e-9)
        df["bb_pct_20"]   = (close - df["bb_lower_20"]) / (df["bb_upper_20"] - df["bb_lower_20"] + 1e-9)

        # ATR
        for p in [7, 14, 21]:
            tr = pd.concat([
                high - low,
                (high - close.shift()).abs(),
                (low  - close.shift()).abs(),
            ], axis=1).max(axis=1)
            df[f"atr_{p}"] = tr.rolling(p).mean()

        # Historical volatility
        for w in [10, 20]:
            df[f"hvol_{w}"] = close.pct_change().rolling(w).std() * np.sqrt(252) * 100

        # Volume indicators
        df["vol_sma_20"]  = volume.rolling(20).mean()
        df["vol_ratio_20"] = volume / (df["vol_sma_20"] + 1e-9)
        df["vwap_20"]     = (close * volume).rolling(20).sum() / (volume.rolling(20).sum() + 1e-9)

        # Stats
        df["daily_return"] = close.pct_change()
        roll_mean = close.rolling(20).mean()
        roll_std  = close.rolling(20).std()
        df["zscore_20"]   = (close - roll_mean) / (roll_std + 1e-9)
        df["hl_range"]    = (high - low) / (close + 1e-9)

        return df

    def _get_value(self, df: pd.DataFrame, idx: int, ref: Any) -> Optional[float]:
        """Resolve a rule value — either a float or another indicator column."""
        if isinstance(ref, str):
            if ref in df.columns:
                v = df[ref].iloc[idx]
                return float(v) if pd.notna(v) else None
            return None
        return float(ref)

    def _evaluate_rule(self, df: pd.DataFrame, idx: int, rule: Rule) -> bool:
        """Evaluate a single rule at a given row index."""
        if rule.indicator not in df.columns:
            return False

        left = df[rule.indicator].iloc[idx]
        if pd.isna(left):
            return False

        op = rule.operator

        if op in ("cross_above", "cross_below"):
            if idx == 0:
                return False
            left_prev  = df[rule.indicator].iloc[idx - 1]
            right_curr = self._get_value(df, idx, rule.value)
            right_prev = self._get_value(df, idx - 1, rule.value)
            if right_curr is None or right_prev is None or pd.isna(left_prev):
                return False
            if op == "cross_above":
                return float(left_prev) <= float(right_prev) and float(left) > float(right_curr)
            else:
                return float(left_prev) >= float(right_prev) and float(left) < float(right_curr)

        right = self._get_value(df, idx, rule.value)
        if right is None:
            return False

        left_f, right_f = float(left), float(right)
        if op == ">":   return left_f >  right_f
        if op == "<":   return left_f <  right_f
        if op == ">=":  return left_f >= right_f
        if op == "<=":  return left_f <= right_f
        if op == "==":  return abs(left_f - right_f) < 1e-9
        return False

    def _evaluate_rules(self, df: pd.DataFrame, idx: int, rules: List[Rule], logic: str) -> bool:
        """Evaluate a list of rules with AND / OR logic."""
        if not rules:
            return False
        results = [self._evaluate_rule(df, idx, r) for r in rules]
        return all(results) if logic == "AND" else any(results)

    def run(self, df: pd.DataFrame, strategy: Strategy) -> Dict:
        """
        Execute strategy on historical data.
        Returns signals, trades, and summary metrics.
        """
        df = self.build_features(df)

        signals  = []
        trades   = []
        position = 0.0
        entry_price = 0.0
        cash     = 100_000.0
        shares   = 0.0
        equity   = []

        for i in range(1, len(df)):
            row   = df.iloc[i]
            price = float(row["close"])
            date  = str(df.index[i])[:10]

            signal = "HOLD"

            if position == 0:
                # Check BUY
                if self._evaluate_rules(df, i, strategy.buy_rules, strategy.logic):
                    signal = "BUY"
                    shares = (cash * 0.99) / price
                    cash  -= shares * price
                    position   = shares
                    entry_price = price
                    trades.append({"date": date, "action": "BUY", "price": price, "shares": shares})

            else:
                # Stop loss / Take profit
                pct_change = (price - entry_price) / entry_price

                sl_hit = strategy.stop_loss_pct   and pct_change <= -strategy.stop_loss_pct
                tp_hit = strategy.take_profit_pct and pct_change >=  strategy.take_profit_pct
                sell_signal = self._evaluate_rules(df, i, strategy.sell_rules, strategy.logic)

                if sl_hit or tp_hit or sell_signal:
                    signal = "SELL"
                    reason = "stop_loss" if sl_hit else ("take_profit" if tp_hit else "signal")
                    cash  += shares * price
                    pnl    = (price - entry_price) * shares
                    trades.append({"date": date, "action": "SELL", "price": price, "shares": shares, "pnl": round(pnl, 2), "reason": reason})
                    shares   = 0.0
                    position = 0.0

            portfolio_value = cash + shares * price
            equity.append({"date": date, "value": round(portfolio_value, 2)})
            signals.append({"date": date, "signal": signal, "price": price})

        # Close open position
        if shares > 0 and len(df) > 0:
            final_price = float(df["close"].iloc[-1])
            cash += shares * final_price
            trades.append({"date": str(df.index[-1])[:10], "action": "SELL", "price": final_price, "shares": shares, "pnl": round((final_price - entry_price) * shares, 2), "reason": "end_of_period"})

        # Metrics
        final_value  = cash
        total_return = (final_value - 100_000) / 100_000 * 100
        values_arr   = np.array([e["value"] for e in equity])
        returns_arr  = np.diff(values_arr) / (values_arr[:-1] + 1e-9)

        sharpe = 0.0
        if len(returns_arr) > 1:
            sharpe = float(np.mean(returns_arr) / (np.std(returns_arr) + 1e-9) * np.sqrt(252))

        peak    = np.maximum.accumulate(values_arr)
        max_dd  = float(np.min((values_arr - peak) / (peak + 1e-9)) * 100)

        sell_trades = [t for t in trades if t["action"] == "SELL"]
        wins        = [t for t in sell_trades if t.get("pnl", 0) > 0]
        win_rate    = len(wins) / len(sell_trades) * 100 if sell_trades else 0

        return {
            "strategy_name":    strategy.name,
            "initial_capital":  100_000,
            "final_value":      round(final_value, 2),
            "total_return_pct": round(total_return, 2),
            "sharpe_ratio":     round(sharpe, 4),
            "max_drawdown_pct": round(max_dd, 2),
            "num_trades":       len(sell_trades),
            "win_rate_pct":     round(win_rate, 2),
            "trades":           trades[:50],
            "equity_curve":     equity,
            "signals":          signals[-100:],
        }

    def validate_strategy(self, buy_rules: List[Dict], sell_rules: List[Dict]) -> Dict:
        """Validate strategy rules before running."""
        errors = []
        warnings = []

        for i, r in enumerate(buy_rules + sell_rules):
            if r.get("indicator") not in SUPPORTED_INDICATORS:
                errors.append(f"Rule {i+1}: unknown indicator '{r.get('indicator')}'")
            if r.get("operator") not in OPERATORS:
                errors.append(f"Rule {i+1}: unknown operator '{r.get('operator')}'")
            v = r.get("value")
            if isinstance(v, str) and v not in SUPPORTED_INDICATORS:
                errors.append(f"Rule {i+1}: unknown value indicator '{v}'")

        if not buy_rules:
            warnings.append("No BUY rules defined")
        if not sell_rules:
            warnings.append("No SELL rules — position will close at end of period")

        return {
            "valid":    len(errors) == 0,
            "errors":   errors,
            "warnings": warnings,
        }

    def get_preset_strategies(self) -> List[Dict]:
        """Return built-in strategy presets."""
        return [
            {
                "name": "RSI Mean Reversion",
                "description": "Buy when RSI < 30 (oversold), sell when RSI > 70 (overbought)",
                "buy_rules":  [{"indicator": "rsi_14", "operator": "<",  "value": 30}],
                "sell_rules": [{"indicator": "rsi_14", "operator": ">",  "value": 70}],
                "logic": "AND",
            },
            {
                "name": "MACD Crossover",
                "description": "Buy on bullish MACD crossover, sell on bearish crossover",
                "buy_rules":  [{"indicator": "macd", "operator": "cross_above", "value": "macd_signal"}],
                "sell_rules": [{"indicator": "macd", "operator": "cross_below", "value": "macd_signal"}],
                "logic": "AND",
            },
            {
                "name": "Golden Cross",
                "description": "Buy when SMA50 crosses above SMA200, sell when it crosses below",
                "buy_rules":  [{"indicator": "sma_50", "operator": "cross_above", "value": "sma_200"}],
                "sell_rules": [{"indicator": "sma_50", "operator": "cross_below", "value": "sma_200"}],
                "logic": "AND",
            },
            {
                "name": "Bollinger Band Squeeze",
                "description": "Buy when price touches lower band, sell when it touches upper band",
                "buy_rules":  [{"indicator": "close", "operator": "<=", "value": "bb_lower_20"}],
                "sell_rules": [{"indicator": "close", "operator": ">=", "value": "bb_upper_20"}],
                "logic": "AND",
            },
            {
                "name": "Combined RSI + MACD",
                "description": "Buy when RSI < 35 AND MACD is bullish, sell when RSI > 65",
                "buy_rules": [
                    {"indicator": "rsi_14", "operator": "<", "value": 35},
                    {"indicator": "macd",   "operator": ">", "value": "macd_signal"},
                ],
                "sell_rules": [{"indicator": "rsi_14", "operator": ">", "value": 65}],
                "logic": "AND",
            },
        ]


strategy_engine = StrategyEngine()
