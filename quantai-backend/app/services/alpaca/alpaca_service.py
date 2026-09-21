"""
Alpaca Market Data Service
Real-time and historical market data via Alpaca API.
Replaces yfinance for live data.
"""
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
from app.core.config import settings


class AlpacaService:

    def __init__(self):
        self.base_url  = settings.alpaca_base_url
        self.data_url  = "https://data.alpaca.markets/v2"
        self.headers   = {
            "APCA-API-KEY-ID":     settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
            "Content-Type":        "application/json",
        }

    # ── Account ───────────────────────────────────────────────────────
    async def get_account(self) -> Dict:
        """Get paper trading account info."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/account", headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json()

    # ── Latest price ──────────────────────────────────────────────────
    async def get_latest_price(self, ticker: str) -> Dict:
        """Get latest real-time price for a ticker."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.data_url}/stocks/{ticker}/trades/latest",
                headers=self.headers,
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                trade = data.get("trade", {})
                return {
                    "ticker": ticker,
                    "price":  trade.get("p", 0),
                    "size":   trade.get("s", 0),
                    "time":   trade.get("t", ""),
                    "source": "alpaca_live",
                }
            # Fallback to latest bar
            return await self.get_latest_bar(ticker)

    async def get_latest_bar(self, ticker: str) -> Dict:
        """Get latest OHLCV bar."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.data_url}/stocks/{ticker}/bars/latest",
                headers=self.headers,
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            bar  = data.get("bar", {})
            return {
                "ticker": ticker,
                "price":  bar.get("c", 0),
                "open":   bar.get("o", 0),
                "high":   bar.get("h", 0),
                "low":    bar.get("l", 0),
                "close":  bar.get("c", 0),
                "volume": bar.get("v", 0),
                "time":   bar.get("t", ""),
                "source": "alpaca_bar",
            }

    async def get_multiple_prices(self, tickers: List[str]) -> Dict[str, float]:
        """Get latest prices for multiple tickers at once."""
        symbols = ",".join(tickers)
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.data_url}/stocks/bars/latest",
                headers=self.headers,
                params={"symbols": symbols},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                bars = data.get("bars", {})
                return {
                    ticker: bars[ticker]["c"]
                    for ticker in tickers
                    if ticker in bars
                }
        return {}

    # ── Historical bars ───────────────────────────────────────────────
    async def get_historical_bars(
        self,
        ticker: str,
        timeframe: str = "1Day",
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict]:
        """Get historical OHLCV bars from Alpaca."""
        if not start:
            start = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
        if not end:
            end = datetime.now().strftime("%Y-%m-%d")

        params = {
            "timeframe": timeframe,
            "start":     start,
            "end":       end,
            "limit":     limit,
            "adjustment": "all",
        }

        bars = []
        async with httpx.AsyncClient() as client:
            while True:
                r = await client.get(
                    f"{self.data_url}/stocks/{ticker}/bars",
                    headers=self.headers,
                    params=params,
                    timeout=30,
                )
                r.raise_for_status()
                data   = r.json()
                new    = data.get("bars", [])
                bars.extend(new)

                next_token = data.get("next_page_token")
                if not next_token or len(bars) >= limit:
                    break
                params["page_token"] = next_token

        return [
            {
                "timestamp": b["t"][:10],
                "open":   b["o"],
                "high":   b["h"],
                "low":    b["l"],
                "close":  b["c"],
                "volume": b["v"],
            }
            for b in bars
        ]

    # ── Orders ────────────────────────────────────────────────────────
    async def place_order(
        self,
        ticker: str,
        side: str,
        qty: float,
        order_type: str = "market",
    ) -> Dict:
        """Place a paper trading order via Alpaca."""
        payload = {
            "symbol":        ticker.upper(),
            "qty":           str(qty),
            "side":          side.lower(),
            "type":          order_type,
            "time_in_force": "day",
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/orders",
                headers=self.headers,
                json=payload,
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            return {
                "order_id":   data.get("id"),
                "ticker":     data.get("symbol"),
                "side":       data.get("side"),
                "qty":        float(data.get("qty", 0)),
                "status":     data.get("status"),
                "type":       data.get("type"),
                "created_at": data.get("created_at"),
            }

    async def get_orders(self, status: str = "all", limit: int = 50) -> List[Dict]:
        """Get orders from Alpaca paper account."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/orders",
                headers=self.headers,
                params={"status": status, "limit": limit},
                timeout=10,
            )
            r.raise_for_status()
            orders = r.json()
            return [
                {
                    "order_id":   o.get("id"),
                    "ticker":     o.get("symbol"),
                    "side":       o.get("side"),
                    "qty":        float(o.get("qty", 0)),
                    "filled_qty": float(o.get("filled_qty", 0)),
                    "fill_price": float(o.get("filled_avg_price") or 0),
                    "status":     o.get("status"),
                    "created_at": o.get("created_at", "")[:19],
                }
                for o in orders
            ]

    async def get_positions(self) -> List[Dict]:
        """Get open positions from Alpaca paper account."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/positions",
                headers=self.headers,
                timeout=10,
            )
            r.raise_for_status()
            positions = r.json()
            return [
                {
                    "ticker":             p.get("symbol"),
                    "qty":                float(p.get("qty", 0)),
                    "avg_entry_price":    float(p.get("avg_entry_price", 0)),
                    "current_price":      float(p.get("current_price", 0)),
                    "market_value":       float(p.get("market_value", 0)),
                    "unrealized_pl":      float(p.get("unrealized_pl", 0)),
                    "unrealized_plpc":    float(p.get("unrealized_plpc", 0)) * 100,
                    "change_today":       float(p.get("change_today", 0)) * 100,
                }
                for p in positions
            ]

    async def get_portfolio_history(self, period: str = "1M") -> Dict:
        """Get portfolio value history."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/account/portfolio/history",
                headers=self.headers,
                params={"period": period, "timeframe": "1D"},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            timestamps   = data.get("timestamp", [])
            equity       = data.get("equity", [])
            profit_loss  = data.get("profit_loss", [])
            return {
                "equity_curve": [
                    {
                        "date":        datetime.fromtimestamp(t).strftime("%Y-%m-%d"),
                        "value":       round(e, 2),
                        "profit_loss": round(pl, 2),
                    }
                    for t, e, pl in zip(timestamps, equity, profit_loss)
                ],
                "base_value": data.get("base_value", 100_000),
            }


alpaca_service = AlpacaService()
