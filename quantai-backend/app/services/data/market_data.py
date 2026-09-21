import yfinance as yf
import pandas as pd
import time
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
from loguru import logger
from typing import Optional

from app.db.models.asset import Asset, AssetType
from app.db.models.ohlcv import OHLCV, Timeframe


ASSET_TYPE_MAP = {
    "EQUITY": AssetType.STOCK,
    "ETF": AssetType.ETF,
    "CRYPTOCURRENCY": AssetType.CRYPTO,
    "CURRENCY": AssetType.FOREX,
    "INDEX": AssetType.INDEX,
    "FUTURE": AssetType.COMMODITY,
}


class MarketDataService:

    async def collect_ticker(
        self,
        db: AsyncSession,
        ticker: str,
        period: str = "2y",
        timeframe: Timeframe = Timeframe.D1,
    ) -> dict:
        ticker = ticker.upper().strip()
        logger.info(f"Collecting {ticker} | period={period} | tf={timeframe}")

        try:
            yf_ticker = yf.Ticker(ticker)

            # --- Download OHLCV first (more reliable than .info) ---
            df = yf_ticker.history(
                period=period,
                interval=timeframe.value,
                auto_adjust=False,
                actions=True,
            )

            if df.empty:
                raise ValueError(f"No OHLCV data returned for {ticker}")

            df = self._clean_ohlcv(df)
            logger.info(f"Downloaded {len(df)} rows for {ticker}")

            # --- Try to get metadata, but don't fail if rate-limited ---
            info = {}
            try:
                time.sleep(random.uniform(1.0, 2.5))
                info = yf_ticker.info or {}
            except Exception as e:
                logger.warning(f"Could not fetch info for {ticker} (rate limited?): {e}")

            # --- Upsert Asset ---
            asset = await self._upsert_asset(db, ticker, info, df)
            logger.info(f"Asset upserted: {asset.name}")

            # --- Store OHLCV ---
            rows_inserted = await self._store_ohlcv(db, ticker, timeframe, df)
            await db.commit()

            return {
                "ticker": ticker,
                "rows_inserted": rows_inserted,
                "date_from": str(df.index.min()),
                "date_to": str(df.index.max()),
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Error collecting {ticker}: {e}")
            raise

    async def _upsert_asset(self, db: AsyncSession, ticker: str, info: dict, df: pd.DataFrame = None) -> Asset:
        asset_type_raw = info.get("quoteType", "EQUITY")
        asset_type = ASSET_TYPE_MAP.get(asset_type_raw, AssetType.STOCK)

        # Detect crypto from ticker pattern if info is empty
        if not info and "-USD" in ticker:
            asset_type = AssetType.CRYPTO
        if not info and ticker.startswith("^"):
            asset_type = AssetType.INDEX

        stmt = select(Asset).where(Asset.ticker == ticker)
        result = await db.execute(stmt)
        asset = result.scalar_one_or_none()

        name = info.get("longName") or info.get("shortName") or ticker

        if asset is None:
            asset = Asset(
                ticker=ticker,
                name=name,
                asset_type=asset_type,
                exchange=info.get("exchange"),
                currency=info.get("currency", "USD"),
                sector=info.get("sector"),
                industry=info.get("industry"),
                market_cap=info.get("marketCap"),
            )
            db.add(asset)
        else:
            asset.name = name
            asset.market_cap = info.get("marketCap") or asset.market_cap
            asset.last_updated = datetime.utcnow()

        await db.flush()
        return asset

    def _clean_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Remove timezone info
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.index.name = "timestamp"
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df = df.dropna(subset=["open", "high", "low", "close"])
        df = df[(df["open"] > 0) & (df["close"] > 0)]
        df = df[~df.index.duplicated(keep="last")]
        return df.sort_index()

    async def _store_ohlcv(self, db: AsyncSession, ticker: str, timeframe: Timeframe, df: pd.DataFrame) -> int:
        records = []
        for ts, row in df.iterrows():
            records.append({
                "ticker": ticker,
                "timeframe": timeframe,
                "timestamp": ts,
                "open": float(row.get("open", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "close": float(row.get("close", 0)),
                "volume": int(row.get("volume", 0)) if pd.notna(row.get("volume")) else None,
                "adj_close": float(row["adj_close"]) if "adj_close" in row and pd.notna(row["adj_close"]) else None,
                "dividends": float(row.get("dividends", 0)) if pd.notna(row.get("dividends", 0)) else 0.0,
                "stock_splits": float(row.get("stock_splits", 0)) if pd.notna(row.get("stock_splits", 0)) else 0.0,
            })

        if not records:
            return 0

        stmt = insert(OHLCV).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["ticker", "timeframe", "timestamp"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "adj_close": stmt.excluded.adj_close,
            }
        )
        await db.execute(stmt)
        return len(records)

    async def get_ohlcv(
        self,
        db: AsyncSession,
        ticker: str,
        timeframe: Timeframe = Timeframe.D1,
        limit: int = 500,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> list[OHLCV]:
        stmt = (
            select(OHLCV)
            .where(OHLCV.ticker == ticker.upper())
            .where(OHLCV.timeframe == timeframe)
            .order_by(OHLCV.timestamp.desc())
        )
        if date_from:
            stmt = stmt.where(OHLCV.timestamp >= date_from)
        if date_to:
            stmt = stmt.where(OHLCV.timestamp <= date_to)
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_assets(self, db: AsyncSession) -> list[Asset]:
        result = await db.execute(select(Asset).where(Asset.is_active == True))
        return result.scalars().all()


market_data_service = MarketDataService()