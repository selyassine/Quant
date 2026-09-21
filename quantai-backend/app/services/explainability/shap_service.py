"""
M10 — Explainable AI
SHAP values + feature importance for LightGBM, LSTM, Transformer.
Explains WHY the model made a specific prediction.
"""
import numpy as np
import pandas as pd
import shap
import joblib
import os
from typing import Dict, List, Optional
import logging

from app.services.ml.models.lightgbm_model import LightGBMPredictor

logger = logging.getLogger(__name__)

MODELS_DIR = "/app/app/services/ml/saved_models"


class ExplainabilityService:
    """
    Provides SHAP-based explanations for ML predictions.
    
    Outputs:
    - Global feature importance (which features matter most overall)
    - Local SHAP values (why THIS specific prediction was made)
    - Feature contribution breakdown (positive vs negative contributors)
    - Human-readable explanation text
    """

    def __init__(self):
        self._explainers: Dict[str, shap.TreeExplainer] = {}

    # ---------------------------------------------------------------- #

    def _get_lgbm_explainer(self, ticker: str) -> Optional[shap.TreeExplainer]:
        """Load or create SHAP TreeExplainer for LightGBM model."""
        if ticker in self._explainers:
            return self._explainers[ticker]

        path = f"{MODELS_DIR}/lgbm_{ticker}.pkl"
        if not os.path.exists(path):
            return None

        data = joblib.load(path)
        classifier = data["classifier"]
        explainer = shap.TreeExplainer(classifier)
        self._explainers[ticker] = explainer
        return explainer

    # ---------------------------------------------------------------- #

    def explain_prediction(self, ticker: str, df: pd.DataFrame) -> Dict:
        """
        Generate SHAP explanation for the latest prediction.
        Returns feature contributions, importance, and human-readable summary.
        """
        predictor = LightGBMPredictor(ticker)
        if not predictor.load():
            raise RuntimeError(f"No LightGBM model found for {ticker}. Train first.")

        # Get features
        X, _, _ = predictor.prepare_features(df)
        X_last = X.tail(1)
        X_scaled = predictor.scaler.transform(X_last)
        X_scaled_df = pd.DataFrame(X_scaled, columns=predictor.feature_cols)

        # Get prediction
        direction_proba = float(predictor.classifier.predict_proba(X_scaled)[0][1])
        direction = "UP" if direction_proba > 0.5 else "DOWN"
        predicted_return = float(predictor.regressor.predict(X_scaled)[0])

        # SHAP values
        explainer = self._get_lgbm_explainer(ticker)
        if explainer is None:
            raise RuntimeError(f"Could not create explainer for {ticker}")

        shap_values = explainer.shap_values(X_scaled_df)

        # For binary classifier, shap_values is list [class0, class1]
        if isinstance(shap_values, list):
            shap_vals = shap_values[1][0]  # class 1 (UP) SHAP values for last row
        else:
            shap_vals = shap_values[0]

        # Build feature contributions
        feature_contributions = []
        for feat, shap_val, feat_val in zip(
            predictor.feature_cols,
            shap_vals,
            X_scaled_df.iloc[0].values
        ):
            feature_contributions.append({
                "feature": feat,
                "shap_value": float(shap_val),
                "feature_value": float(feat_val),
                "impact": "positive" if shap_val > 0 else "negative",
            })

        # Sort by absolute SHAP value
        feature_contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        top_contributors = feature_contributions[:15]

        # Global feature importance
        importance = dict(zip(
            predictor.feature_cols,
            predictor.classifier.feature_importances_.tolist()
        ))
        global_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:15]

        # Base value (expected model output)
        base_value = float(explainer.expected_value[1] if isinstance(explainer.expected_value, list)
                          else explainer.expected_value)

        # Human-readable explanation
        top_positive = [f for f in top_contributors if f["shap_value"] > 0][:3]
        top_negative = [f for f in top_contributors if f["shap_value"] < 0][:3]

        explanation_text = self._generate_explanation(
            ticker, direction, direction_proba, predicted_return,
            top_positive, top_negative
        )

        # SHAP waterfall data (for chart)
        waterfall = self._build_waterfall(base_value, top_contributors[:10])

        return {
            "ticker": ticker,
            "prediction": {
                "direction": direction,
                "probability": float(round(direction_proba * 100, 2)),
                "predicted_return_pct": float(round(predicted_return * 100, 2)),
            },
            "explanation": explanation_text,
            "top_contributors": top_contributors[:10],
            "global_feature_importance": [
                {"feature": k, "importance": float(round(v, 4))}
                for k, v in global_importance
            ],
            "base_value": float(round(base_value, 4)),
            "waterfall": waterfall,
            "model": "lightgbm",
            "num_features_analyzed": len(predictor.feature_cols),
        }

    # ---------------------------------------------------------------- #

    def _generate_explanation(
        self,
        ticker: str,
        direction: str,
        proba: float,
        predicted_return: float,
        top_positive: List[Dict],
        top_negative: List[Dict],
    ) -> str:
        """Generate human-readable explanation."""
        conf = abs(proba - 0.5) * 2 * 100

        lines = []
        lines.append(f"The model predicts {ticker} will go {direction} with {proba*100:.1f}% probability (confidence: {conf:.1f}%).")
        lines.append(f"Expected return: {predicted_return*100:+.2f}%")
        lines.append("")

        if top_positive:
            lines.append("Main reasons supporting this prediction:")
            for f in top_positive:
                feat_name = f["feature"].replace("_", " ").upper()
                lines.append(f"  + {feat_name}: contributing +{abs(f['shap_value']):.4f} to the score")

        if top_negative:
            lines.append("")
            lines.append("Factors working against this prediction:")
            for f in top_negative:
                feat_name = f["feature"].replace("_", " ").upper()
                lines.append(f"  - {feat_name}: contributing -{abs(f['shap_value']):.4f} to the score")

        return "\n".join(lines)

    def _build_waterfall(self, base_value: float, contributors: List[Dict]) -> List[Dict]:
        """Build waterfall chart data."""
        waterfall = []
        running = base_value

        waterfall.append({
            "label": "Base value",
            "value": float(round(base_value, 4)),
            "cumulative": float(round(running, 4)),
            "type": "base",
        })

        for c in contributors:
            running += c["shap_value"]
            waterfall.append({
                "label": c["feature"],
                "value": float(round(c["shap_value"], 4)),
                "cumulative": float(round(running, 4)),
                "type": c["impact"],
            })

        return waterfall

    # ---------------------------------------------------------------- #

    def feature_importance_summary(self, ticker: str) -> Dict:
        """
        Get global feature importance without computing SHAP (faster).
        Uses LightGBM built-in feature importance.
        """
        predictor = LightGBMPredictor(ticker)
        if not predictor.load():
            raise RuntimeError(f"No LightGBM model found for {ticker}")

        importance = dict(zip(
            predictor.feature_cols,
            predictor.classifier.feature_importances_.tolist()
        ))
        sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

        # Group by category
        categories = {
            "momentum": ["rsi", "macd", "return", "momentum"],
            "volatility": ["atr", "bb_", "std_", "vol"],
            "trend": ["ema", "sma", "adx", "cci"],
            "volume": ["obv", "mfi", "vol_"],
            "statistical": ["skew", "kurt", "lag"],
        }

        categorized = {}
        for feat, imp in sorted_importance:
            category = "other"
            for cat, keywords in categories.items():
                if any(feat.lower().startswith(k) for k in keywords):
                    category = cat
                    break
            if category not in categorized:
                categorized[category] = []
            categorized[category].append({"feature": feat, "importance": float(round(imp, 4))})

        category_totals = {
            cat: float(round(sum(f["importance"] for f in feats), 4))
            for cat, feats in categorized.items()
        }

        return {
            "ticker": ticker,
            "top_features": [
                {"feature": k, "importance": float(round(v, 4))}
                for k, v in sorted_importance[:20]
            ],
            "category_breakdown": category_totals,
            "categorized_features": categorized,
            "total_features": len(predictor.feature_cols),
        }


# Singleton
explainability_service = ExplainabilityService()
