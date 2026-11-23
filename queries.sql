-- Crypto metadata
SELECT * FROM cryptocurrencies ORDER BY market_cap_rank LIMIT 3;
SELECT * FROM cryptocurrencies WHERE total_supply > 0 AND circulating_supply / total_supply > 0.90;
SELECT * FROM cryptocurrencies WHERE ath > 0 AND current_price >= ath * 0.90;
SELECT AVG(market_cap_rank) AS avg_rank FROM cryptocurrencies WHERE total_volume > 1000000000;
SELECT * FROM cryptocurrencies ORDER BY updated_date DESC LIMIT 1;

-- Historical crypto prices
SELECT MAX(price_usd) FROM crypto_prices WHERE coin_id='bitcoin' AND date >= date('now','-365 day');
SELECT AVG(price_usd) FROM crypto_prices WHERE coin_id='ethereum' AND date >= date('now','-365 day');
SELECT date, price_usd FROM crypto_prices WHERE coin_id='bitcoin' AND date >= '2025-01-01' AND date < '2025-02-01' ORDER BY date;
SELECT coin_id, AVG(price_usd) AS avg_price FROM crypto_prices WHERE date >= date('now','-365 day') GROUP BY coin_id ORDER BY avg_price DESC;
-- Closest available observations on/after the requested boundary dates
WITH boundary AS (
 SELECT (SELECT price_usd FROM crypto_prices WHERE coin_id='bitcoin' AND date >= '2024-09-01' ORDER BY date LIMIT 1) AS sep_2024,
        (SELECT price_usd FROM crypto_prices WHERE coin_id='bitcoin' AND date >= '2025-09-01' ORDER BY date LIMIT 1) AS sep_2025
)
SELECT 100.0 * (sep_2025-sep_2024)/NULLIF(sep_2024,0) AS pct_change FROM boundary;

-- Oil and stocks
SELECT MAX(price_usd) FROM oil_prices WHERE date >= date('now','-5 years');
SELECT strftime('%Y',date) AS year, AVG(price_usd) AS avg_price FROM oil_prices GROUP BY year ORDER BY year;
SELECT * FROM oil_prices WHERE date BETWEEN '2020-03-01' AND '2020-04-30' ORDER BY date;
SELECT strftime('%Y',date) AS year, MAX(price_usd)-MIN(price_usd) AS range_usd FROM oil_prices GROUP BY year ORDER BY year;
SELECT MIN(price_usd) AS lowest_price FROM oil_prices WHERE date >= date('now','-10 years');
SELECT * FROM stock_prices WHERE ticker='^GSPC' ORDER BY date;
SELECT MAX(close) FROM stock_prices WHERE ticker='^IXIC';
SELECT date, high-low AS daily_range FROM stock_prices WHERE ticker='^GSPC' ORDER BY daily_range DESC LIMIT 5;
SELECT ticker, strftime('%Y-%m',date) AS month, AVG(close) AS avg_close FROM stock_prices GROUP BY ticker, month ORDER BY month,ticker;
SELECT AVG(volume) FROM stock_prices WHERE ticker='^NSEI' AND date >= '2024-01-01' AND date < '2025-01-01';

-- Daily cross-market snapshot. NULL values are expected on market holidays.
SELECT c.date, c.price_usd AS bitcoin_usd, o.price_usd AS oil_usd,
       sp.close AS sp500_close, n.close AS nifty_close
FROM crypto_prices c
LEFT JOIN oil_prices o ON o.date=c.date
LEFT JOIN stock_prices sp ON sp.date=c.date AND sp.ticker='^GSPC'
LEFT JOIN stock_prices n ON n.date=c.date AND n.ticker='^NSEI'
WHERE c.coin_id='bitcoin' ORDER BY c.date;

-- Daily returns and same-day correlation inputs (calculate Pearson r in pandas).
WITH joined AS (
 SELECT c.date, c.price_usd AS btc, o.price_usd AS oil,
        LAG(c.price_usd) OVER (ORDER BY c.date) AS prev_btc,
        LAG(o.price_usd) OVER (ORDER BY o.date) AS prev_oil
 FROM crypto_prices c JOIN oil_prices o ON o.date=c.date
 WHERE c.coin_id='bitcoin'
)
SELECT date, (btc/prev_btc)-1 AS btc_return, (oil/prev_oil)-1 AS oil_return
FROM joined WHERE prev_btc IS NOT NULL AND prev_oil IS NOT NULL;
