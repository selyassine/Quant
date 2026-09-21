"""
Run INSIDE Docker after copying CSVs.
Imports market_data_csv/*.csv into PostgreSQL.

Usage:
  docker cp scripts/market_data_csv quantai_api:/app/scripts/market_data_csv
  docker exec quantai_api python scripts/import_csv.py
"""
import asyncio
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import AsyncSessionLocal, init_db
from app.db.models.asset import Asset, AssetType
from app.db.models.ohlcv import OHLCV, Timeframe
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
from loguru import logger

CSV_DIR = os.path.join(os.path.dirname(__file__), "market_data_csv")

ASSET_TYPE_HINTS = {
    "BTC_USD": AssetType.CRYPTO,
    "ETH_USD": AssetType.CRYPTO,
    "SPY": AssetType.ETF,
    "QQQ": AssetType.ETF,
}

async def import_csv(db, csv_path: str):
    filename = os.path.basename(csv_path)
    ticker_key = filename.replace(".csv", "").upper()
    ticker = ticker_key.replace("_", "-") if "USD" in ticker_key else ticker_key

    df = pd.read_csv(csv_path, index_col="timestamp", parse_dates=True)
    if df.empty:
        logger.warning(f"Empty CSV: {filename}")
        return

    # Upsert asset
    asset_type = ASSET_TYPE_HINTS.get(ticker_key, AssetType.STOCK)
    stmt = select(Asset).where(Asset.ticker == ticker)
    result = await db.execute(stmt)
    asset = result.scalar_one_or_none()
    if asset is None:
        asset = Asset(
            ticker=ticker,
            name=ticker,
            asset_type=asset_type,
            currency="USD",
        )
        db.add(asset)
        await db.flush()

    # Build records
    records = []
    for ts, row in df.iterrows():
        if hasattr(ts, 'tz_localize'):
            ts = ts.tz_localize(None) if ts.tzinfo else ts
        records.append({
            "ticker": ticker,
            "timeframe": Timeframe.D1,
            "timestamp": ts,
            "open": float(row.get("open", 0)),
            "high": float(row.get("high", 0)),
            "low": float(row.get("low", 0)),
            "close": float(row.get("close", 0)),
            "volume": int(row["volume"]) if pd.notna(row.get("volume")) else None,
            "adj_close": float(row["adj_close"]) if "adj_close" in row and pd.notna(row["adj_close"]) else None,
            "dividends": float(row.get("dividends", 0)) if pd.notna(row.get("dividends", 0)) else 0.0,
            "stock_splits": float(row.get("stock_splits", 0)) if pd.notna(row.get("stock_splits", 0)) else 0.0,
        })

    stmt = insert(OHLCV).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["ticker", "timeframe", "timestamp"],
        set_={"close": stmt.excluded.close, "volume": stmt.excluded.volume},
    )
    await db.execute(stmt)
    await db.commit()
    logger.success(f"✓ {ticker}: {len(records)} rows imported")

async def main():
    await init_db()
    if not os.path.exists(CSV_DIR):
        logger.error(f"CSV directory not found: {CSV_DIR}")
        logger.info("Run download_local.py on your Windows machine first, then:")
        logger.info("  docker cp scripts/market_data_csv quantai_api:/app/scripts/market_data_csv")
        return

    csv_files = [f for f in os.listdir(CSV_DIR) if f.endswith(".csv")]
    if not csv_files:
        logger.error("No CSV files found in market_data_csv/")
        return

    logger.info(f"Found {len(csv_files)} CSV files to import")
    async with AsyncSessionLocal() as db:
        for f in csv_files:
            try:
                await import_csv(db, os.path.join(CSV_DIR, f))
            except Exception as e:
                logger.error(f"✗ {f}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
