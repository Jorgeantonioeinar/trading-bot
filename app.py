import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(layout="wide")
st.title("⚡ THUNDER RADAR PRO - DETECTOR DE DESPEGUE")

# ===================== SIDEBAR =====================
st.sidebar.title("⚙️ CONFIGURACIÓN")

perfil = st.sidebar.selectbox(
    "Sensibilidad",
    ["Conservador", "Equilibrado", "Agresivo"]
)

precio_min = st.sidebar.number_input("Precio mínimo", value=0.1)
precio_max = st.sidebar.number_input("Precio máximo", value=200.0)

vol_min = st.sidebar.number_input("Volumen mínimo", value=10000)
vol_max = st.sidebar.number_input("Volumen máximo", value=1000000000)

modo_manual = st.sidebar.toggle("Usar mis tickers")

if modo_manual:
    tickers_input = st.sidebar.text_input(
        "Tickers",
        "TSLA,NVDA,AMD,AAPL,PLTR,SOFI"
    )
    tickers = [t.strip().upper() for t in tickers_input.split(",")]
else:
    tickers = [
        "TSLA","NVDA","AMD","AAPL","PLTR","SOFI",
        "RIOT","MARA","COIN","LCID","RIVN","GME","AMC"
    ]

# ===================== SENSIBILIDAD =====================
map_sens = {
    "Conservador": 7,
    "Equilibrado": 5,
    "Agresivo": 3
}
sensibilidad = map_sens[perfil]

# ===================== FUNCIONES =====================

def get_data(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)
        return df
    except:
        return pd.DataFrame()

def indicadores(df):
    df['ema9'] = df['Close'].ewm(span=9).mean()
    df['ema20'] = df['Close'].ewm(span=20).mean()

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['vol_avg'] = df['Volume'].rolling(20).mean()
    df['vol_ratio'] = df['Volume'] / df['vol_avg']

    df['momentum'] = df['Close'].pct_change(3) * 100

    return df

# 🔥 DETECTOR DE DESPEGUE (CLAVE)
def detectar_despegue(df):
    last = df.iloc[-1]

    condiciones = [
        last['momentum'] > 1.5,        # movimiento fuerte
        last['vol_ratio'] > 2,         # volumen explotando
        last['Close'] > last['ema9'],  # tendencia
    ]

    return sum(condiciones)

def score_total(df):
    last = df.iloc[-1]
    score = 0

    if last['ema9'] > last['ema20']: score += 2
    if last['rsi'] > 50: score += 2
    if last['vol_ratio'] > 2: score += 3
    if last['momentum'] > 2: score += 3

    return min(score, 10)

def estado_rsi(rsi):
    if rsi < 30: return "🟢 Bajo"
    elif rsi < 70: return "🟡 Medio"
    else: return "🔴 Alto"

# ===================== UI =====================

if st.button("🚀 ESCANEAR MERCADO"):
    resultados = []

    for t in tickers:
        df = get_data(t)

        if df.empty or len(df) < 20:
            continue

        df = indicadores(df)
        last = df.iloc[-1]

        precio = float(last['Close'])

        if not (precio_min <= precio <= precio_max):
            continue

        if not (vol_min <= last['Volume'] <= vol_max):
            continue

        despegue = detectar_despegue(df)
        score = score_total(df)

        if score < sensibilidad:
            continue

        resultados.append({
            "Ticker": t,
            "Precio": round(precio,2),
            "🔥 Despegue": despegue,
            "Score (1-10)": score,
            "RSI": round(float(last['rsi']),1),
            "Estado RSI": estado_rsi(last['rsi']),
            "Volumen": int(last['Volume']),
            "Vol Ratio": round(float(last['vol_ratio']),2),
            "Momentum %": round(float(last['momentum']),2)
        })

    if resultados:
        df_res = pd.DataFrame(resultados).sort_values(
            by=["🔥 Despegue","Score (1-10)"],
            ascending=False
        )

        st.success("🚀 Oportunidades detectadas")
        st.dataframe(df_res, use_container_width=True)

        # 🔥 ALERTA CLARA
        top = df_res.iloc[0]
        if top["🔥 Despegue"] >= 2:
            st.warning(f"🔥 POSIBLE DESPEGUE: {top['Ticker']}")

    else:
        st.error("❌ No hay oportunidades con estos filtros")
