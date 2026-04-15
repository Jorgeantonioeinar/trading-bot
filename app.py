import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz

st.set_page_config(page_title="THUNDER RADAR PRO", layout="wide")

# ===================== FUNCIONES =====================

def calcular_indicadores(df):
    df['ema9'] = df['Close'].ewm(span=9).mean()
    df['ema20'] = df['Close'].ewm(span=20).mean()

    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['vwap'] = (tp * df['Volume']).cumsum() / df['Volume'].cumsum()

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['atr'] = (df['High'] - df['Low']).rolling(14).mean()

    # Momentum %
    df['momentum'] = df['Close'].pct_change(3) * 100

    # Volumen explosivo
    df['vol_avg'] = df['Volume'].rolling(20).mean()
    df['vol_ratio'] = df['Volume'] / df['vol_avg']

    return df


def detectar_breakout(df):
    high_20 = df['High'].rolling(20).max().iloc[-2]
    return df['Close'].iloc[-1] > high_20


def obtener_score(df):
    last = df.iloc[-1]
    score = 0

    if last['Close'] > last['vwap']:
        score += 2

    if last['ema9'] > last['ema20']:
        score += 2

    if last['rsi'] > 55:
        score += 1

    if last['vol_ratio'] > 2:
        score += 2

    if last['momentum'] > 2:
        score += 2

    if detectar_breakout(df):
        score += 3

    return score


def estrategia_scalping(df):
    last = df.iloc[-1]

    if last['rsi'] > 70:
        return "⚠️ Esperar pullback (sobrecompra)"

    if last['ema9'] > last['ema20'] and last['Close'] > last['vwap']:
        return "🟢 Entrada en pullback a EMA9"

    if detectar_breakout(df):
        return "🚀 Entrada en breakout"

    return "⚖️ Sin confirmación"


# ===================== UI =====================

st.title("⚡ THUNDER RADAR PRO - SCALPING")

sensibilidad = st.slider("Sensibilidad", 3, 10, 5)

tickers = st.text_input("Tickers", "IMMP,BIRD,AGAE,VSA,TSLA,NVDA,AMD").split(",")

if st.button("🚀 ESCANEAR"):
    resultados = []

    for t in tickers:
        try:
            df = yf.download(t.strip(), period="1d", interval="5m", prepost=True, progress=False)

            if df.empty or len(df) < 30:
                continue

            df = calcular_indicadores(df)

            score = obtener_score(df)

            if score < sensibilidad:
                continue

            last = df.iloc[-1]

            resultados.append({
                "Ticker": t,
                "Precio": round(float(last['Close']), 2),
                "Score": score,
                "RSI": round(float(last['rsi']), 1),
                "Momentum %": round(float(last['momentum']), 2),
                "Vol Ratio": round(float(last['vol_ratio']), 2),
                "Estrategia": estrategia_scalping(df)
            })

        except Exception as e:
            st.write(f"Error {t}: {e}")
            continue

    if resultados:
        df_res = pd.DataFrame(resultados).sort_values(by="Score", ascending=False)
        st.dataframe(df_res, use_container_width=True)
    else:
        st.warning("No hay oportunidades")
