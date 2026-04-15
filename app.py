import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import time

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# ================= CONFIG =================
st.set_page_config(layout="wide")
st.title("⚡ THUNDER RADAR PRO - AUTO TRADING REAL")

API_KEY = st.secrets["PKOKUMRZBCA2YJKVZIATSPGV5J"]
SECRET = st.secrets["2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"]

alpaca = TradingClient(API_KEY, SECRET, paper=True)

# ================= SIDEBAR =================
st.sidebar.title("⚙️ CONFIG")

auto = st.sidebar.toggle("🤖 Auto Trading", False)
qty = st.sidebar.number_input("Cantidad por trade", 1, 1000, 1)

min_score = st.sidebar.slider("Sensibilidad", 1, 10, 6)
precio_min = st.sidebar.number_input("Precio mínimo", 0.1)
precio_max = st.sidebar.number_input("Precio máximo", 500.0)

refresh = st.sidebar.checkbox("📡 Auto refresh (5s)")

# ================= ALERTA SONIDO =================
def alerta():
    st.markdown("""
    <audio autoplay>
    <source src="https://www.soundjay.com/buttons/sounds/beep-07.mp3">
    </audio>
    """, unsafe_allow_html=True)

# ================= TOP GAINERS =================
@st.cache_data(ttl=60)
def get_gainers():
    url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=day_gainers&count=100"
    data = requests.get(url).json()
    return [q['symbol'] for q in data['finance']['result'][0]['quotes']]

# ================= INDICADORES =================
def analizar(df):
    df['ema9'] = df['Close'].ewm(span=9).mean()
    df['ema20'] = df['Close'].ewm(span=20).mean()

    df['vol_avg'] = df['Volume'].rolling(20).mean()
    df['vol_ratio'] = df['Volume'] / df['vol_avg']

    df['momentum'] = df['Close'].pct_change(3)*100

    df = df.replace([np.inf, -np.inf], np.nan).dropna()

    if len(df) < 10:
        return None

    last = df.iloc[-1]

    score = 0
    if last['ema9'] > last['ema20']: score += 3
    if last['vol_ratio'] > 1.5: score += 3
    if last['momentum'] > 1: score += 2
    if last['momentum'] > 2: score += 2

    return score, last

# ================= TRAILING =================
positions = {}

def buy(symbol, price):
    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY
    )
    alpaca.submit_order(order)

    positions[symbol] = {
        "entry": price,
        "trail": price * 0.98
    }

def sell(symbol):
    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY
    )
    alpaca.submit_order(order)

    positions.pop(symbol, None)

# ================= AUTO REFRESH =================
if refresh:
    time.sleep(5)
    st.rerun()

# ================= MAIN =================
if st.button("🚀 INICIAR RADAR") or refresh:

    tickers = get_gainers()
    resultados = []

    for t in tickers:
        try:
            df = yf.download(t, period="1d", interval="5m", progress=False)

            if df.empty:
                continue

            resultado = analizar(df)
            if resultado is None:
                continue

            score, last = resultado
            precio = float(last['Close'])

            if not (precio_min <= precio <= precio_max):
                continue

            if score < min_score:
                continue

            tipo = "🚀 FUERTE" if score >= 7 else "🟢 TEMPRANO"

            resultados.append({
                "Ticker": t,
                "Tipo": tipo,
                "Precio": round(precio,2),
                "Score": score
            })

            # 🔔 ALERTA
            if score >= 7:
                alerta()
                st.success(f"🚀 DESPEGUE: {t}")

                if auto and t not in positions:
                    buy(t, precio)

            # 🔄 TRAILING
            if t in positions:
                trail = max(positions[t]["trail"], precio * 0.99)
                positions[t]["trail"] = trail

                if precio < trail:
                    st.warning(f"🔴 SALIDA: {t}")
                    if auto:
                        sell(t)

        except:
            continue

    if resultados:
        df_res = pd.DataFrame(resultados).sort_values(by="Score", ascending=False)
        st.dataframe(df_res, use_container_width=True)
    else:
        st.warning("No hay oportunidades ahora")
