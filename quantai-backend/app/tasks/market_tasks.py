from app.tasks.celery_app import celery_app
from app.db.database import AsyncSessionLocal
from app.services.data.market_data import market_data_service
from app.db.models.ohlcv import Timeframe
from loguru import logger
import asyncio


def run_async(coro):
    """Run an async coroutine inside a Celery sync task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_ticker_task(self, ticker: str, period: str = "2y", timeframe: str = "1d"):
    """Celery task: collect OHLCV data for a single ticker."""
    logger.info(f"[Task] collect_ticker_task | {ticker} | {period} | {timeframe}")
    tf = Timeframe(timeframe)

    async def _run():
        async with AsyncSessionLocal() as db:
            return await market_data_service.collect_ticker(db, ticker, period, tf)

    try:
        result = run_async(_run())
        logger.info(f"[Task] Done: {result}")
        return result
    except Exception as exc:
        logger.error(f"[Task] Failed for {ticker}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task
def refresh_all_assets():
    """Celery beat task: refresh data for all tracked assets."""
    logger.info("[Beat] refresh_all_assets started")

    async def _run():
        async with AsyncSessionLocal() as db:
            assets = await market_data_service.get_assets(db)
            return [a.ticker for a in assets]

    tickers = run_async(_run())
    for ticker in tickers:
        collect_ticker_task.delay(ticker, "5d", "1d")

    logger.info(f"[Beat] Queued {len(tickers)} tickers for refresh")
    return {"queued": len(tickers)}
