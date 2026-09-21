"""
Real-time price streaming via Server-Sent Events (SSE).
Frontend connects and receives live prices every 2 seconds.
"""
import asyncio
import json
from typing import AsyncGenerator, List
from loguru import logger
from app.services.alpaca.alpaca_service import alpaca_service

DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "SPY", "QQQ"]


async def price_stream(tickers: List[str] = None) -> AsyncGenerator[str, None]:
    """
    Async generator that yields live prices as SSE events.
    Frontend: EventSource('/api/v1/realtime/stream')
    """
    if not tickers:
        tickers = DEFAULT_TICKERS

    logger.info(f"[SSE] Starting price stream for {tickers}")

    while True:
        try:
            prices = await alpaca_service.get_multiple_prices(tickers)

            payload = {
                "type":      "prices",
                "timestamp": asyncio.get_event_loop().time(),
                "data":      prices,
            }

            yield f"data: {json.dumps(payload)}\n\n"

        except Exception as e:
            logger.warning(f"[SSE] Price fetch error: {e}")
            error_payload = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_payload)}\n\n"

        await asyncio.sleep(2)  # update every 2 seconds
