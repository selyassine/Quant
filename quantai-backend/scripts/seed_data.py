"""
Seed script: collect initial data for popular tickers.
Run: docker exec quantai_api python scripts/seed_data.py
"""
import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import AsyncSessionLocal, init_db
from app.services.data.market_data import market_data_service
from loguru import logger

# Reduced list — collect a few tickers to test, add more later
TICKERS = [
    "AAPL", "MSFT", "NVDA", "TSLA",
    "SPY", "QQQ",
    "BTC-USD", "ETH-USD",
]

async def main():
    await init_db()
    success, failed = [], []

    async with AsyncSessionLocal() as db:
        for i, ticker in enumerate(TICKERS):
            try:
                result = await market_data_service.collect_ticker(db, ticker, period="2y")
                logger.success(f"✓ {ticker}: {result['rows_inserted']} rows — {result['date_from'][:10]} → {result['date_to'][:10]}")
                success.append(ticker)
            except Exception as e:
                logger.error(f"✗ {ticker}: {e}")
                failed.append(ticker)

            # Pause between tickers to avoid rate limiting
            if i < len(TICKERS) - 1:
                wait = 3
                logger.info(f"Waiting {wait}s before next ticker...")
                await asyncio.sleep(wait)

    logger.info(f"\n{'='*40}")
    logger.info(f"Done: {len(success)} success, {len(failed)} failed")
    if success:
        logger.success(f"✓ {', '.join(success)}")
    if failed:
        logger.warning(f"✗ {', '.join(failed)} — retry individually with:")
        for t in failed:
            logger.warning(f"  curl -X POST 'http://localhost:8000/api/v1/market/collect/sync/{t}?period=2y'")

if __name__ == "__main__":
    asyncio.run(main())