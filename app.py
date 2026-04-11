import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")

st.title("🚀 SCALPING RADAR PRO")

symbols_input = st.text_input("Acciones", "AAPL,TSLA,AMD, NVDA, META")

def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

if st.button("🔍 Escanear mercado"):

    symbols = [s.strip() for s in symbols_input.split(",")]

    resultados = []

    for sym in symbols:
        try:
            df = yf.download(sym, period="1d", interval="5m", progress=False)

            if df is None or df.empty:
                continue

            # limpiar columnas
            if hasattr(df.columns, "levels"):
                df.columns = df.columns.get_level_values(0)

            df["Close"] = df["Close"].astype(float)
            df["Volume"] = df["Volume"].astype(float)

            # indicadores
            df["EMA9"] = ema(df["Close"], 9)
            df["EMA20"] = ema(df["Close"], 20)
            df["RSI"] = rsi(df["Close"])

            last = df.iloc[-1]

            ema9 = last["EMA9"]
            ema20 = last["EMA20"]
            rsi_val = last["RSI"]
            price = last["Close"]

            # volumen relativo
            vol_actual = last["Volume"]
            vol_prom = df["Volume"].rolling(20).mean().iloc[-1]

            # momentum (subida reciente)
            cambio = (df["Close"].iloc[-1] - df["Close"].iloc[-5]) / df["Close"].iloc[-5] * 100

            score = 0

            # tendencia
            if ema9 > ema20:
                score += 3

            # RSI
            if 55 < rsi_val < 70:
                score += 2

            # volumen
            if vol_actual > vol_prom:
                score += 2

            # momentum fuerte
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

    st.subheader("📊 MEJORES OPORTUNIDADES")

    for r in resultados:
        if r["score"] >= 7:
            st.success(f"{r['symbol']} | Precio: {r['price']} | Score: {r['score']} | Momentum: {r['momentum']}%")
        elif r["score"] >= 5:
            st.warning(f"{r['symbol']} | Precio: {r['price']} | Score: {r['score']} | Momentum: {r['momentum']}%")
        else:
            st.write(f"{r['symbol']} | Precio: {r['price']} | Score: {r['score']} | Momentum: {r['momentum']}%")
