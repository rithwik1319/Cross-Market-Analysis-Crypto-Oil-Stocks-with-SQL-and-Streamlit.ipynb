"""Colab/local ETL: collect market data, clean it, and load SQLite."""
from __future__ import annotations
import os, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DATABASE_PATH", "market_data.db")
VS_CURRENCY = "usd"  # Keep all crypto price columns and comparisons in USD.
CRYPTO_COUNT = 250
HISTORY_DAYS = 365
TICKERS = ["^GSPC", "^IXIC", "^NSEI"]
START_DATE, OIL_END_DATE = "2020-01-01", "2026-01-01"  # oil end date is exclusive
STOCK_END_DATE = "2025-10-01"  # includes September 2025; Yahoo end date is exclusive
OIL_URL = "https://raw.githubusercontent.com/datasets/oil-prices/main/data/wti-daily.csv"

def get_json(url, params=None, headers=None):
    response = requests.get(url, params=params, headers=headers, timeout=45)
    response.raise_for_status()
    return response.json()

def fetch_coins():
    all_rows = []
    headers = {}
    key = os.getenv("COINGECKO_API_KEY")
    if key:
        headers["x-cg-demo-api-key"] = key
    for page in range(1, 3):  # 2 pages x 250 = top 500; retain top 250 below
        rows = get_json("https://api.coingecko.com/api/v3/coins/markets",
            {"vs_currency": VS_CURRENCY, "order": "market_cap_desc", "per_page": 250,
             "page": page, "sparkline": "false"}, headers)
        all_rows.extend(rows)
        time.sleep(1.2)
    df = pd.DataFrame(all_rows).sort_values("market_cap_rank").head(CRYPTO_COUNT)
    cols = ["id", "symbol", "name", "current_price", "market_cap", "market_cap_rank",
            "total_volume", "circulating_supply", "total_supply", "ath", "atl", "last_updated"]
    df = df[cols].copy()
    df["symbol"] = df["symbol"].str.upper()
    df["last_updated"] = pd.to_datetime(df["last_updated"], utc=True).dt.date.astype(str)
    df = df.rename(columns={"last_updated": "updated_date"})
    return df

def fetch_crypto_history(coin_ids):
    headers = {}
    key = os.getenv("COINGECKO_API_KEY")
    if key: headers["x-cg-demo-api-key"] = key
    chunks=[]
    for coin in coin_ids:
        data = get_json(f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart",
                        {"vs_currency": VS_CURRENCY, "days": HISTORY_DAYS, "interval": "daily"}, headers)
        frame = pd.DataFrame(data["prices"], columns=["timestamp", "price_usd"])
        frame["coin_id"] = coin
        frame["date"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True).dt.date.astype(str)
        chunks.append(frame[["coin_id", "date", "price_usd"]])
        time.sleep(1.5)
    return pd.concat(chunks, ignore_index=True).drop_duplicates(["coin_id", "date"])

def fetch_oil():
    df = pd.read_csv(OIL_URL)
    # Source columns are Date and Price; use case-insensitive lookup for robustness.
    mapping = {c.lower(): c for c in df.columns}
    df = df.rename(columns={mapping["date"]: "date", mapping["price"]: "price_usd"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date.astype("string")
    df["price_usd"] = pd.to_numeric(df["price_usd"], errors="coerce")
    return df.dropna(subset=["date"]).query("date >= @START_DATE and date < @OIL_END_DATE")[["date", "price_usd"]]

def fetch_stocks():
    pieces=[]
    for ticker in TICKERS:
        df = yf.download(ticker, start=START_DATE, end=STOCK_END_DATE, auto_adjust=False,
                         progress=False, group_by="column")
        if df.empty: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.rename_axis("date").reset_index()
        df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
        df["ticker"] = ticker
        df = df.rename(columns={"Open":"open", "High":"high", "Low":"low", "Close":"close", "Volume":"volume"})
        pieces.append(df[["date", "ticker", "open", "high", "low", "close", "volume"]])
    if not pieces: return pd.DataFrame(columns=["date","ticker","open","high","low","close","volume"])
    return pd.concat(pieces, ignore_index=True)

def main():
    coins = fetch_coins()
    top_ids = coins.nsmallest(3, "market_cap_rank")["id"].tolist()
    print("Historical crypto selected:", top_ids)
    crypto = fetch_crypto_history(top_ids)
    oil = fetch_oil()
    stocks = fetch_stocks()
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        conn.execute("DELETE FROM crypto_prices")
        conn.execute("DELETE FROM oil_prices")
        conn.execute("DELETE FROM stock_prices")
        conn.execute("DELETE FROM cryptocurrencies")
        coins.to_sql("cryptocurrencies", conn, if_exists="append", index=False)
        crypto.to_sql("crypto_prices", conn, if_exists="append", index=False)
        oil.to_sql("oil_prices", conn, if_exists="append", index=False)
        stocks.to_sql("stock_prices", conn, if_exists="append", index=False)
        conn.commit()
    print(f"Loaded {len(coins)} coins, {len(crypto)} crypto prices, {len(oil)} oil rows, {len(stocks)} stock rows into {DB_PATH}")

if __name__ == "__main__": main()
