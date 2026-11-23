# Cross-Market Analysis: Crypto, Oil & Stocks

Runnable starter implementation for the requested SQL + Streamlit project. It collects top-250 CoinGecko metadata, daily prices for the top 3 coins, WTI prices, and Yahoo Finance index data into SQLite.

## Important data choices

- All crypto prices use USD (`vs_currency=usd`) because the proposed SQL schema names the fields `price_usd`; switch `VS_CURRENCY` in `etl.py` to `inr` only if you also rename the columns and UI labels.
- CoinGecko's `/market_chart?days=365` returns a rolling year of history. It cannot provide a fixed 2025 comparison when run in late 2026 using only this request. For full 2025 crypto data, use a CoinGecko plan/end point that permits historical date ranges, or supply a licensed historical file and load it into `crypto_prices`.
- The oil file and Yahoo history are requested from 2020-01-01 through 2025-12-31. End dates in Yahoo's API are exclusive.
- Market holidays differ. Joins are by exact date; missing values are left NULL rather than filled or forward-carried.

## Run locally

1. Install Python 3.10+.
2. Open a terminal in this folder and create an environment: `python -m venv .venv` then activate it.
3. Install: `pip install -r requirements.txt`.
4. Optional: copy `.env.example` to `.env` and enter a CoinGecko Demo API key.
5. Collect and load data: `python etl.py`.
6. Start dashboard: `streamlit run app.py`.

The first ETL may take several minutes because of public API rate limits. If a source errors, rerun; completed data is loaded only after fetching all sources succeeds.

## Run in Google Colab

Upload this folder (or put it in Drive), then run these cells:

```python
%cd /content/cross_market_project
!pip -q install -r requirements.txt
!python etl.py
```

For an interactive app, use a secure Streamlit Community Cloud deployment or a Colab tunneling solution that you configure yourself. Do not expose API keys in a public notebook.

## Tables and analysis

`schema.sql` defines `cryptocurrencies`, `crypto_prices`, `oil_prices`, and `stock_prices`; `queries.sql` contains the requested SQL examples. The app has three pages: date-filtered market explorer, coin trend explorer, and a curated SQL query runner.

Pearson correlation should use aligned daily **returns**, not raw price levels, because levels trend over time. Use the SQL return query in `queries.sql`, then in Python: `returns[['btc_return','oil_return']].corr().iloc[0,1]`. Correlation describes historical co-movement; it does not establish causation or a trading strategy.
