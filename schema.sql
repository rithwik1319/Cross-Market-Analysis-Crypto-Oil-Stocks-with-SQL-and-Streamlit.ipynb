PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cryptocurrencies (
  id TEXT PRIMARY KEY,
  symbol TEXT NOT NULL,
  name TEXT NOT NULL,
  current_price REAL,
  market_cap INTEGER,
  market_cap_rank INTEGER,
  total_volume INTEGER,
  circulating_supply REAL,
  total_supply REAL,
  ath REAL,
  atl REAL,
  updated_date TEXT
);

CREATE TABLE IF NOT EXISTS crypto_prices (
  coin_id TEXT NOT NULL REFERENCES cryptocurrencies(id),
  date TEXT NOT NULL,
  price_usd REAL NOT NULL,
  PRIMARY KEY (coin_id, date)
);

CREATE TABLE IF NOT EXISTS oil_prices (
  date TEXT PRIMARY KEY,
  price_usd REAL
);

CREATE TABLE IF NOT EXISTS stock_prices (
  date TEXT NOT NULL,
  ticker TEXT NOT NULL,
  open REAL,
  high REAL,
  low REAL,
  close REAL,
  volume INTEGER,
  PRIMARY KEY (date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_crypto_date ON crypto_prices(date);
CREATE INDEX IF NOT EXISTS idx_stock_ticker_date ON stock_prices(ticker, date);
