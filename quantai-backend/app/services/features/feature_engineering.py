import pandas as pd
import numpy as np
from loguru import logger
from typing import Optional


class FeatureEngineeringService:
    """
    Generates technical indicators and statistical features from OHLCV data.
    All methods operate on a DataFrame with columns: open, high, low, close, volume.
    """

    def generate_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run all feature groups and return enriched DataFrame."""
        df = df.copy().sort_index()

        try:
            df = self._add_trend_indicators(df)
            df = self._add_momentum_indicators(df)
            df = self._add_volatility_indicators(df)
            df = self._add_volume_indicators(df)
            df = self._add_statistical_features(df)
            df = self._add_lag_features(df)
            logger.info(f"Generated {len(df.columns)} features for {len(df)} rows")
        except Exception as e:
            logger.error(f"Feature engineering error: {e}")
            raise

        return df

    # ------------------------------------------------------------------ #
    # TREND
    # ------------------------------------------------------------------ #

    def _add_trend_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]

        # Simple / Exponential Moving Averages
        for w in [5, 10, 20, 50, 100, 200]:
            df[f"sma_{w}"] = close.rolling(w).mean()
            df[f"ema_{w}"] = close.ewm(span=w, adjust=False).mean()

        # MACD (12-26-9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # ADX (Average Directional Index) — 14 periods
        df = self._adx(df, 14)

        # Ichimoku
        df = self._ichimoku(df)

        # Price relative to moving averages
        for w in [20, 50, 200]:
            df[f"price_vs_sma_{w}"] = (close - df[f"sma_{w}"]) / df[f"sma_{w}"]

        return df

    # ------------------------------------------------------------------ #
    # MOMENTUM
    # ------------------------------------------------------------------ #

    def _add_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # RSI (14)
        for period in [7, 14, 21]:
            df[f"rsi_{period}"] = self._rsi(close, period)

        # Stochastic (14, 3)
        lowest_low = low.rolling(14).min()
        highest_high = high.rolling(14).max()
        df["stoch_k"] = 100 * (close - lowest_low) / (highest_high - lowest_low + 1e-9)
        df["stoch_d"] = df["stoch_k"].rolling(3).mean()

        # Rate of Change
        for period in [5, 10, 20]:
            df[f"roc_{period}"] = close.pct_change(period) * 100

        # Momentum
        for period in [5, 10, 20]:
            df[f"mom_{period}"] = close - close.shift(period)

        # Williams %R
        df["williams_r"] = -100 * (high.rolling(14).max() - close) / (
            high.rolling(14).max() - low.rolling(14).min() + 1e-9
        )

        return df

    # ------------------------------------------------------------------ #
    # VOLATILITY
    # ------------------------------------------------------------------ #

    def _add_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # Bollinger Bands (20, 2)
        for window in [10, 20]:
            mid = close.rolling(window).mean()
            std = close.rolling(window).std()
            df[f"bb_upper_{window}"] = mid + 2 * std
            df[f"bb_lower_{window}"] = mid - 2 * std
            df[f"bb_mid_{window}"] = mid
            df[f"bb_width_{window}"] = (df[f"bb_upper_{window}"] - df[f"bb_lower_{window}"]) / (mid + 1e-9)
            df[f"bb_pct_{window}"] = (close - df[f"bb_lower_{window}"]) / (
                df[f"bb_upper_{window}"] - df[f"bb_lower_{window}"] + 1e-9
            )

        # ATR (Average True Range)
        for period in [7, 14, 21]:
            df[f"atr_{period}"] = self._atr(df, period)

        # Historical volatility (annualised)
        for window in [10, 20, 30]:
            df[f"hvol_{window}"] = close.pct_change().rolling(window).std() * np.sqrt(252) * 100

        return df

    # ------------------------------------------------------------------ #
    # VOLUME
    # ------------------------------------------------------------------ #

    def _add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if "volume" not in df.columns or df["volume"].isna().all():
            return df

        close = df["close"]
        volume = df["volume"]

        # Volume moving averages
        for w in [5, 10, 20]:
            df[f"vol_sma_{w}"] = volume.rolling(w).mean()
            df[f"vol_ratio_{w}"] = volume / (df[f"vol_sma_{w}"] + 1e-9)

        # VWAP (rolling 20)
        df["vwap_20"] = (close * volume).rolling(20).sum() / (volume.rolling(20).sum() + 1e-9)
        df["price_vs_vwap"] = (close - df["vwap_20"]) / (df["vwap_20"] + 1e-9)

        # OBV (On-Balance Volume)
        obv = [0]
        for i in range(1, len(df)):
            if close.iloc[i] > close.iloc[i - 1]:
                obv.append(obv[-1] + volume.iloc[i])
            elif close.iloc[i] < close.iloc[i - 1]:
                obv.append(obv[-1] - volume.iloc[i])
            else:
                obv.append(obv[-1])
        df["obv"] = obv

        # Volume-weighted price change
        df["vol_price_change"] = close.pct_change() * volume

        return df

    # ------------------------------------------------------------------ #
    # STATISTICAL
    # ------------------------------------------------------------------ #

    def _add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        returns = close.pct_change()

        # Rolling stats on returns
        for w in [5, 10, 20, 60]:
            df[f"ret_mean_{w}"] = returns.rolling(w).mean()
            df[f"ret_std_{w}"] = returns.rolling(w).std()
            df[f"ret_skew_{w}"] = returns.rolling(w).skew()
            df[f"ret_kurt_{w}"] = returns.rolling(w).kurt()

        # Autocorrelation (lag 1)
        df["autocorr_1"] = returns.rolling(20).apply(lambda x: x.autocorr(lag=1), raw=False)

        # Z-score of close (20-period)
        roll_mean = close.rolling(20).mean()
        roll_std = close.rolling(20).std()
        df["zscore_20"] = (close - roll_mean) / (roll_std + 1e-9)

        # Daily return
        df["daily_return"] = returns
        df["log_return"] = np.log1p(returns)

        # High-Low range
        df["hl_range"] = (df["high"] - df["low"]) / (df["close"] + 1e-9)

        # Gap (open vs prev close)
        df["gap"] = (df["open"] - close.shift(1)) / (close.shift(1) + 1e-9)

        return df

    # ------------------------------------------------------------------ #
    # LAG FEATURES
    # ------------------------------------------------------------------ #

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        returns = df["daily_return"] if "daily_return" in df.columns else close.pct_change()

        for lag in [1, 2, 3, 5, 10, 20]:
            df[f"close_lag_{lag}"] = close.shift(lag)
            df[f"return_lag_{lag}"] = returns.shift(lag)

        return df

    # ------------------------------------------------------------------ #
    # HELPERS
    # ------------------------------------------------------------------ #

    def _rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs))

    def _atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def _adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        high, low, close = df["high"], df["low"], df["close"]
        plus_dm = high.diff().clip(lower=0)
        minus_dm = (-low.diff()).clip(lower=0)
        tr = self._atr(df, period)

        plus_di = 100 * plus_dm.rolling(period).mean() / (tr + 1e-9)
        minus_di = 100 * minus_dm.rolling(period).mean() / (tr + 1e-9)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)

        df["adx"] = dx.rolling(period).mean()
        df["plus_di"] = plus_di
        df["minus_di"] = minus_di
        return df

    def _ichimoku(self, df: pd.DataFrame) -> pd.DataFrame:
        high, low = df["high"], df["low"]

        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
        chikou = df["close"].shift(-26)

        df["ichi_tenkan"] = tenkan
        df["ichi_kijun"] = kijun
        df["ichi_senkou_a"] = senkou_a
        df["ichi_senkou_b"] = senkou_b
        df["ichi_chikou"] = chikou
        df["ichi_cloud_size"] = (senkou_a - senkou_b).abs()

        return df


feature_service = FeatureEngineeringService()
