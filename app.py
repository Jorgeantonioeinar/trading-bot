import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time
import os

# ================== CONFIG ==================
st.set_page_config(layout="wide")
st.title("⚡ THUNDER RADAR PRO MAX")

# 🔐 API KEYS (Streamlit secrets)
API_KEY = st.secrets.get("ALPACA_API_KEY", None)
SECRET_KEY = st.secrets.get("ALPACA_SECRET_KEY", None)

# Intentar Alpaca
use_alpaca = False
if API_KEY and SECRET_KEY:
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
        use_alpaca = True
    except:
        use_alpaca = False

# ===================== SIDEBAR =====================
st.sidebar.title("⚙️ CONFIGURACIÓN")

perfil = st.sidebar.selectbox(
    "Sensibilidad",
    ["Conservador", "Equilibrado", "Agresivo"]
)

auto_trade = st.sidebar.toggle("🤖 Auto Trading", False)
cantidad = st.sidebar.number_input("Cantidad", 1, 1000, 1)

precio_min = st.sidebar.number_input("Precio mínimo", 0.1)
precio_max = st.sidebar.number_input("Precio máximo", 200.0)

vol_min = st.sidebar.number_input("Volumen mínimo", 10000)
vol_max = st.sidebar.number_input("Volumen máximo", 1000000000)

tickers = st.sidebar.text_input(
    "Tickers",
    "TSLA,NVDA,AMD,AAPL,PLTR,SOFI"
).split(",")

tickers = [t.strip().upper() for t in tickers]

map_sens = {"Conservador":7,"Equilibrado":5,"Agresivo":3}
sensibilidad = map_sens[perfil]

# ===================== DATA =====================

def get_data(symbol):
    # 👉 1. Intentar Alpaca
    if use_alpaca:
        try:
            req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                limit=50
            )
            bars = data_client.get_stock_bars(req).df

            if not bars.empty:
                df = bars.reset_index()

                # 🔥 NORMALIZAR COLUMNAS
                df = df[df['symbol'] == symbol]

                df = df.rename(columns={
                    'close': 'Close',
                    'high': 'High',
                    'low': 'Low',
                    'volume': 'Volume'
                })

                return df[['Close','High','Low','Volume']]

        except Exception as e:
            st.warning(f"Alpaca fallo {symbol}")

    # 👉 2. Fallback yfinance
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)

        # 🔥 ARREGLAR MULTIINDEX
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df[['Close','High','Low','Volume']].dropna()

    except:
        return pd.DataFrame()

# ===================== INDICADORES =====================

def indicadores(df):
    df = df.copy()

    # 🔥 asegurar tipos correctos
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')

    df = df.dropna()

    df['ema9'] = df['Close'].ewm(span=9).mean()
    df['ema20'] = df['Close'].ewm(span=20).mean()

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()

    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))

    df['vol_avg'] = df['Volume'].rolling(20).mean()

    # 🔥 PROTECCIÓN TOTAL
    df['vol_ratio'] = df['Volume'].div(df['vol_avg']).replace([np.inf, -np.inf], np.nan)

    df['momentum'] = df['Close'].pct_change(3) * 100

    df = df.dropna()

    return df

# ===================== LÓGICA =====================

def detectar_despegue(df):
    last = df.iloc[-1]
    return sum([
        last['momentum'] > 1.2,
        last['vol_ratio'] > 1.8,
        last['Close'] > last['ema9']
    ])

def atr(df):
    return (df['High'] - df['Low']).rolling(14).mean().iloc[-1]

# ===================== AUTO REFRESH =====================
if st.sidebar.checkbox("📡 Auto refresh 5s"):
    time.sleep(5)
    st.rerun()

# ===================== MAIN =====================

if st.button("🚀 ESCANEAR"):
    resultados = []

    for t in tickers:
        df = get_data(t)

        if df.empty or len(df) < 30:
            continue

        df = indicadores(df)
        if df.empty:
            continue

        last = df.iloc[-1]

        precio = float(last['Close'])

        if not (precio_min <= precio <= precio_max):
            continue

        if not (vol_min <= last['Volume'] <= vol_max):
            continue

        despegue = detectar_despegue(df)

        score = 0
        if last['ema9'] > last['ema20']: score += 3
        if last['rsi'] > 50: score += 2
        if last['vol_ratio'] > 2: score += 3
        if last['momentum'] > 2: score += 2

        if score < sensibilidad:
            continue

        atr_val = atr(df)
        resultados.append({
            "Ticker": t,
            "Precio": round(precio,2),
            "🔥 Despegue": despegue,
            "Score": score,
            "RSI": round(last['rsi'],1),
            "Vol Ratio": round(last['vol_ratio'],2),
            "SL": round(precio - atr_val*1.5,2),
            "TP": round(precio + atr_val*2,2)
        })

    if resultados:
        df_res = pd.DataFrame(resultados).sort_values(by="🔥 Despegue", ascending=False)
        st.dataframe(df_res, use_container_width=True)

        top = df_res.iloc[0]

        if top["🔥 Despegue"] >= 2:
            st.warning(f"🔥 DESPEGUE: {top['Ticker']}")

        st.line_chart(get_data(top['Ticker'])['Close'])

        if auto_trade:
            st.success(f"🤖 Auto listo para ejecutar {top['Ticker']} x{cantidad}")

    else:
        st.error("❌ No hay oportunidades")
