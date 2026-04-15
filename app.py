import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# ================= CONFIG =================
st.set_page_config(layout="wide")
st.title("⚡ THUNDER RADAR PRO ULTRA")

API_KEY = st.secrets["PKOKUMRZBCA2YJKVZIATSPGV5J"]
SECRET_KEY = st.secrets["2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"]

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

# ================= SIDEBAR =================
st.sidebar.title("⚙️ CONFIG")

auto = st.sidebar.toggle("🤖 Auto Trading", False)
qty = st.sidebar.number_input("Cantidad", 1, 1000, 1)

tickers = st.sidebar.text_input(
    "Tickers",
    "TSLA,NVDA,AMD"
).split(",")

tickers = [t.strip().upper() for t in tickers]

# ================= DATA =================
def get_data(symbol):
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Minute,
        limit=100
    )
    bars = data_client.get_stock_bars(req).df

    if bars.empty:
        return pd.DataFrame()

    df = bars.reset_index()
    df = df[df['symbol'] == symbol]

    df = df.rename(columns={
        'open':'Open','high':'High','low':'Low',
        'close':'Close','volume':'Volume'
    })

    return df

# ================= IA DETECCION =================
def detectar_ruptura(df):
    last = df.iloc[-1]

    score = 0

    if last['Close'] > df['Close'].rolling(20).max().iloc[-2]:
        score += 3  # breakout

    if last['Volume'] > df['Volume'].rolling(20).mean().iloc[-1] * 2:
        score += 3  # volumen fuerte

    if last['Close'] > last['Close'] - df['Close'].diff().rolling(3).mean().iloc[-1]:
        score += 2  # aceleración

    if last['Close'] > last['Close'].rolling(5).mean().iloc[-1]:
        score += 2  # tendencia corta

    return score

# ================= INDICADORES =================
def indicadores(df):
    df['ema9'] = df['Close'].ewm(span=9).mean()
    df['ema20'] = df['Close'].ewm(span=20).mean()

    df['vol_avg'] = df['Volume'].rolling(20).mean()
    df['vol_ratio'] = df['Volume'] / df['vol_avg']

    return df.dropna()

# ================= TRAILING =================
positions = {}

def comprar(symbol, precio):
    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY
    )
    trading_client.submit_order(order)

    positions[symbol] = {
        "entry": precio,
        "trail": precio * 0.98
    }

def vender(symbol):
    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY
    )
    trading_client.submit_order(order)

    positions.pop(symbol, None)

# ================= MAIN =================

if st.sidebar.checkbox("📡 Auto refresh"):
    time.sleep(3)
    st.rerun()

if st.button("🚀 ESCANEAR"):

    for t in tickers:
        df = get_data(t)

        if df.empty:
            continue

        df = indicadores(df)
        if df.empty:
            continue

        last = df.iloc[-1]
        precio = float(last['Close'])

        score = detectar_ruptura(df)

        # 📊 GRAFICO VELAS PRO
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close']
        )])

        st.subheader(f"{t} | Score IA: {score}")
        st.plotly_chart(fig, use_container_width=True)

        # 🚀 ALERTA
        if score >= 6:
            st.success(f"🚀 POSIBLE DESPEGUE: {t}")

            if auto and t not in positions:
                comprar(t, precio)

        # 🔄 TRAILING
        if t in positions:
            trail = max(positions[t]["trail"], precio * 0.99)
            positions[t]["trail"] = trail

            st.write(f"Trailing: {trail}")

            if precio < trail:
                st.warning(f"🔴 SALIDA: {t}")
                if auto:
                    vender(t)
