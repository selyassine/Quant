"""
M11 — AI Financial Assistant Endpoints
Groq LLM + RAG + 5 financial tools
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

from app.services.assistant.assistant_service import AssistantService
from app.services.rag.rag_service import rag_service

router = APIRouter(tags=["AI Assistant"])

# Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
def get_assistant() -> AssistantService:
    return AssistantService(api_key=GROQ_API_KEY)


# ------------------------------------------------------------------ #
#  SCHEMAS
# ------------------------------------------------------------------ #

class MessageItem(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str = Field(description="User message")
    history: List[MessageItem] = Field(default=[], description="Previous messages")

class QuickAnalysisRequest(BaseModel):
    ticker: str = Field(default="AAPL")

class PortfolioAdviceRequest(BaseModel):
    tickers: List[str] = Field(default=["AAPL", "MSFT", "NVDA", "SPY"])

class IndexRequest(BaseModel):
    ticker: str
    price: float
    change_pct: float
    volume: int = 0


# ------------------------------------------------------------------ #
#  ENDPOINTS
# ------------------------------------------------------------------ #

@router.post("/chat")
async def chat(req: ChatRequest):
    """
    **Main chat endpoint** — Groq LLM + RAG + 5 financial tools.

    The assistant automatically:
    - Detects which tool to use based on the question
    - Calls prediction, portfolio, backtest, news, or SHAP APIs
    - Returns a comprehensive data-driven response

    Example questions:
    - "Should I buy AAPL right now?"
    - "Optimize a portfolio with MSFT, NVDA, and SPY"
    - "What's the best strategy for TSLA?"
    - "Why does the model predict NVDA will go up?"
    - "What's the latest news on GOOGL?"
    """
    try:
        assistant = get_assistant()
        history = [{"role": m.role, "content": m.content} for m in req.history]
        result = await assistant.chat(history, req.message)
        return {
            "response": result["response"],
            "tools_used": result["tools_used"],
            "model": "llama-3.3-70b-versatile",
            "rag_enabled": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def quick_analysis(req: QuickAnalysisRequest):
    """
    **Quick analysis** of a single ticker.
    Combines prediction + news + SHAP explanation.
    """
    try:
        assistant = get_assistant()
        result = await assistant.quick_analysis(req.ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio-advice")
async def portfolio_advice(req: PortfolioAdviceRequest):
    """
    **Portfolio advice** for a list of tickers.
    Runs Markowitz optimization and explains the allocation.
    """
    try:
        assistant = get_assistant()
        result = await assistant.portfolio_advice(req.tickers)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/index")
async def index_market_data(req: IndexRequest):
    """Index market data into the RAG vector store."""
    try:
        rag_service.add_market_context(
            req.ticker, req.price, req.change_pct, req.volume
        )
        return {"status": "indexed", "ticker": req.ticker, "total": rag_service.index_count()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag/status")
async def rag_status():
    """Get RAG vector store status."""
    return {
        "indexed_documents": rag_service.index_count(),
        "status": "active" if rag_service.index_count() > 0 else "empty",
    }


@router.get("/health")
async def assistant_health():
    return {
        "status": "ok",
        "module": "AI Assistant M11",
        "llm": "Groq llama-3.3-70b-versatile",
        "rag": "ChromaDB",
        "tools": 5,
    }