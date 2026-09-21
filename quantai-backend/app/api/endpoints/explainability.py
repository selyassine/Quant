"""
M10 — Explainable AI API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging

from app.db.database import get_db
from app.services.explainability.shap_service import explainability_service
from app.services.ml.ml_service import ml_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/explain/{ticker}", tags=["Explainable AI"])
async def explain_prediction(
    ticker: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Explain WHY the model made its prediction for a ticker.
    Returns SHAP values, top contributing features, waterfall data,
    and a human-readable explanation.
    
    Requires trained LightGBM model — call POST /predict/train first.
    """
    try:
        ticker = ticker.upper()
        df = await ml_service._load_ohlcv(ticker, db)
        df = ml_service._add_features(df)

        result = explainability_service.explain_prediction(ticker, df)
        return result

    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"SHAP explain failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/importance/{ticker}", tags=["Explainable AI"])
async def feature_importance(ticker: str):
    """
    Get global feature importance for a ticker's model.
    Faster than /explain — uses built-in LightGBM importance.
    Returns top features + category breakdown (momentum, volatility, trend, volume).
    """
    try:
        result = explainability_service.feature_importance_summary(ticker.upper())
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Feature importance failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", tags=["Explainable AI"])
async def explainability_health():
    return {"status": "ok", "method": "SHAP TreeExplainer", "models_supported": ["lightgbm"]}
