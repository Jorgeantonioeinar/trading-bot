import streamlit as st
import yfinance as yf
import pandas as pd
from alpaca_trade_api import REST

# 🔐 CONFIGURA TUS KEYS
API_KEY = "TU_API_KEY"
API_SECRET = "TU_API_SECRET"
BASE_URL = "https://paper-api.alpaca.markets"

alpaca = REST(API_KEY, API_SECRET, BASE_URL)

st.set_page_config(layout="wide")
st.title("🚀 SCALPING BOT PRO + TRADING")

symbols_input = st.text_input("Acciones", "AAPL,TSLA,AMD,NVDA,META")

auto_mode = st.checkbox("🤖 Modo Automático")
capital = st.number_input("Capital por operación ($)", 10, 10000, 100)

def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def trade(symbol, action, qty):
    try:
        alpaca.submit_order(
            symbol=symbol,
            qty=qty,
            side=action.lower(),
            type="market",
            time_in_force="day"
        )
        st.success(f"{action} ejecutado en {symbol}")
    except Exception as e:
        st.error(f"Error trade: {e}")

def trailing_stop(symbol, buy_price):
    # trailing stop simple 1%
    current = float(alpaca.get_last_trade(symbol).price)

    if current < buy_price * 0.99:
        trade(symbol, "SELL", 1)
        st.warning(f"🔴 STOP LOSS activado {symbol}")

if st.button("🔍 Escanear mercado"):

    symbols = [s.strip() for s in symbols_input.split(",")]
    resultados = []

    for sym in symbols:
        try:
            df = yf.download(sym, period="1d", interval="5m", progress=False)

            if df is None or df.empty:
                continue

            if hasattr(df.columns, "levels"):
                df.columns = df.columns.get_level_values(0)

            df["Close"] = df["Close"].astype(float)
            df["Volume"] = df["Volume"].astype(float)

            df["EMA9"] = ema(df["Close"], 9)
            df["EMA20"] = ema(df["Close"], 20)
            df["RSI"] = rsi(df["Close"])

            last = df.iloc[-1]

            ema9 = last["EMA9"]
            ema20 = last["EMA20"]
            rsi_val = last["RSI"]
            price = last["Close"]

            vol_actual = last["Volume"]
            vol_prom = df["Volume"].rolling(20).mean().iloc[-1]

            cambio = (df["Close"].iloc[-1] - df["Close"].iloc[-5]) / df["Close"].iloc[-5] * 100

            score = 0

            if ema9 > ema20:
                score += 3
            if 55 < rsi_val < 70:
                score += 2
            if vol_actual > vol_prom:
                score += 2
            if cambio > 0.5:
                score += 3

            resultados.append({
                "symbol": sym,
                "price": round(price,2),
                "score": score,
                "momentum": round(cambio,2)
            })

        except Exception as e:
            st.error(f"{sym} error: {e}")

    resultados = sorted(resultados, key=lambda x: x["score"], reverse=True)

    st.subheader("📊 OPORTUNIDADES")

    for r in resultados:
        col1, col2, col3 = st.columns([2,1,1])

        with col1:
            st.write(f"{r['symbol']} | Precio: {r['price']} | Score: {r['score']}")

        with col2:
            if st.button(f"🟢 Comprar {r['symbol']}"):
                qty = int(capital / r["price"])
                trade(r["symbol"], "BUY", qty)

        with col3:
            if st.button(f"🔴 Vender {r['symbol']}"):
                trade(r["symbol"], "SELL", 1)

        # 🤖 AUTO MODE
        if auto_mode and r["score"] >= 7:
            qty = int(capital / r["price"])
            trade(r["symbol"], "BUY", qty)
