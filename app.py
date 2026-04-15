import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time

st.set_page_config(layout="wide")
st.title("⚡ THUNDER RADAR PRO MAX")

# ===================== SIDEBAR =====================
st.sidebar.title("⚙️ CONFIGURACIÓN")

perfil = st.sidebar.selectbox(
    "Sensibilidad",
    ["Conservador", "Equilibrado", "Agresivo"]
)

auto_trade = st.sidebar.toggle("🤖 Auto Trading", False)

cantidad = st.sidebar.number_input("Cantidad a comprar", 1, 1000, 1)

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

# ===================== FUNCIONES =====================

def get_data(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        df = df.dropna()
        return df
    except:
        return pd.DataFrame()

def indicadores(df):
    df = df.copy()

    df['ema9'] = df['Close'].ewm(span=9).mean()
    df['ema20'] = df['Close'].ewm(span=20).mean()

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))

    df['vol_avg'] = df['Volume'].rolling(20).mean()
    df['vol_ratio'] = df['Volume'] / df['vol_avg']

    df['momentum'] = df['Close'].pct_change(3) * 100

    # 🔥 LIMPIEZA ANTI-ERROR
    df = df.replace([np.inf, -np.inf], np.nan).dropna()

    return df

def detectar_despegue(df):
    last = df.iloc[-1]
    condiciones = [
        last['momentum'] > 1.2,
        last['vol_ratio'] > 1.8,
        last['Close'] > last['ema9']
    ]
    return sum(condiciones)

def atr(df):
    return (df['High'] - df['Low']).rolling(14).mean().iloc[-1]

def alerta_sonido():
    st.audio("https://www.soundjay.com/buttons/sounds/beep-07.mp3")

# ===================== AUTO REFRESH =====================
refresh = st.sidebar.checkbox("📡 Auto refresh (5s)")

if refresh:
    time.sleep(5)
    st.rerun()

# ===================== MAIN =====================

if st.button("🚀 ESCANEAR") or refresh:
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

        # 🔥 STOP / TAKE PROFIT DINÁMICO
        atr_val = atr(df)
        stop_loss = precio - (atr_val * 1.5)
        take_profit = precio + (atr_val * 2)

        resultados.append({
            "Ticker": t,
            "Precio": round(precio,2),
            "🔥 Despegue": despegue,
            "Score": score,
            "RSI": round(last['rsi'],1),
            "Vol Ratio": round(last['vol_ratio'],2),
            "SL": round(stop_loss,2),
            "TP": round(take_profit,2)
        })

    if resultados:
        df_res = pd.DataFrame(resultados).sort_values(by="🔥 Despegue", ascending=False)
        st.dataframe(df_res, use_container_width=True)

        top = df_res.iloc[0]

        # 🔔 ALERTA
        if top["🔥 Despegue"] >= 2:
            st.warning(f"🔥 DESPEGUE DETECTADO: {top['Ticker']}")
            alerta_sonido()

        # 📊 GRÁFICO
        df_chart = get_data(top['Ticker'])
        st.line_chart(df_chart['Close'])

        # 🤖 AUTO TRADE
        if auto_trade and top["🔥 Despegue"] >= 3:
            st.success(f"🤖 COMPRA AUTOMÁTICA {top['Ticker']} x{cantidad}")

    else:
        st.error("❌ No hay oportunidades")
