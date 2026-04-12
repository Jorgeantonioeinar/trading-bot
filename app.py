import streamlit as st
import yfinance as yf
import pandas as pd
from alpaca_trade_api import REST

# ================================
# 🔐 CONFIGURACIÓN SEGURA
# ================================
API_KEY = st.secrets["PKOKUMRZBCA2YJKVZIATSPGV5J"]
API_SECRET = st.secrets["2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"]
BASE_URL = "https://paper-api.alpaca.markets"

alpaca = REST(API_KEY, API_SECRET, BASE_URL)

# ================================
# 🎨 INTERFAZ
# ================================
st.set_page_config(layout="wide")
st.title("🚀 SCALPING BOT PRO")

symbols_input = st.text_input(
    "Acciones (separadas por coma)",
    "AAPL,TSLA,AMD,NVDA,META"
)

auto_mode = st.checkbox("🤖 Modo Automático")
capital = st.number_input("Capital por operación ($)", 10, 10000, 100)

# ================================
# 📊 INDICADORES
# ================================
def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ================================
# 💰 TRADING
# ================================
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

# ================================
# 🔍 SCANNER
# ================================
if st.button("🔍 Escanear mercado"):

    symbols = [s.strip() for s in symbols_input.split(",")]
    resultados = []

    for sym in symbols:
        try:
            df = yf.download(
                sym,
                period="1d",
                interval="5m",
                progress=False
            )

            if df is None or df.empty:
                continue

            # 🔧 LIMPIAR COLUMNAS
            if hasattr(df.columns, "levels"):
                df.columns = df.columns.get_level_values(0)

            # 🔧 ASEGURAR NUMÉRICOS
            df["Close"] = df["Close"].astype(float)
            df["Volume"] = df["Volume"].astype(float)

            # 📊 INDICADORES
            df["EMA9"] = ema(df["Close"], 9)
            df["EMA20"] = ema(df["Close"], 20)
            df["RSI"] = rsi(df["Close"])

            last = df.iloc[-1]

            ema9 = float(last["EMA9"])
            ema20 = float(last["EMA20"])
            rsi_val = float(last["RSI"])
            price = float(last["Close"])

            # 📊 VOLUMEN
            vol_actual = float(last["Volume"])
            vol_prom = float(df["Volume"].rolling(20).mean().iloc[-1])

            # ⚡ MOMENTUM
            cambio = (
                (df["Close"].iloc[-1] - df["Close"].iloc[-5])
                / df["Close"].iloc[-5]
            ) * 100

            # 🎯 SCORE
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
                "price": round(price, 2),
                "score": score,
                "momentum": round(cambio, 2)
            })

        except Exception as e:
            st.error(f"{sym} error: {e}")

    # 🔝 ORDENAR
    resultados = sorted(resultados, key=lambda x: x["score"], reverse=True)

    # ================================
    # 📊 MOSTRAR RESULTADOS
    # ================================
    st.subheader("📊 MEJORES OPORTUNIDADES")

    for r in resultados:
        col1, col2, col3 = st.columns([2,1,1])

        with col1:
            st.write(
                f"{r['symbol']} | Precio: {r['price']} | "
                f"Score: {r['score']} | Momentum: {r['momentum']}%"
            )

        with col2:
            if st.button(f"🟢 Comprar {r['symbol']}"):
                qty = int(capital / r["price"])
                if qty > 0:
                    trade(r["symbol"], "BUY", qty)

        with col3:
            if st.button(f"🔴 Vender {r['symbol']}"):
                trade(r["symbol"], "SELL", 1)

        # 🤖 MODO AUTOMÁTICO
        if auto_mode and r["score"] >= 7:
            qty = int(capital / r["price"])
            if qty > 0:
                trade(r["symbol"], "BUY", qty)
