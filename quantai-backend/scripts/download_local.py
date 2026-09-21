"""
Run this script LOCALLY on your Windows machine (NOT inside Docker).
It downloads data from Yahoo Finance and saves CSV files.

Usage:
  pip install yfinance pandas
  python scripts/download_local.py
"""
import yfinance as yf
import pandas as pd
import os
import time

TICKERS = [
    "AAPL", "MSFT", "NVDA", "TSLA", "GOOGL",
    "SPY", "QQQ",
    "BTC-USD", "ETH-USD",
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "market_data_csv")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_ticker(ticker: str, period: str = "2y"):
    print(f"Downloading {ticker}...", end=" ")
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval="1d", auto_adjust=False, actions=True)
        if df.empty:
            print("EMPTY — skipped")
            return

        # Clean
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df = df.dropna(subset=["open", "high", "low", "close"])
        df = df[(df["open"] > 0) & (df["close"] > 0)]
        df.index.name = "timestamp"

        # Save
        out_path = os.path.join(OUTPUT_DIR, f"{ticker.replace('-', '_')}.csv")
        df.to_csv(out_path)
        print(f"OK — {len(df)} rows → {out_path}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    print(f"Saving CSVs to: {os.path.abspath(OUTPUT_DIR)}\n")
    for i, ticker in enumerate(TICKERS):
        download_ticker(ticker)
        if i < len(TICKERS) - 1:
            time.sleep(1.5)
    print(f"\nDone. Now run: python scripts/import_csv.py")
