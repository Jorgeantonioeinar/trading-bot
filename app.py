import streamlit as st
import pandas as pd
import numpy as np
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# ================== CONFIG ==================
API_KEY = "TU_API_KEY"
SECRET_KEY = "TU_SECRET_KEY"

data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)

st.set_page_config(layout="wide")
st.title("⚡ THUNDER RADAR PRO - REAL TIME")

# ================== SIDEBAR ==================
modo_auto = st.sidebar.toggle("🤖 Auto Trading", False)

tickers_input = st.sidebar.text_input(
    "Tickers",
    "TSLA,NVDA,AMD,AAPL,PLTR,SOFI"
)

tickers = [t.strip().upper() for t in tickers_input.split(",")]

# ================== FUNCIONES ==================

def get_data(symbol):
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Minute,
        limit=50
    )
    bars = data_client.get_stock_bars(req).df
    return bars[bars['symbol'] == symbol]


def indicadores(df):
    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema20'] = df['close'].ewm(span=20).mean()

    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['vol_avg'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_avg']

    return df


# ================== CALIFICACIONES ==================

def score_compra(df):
    last = df.iloc[-1]
    s = 0

    if last['ema9'] > last['ema20']: s += 3
    if last['close'] > last['ema9']: s += 2
    if last['vol_ratio'] > 1.5: s += 3
    if last['rsi'] < 70: s += 2

    return min(s, 10)


def score_venta(df):
    last = df.iloc[-1]
    s = 0

    if last['ema9'] < last['ema20']: s += 3
    if last['rsi'] > 65: s += 3
    if last['vol_ratio'] > 1.5: s += 2

    return min(s, 10)


def score_volumen(df):
    v = df.iloc[-1]['vol_ratio']
    return min(int(v * 3), 10)


def estado_rsi(rsi):
    if rsi < 30: return "🟢 BAJO"
    elif rsi < 70: return "🟡 MEDIO"
    else: return "🔴 ALTO"


# ================== EJECUCIÓN ==================

if st.button("🚀 ESCANEAR TIEMPO REAL"):
    resultados = []

    for t in tickers:
        try:
            df = get_data(t)

            if df.empty:
                continue

            df = indicadores(df)
            last = df.iloc[-1]

            compra = score_compra(df)
            venta = score_venta(df)
            volumen = score_volumen(df)

            resultados.append({
                "Ticker": t,
                "Precio": round(float(last['close']),2),
                "Compra (1-10)": compra,
                "Venta (1-10)": venta,
                "Volumen (1-10)": volumen,
                "RSI": round(float(last['rsi']),1),
                "Estado RSI": estado_rsi(last['rsi'])
            })

            # ================= AUTO TRADING =================
            if modo_auto:
                if compra >= 8 and volumen >= 6:
                    order = MarketOrderRequest(
                        symbol=t,
                        qty=1,
                        side=OrderSide.BUY,
                        time_in_force=TimeInForce.DAY
                    )
                    trading_client.submit_order(order)

        except Exception as e:
            st.warning(f"{t}: {e}")

    if resultados:
        df_res = pd.DataFrame(resultados).sort_values(by="Compra (1-10)", ascending=False)
        st.dataframe(df_res, use_container_width=True)
    else:
        st.error("No hay datos")
