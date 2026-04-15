import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

st.set_page_config(page_title="THUNDER RADAR PRO", layout="wide")

# ===================== SIDEBAR =====================
st.sidebar.title("⚙️ CONFIGURACIÓN")

modo = st.sidebar.selectbox("Modo", ["Automático", "Manual"])

sensibilidad = st.sidebar.selectbox(
    "Perfil de riesgo",
    ["Conservador", "Equilibrado", "Agresivo"]
)

precio_min = st.sidebar.number_input("Precio mínimo", value=0.1)
precio_max = st.sidebar.number_input("Precio máximo", value=200.0)

vol_min = st.sidebar.number_input("Volumen mínimo", value=100000)
vol_max = st.sidebar.number_input("Volumen máximo", value=1000000000)

# Lista base automática (tipo Webull)
tickers_auto = [
    "TSLA","NVDA","AMD","AAPL","AMZN","META","PLTR","SOFI",
    "RIOT","MARA","COIN","LCID","RIVN","GME","AMC"
]

if modo == "Manual":
    tickers_input = st.sidebar.text_input("Tickers", "TSLA,NVDA,AMD")
    tickers = [x.strip().upper() for x in tickers_input.split(",")]
else:
    tickers = tickers_auto

# Sensibilidad numérica
map_sens = {
    "Conservador": 7,
    "Equilibrado": 5,
    "Agresivo": 3
}
sensibilidad_valor = map_sens[sensibilidad]

# ===================== FUNCIONES =====================

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


def score(df):
    last = df.iloc[-1]
    s = 0

    if last['ema9'] > last['ema20']: s += 2
    if last['rsi'] > 55: s += 2
    if last['vol_ratio'] > 2: s += 3
    if last['momentum'] > 2: s += 3

    return s


def estrategia(df):
    last = df.iloc[-1]

    if last['rsi'] > 70:
        return "⚠️ Esperar retroceso"

    if last['ema9'] > last['ema20']:
        return "🟢 Entrada en pullback"

    return "⚖️ Esperar"


# ===================== UI =====================

st.title("⚡ THUNDER RADAR PRO")

if st.button("🚀 ESCANEAR MERCADO"):
    resultados = []

    for t in tickers:
        try:
            df = yf.download(t, period="1d", interval="5m", progress=False)

            if df.empty or len(df) < 20:
                continue

            df = indicadores(df)
            last = df.iloc[-1]

            precio = float(last['Close'])

            if not (precio_min <= precio <= precio_max):
                continue

            if not (vol_min <= last['Volume'] <= vol_max):
                continue

            s = score(df)

            if s < sensibilidad_valor:
                continue

            resultados.append({
                "Ticker": t,
                "Precio": round(precio,2),
                "Score": s,
                "RSI": round(float(last['rsi']),1),
                "Momentum %": round(float(last['momentum']),2),
                "Volumen": int(last['Volume']),
                "Estrategia": estrategia(df)
            })

        except Exception as e:
            st.warning(f"{t}: {e}")

    if resultados:
        df_res = pd.DataFrame(resultados).sort_values(by="Score", ascending=False)
        st.success(f"{len(df_res)} oportunidades encontradas")
        st.dataframe(df_res, use_container_width=True)
    else:
        st.error("No hay oportunidades con estos filtros")
