import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")

st.title("🚀 BOT SCALPING PRO")

symbols_input = st.text_input("Acciones", "AAPL,TSLA,AMD")

# EMA manual
def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()

if st.button("🔍 Escanear"):
    for sym in symbols_input.split(","):
        df = yf.download(sym.strip(), period="1d", interval="1m")

        if df.empty:
            continue

        df["EMA9"] = ema(df["Close"], 9)
        df["EMA20"] = ema(df["Close"], 20)

        last = df.iloc[-1]

        st.write(f"{sym} → Precio: {round(last['Close'],2)} | EMA9: {round(last['EMA9'],2)}")
