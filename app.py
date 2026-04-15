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
st.title("⚡ THUNDER RADAR PRO - NIVEL PROFESIONAL")

# ================= SECRETS =================
try:
    API_KEY = ["PKOKUMRZBCA2YJKVZIATSPGV5J"]
    SECRET = ["2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"]
    alpaca = TradingClient(API_KEY, SECRET, paper=True)
except:
    st.error("❌ Configura tus claves en Secrets")
    st.stop()

# ================= SIDEBAR =================
st.sidebar.title("⚙️ CONFIG")

auto = st.sidebar.toggle("🤖 Auto Trading", False)
qty_manual = st.sidebar.number_input("Cantidad manual", 1, 1000, 1)

min_score = st.sidebar.slider("Sensibilidad", 1, 10, 6)

precio_min = st.sidebar.number_input("Precio mínimo", 0.5)
precio_max = st.sidebar.number_input("Precio máximo", 500.0)

auto_refresh = st.sidebar.checkbox("📡 Auto refresh (5s)")

# ================= TOP GAINERS =================
@st.cache_data(ttl=60)
def get_gainers():

    url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=day_gainers&count=100"

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, headers=headers, timeout=5)

        if res.status_code != 200:
            raise Exception("HTTP error")

        data = res.json()

        quotes = data.get('finance', {}).get('result', [{}])[0].get('quotes', [])

        tickers = [q.get('symbol') for q in quotes if q.get('symbol')]

        if len(tickers) == 0:
            raise Exception("Vacío")

        return tickers

    except:
        st.warning("⚠️ Yahoo falló → usando backup")

        return [
            "TSLA","NVDA","AMD","AAPL","AMZN","META",
            "PLTR","SOFI","COIN","RIOT","MARA",
            "SMCI","IONQ","RKLB","LCID","RIVN",
            "SPY","QQQ","TQQQ","SQQQ"
        ]

# ================= INDICADORES =================
def analizar(df):

    df['ema9'] = df['Close'].ewm(span=9).mean()
    df['ema20'] = df['Close'].ewm(span=20).mean()

    df['vol_avg'] = df['Volume'].rolling(20).mean()
    df['vol_ratio'] = df['Volume'] / df['vol_avg']

    df['momentum'] = df['Close'].pct_change(3) * 100

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

# ================= GESTIÓN RIESGO =================
def calcular_qty(precio):
    balance = 10000  # ajustable
    riesgo_pct = 0.01

    stop = precio * 0.98
    riesgo = precio - stop

    if riesgo <= 0:
        return 1

    qty = int((balance * riesgo_pct) / riesgo)
    return max(qty, 1)

# ================= POSICIONES =================
positions = {}

def buy(symbol, price):
    qty = calcular_qty(price)

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
        qty=qty_manual,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY
    )

    alpaca.submit_order(order)
    positions.pop(symbol, None)

# ================= AUTO REFRESH =================
if auto_refresh:
    time.sleep(5)
    st.rerun()

# ================= MAIN =================
if st.button("🚀 INICIAR RADAR") or auto_refresh:

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

            # 🔴 FILTROS PROFESIONALES
            if last['Volume'] < 50000:
                continue

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

            # ================= COMPRA =================
            if score >= 7:
                st.success(f"🚀 DESPEGUE: {t}")

                if auto and t not in positions:
                    buy(t, precio)

            # ================= TRAILING =================
            if t in positions:
                trail = max(positions[t]["trail"], precio * 0.995)
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
        st.warning("⚠️ No hay oportunidades ahora")
