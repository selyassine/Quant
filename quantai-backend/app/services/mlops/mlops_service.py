"""
M12 — MLOps & Monitoring Service
Model performance tracking, data drift detection, prediction accuracy,
feature drift, and retraining recommendations.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


class MLOpsService:

    # ------------------------------------------------------------------ #
    #  MODEL REGISTRY
    # ------------------------------------------------------------------ #

    async def get_model_registry(self, session) -> Dict:
        result = await session.execute(text(
            "SELECT DISTINCT ticker FROM assets ORDER BY ticker"
        ))
        tickers = [r[0] for r in result.fetchall()]

        import os
        models_dir = "/app/models"
        registry = []

        for ticker in tickers:
            trained_models = []
            last_trained = None

            for model_name in ["lightgbm", "lstm", "transformer"]:
                path     = f"{models_dir}/{ticker}_{model_name}.pkl"
                alt_path = f"{models_dir}/{ticker}_{model_name}.pt"
                exists   = os.path.exists(path) or os.path.exists(alt_path)
                if exists:
                    trained_models.append(model_name)
                    mtime = os.path.getmtime(path if os.path.exists(path) else alt_path)
                    dt    = datetime.fromtimestamp(mtime)
                    if last_trained is None or dt > last_trained:
                        last_trained = dt

            data_result = await session.execute(text("""
                SELECT MAX(timestamp), COUNT(*) FROM ohlcv WHERE ticker = :ticker
            """), {"ticker": ticker})
            row = data_result.fetchone()
            last_data  = row[0] if row else None
            data_count = row[1] if row else 0

            registry.append({
                "ticker":         ticker,
                "trained_models": trained_models,
                "num_models":     len(trained_models),
                "last_trained":   last_trained.isoformat() if last_trained else None,
                "last_data_point": last_data.isoformat() if last_data else None,
                "data_points":    data_count,
                "status":         "trained" if trained_models else "not_trained",
                "needs_retraining": self._needs_retraining(last_trained),
            })

        return {
            "total_tickers":   len(tickers),
            "trained_tickers": sum(1 for r in registry if r["status"] == "trained"),
            "models":          registry,
        }

    def _needs_retraining(self, last_trained: Optional[datetime]) -> bool:
        if last_trained is None:
            return True
        return (datetime.now() - last_trained).days > 7

    # ------------------------------------------------------------------ #
    #  DATA DRIFT DETECTION  (fixed)
    # ------------------------------------------------------------------ #

    async def detect_data_drift(self, ticker: str, session) -> Dict:
        result = await session.execute(text("""
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE ticker = :ticker
            ORDER BY timestamp ASC
        """), {"ticker": ticker})
        rows = result.fetchall()

        if len(rows) < 60:
            return {"error": f"Not enough data for drift detection — need 60+ rows, got {len(rows)}"}

        df = pd.DataFrame(rows, columns=["date","open","high","low","close","volume"])
        df["date"]   = pd.to_datetime(df["date"])
        df["close"]  = df["close"].astype(float)
        df["open"]   = df["open"].astype(float)
        df["high"]   = df["high"].astype(float)
        df["low"]    = df["low"].astype(float)
        df["volume"] = df["volume"].astype(float)

        # Compute features — use fillna to avoid losing too many rows
        df["return_1d"] = df["close"].pct_change()
        df["hl_ratio"]  = (df["high"] - df["low"]) / df["close"].replace(0, np.nan)
        df["co_ratio"]  = (df["close"] - df["open"]) / df["open"].replace(0, np.nan)
        vol_ma = df["volume"].rolling(20, min_periods=5).mean()
        df["vol_norm"]  = (df["volume"] / vol_ma.replace(0, np.nan)).fillna(1.0)

        # Drop only rows where core features are NaN
        df = df[["date","return_1d","hl_ratio","co_ratio","vol_norm"]].dropna(subset=["return_1d","hl_ratio","co_ratio"])
        df = df.fillna(1.0)  # fill remaining vol_norm NaNs

        if len(df) < 40:
            return {"error": f"Not enough clean data after feature computation — got {len(df)} rows"}

        split = int(len(df) * 0.7)
        ref   = df.iloc[:split]
        curr  = df.iloc[split:]

        features = ["return_1d", "hl_ratio", "co_ratio", "vol_norm"]
        drift_results = []

        for feat in features:
            try:
                psi = self._compute_psi(ref[feat].values, curr[feat].values)
            except Exception:
                psi = 0.0
            drift_results.append({
                "feature":    feat,
                "psi":        round(psi, 4),
                "drift_level": "high" if psi > 0.2 else "medium" if psi > 0.1 else "low",
                "ref_mean":   round(float(ref[feat].mean()), 6),
                "curr_mean":  round(float(curr[feat].mean()), 6),
                "ref_std":    round(float(ref[feat].std()), 6),
                "curr_std":   round(float(curr[feat].std()), 6),
            })

        overall_psi = float(np.mean([d["psi"] for d in drift_results]))
        drift_results.sort(key=lambda x: x["psi"], reverse=True)

        return {
            "ticker":           ticker,
            "overall_psi":      round(overall_psi, 4),
            "drift_detected":   overall_psi > 0.1,
            "severity":         "high" if overall_psi > 0.2 else "medium" if overall_psi > 0.1 else "low",
            "reference_period": f"{ref['date'].iloc[0].date()} → {ref['date'].iloc[-1].date()}",
            "current_period":   f"{curr['date'].iloc[0].date()} → {curr['date'].iloc[-1].date()}",
            "features":         drift_results,
            "recommendation": (
                "Retrain models immediately — significant distribution shift detected"
                if overall_psi > 0.2 else
                "Monitor closely — moderate drift detected"
                if overall_psi > 0.1 else
                "No action needed — data distribution is stable"
            ),
        }

    def _compute_psi(self, reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
        ref_clean  = reference[np.isfinite(reference)]
        curr_clean = current[np.isfinite(current)]
        if len(ref_clean) < 5 or len(curr_clean) < 5:
            return 0.0
        breakpoints = np.percentile(ref_clean, np.linspace(0, 100, bins + 1))
        breakpoints = np.unique(breakpoints)
        if len(breakpoints) < 2:
            return 0.0
        ref_counts  = np.histogram(ref_clean,  bins=breakpoints)[0]
        curr_counts = np.histogram(curr_clean, bins=breakpoints)[0]
        ref_pct  = (ref_counts  + 1e-6) / max(len(ref_clean), 1)
        curr_pct = (curr_counts + 1e-6) / max(len(curr_clean), 1)
        psi = np.sum((curr_pct - ref_pct) * np.log(curr_pct / ref_pct))
        return float(abs(psi))

    # ------------------------------------------------------------------ #
    #  PREDICTION ACCURACY
    # ------------------------------------------------------------------ #

    async def prediction_accuracy(self, ticker: str, session) -> Dict:
        result = await session.execute(text("""
            SELECT timestamp, close
            FROM ohlcv
            WHERE ticker = :ticker
            ORDER BY timestamp DESC
            LIMIT 90
        """), {"ticker": ticker})
        rows = result.fetchall()

        if len(rows) < 20:
            return {"error": "Not enough data"}

        df = pd.DataFrame(rows, columns=["date","close"])
        df["close"] = df["close"].astype(float)
        df = df.sort_values("date").reset_index(drop=True)
        df["actual_return"] = df["close"].pct_change().shift(-1)
        df["actual_dir"]    = (df["actual_return"] > 0).astype(int)
        df["pred_dir"]      = (df["close"].pct_change(5) > 0).astype(int)
        df = df.dropna()

        correct  = int((df["pred_dir"] == df["actual_dir"]).sum())
        total    = len(df)
        accuracy = correct / total if total > 0 else 0

        tp = int(((df["pred_dir"] == 1) & (df["actual_dir"] == 1)).sum())
        tn = int(((df["pred_dir"] == 0) & (df["actual_dir"] == 0)).sum())
        fp = int(((df["pred_dir"] == 1) & (df["actual_dir"] == 0)).sum())
        fn = int(((df["pred_dir"] == 0) & (df["actual_dir"] == 1)).sum())

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "ticker":    ticker,
            "accuracy":  round(accuracy * 100, 2),
            "precision": round(precision * 100, 2),
            "recall":    round(recall * 100, 2),
            "f1_score":  round(f1, 4),
            "total_predictions":   total,
            "correct_predictions": correct,
            "confusion_matrix": {
                "true_positive":  tp,
                "true_negative":  tn,
                "false_positive": fp,
                "false_negative": fn,
            },
            "grade": (
                "A" if accuracy > 0.6 else
                "B" if accuracy > 0.55 else
                "C" if accuracy > 0.5 else "D"
            ),
        }

    # ------------------------------------------------------------------ #
    #  SYSTEM HEALTH
    # ------------------------------------------------------------------ #

    async def system_health(self, session) -> Dict:
        try:
            r = await session.execute(text("SELECT COUNT(*) FROM ohlcv"))
            total_rows = r.scalar()
            db_ok = True
        except Exception:
            total_rows = 0
            db_ok = False

        result = await session.execute(text("""
            SELECT ticker, MAX(timestamp) as last_ts, COUNT(*) as cnt
            FROM ohlcv GROUP BY ticker ORDER BY ticker
        """))
        ticker_health = []
        now = datetime.utcnow()
        for row in result.fetchall():
            last     = row[1]
            days_old = (now - last).days if last else 999
            ticker_health.append({
                "ticker":            row[0],
                "last_update":       last.isoformat() if last else None,
                "days_since_update": days_old,
                "data_points":       row[2],
                "fresh":             days_old <= 5,
            })

        fresh_count = sum(1 for t in ticker_health if t["fresh"])

        import os
        models_dir  = "/app/models"
        model_files = []
        if os.path.exists(models_dir):
            model_files = os.listdir(models_dir)

        return {
            "status": "healthy" if db_ok else "degraded",
            "database": {"connected": db_ok, "total_rows": total_rows},
            "data_freshness": {
                "fresh_tickers": fresh_count,
                "total_tickers": len(ticker_health),
                "tickers":       ticker_health,
            },
            "models": {
                "total_files": len(model_files),
                "files":       model_files[:20],
            },
            "checked_at": datetime.utcnow().isoformat(),
        }

    # ------------------------------------------------------------------ #
    #  RETRAINING REPORT
    # ------------------------------------------------------------------ #

    async def retraining_report(self, session) -> Dict:
        registry    = await self.get_model_registry(session)
        drift_alerts = []

        for model in registry["models"]:
            ticker  = model["ticker"]
            reasons = []
            if model["status"] == "not_trained":
                reasons.append("No models trained yet")
            if model["needs_retraining"] and model["status"] == "trained":
                reasons.append("Models older than 7 days")
            if reasons:
                drift_alerts.append({
                    "ticker":   ticker,
                    "priority": "high" if "No models" in reasons[0] else "medium",
                    "reasons":  reasons,
                    "action":   f'POST /api/v1/predict/train  body: {{"ticker": "{ticker}"}}',
                })

        return {
            "alerts":       drift_alerts,
            "total_alerts": len(drift_alerts),
            "summary": (
                f"{len(drift_alerts)} tickers need attention"
                if drift_alerts else "All models are up to date"
            ),
        }


mlops_service = MLOpsService()