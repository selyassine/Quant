"""
QuantAI — Portfolio Endpoints
Phase 3 : Markowitz, Black-Litterman, Risk Analysis, Efficient Frontier
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from app.services.portfolio.portfolio_service import portfolio_service

router = APIRouter(tags=["Portfolio Management"])


# ------------------------------------------------------------------ #
#  SCHÉMAS
# ------------------------------------------------------------------ #

class MarkowitzRequest(BaseModel):
    tickers: List[str] = Field(
        default=["AAPL", "MSFT", "NVDA", "GOOGL", "SPY"],
        description="Liste des tickers à optimiser"
    )
    objective: str = Field(
        default="sharpe",
        description="Objectif : 'sharpe' | 'min_vol' | 'max_return'"
    )
    max_weight: float = Field(
        default=0.4,
        description="Poids maximum par actif (0.4 = 40%)"
    )
    days: int = Field(
        default=252,
        description="Nombre de jours historiques (252 = 1 an)"
    )


class ViewItem(BaseModel):
    type: str = Field(description="'absolute' ou 'relative'")
    ticker: Optional[str] = Field(default=None, description="Pour vue absolue")
    long: Optional[str] = Field(default=None, description="Pour vue relative")
    short: Optional[str] = Field(default=None, description="Pour vue relative")
    returnVal: float = Field(alias="return", description="Rendement attendu (0.15 = 15%)")
    confidence: float = Field(default=0.7, description="Confiance 0-1")

    class Config:
        populate_by_name = True


class BlackLittermanRequest(BaseModel):
    tickers: List[str] = Field(
        default=["AAPL", "MSFT", "NVDA", "GOOGL", "SPY"]
    )
    views: Optional[List[Dict]] = Field(
        default=None,
        description="Vues du trader (optionnel)"
    )
    max_weight: float = Field(default=0.4)
    days: int = Field(default=252)


class AnalyzeRequest(BaseModel):
    weights: Dict[str, float] = Field(
        default={"AAPL": 0.3, "MSFT": 0.25, "NVDA": 0.25, "SPY": 0.2},
        description="Poids du portfolio actuel"
    )
    benchmark: Optional[str] = Field(default="SPY")
    days: int = Field(default=252)


class FrontierRequest(BaseModel):
    tickers: List[str] = Field(
        default=["AAPL", "MSFT", "NVDA", "GOOGL"]
    )
    n_points: int = Field(default=30)
    days: int = Field(default=252)


# ------------------------------------------------------------------ #
#  ENDPOINTS
# ------------------------------------------------------------------ #

@router.post("/optimize/markowitz")
async def optimize_markowitz(req: MarkowitzRequest):
    """
    Optimise un portfolio avec la méthode Markowitz.

    - **sharpe** : maximise le Sharpe Ratio (meilleur rapport rendement/risque)
    - **min_vol** : minimise la volatilité (portfolio le plus stable)
    - **max_return** : maximise le rendement (plus risqué)
    """
    try:
        result = await portfolio_service.optimize_markowitz(
            tickers=req.tickers,
            objective=req.objective,
            max_weight=req.max_weight,
            days=req.days,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize/black-litterman")
async def optimize_black_litterman(req: BlackLittermanRequest):
    """
    Optimise un portfolio avec Black-Litterman.

    Permet d'intégrer des **vues du trader** sur les actifs.

    Exemple de vues :
    ```json
    [
      {"type": "absolute", "ticker": "AAPL", "return": 0.15, "confidence": 0.8},
      {"type": "relative", "long": "MSFT", "short": "GOOGL", "return": 0.05, "confidence": 0.6}
    ]
    ```
    """
    try:
        result = await portfolio_service.optimize_black_litterman(
            tickers=req.tickers,
            views=req.views,
            max_weight=req.max_weight,
            days=req.days,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_portfolio(req: AnalyzeRequest):
    """
    Analyse un portfolio existant.

    Calcule toutes les métriques de risque :
    - Sharpe, Sortino, Calmar ratios
    - VaR 95% et 99%, CVaR
    - Max Drawdown, volatilité annualisée
    - Beta et Alpha vs benchmark
    """
    try:
        result = await portfolio_service.analyze_portfolio(
            weights=req.weights,
            benchmark_ticker=req.benchmark,
            days=req.days,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/frontier")
async def efficient_frontier(req: FrontierRequest):
    """
    Calcule la frontière efficiente (courbe rendement/risque).

    Retourne N points sur la frontière pour afficher le graphique.
    """
    try:
        result = await portfolio_service.efficient_frontier(
            tickers=req.tickers,
            n_points=req.n_points,
            days=req.days,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def portfolio_health():
    return {"status": "ok", "module": "Portfolio Management Phase 3"}
