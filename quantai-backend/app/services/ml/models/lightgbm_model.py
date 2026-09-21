"""
LightGBM model for short-term price direction prediction.
Predicts: next-day return direction (up/down) + magnitude
"""
import numpy as np
import pandas as pd
import lightgbm as lgb
import joblib
import os
from typing import Dict, Tuple, Optional
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, mean_squared_error
import logging

logger = logging.getLogger(__name__)

MODELS_DIR = "/app/app/services/ml/saved_models"


class LightGBMPredictor:
    """
    LightGBM-based predictor for financial time series.
    Two heads:
      - classifier: predict direction (1=up, 0=down)
      - regressor:  predict next-day return magnitude
    """

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.classifier = None
        self.regressor = None
        self.scaler = StandardScaler()
        self.feature_cols: list = []
        self.is_trained = False

    # ------------------------------------------------------------------ #
    #  Feature preparation                                                 #
    # ------------------------------------------------------------------ #

    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Build feature matrix X and targets y_clf / y_reg from OHLCV + features df.
        Expects columns: open, high, low, close, volume + technical indicators
        """
        df = df.copy().sort_values("date").reset_index(drop=True)

        # --- targets ---
        df["future_return"] = df["close"].pct_change(1).shift(-1)
        df["direction"] = (df["future_return"] > 0).astype(int)

        # --- price-derived features ---
        df["return_1d"] = df["close"].pct_change(1)
        df["return_3d"] = df["close"].pct_change(3)
        df["return_5d"] = df["close"].pct_change(5)
        df["return_10d"] = df["close"].pct_change(10)
        df["return_20d"] = df["close"].pct_change(20)

        df["hl_ratio"] = (df["high"] - df["low"]) / df["close"]
        df["co_ratio"] = (df["close"] - df["open"]) / df["open"]

        df["vol_change"] = df["volume"].pct_change(1)
        df["vol_ma5"] = df["volume"].rolling(5).mean() / df["volume"].rolling(20).mean()

        # --- rolling stats ---
        for w in [5, 10, 20, 60]:
            df[f"std_{w}"] = df["return_1d"].rolling(w).std()
            df[f"skew_{w}"] = df["return_1d"].rolling(w).skew()

        # --- existing technical indicator columns ---
        indicator_cols = [
            c for c in df.columns
            if any(c.startswith(p) for p in [
                "rsi", "macd", "bb_", "atr", "adx", "ema", "sma",
                "vwap", "obv", "stoch", "cci", "willr", "mfi"
            ])
        ]

        base_features = [
            "return_1d", "return_3d", "return_5d", "return_10d", "return_20d",
            "hl_ratio", "co_ratio", "vol_change", "vol_ma5",
            "std_5", "std_10", "std_20", "std_60",
            "skew_5", "skew_10", "skew_20", "skew_60",
        ]

        self.feature_cols = base_features + indicator_cols

        # keep only existing columns
        self.feature_cols = [c for c in self.feature_cols if c in df.columns]

        df.dropna(subset=self.feature_cols + ["direction", "future_return"], inplace=True)

        X = df[self.feature_cols]
        y_clf = df["direction"]
        y_reg = df["future_return"]

        return X, y_clf, y_reg

    # ------------------------------------------------------------------ #
    #  Training                                                            #
    # ------------------------------------------------------------------ #

    def train(self, df: pd.DataFrame) -> Dict:
        """Train both classifier and regressor. Returns eval metrics."""
        logger.info(f"[LightGBM] Training on {self.ticker} — {len(df)} rows")

        X, y_clf, y_reg = self.prepare_features(df)

        if len(X) < 100:
            raise ValueError(f"Not enough data: {len(X)} rows (need 100+)")

        # Time-series split (no leakage)
        tscv = TimeSeriesSplit(n_splits=5)
        split = list(tscv.split(X))
        train_idx, val_idx = split[-1]

        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_clf_train, y_clf_val = y_clf.iloc[train_idx], y_clf.iloc[val_idx]
        y_reg_train, y_reg_val = y_reg.iloc[train_idx], y_reg.iloc[val_idx]

        # Scale
        X_train_s = self.scaler.fit_transform(X_train)
        X_val_s = self.scaler.transform(X_val)

        # ---- Classifier ----
        self.classifier = lgb.LGBMClassifier(
            n_estimators=500,
            learning_rate=0.05,
            num_leaves=31,
            max_depth=6,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=0.1,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
        self.classifier.fit(
            X_train_s, y_clf_train,
            eval_set=[(X_val_s, y_clf_val)],
            callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(False)],
        )

        # ---- Regressor ----
        self.regressor = lgb.LGBMRegressor(
            n_estimators=500,
            learning_rate=0.05,
            num_leaves=31,
            max_depth=6,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=0.1,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
        self.regressor.fit(
            X_train_s, y_reg_train,
            eval_set=[(X_val_s, y_reg_val)],
            callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(False)],
        )

        # ---- Metrics ----
        clf_preds = self.classifier.predict(X_val_s)
        clf_proba = self.classifier.predict_proba(X_val_s)[:, 1]
        reg_preds = self.regressor.predict(X_val_s)

        metrics = {
            "model": "lightgbm",
            "ticker": self.ticker,
            "train_rows": len(X_train),
            "val_rows": len(X_val),
            "accuracy": float(accuracy_score(y_clf_val, clf_preds)),
            "auc_roc": float(roc_auc_score(y_clf_val, clf_proba)),
            "rmse_return": float(np.sqrt(mean_squared_error(y_reg_val, reg_preds))),
            "feature_count": len(self.feature_cols),
        }

        self.is_trained = True
        logger.info(f"[LightGBM] {self.ticker} — accuracy={metrics['accuracy']:.3f}, auc={metrics['auc_roc']:.3f}")
        return metrics

    # ------------------------------------------------------------------ #
    #  Prediction                                                          #
    # ------------------------------------------------------------------ #

    def predict(self, df: pd.DataFrame) -> Dict:
        """Predict on latest data row."""
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first.")

        X, _, _ = self.prepare_features(df)
        X_last = X.tail(1)
        X_scaled = self.scaler.transform(X_last)

        direction_proba = float(self.classifier.predict_proba(X_scaled)[0][1])
        direction = int(direction_proba > 0.5)
        predicted_return = float(self.regressor.predict(X_scaled)[0])

        # Feature importance top 10
        importance = dict(zip(
            self.feature_cols,
            self.classifier.feature_importances_.tolist()
        ))
        top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "model": "lightgbm",
            "ticker": self.ticker,
            "direction": "up" if direction == 1 else "down",
            "direction_probability": direction_proba,
            "predicted_return_pct": predicted_return * 100,
            "confidence": abs(direction_proba - 0.5) * 2,  # 0..1
            "top_features": dict(top_features),
        }

    # ------------------------------------------------------------------ #
    #  Persistence                                                         #
    # ------------------------------------------------------------------ #

    def save(self):
        os.makedirs(MODELS_DIR, exist_ok=True)
        path = f"{MODELS_DIR}/lgbm_{self.ticker}"
        joblib.dump({
            "classifier": self.classifier,
            "regressor": self.regressor,
            "scaler": self.scaler,
            "feature_cols": self.feature_cols,
            "ticker": self.ticker,
        }, f"{path}.pkl")
        logger.info(f"[LightGBM] Saved model to {path}.pkl")

    def load(self) -> bool:
        path = f"{MODELS_DIR}/lgbm_{self.ticker}.pkl"
        if not os.path.exists(path):
            return False
        data = joblib.load(path)
        self.classifier = data["classifier"]
        self.regressor = data["regressor"]
        self.scaler = data["scaler"]
        self.feature_cols = data["feature_cols"]
        self.is_trained = True
        logger.info(f"[LightGBM] Loaded model from {path}")
        return True
