import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime
import pytz

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="THUNDER RADAR V80 - ULTRA PRO", layout="wide")

# --- ESTILOS PROFESIONALES ---
st.markdown("""
    <style>
    .stMetric { background-color: #1e2130; padding: 10px; border-radius: 8px; border: 1px solid #4a4d61; }
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; }
    .buy-btn { background-color: #2e7d32 !important; color: white !important; }
    .sell-btn { background-color: #c62828 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CLAVES DE ACCESO ---
ALPACA_API_KEY = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca():
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

alpaca = get_alpaca()

# --- DETERMINAR SESIÓN DE MERCADO ---
def get_market_session():
    tz = pytz.timezone('US/Eastern')
    now = datetime.now(tz)
    # Pre-market: 04:00 - 09:30
    # Regular: 09:30 - 16:00
    # After-hours: 16:00 - 20:00
    if now.time() < datetime.strptime("09:30", "%H:%M").time(): return "PRE-MARKET"
    elif now.time() > datetime.strptime("16:00", "%H:%M").time(): return "AFTER-HOURS"
    else: return "REGULAR"

session = get_market_session()

# --- LÓGICA DE CALIFICACIÓN (1-10) ---
def obtener_scores(df):
    actual = df.iloc[-1]
    score_up = 0
    score_down = 0
    
    # Tendencia por Medias y RSI
    if actual['Close'] > df['Close'].ewm(span=9).mean().iloc[-1]: score_up += 3
    else: score_down += 3
    
    if actual['rsi'] > 55: score_up += 3
    elif actual['rsi'] < 45: score_down += 3
    
    # Momentum de Volumen
    vol_prom = df['Volume'].rolling(20).mean().iloc[-1]
    if actual['Volume'] > vol_prom * 1.5: score_up += 4
    
    return min(score_up, 10), min(score_down, 10)

# --- BARRA LATERAL ---
st.sidebar.header(f"🏛️ ESTADO: {session}")

# PASO 2: AJUSTE DE ENTRADA MANUAL (Respuesta inmediata)
usar_manual = st.sidebar.toggle("Modo Manual (Digitar Tickers)", value=True)
if usar_manual:
    tickers_input = st.sidebar.text_input("Ingresa tickers (ej: AGAE, MARA, TSLA)", "AGAE, MARA")
    lista_tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
else:
    lista_tickers = ["TSLA", "NVDA", "AMD", "GME", "AMC", "MARA", "RIOT", "PLTR", "MSTR"]

precio_min = st.sidebar.number_input("Precio Mín $", value=0.1, step=0.1)
precio_max = st.sidebar.number_input("Precio Máx $", value=500.0, step=1.0)
vol_filtro = st.sidebar.number_input("Filtro Vol. Diario", value=10000) # Bajado para acciones como AGAE

# --- 1. MONITOR DE POSICIONES EN VIVO ---
st.subheader("💼 Mis Posiciones y Ganancias (P&L)")
try:
    positions = alpaca.get_all_positions()
    if positions:
        pos_list = []
        for p in positions:
            p_n_l = float(p.unrealized_plpc) * 100
            pos_list.append({
                "Ticker": p.symbol,
                "Cant": p.qty,
                "Precio Ent.": round(float(p.avg_entry_price), 2),
                "Precio Act.": round(float(p.current_price), 2),
                "Ganancia %": f"{round(p_n_l, 2)}%",
                "Estado": "📈" if p_n_l > 0 else "📉"
            })
        st.dataframe(pd.DataFrame(pos_list), use_container_width=True)
        
        col_v1, col_v2 = st.columns([2, 1])
        with col_v1:
            t_a_vender = st.selectbox("Ticker para VENTA INMEDIATA", [p.symbol for p in positions])
        with col_v2:
            if st.button("🔴 VENDER AHORA", use_container_width=True):
                alpaca.close_position(t_a_vender)
                st.success(f"Venta ejecutada en {t_a_vender}")
    else:
        st.info("Sin posiciones abiertas.")
except:
    st.error("Error: Verifica tus claves de Alpaca o conexión.")

st.divider()

# --- 2. RADAR DE MERCADO ---
if st.button("🚀 INICIAR ESCANEO EXPLOSIVO"):
    with st.spinner(f"Buscando Momentum en {session}..."):
        # prepost=True es vital para ver Pre-market y After-hours
        data = yf.download(lista_tickers, period="2d", interval="5m", prepost=True, group_by='ticker', progress=False)
        resultados = []

        for t in lista_tickers:
            try:
                df = data[t].dropna()
                if len(df) < 15: continue
                
                # Indicadores rápidos
                actual = df.iloc[-1]
                precio = round(actual['Close'], 2)
                
                # Filtro básico
                if not (precio_min <= precio <= precio_max): continue
                if actual['Volume'] < vol_filtro: continue

                # RSI 7
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(7).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
                df['rsi'] = 100 - (100 / (1 + (gain / loss)))

                # ATR para SL/TP
                df['atr'] = (df['High'] - df['Low']).rolling(14).mean()
                atr = df['atr'].iloc[-1]

                # PASO 1: PUNTAJE DE VOLUMEN AGRESIVO
                vol_actual = actual['Volume']
                vol_prom = df['Volume'].rolling(20).mean().iloc[-1]
                
                # Si el volumen promedio es bajo pero hay un pico, le damos importancia
                if vol_prom < 1000:
                    score_vol = 8 if vol_actual > 5000 else 2
                else:
                    score_vol = min(10, int((vol_actual / (vol_prom + 1)) * 10))

                s_up, s_down = obtener_scores(df)
                gap = ((precio - df['Open'].iloc[-1]) / df['Open'].iloc[-1]) * 100

                resultados.append({
                    "Ticker": t,
                    "Precio": precio,
                    "Score Alcista": f"{s_up}/10",
                    "Score Bajista": f"{s_down}/10",
                    "Gap %": f"{round(gap, 2)}%",
                    "Vol. Score": f"{score_vol}/10",
                    "Stop Loss": round(precio - (atr * 1.5), 2),
                    "Take Profit": round(precio + (atr * 3), 2)
                })
            except: continue

        if resultados:
            df_final = pd.DataFrame(resultados).sort_values(by="Score Alcista", ascending=False)
            st.dataframe(df_final, use_container_width=True)
            
            st.subheader("🛒 Ejecución Rápida con Protección")
            c_b1, c_b2, c_b3 = st.columns(3)
            with c_b1:
                t_buy = st.selectbox("Seleccionar para comprar", df_final['Ticker'])
                row = df_final[df_final['Ticker'] == t_buy].iloc[0]
            with c_b2:
                cant = st.number_input("Cantidad", value=1, min_value=1)
            with c_b3:
                if st.button("🟢 COMPRAR AHORA"):
                    try:
                        req = MarketOrderRequest(
                            symbol=t_buy, qty=cant, side=OrderSide.BUY, time_in_force=TimeInForce.GTC,
                            take_profit=TakeProfitRequest(limit_price=row['Take Profit']),
                            stop_loss=StopLossRequest(stop_price=row['Stop Loss'])
                        )
                        alpaca.submit_order(req)
                        st.success(f"Comprado {t_buy}. SL: {row['Stop Loss']} TP: {row['Take Profit']}")
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.warning("No se encontraron acciones con los filtros actuales. Prueba bajando el Filtro de Vol. Diario.")
