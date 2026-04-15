import streamlit as st
import pandas as pd
import numpy as np
import time

# Alpaca
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# ================= CONFIG =================
st.set_page_config(layout="wide")
st.title("⚡ THUNDER RADAR PRO - AUTO TRADING")

API_KEY = st.secrets["PKOKUMRZBCA2YJKVZIATSPGV5J"]
SECRET_KEY = st.secrets["2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"]

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

# ================= SIDEBAR =================
st.sidebar.title("⚙️ CONFIGURACIÓN")

auto_mode = st.sidebar.toggle("🤖 Auto Trading", False)
qty = st.sidebar.number_input("Cantidad", 1, 1000, 1)

tickers = st.sidebar.text_input(
    "Tickers",
    "TSLA,NVDA,AMD,AAPL"
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
        'close':'Close',
        'high':'High',
        'low':'Low',
        'open':'Open',
        'volume':'Volume'
    })

    return df

# ================= INDICADORES =================
def indicadores(df):
    df['ema9'] = df['Close'].ewm(span=9).mean()
    df['ema20'] = df['Close'].ewm(span=20).mean()

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()

    rs = gain / loss.replace(0,np.nan)
    df['rsi'] = 100 - (100/(1+rs))

    df['vol_avg'] = df['Volume'].rolling(20).mean()
    df['vol_ratio'] = df['Volume'] / df['vol_avg']

    df['momentum'] = df['Close'].pct_change(3)*100

    df = df.replace([np.inf,-np.inf],np.nan).dropna()
    return df

# ================= LOGICA =================
def detectar_compra(df):
    last = df.iloc[-1]
    return (
        last['ema9'] > last['ema20'] and
        last['momentum'] > 1 and
        last['vol_ratio'] > 1.5 and
        last['rsi'] < 70
    )

def detectar_venta(df):
    last = df.iloc[-1]
    return (
        last['Close'] < last['ema9'] or
        last['rsi'] > 75 or
        last['momentum'] < -0.5
    )

def atr(df):
    return (df['High'] - df['Low']).rolling(14).mean().iloc[-1]

# ================= TRAILING =================
positions = {}

def ejecutar_compra(symbol, precio):
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

def ejecutar_venta(symbol):
    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY
    )
    trading_client.submit_order(order)

    positions.pop(symbol, None)

# ================= MAIN =================
if st.sidebar.checkbox("📡 Auto refresh 5s"):
    time.sleep(5)
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

        compra = detectar_compra(df)
        venta = detectar_venta(df)

        atr_val = atr(df)

        # 📊 GRAFICO VELAS
        st.subheader(f"{t}")
        st.line_chart(df[['Close']])

        st.write(f"Precio: {precio}")

        # ================= COMPRA =================
        if compra:
            st.success(f"🟢 COMPRA: {t}")

            if auto_mode and t not in positions:
                ejecutar_compra(t, precio)

        # ================= TRAILING =================
        if t in positions:
            pos = positions[t]

            nuevo_trail = max(pos["trail"], precio - atr_val)
            positions[t]["trail"] = nuevo_trail

            st.write(f"Trailing Stop: {nuevo_trail}")

            if precio < nuevo_trail:
                st.warning(f"🔴 TRAILING STOP ACTIVADO: {t}")
                if auto_mode:
                    ejecutar_venta(t)

        # ================= VENTA =================
        if venta and t in positions:
            st.error(f"🔻 VENTA: {t}")
            if auto_mode:
                ejecutar_venta(t)
