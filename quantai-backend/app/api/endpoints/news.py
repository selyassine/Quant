"""
M8 — News Intelligence API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from app.services.news.news_collector import news_collector
from app.services.news.sentiment_service import sentiment_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ticker/{ticker}", tags=["News Intelligence"])
async def get_ticker_news(
    ticker: str,
    limit: int = Query(20, ge=1, le=50),
):
    """
    Get latest news + sentiment analysis for a ticker.
    Returns articles with sentiment scores and impact estimates.
    """
    try:
        ticker = ticker.upper()
        articles = await news_collector.collect_for_ticker(ticker, limit=limit)

        if not articles:
            return {
                "ticker": ticker,
                "articles": [],
                "aggregate": sentiment_service.aggregate_sentiment([]),
                "message": "No news found for this ticker",
            }

        enriched = sentiment_service.analyze_articles(articles)
        aggregate = sentiment_service.aggregate_sentiment(enriched)

        return {
            "ticker": ticker,
            "articles": enriched,
            "aggregate": aggregate,
        }

    except Exception as e:
        logger.error(f"News fetch failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market", tags=["News Intelligence"])
async def get_market_news(limit: int = Query(30, ge=1, le=50)):
    """Get general market news with sentiment analysis."""
    try:
        articles = await news_collector.collect_general(limit=limit)
        enriched = sentiment_service.analyze_articles(articles)
        aggregate = sentiment_service.aggregate_sentiment(enriched)

        return {
            "articles": enriched,
            "aggregate": aggregate,
        }
    except Exception as e:
        logger.error(f"Market news fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment/{ticker}", tags=["News Intelligence"])
async def get_sentiment_only(ticker: str):
    """
    Get just the sentiment summary for a ticker (fast).
    Returns: overall sentiment, score, positive/negative/neutral %.
    """
    try:
        ticker = ticker.upper()
        articles = await news_collector.collect_for_ticker(ticker, limit=10)
        enriched = sentiment_service.analyze_articles(articles)
        aggregate = sentiment_service.aggregate_sentiment(enriched)
        return {"ticker": ticker, **aggregate}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", tags=["News Intelligence"])
async def news_health():
    return {
        "status": "ok",
        "sentiment_model": "FinBERT (ProsusAI/finbert) with rule-based fallback",
        "sources": ["Yahoo Finance RSS", "Reuters", "MarketWatch"],
    }
