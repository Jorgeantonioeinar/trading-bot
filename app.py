import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="THUNDER RADAR V80 - PRO", layout="wide")

# --- ESTILOS PROFESIONALES ---
st.markdown("""
    <style>
    .metric-card { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #4a4d61; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #2e7d32; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- CLAVES DE ACCESO ---
ALPACA_API_KEY = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca():
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

alpaca = get_alpaca()

# --- LÓGICA DE CALIFICACIÓN (1-10) ---
def calificar_oportunidad(df):
    actual = df.iloc[-1]
    score_alcista = 0
    score_bajista = 0
    
    # 1. RSI
    if 40 < actual['rsi'] < 60: score_alcista += 2
    if actual['rsi'] > 60: score_alcista += 4
    if actual['rsi'] < 35: score_bajista += 4
    
    # 2. VWAP & Medias (Tendencia)
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (tp * df['Volume']).cumsum() / df['Volume'].cumsum()
    vwap_actual = vwap.iloc[-1]
    
    ema_9 = df['Close'].ewm(span=9).mean().iloc[-1]
    ema_20 = df['Close'].ewm(span=20).mean().iloc[-1]
    
    if actual['Close'] > vwap_actual: score_alcista += 3
    else: score_bajista += 3
    
    if ema_9 > ema_20: score_alcista += 3
    else: score_bajista += 3
    
    return min(score_alcista, 10), min(score_bajista, 10)

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ CONFIGURACIÓN")
modo_radar = st.sidebar.radio("Modo", ["Radar Automático", "Radar Manual"])

col_p1, col_p2 = st.sidebar.columns(2)
precio_min = col_p1.number_input("Precio Mín $", value=0.2)
precio_max = col_p2.number_input("Precio Máx $", value=300.0)

if modo_radar == "Radar Manual":
    tickers_input = st.sidebar.text_area("Tickers", "AAPL, TSLA, NVDA, AMD, GME, AMC")
    lista_tickers = [t.strip().upper() for t in tickers_input.split(",")]
else:
    lista_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "NFLX", "MSTR", 
                     "COIN", "MARA", "RIOT", "PLTR", "SOFI", "PYPL", "SQ", "UBER", "LCID", "GME"]

# --- INTERFAZ PRINCIPAL ---
st.title("⚡ THUNDER PROFESSIONAL RADAR V80")

if st.button("🚀 INICIAR ESCANEO DE MERCADO"):
    with st.spinner("Calculando Scores y Niveles de Salida..."):
        data_all = yf.download(lista_tickers, period="5d", interval="5m", group_by='ticker', progress=False)
        resultados = []

        for t in lista_tickers:
            try:
                df = data_all[t].dropna()
                if len(df) < 20: continue
                
                # --- INDICADORES ---
                precio_actual = df['Close'].iloc[-1]
                if not (precio_min <= precio_actual <= precio_max): continue

                # RSI 7
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
                df['rsi'] = 100 - (100 / (1 + (gain / loss)))
                
                # Calificación
                s_alcista, s_bajista = calificar_oportunidad(df)
                
                # ATR para SL/TP
                atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
                st_loss = round(precio_actual - (atr * 1.5), 2)
                tk_profit = round(precio_actual + (atr * 3), 2)
                
                # Gap
                precio_apertura = df['Open'].iloc[-1]
                gap_pct = ((precio_actual - precio_apertura) / precio_apertura) * 100

                resultados.append({
                    "Ticker": t,
                    "Precio": round(precio_actual, 2),
                    "Score Alcista": f"{s_alcista}/10",
                    "Score Bajista": f"{s_bajista}/10",
                    "Gap %": f"{round(gap_pct, 2)}%",
                    "RSI": round(df['rsi'].iloc[-1], 1),
                    "Stop Loss": st_loss,
                    "Take Profit": tk_profit
                })
            except:
                continue

    if resultados:
        df_final = pd.DataFrame(resultados).sort_values(by="Score Alcista", ascending=False)
        st.markdown("### 🎯 Oportunidades con Gestión de Riesgo")
        st.dataframe(df_final, use_container_width=True)
        
        st.divider()
        col_ex1, col_ex2 = st.columns([1, 2])
        with col_ex1:
            st.subheader("⚡ Ejecución")
            t_trade = st.selectbox("Seleccionar Ticker", df_final['Ticker'])
            datos_t = df_final[df_final['Ticker'] == t_trade].iloc[0]
            cant = st.number_input("Cantidad", value=10)
            
            if st.button("🟢 COMPRAR CON PROTECCIÓN"):
                try:
                    req = MarketOrderRequest(
                        symbol=t_trade, qty=cant, side=OrderSide.BUY, time_in_force=TimeInForce.GTC,
                        take_profit=TakeProfitRequest(limit_price=datos_t['Take Profit']),
                        stop_loss=StopLossRequest(stop_price=datos_t['Stop Loss'])
                    )
                    alpaca.submit_order(req)
                    st.success(f"Comprado {t_trade}. SL: {datos_t['Stop Loss']} | TP: {datos_t['Take Profit']}")
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.warning("Ajusta los filtros, no hay coincidencias ahora.")
