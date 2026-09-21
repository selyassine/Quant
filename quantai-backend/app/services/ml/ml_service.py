"""
ML Service — orchestrates data loading, feature engineering, and model training/prediction.
"""
import pandas as pd
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import logging

from app.services.ml.ensemble import EnsemblePredictor
from app.services.features.feature_engineering import FeatureEngineeringService

logger = logging.getLogger(__name__)


class MLService:
    def __init__(self):
        self._predictors: Dict[str, EnsemblePredictor] = {}
        self.feature_service = FeatureEngineeringService()

    async def _load_ohlcv(self, ticker: str, db: AsyncSession) -> pd.DataFrame:
        """Load OHLCV data from PostgreSQL into a DataFrame."""
        query = text("""
            SELECT timestamp as date, open, high, low, close, volume
            FROM ohlcv
            WHERE ticker = :ticker
            ORDER BY timestamp ASC
        """)
        result = await db.execute(query, {"ticker": ticker})
        rows = result.fetchall()

        if not rows:
            raise ValueError(f"No OHLCV data found for {ticker}")

        df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
        return df

    def _add_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute technical indicators and append to df."""
        try:
            features_df = self.feature_service.compute_features(df)
            # Merge features back
            df = df.merge(features_df, on="date", how="left", suffixes=("", "_feat"))
        except Exception as e:
            logger.warning(f"Feature engineering failed: {e} — using raw OHLCV only")
        return df

    # ---------------------------------------------------------------- #

    async def train(
        self,
        ticker: str,
        db: AsyncSession,
        models: Optional[List[str]] = None,
    ) -> Dict:
        """Full training pipeline for a ticker."""
        logger.info(f"[MLService] Starting training for {ticker}")

        df = await self._load_ohlcv(ticker, db)
        df = self._add_features(df)

        if len(df) < 100:
            raise ValueError(f"Insufficient data for {ticker}: {len(df)} rows (need 100+)")

        predictor = EnsemblePredictor(ticker)
        result = predictor.train(df, models=models)

        self._predictors[ticker] = predictor
        logger.info(f"[MLService] Training complete for {ticker}")
        return result

    async def predict(self, ticker: str, db: AsyncSession) -> Dict:
        """Generate ensemble prediction for a ticker."""
        # Try cache first
        if ticker not in self._predictors:
            predictor = EnsemblePredictor(ticker)
            loaded = predictor.load()
            if not loaded:
                raise RuntimeError(f"No trained model found for {ticker}. Train first.")
            self._predictors[ticker] = predictor

        df = await self._load_ohlcv(ticker, db)
        df = self._add_features(df)

        return self._predictors[ticker].predict(df)

    async def get_status(self, ticker: str) -> Dict:
        """Get model status for a ticker."""
        if ticker in self._predictors:
            return self._predictors[ticker].get_model_status()

        predictor = EnsemblePredictor(ticker)
        loaded = predictor.load()
        if loaded:
            self._predictors[ticker] = predictor
            return predictor.get_model_status()

        return {
            "ticker": ticker,
            "lightgbm": False,
            "lstm": False,
            "transformer": False,
            "weights": {},
            "message": "No trained models found. Call /train first.",
        }

    async def get_all_status(self) -> List[Dict]:
        """Status of all loaded predictors."""
        return [p.get_model_status() for p in self._predictors.values()]


# Singleton
ml_service = MLService()