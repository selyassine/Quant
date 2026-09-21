"""
M12 — MLOps & Monitoring Endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.db.database import AsyncSessionLocal
from app.services.mlops.mlops_service import mlops_service

router = APIRouter(tags=["MLOps & Monitoring"])


@router.get("/health")
async def system_health():
    """Overall system health: DB status, data freshness, model files."""
    try:
        async with AsyncSessionLocal() as session:
            return await mlops_service.system_health(session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registry")
async def model_registry():
    """Model registry: which models are trained per ticker."""
    try:
        async with AsyncSessionLocal() as session:
            return await mlops_service.get_model_registry(session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drift/{ticker}")
async def data_drift(ticker: str):
    """
    Data drift detection using PSI (Population Stability Index).
    Compares recent data distribution vs historical baseline.
    """
    try:
        async with AsyncSessionLocal() as session:
            return await mlops_service.detect_data_drift(ticker.upper(), session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accuracy/{ticker}")
async def prediction_accuracy(ticker: str):
    """
    Prediction accuracy metrics: accuracy, precision, recall, F1, confusion matrix.
    """
    try:
        async with AsyncSessionLocal() as session:
            return await mlops_service.prediction_accuracy(ticker.upper(), session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retraining")
async def retraining_report():
    """Which tickers need retraining and why."""
    try:
        async with AsyncSessionLocal() as session:
            return await mlops_service.retraining_report(session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def mlops_dashboard():
    """
    Full MLOps dashboard — health + registry + retraining report in one call.
    """
    try:
        async with AsyncSessionLocal() as session:
            health   = await mlops_service.system_health(session)
            registry = await mlops_service.get_model_registry(session)
            retrain  = await mlops_service.retraining_report(session)
        return {
            "health":   health,
            "registry": registry,
            "retraining": retrain,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
