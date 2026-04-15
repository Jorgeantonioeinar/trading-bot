import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# ================= CONFIG =================
st.set_page_config(layout="wide")
st.title("⚡ THUNDER RADAR PRO FINAL")

# ================= SIDEBAR =================
auto = st.sidebar.toggle("🤖 Auto Trading (solo visual)", False)

tickers = st.sidebar.text_input(
    "Tickers",
    "TSLA,NVDA,AMD,AAPL"
).split(",")

tickers = [t.strip().upper() for t in tickers]

# ================= DATA =================
def get_data(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df[['Open','High','Low','Close','Volume']].dropna()

    except:
        return pd.DataFrame()

# ================= INDICADORES =================
def indicadores(df):
    df = df.copy()

    df['ema9'] = df['Close'].ewm(span=9).mean()
    df['ema20'] = df['Close'].ewm(span=20).mean()

    df['vol_avg'] = df['Volume'].rolling(20).mean()
    df['vol_ratio'] = df['Volume'] / df['vol_avg']

    df['momentum'] = df['Close'].pct_change(3)*100

    df = df.replace([np.inf,-np.inf],np.nan).dropna()

    return df

# ================= IA SIMPLE =================
def score_ia(df):
    last = df.iloc[-1]
    score = 0

    if last['Close'] > last['ema9']: score += 2
    if last['ema9'] > last['ema20']: score += 2
    if last['vol_ratio'] > 1.5: score += 3
    if last['momentum'] > 1: score += 3

    return score

# ================= MAIN =================

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

        score = score_ia(df)

        resultados.append({
            "Ticker": t,
            "Precio": round(precio,2),
            "Score IA (1-10)": score,
            "Vol Ratio": round(last['vol_ratio'],2),
            "Momentum %": round(last['momentum'],2)
        })

        # ================= GRAFICO =================
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close']
        )])

        st.subheader(f"{t}")
        st.plotly_chart(fig, use_container_width=True)

        # ================= ALERTA =================
        if score >= 7:
            st.success(f"🚀 POSIBLE DESPEGUE: {t}")

    if resultados:
        df_res = pd.DataFrame(resultados).sort_values(by="Score IA (1-10)", ascending=False)
        st.dataframe(df_res, use_container_width=True)
    else:
        st.warning("No hay datos suficientes")
