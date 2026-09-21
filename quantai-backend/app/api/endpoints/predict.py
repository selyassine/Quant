"""
Prediction Engine API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from app.db.database import get_db
from app.services.ml.ml_service import ml_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ------------------------------------------------------------------ #
#  Schemas                                                             #
# ------------------------------------------------------------------ #

class TrainRequest(BaseModel):
    ticker: str
    models: Optional[List[str]] = None  # None = train all

class TrainResponse(BaseModel):
    ticker: str
    status: str
    models_trained: List[str] = []
    weights: Dict[str, float] = {}
    message: str = ""

class PredictionResponse(BaseModel):
    ticker: str
    ensemble_direction: str
    ensemble_probability: float
    ensemble_confidence: float
    signal: str
    agreement_score: float
    weights_used: Dict[str, float]
    individual_predictions: Dict[str, Any]

class ModelStatusResponse(BaseModel):
    ticker: str
    lightgbm: bool
    lstm: bool
    transformer: bool
    weights: Dict[str, float] = {}


# ------------------------------------------------------------------ #
#  Endpoints                                                           #
# ------------------------------------------------------------------ #

@router.post("/train", response_model=TrainResponse, tags=["Prediction Engine"])
async def train_model(
    request: TrainRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Train LightGBM + LSTM + Transformer for a ticker.
    Training runs synchronously (can take 1-5 minutes).
    Use /train/async for background training.
    """
    try:
        result = await ml_service.train(
            ticker=request.ticker,
            db=db,
            models=request.models,
        )
        return TrainResponse(
            ticker=request.ticker,
            status="success",
            models_trained=result.get("models_trained", []),
            weights=result.get("weights", {}),
            message=f"Trained {len(result.get('models_trained', []))} models successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Training failed for {request.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train/async", tags=["Prediction Engine"])
async def train_model_async(
    request: TrainRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start model training in background. Returns immediately.
    Poll /status/{ticker} to check progress.
    """
    async def _train():
        try:
            await ml_service.train(ticker=request.ticker, db=db, models=request.models)
        except Exception as e:
            logger.error(f"Async training failed for {request.ticker}: {e}")

    background_tasks.add_task(_train)
    return {
        "ticker": request.ticker,
        "status": "training_started",
        "message": f"Training started for {request.ticker}. Poll GET /predict/status/{request.ticker}",
    }


@router.get("/predict/{ticker}", response_model=PredictionResponse, tags=["Prediction Engine"])
async def predict(
    ticker: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get ensemble prediction for a ticker.
    Requires trained models — call /train first.
    """
    try:
        result = await ml_service.predict(ticker=ticker.upper(), db=db)
        return PredictionResponse(**result)
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{ticker}", response_model=ModelStatusResponse, tags=["Prediction Engine"])
async def model_status(ticker: str):
    """Check if models are trained for a given ticker."""
    result = await ml_service.get_status(ticker=ticker.upper())
    return ModelStatusResponse(**{k: result[k] for k in ModelStatusResponse.model_fields})


@router.get("/status", tags=["Prediction Engine"])
async def all_models_status():
    """List all loaded models and their status."""
    return await ml_service.get_all_status()


@router.get("/predict/batch", tags=["Prediction Engine"])
async def predict_batch(
    tickers: str,  # comma-separated: AAPL,MSFT,NVDA
    db: AsyncSession = Depends(get_db),
):
    """
    Get predictions for multiple tickers at once.
    Example: GET /predict/batch?tickers=AAPL,MSFT,NVDA
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    results = {}

    for ticker in ticker_list:
        try:
            results[ticker] = await ml_service.predict(ticker=ticker, db=db)
        except Exception as e:
            results[ticker] = {"error": str(e)}

    return results
