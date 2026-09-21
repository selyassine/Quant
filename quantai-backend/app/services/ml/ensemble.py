"""
Ensemble model: combines LightGBM + LSTM + Transformer predictions.
Uses weighted voting with dynamic confidence weighting.
"""
import numpy as np
import pandas as pd
import joblib
import os
from typing import Dict, List, Optional
import logging

from app.services.ml.models.lightgbm_model import LightGBMPredictor
from app.services.ml.models.lstm_model import LSTMPredictor
from app.services.ml.models.transformer_model import TransformerPredictor

logger = logging.getLogger(__name__)

MODELS_DIR = "/app/app/services/ml/saved_models"


class EnsemblePredictor:
    """
    Weighted ensemble of LightGBM + LSTM + Transformer.
    Weights are based on validation AUC during training.
    Default equal weights if not trained.
    """

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.lgbm = LightGBMPredictor(ticker)
        self.lstm = LSTMPredictor(ticker)
        self.transformer = TransformerPredictor(ticker)
        self.weights = {"lightgbm": 1/3, "lstm": 1/3, "transformer": 1/3}
        self.model_metrics: Dict = {}

    # ---------------------------------------------------------------- #

    def train(self, df: pd.DataFrame, models: List[str] = None) -> Dict:
        """
        Train all (or selected) models and compute ensemble weights.
        models: list of ['lightgbm', 'lstm', 'transformer'] — default all
        """
        if models is None:
            models = ["lightgbm", "lstm", "transformer"]

        results = {}
        auc_scores = {}

        if "lightgbm" in models:
            try:
                m = self.lgbm.train(df)
                results["lightgbm"] = m
                auc_scores["lightgbm"] = m["auc_roc"]
                self.lgbm.save()
            except Exception as e:
                logger.error(f"[Ensemble] LightGBM failed: {e}")
                results["lightgbm"] = {"error": str(e)}

        if "lstm" in models:
            try:
                m = self.lstm.train(df)
                results["lstm"] = m
                auc_scores["lstm"] = m["auc_roc"]
                self.lstm.save()
            except Exception as e:
                logger.error(f"[Ensemble] LSTM failed: {e}")
                results["lstm"] = {"error": str(e)}

        if "transformer" in models:
            try:
                m = self.transformer.train(df)
                results["transformer"] = m
                auc_scores["transformer"] = m["auc_roc"]
                self.transformer.save()
            except Exception as e:
                logger.error(f"[Ensemble] Transformer failed: {e}")
                results["transformer"] = {"error": str(e)}

        # Compute softmax weights based on AUC
        if auc_scores:
            total = sum(auc_scores.values())
            self.weights = {k: v / total for k, v in auc_scores.items()}
        
        self.model_metrics = results
        self._save_meta()

        return {
            "ticker": self.ticker,
            "models_trained": list(auc_scores.keys()),
            "weights": self.weights,
            "individual_results": results,
        }

    # ---------------------------------------------------------------- #

    def predict(self, df: pd.DataFrame) -> Dict:
        """Ensemble prediction with weighted vote."""
        predictions = {}
        probas = {}

        # LightGBM
        if self.lgbm.is_trained:
            try:
                p = self.lgbm.predict(df)
                predictions["lightgbm"] = p
                probas["lightgbm"] = p["direction_probability"]
            except Exception as e:
                logger.warning(f"[Ensemble] LightGBM predict failed: {e}")

        # LSTM
        if self.lstm.is_trained:
            try:
                p = self.lstm.predict(df)
                predictions["lstm"] = p
                probas["lstm"] = p["direction_probability"]
            except Exception as e:
                logger.warning(f"[Ensemble] LSTM predict failed: {e}")

        # Transformer
        if self.transformer.is_trained:
            try:
                p = self.transformer.predict(df)
                predictions["transformer"] = p
                probas["transformer"] = p["direction_probability"]
            except Exception as e:
                logger.warning(f"[Ensemble] Transformer predict failed: {e}")

        if not probas:
            raise RuntimeError("No models available for prediction")

        # Weighted average
        weighted_proba = sum(
            probas[m] * self.weights.get(m, 1/3)
            for m in probas
        ) / sum(self.weights.get(m, 1/3) for m in probas)

        # Agreement score (how much models agree)
        proba_values = list(probas.values())
        agreement = 1.0 - np.std(proba_values) * 2  # 1=full agreement, 0=disagree

        direction = "up" if weighted_proba > 0.5 else "down"
        confidence = abs(weighted_proba - 0.5) * 2 * max(0, agreement)

        # Signal strength
        if confidence > 0.6:
            signal = "STRONG_BUY" if direction == "up" else "STRONG_SELL"
        elif confidence > 0.3:
            signal = "BUY" if direction == "up" else "SELL"
        else:
            signal = "NEUTRAL"

        return {
            "ticker": self.ticker,
            "ensemble_direction": direction,
            "ensemble_probability": float(weighted_proba),
            "ensemble_confidence": float(confidence),
            "signal": signal,
            "agreement_score": float(agreement),
            "weights_used": self.weights,
            "individual_predictions": {
                m: {
                    "direction": predictions[m]["direction"],
                    "probability": predictions[m]["direction_probability"],
                    "confidence": predictions[m]["confidence"],
                }
                for m in predictions
            },
        }

    # ---------------------------------------------------------------- #

    def load(self) -> bool:
        """Load all available models."""
        lgbm_ok = self.lgbm.load()
        lstm_ok = self.lstm.load()
        transformer_ok = self.transformer.load()

        meta_path = f"{MODELS_DIR}/ensemble_{self.ticker}_meta.pkl"
        if os.path.exists(meta_path):
            meta = joblib.load(meta_path)
            self.weights = meta.get("weights", self.weights)

        return lgbm_ok or lstm_ok or transformer_ok

    def _save_meta(self):
        os.makedirs(MODELS_DIR, exist_ok=True)
        joblib.dump({
            "ticker": self.ticker,
            "weights": self.weights,
            "model_metrics": self.model_metrics,
        }, f"{MODELS_DIR}/ensemble_{self.ticker}_meta.pkl")

    def get_model_status(self) -> Dict:
        return {
            "ticker": self.ticker,
            "lightgbm": self.lgbm.is_trained,
            "lstm": self.lstm.is_trained,
            "transformer": self.transformer.is_trained,
            "weights": self.weights,
        }
