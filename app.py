import streamlit as st
import yfinance as yf
import pandas_ta as ta

st.set_page_config(layout="wide")

st.title("🚀 BOT SCALPING PRO")

symbols_input = st.text_input("Acciones", "AAPL,TSLA,AMD")

if st.button("🔍 Escanear"):
    for sym in symbols_input.split(","):
        df = yf.download(sym.strip(), period="1d", interval="1m")

        if df.empty:
            continue

        df["EMA9"] = ta.ema(df["Close"], length=9)
        df["EMA20"] = ta.ema(df["Close"], length=20)

        last = df.iloc[-1]

        st.write(f"{sym} → {round(last['Close'],2)}")
