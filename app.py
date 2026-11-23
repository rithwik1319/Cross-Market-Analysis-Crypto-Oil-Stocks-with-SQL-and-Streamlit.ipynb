from pathlib import Path
import os, sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
DB = os.getenv("DATABASE_PATH", "market_data.db")
st.set_page_config(page_title="Cross-Market Analysis", page_icon="📈", layout="wide")
st.title("📈 Cross-Market Analysis")
st.caption("Explore crypto in INR, WTI in USD per barrel, and global indices with SQL.")

@st.cache_data(ttl=120)
def read_sql(sql, params=()):
    if not Path(DB).exists(): return pd.DataFrame()
    with sqlite3.connect(DB) as conn: return pd.read_sql_query(sql, conn, params=params)

@st.cache_data(ttl=120)
def options():
    return (read_sql("SELECT DISTINCT coin_id FROM crypto_prices ORDER BY coin_id")['coin_id'].tolist(),
            read_sql("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker")['ticker'].tolist())

coins, tickers = options()
pages = ["Market Explorer", "Crypto Analysis", "SQL Query Runner"]
page = st.sidebar.radio("Page", pages)
if not Path(DB).exists():
    st.warning(f"Database not found: {DB}. Run `python etl.py` first (or upload a populated market_data.db).")
    st.stop()

if page == "Market Explorer":
    st.header("Market snapshot")
    dates = read_sql("SELECT MIN(date) AS min_date, MAX(date) AS max_date FROM crypto_prices")
    if dates.empty or pd.isna(dates.loc[0,"min_date"]): st.info("No data yet. Run the ETL first."); st.stop()
    min_date, max_date = pd.to_datetime(dates.loc[0,"min_date"]).date(), pd.to_datetime(dates.loc[0,"max_date"]).date()
    selected = st.date_input("Date range", value=(min_date,max_date), min_value=min_date, max_value=max_date)
    if not isinstance(selected, tuple) or len(selected) != 2: st.stop()
    start, end = selected[0].isoformat(), selected[1].isoformat()
    btc = read_sql("SELECT AVG(price_inr) AS v FROM crypto_prices WHERE coin_id='bitcoin' AND date BETWEEN ? AND ?", (start,end))
    oil = read_sql("SELECT AVG(price_usd) AS v FROM oil_prices WHERE date BETWEEN ? AND ?", (start,end))
    sp = read_sql("SELECT AVG(close) AS v FROM stock_prices WHERE ticker='^GSPC' AND date BETWEEN ? AND ?", (start,end))
    nifty = read_sql("SELECT AVG(close) AS v FROM stock_prices WHERE ticker='^NSEI' AND date BETWEEN ? AND ?", (start,end))
    cols = st.columns(4)
    for col, label, frame in zip(cols,["Bitcoin avg (INR)","WTI avg (USD/bbl)","S&P 500 avg close","NIFTY avg close"],[btc,oil,sp,nifty]):
        val = frame.iloc[0,0] if not frame.empty else None
        col.metric(label, f"{val:,.2f}" if pd.notna(val) else "No data")
    snapshot = read_sql("""SELECT c.date, c.price_inr AS bitcoin_inr, o.price_usd AS oil_usd,
      s.close AS sp500_close, n.close AS nifty_close FROM crypto_prices c
      LEFT JOIN oil_prices o ON o.date=c.date
      LEFT JOIN stock_prices s ON s.date=c.date AND s.ticker='^GSPC'
      LEFT JOIN stock_prices n ON n.date=c.date AND n.ticker='^NSEI'
      WHERE c.coin_id='bitcoin' AND c.date BETWEEN ? AND ? ORDER BY c.date""", (start,end))
    st.subheader("Daily market snapshot")
    st.dataframe(snapshot, use_container_width=True, hide_index=True)
    if not snapshot.empty:
        long = snapshot.melt(id_vars="date", var_name="market", value_name="price")
        st.plotly_chart(px.line(long, x="date", y="price", color="market", title="Daily prices (native units)"), use_container_width=True)

elif page == "Crypto Analysis":
    st.header("Top coin price history")
    if not coins: st.info("No crypto history loaded yet."); st.stop()
    coin = st.selectbox("Coin", coins, index=coins.index("bitcoin") if "bitcoin" in coins else 0)
    frame = read_sql("SELECT date, price_inr FROM crypto_prices WHERE coin_id=? ORDER BY date", (coin,))
    if frame.empty: st.info("No rows for this coin.")
    else:
        a,b = st.columns(2)
        start = a.date_input("From", pd.to_datetime(frame.date.min()).date(), key="crypto_from")
        end = b.date_input("To", pd.to_datetime(frame.date.max()).date(), key="crypto_to")
        shown = frame[(frame.date >= start.isoformat()) & (frame.date <= end.isoformat())]
        st.plotly_chart(px.line(shown, x="date", y="price_inr", title=f"{coin.title()} daily price (INR)"), use_container_width=True)
        st.dataframe(shown, use_container_width=True, hide_index=True)

else:
    st.header("Predefined SQL analytics")
    queries = {
      "Top 3 coins by market cap": "SELECT id,symbol,name,market_cap,market_cap_rank FROM cryptocurrencies ORDER BY market_cap_rank LIMIT 3",
      "Supply above 90%": "SELECT id,symbol,name,circulating_supply,total_supply FROM cryptocurrencies WHERE total_supply>0 AND circulating_supply/total_supply>0.90",
      "Coins within 10% of ATH": "SELECT id,name,current_price,ath FROM cryptocurrencies WHERE ath>0 AND current_price>=ath*0.90",
      "Highest Bitcoin daily price": "SELECT MAX(price_inr) AS highest_btc_price_inr FROM crypto_prices WHERE coin_id='bitcoin'",
      "Average oil price by year": "SELECT strftime('%Y',date) year, AVG(price_usd) avg_price FROM oil_prices GROUP BY year ORDER BY year",
      "Monthly average stock close": "SELECT ticker,strftime('%Y-%m',date) month,AVG(close) avg_close FROM stock_prices GROUP BY ticker,month ORDER BY month,ticker",
      "Oil and Bitcoin same-day prices": "SELECT c.date,c.price_inr bitcoin_inr,o.price_usd oil_usd FROM crypto_prices c JOIN oil_prices o ON c.date=o.date WHERE c.coin_id='bitcoin' ORDER BY c.date",
      "Daily multi-market snapshot": "SELECT c.date,c.price_inr bitcoin_inr,o.price_usd oil_usd,s.close sp500,n.close nifty FROM crypto_prices c LEFT JOIN oil_prices o ON o.date=c.date LEFT JOIN stock_prices s ON s.date=c.date AND s.ticker='^GSPC' LEFT JOIN stock_prices n ON n.date=c.date AND n.ticker='^NSEI' WHERE c.coin_id='bitcoin' ORDER BY c.date",
    }
    selected_name = st.selectbox("Choose a query", list(queries))
    st.code(queries[selected_name], language="sql")
    if st.button("Run query", type="primary"):
        st.dataframe(read_sql(queries[selected_name]), use_container_width=True, hide_index=True)
