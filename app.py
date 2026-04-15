import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime, timedelta
import pytz
import time

# --- 1. CONFIGURACIÓN DE TERMINAL PROFESIONAL ---
st.set_page_config(page_title="THUNDER RADAR V90 - OMNI-MARKET", layout="wide")

# Estilos Webull-Style
st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    .stMetric { background-color: #1e222d; padding: 15px; border-radius: 10px; border-left: 5px solid #2962ff; }
    .stButton>button { width: 100%; border-radius: 4px; font-weight: bold; height: 3.5em; text-transform: uppercase; }
    .buy-btn { background-color: #00c853 !important; color: white !important; }
    .sell-btn { background-color: #ff5252 !important; color: white !important; }
    .stDataFrame { border: 1px solid #2a2e39; }
    h1, h2, h3 { color: #d1d4dc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CREDENCIALES Y CONEXIÓN ---
ALPACA_API_KEY = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca():
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

alpaca = get_alpaca()

# --- 3. MOTOR DE DETECCIÓN DE EXPLOSIÓN (LÓGICA WEBULL) ---
def get_market_session():
    tz = pytz.timezone('US/Eastern')
    now = datetime.now(tz)
    if now.weekday() >= 5: return "CERRADO (Finde)"
    
    pre_market_start = now.replace(hour=4, minute=0, second=0)
    market_open = now.replace(hour=9, minute=30, second=0)
    market_close = now.replace(hour=16, minute=0, second=0)
    after_hours_end = now.replace(hour=20, minute=0, second=0)

    if pre_market_start <= now < market_open: return "PRE-MARKET"
    elif market_open <= now <= market_close: return "REGULAR"
    elif market_close < now <= after_hours_end: return "AFTER-HOURS"
    else: return "CERRADO"

def calc_indicators(df):
    # VWAP
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['vwap'] = (tp * df['Volume']).cumsum() / (df['Volume'].cumsum() + 1e-9)
    # EMAs
    df['ema_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
    # ATR
    df['atr'] = (df['High'] - df['Low']).rolling(14).mean()
    return df

# --- 4. BARRA LATERAL: AJUSTES DE SENSIBILIDAD ---
session = get_market_session()
st.sidebar.title("🎮 CONTROLES DE RADAR")
st.sidebar.info(f"SESIÓN ACTUAL: **{session}**")

sensibilidad = st.sidebar.select_slider(
    "NIVEL DE SENSIBILIDAD (EXPLOSIÓN)",
    options=["Baja", "Media", "Alta"],
    value="Media",
    help="Alta detecta movimientos pequeños (scalping rápido). Baja espera confirmación de volumen pesado."
)

# Ajuste automático de parámetros según sensibilidad y sesión
mult_vol = {"Baja": 3.0, "Media": 2.0, "Alta": 1.2}[sensibilidad]
mult_price = {"Baja": 2.5, "Media": 1.5, "Alta": 0.8}[sensibilidad]

# Si es pre-market, bajamos la exigencia de volumen base automáticamente
vol_min_auto = 500 if "REGULAR" not in session else 5000

precio_min = st.sidebar.number_input("Precio Mín $", value=0.5, step=0.1)
precio_max = st.sidebar.number_input("Precio Máx $", value=150.0, step=1.0)

usar_custom = st.sidebar.toggle("Usar Mis Tickers", value=True)
if usar_custom:
    lista_raw = st.sidebar.text_area("Tickers (separados por coma)", "AGAE, JZXN, KUST, CING, TPET, PEGY, TSLA, NVDA", height=100)
    lista_tickers = [x.strip().upper() for x in lista_raw.split(",") if x.strip()]
else:
    lista_tickers = ["TSLA", "NVDA", "AMD", "MARA", "RIOT", "PLTR", "SOFI", "MSTR", "GME", "AMC"]

# --- 5. CUERPO PRINCIPAL ---
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("⚡ THUNDER RADAR V90 - PRO")
with col_h2:
    if st.button("🔄 REFRESCAR TODO"): st.rerun()

# MONITOR DE POSICIONES (CON FIX PARA NONETYPE)
st.subheader("💼 PORTAFOLIO EN VIVO")
try:
    posiciones = alpaca.get_all_positions()
    if posiciones:
        p_list = []
        for p in posiciones:
            p_list.append({
                "TICKER": p.symbol,
                "CANT": p.qty,
                "COSTO": round(float(p.avg_entry_price), 2),
                "PRECIO": round(float(p.current_price), 2),
                "P&L %": f"{round(float(p.unrealized_plpc or 0)*100, 2)}%",
                "VALOR": f"${round(float(p.market_value), 2)}"
            })
        st.dataframe(pd.DataFrame(p_list), use_container_width=True)
    else:
        st.info("Sin posiciones abiertas.")
except:
    st.warning("No se pudo conectar con Alpaca para ver posiciones.")

st.divider()

# --- 6. MOTOR DE ESCANEO ---
if st.button("🚀 INICIAR ESCANEO DE MOMENTUM", use_container_width=True):
    with st.spinner(f"Escaneando con Sensibilidad {sensibilidad}..."):
        # Descarga robusta
        data = yf.download(lista_tickers, period="2d", interval="1m", group_by='ticker', prepost=True, progress=False)
        resultados = []

        for t in lista_tickers:
            try:
                # Manejo de dataframe según cantidad de tickers
                df = data[t].dropna().copy() if len(lista_tickers) > 1 else data.dropna().copy()
                if len(df) < 30: continue
                
                df = calc_indicators(df)
                actual = df.iloc[-1]
                previa = df.iloc[-2]
                hace_5m = df.iloc[-6] if len(df) > 6 else df.iloc[0]
                
                # Métricas de Explosión
                precio = round(actual['Close'], 2)
                vol_actual = actual['Volume']
                vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
                
                cambio_5m = ((precio - hace_5m['Close']) / hace_5m['Close']) * 100
                spike_vol = vol_actual / (vol_avg + 1e-9)
                
                # LÓGICA DE FILTRADO (EL CORAZÓN DEL PROGRAMA)
                # 1. Filtro de Precio
                if not (precio_min <= precio <= precio_max): continue
                
                # 2. Detección de Explosión (Momentum)
                # Se activa si el precio sube más del umbral Y el volumen es mayor al promedio
                es_explosion = (cambio_5m >= mult_price) and (spike_vol >= mult_vol)
                
                # 3. Filtro Adicional por Sesión (Si es pre-market, aceptamos menos volumen absoluto)
                if not es_explosion and vol_actual < vol_min_auto: continue
                
                # Cálculo de Scores
                score_bull = 0
                if precio > actual['vwap']: score_bull += 3
                if actual['ema_9'] > actual['ema_20']: score_bull += 3
                if actual['rsi'] > 50: score_bull += 2
                if precio > actual['ema_9']: score_bull += 2

                resultados.append({
                    "TICKER": t,
                    "PRECIO": precio,
                    "CAMBIO 5m %": round(cambio_5m, 2),
                    "VOL / PROMEDIO": f"{round(spike_vol, 1)}x",
                    "SCORE BULL": f"{score_bull}/10",
                    "RSI": round(actual['rsi'], 1),
                    "VWAP": round(actual['vwap'], 2),
                    "STOP LOSS": round(precio - (actual['atr'] * 2), 2),
                    "TAKE PROFIT": round(precio + (actual['atr'] * 4), 2),
                    "VOLUMEN": int(vol_actual)
                })
            except:
                continue

        if resultados:
            df_res = pd.DataFrame(resultados).sort_values(by="CAMBIO 5m %", ascending=False)
            st.subheader(f"🎯 EXPLOSIONES DETECTADAS ({sensibilidad})")
            
            # Formateo visual
            st.dataframe(df_res.style.background_gradient(subset=['CAMBIO 5m %'], cmap='Greens'), use_container_width=True)

            # PANEL DE EJECUCIÓN
            st.divider()
            c1, c2 = st.columns([1, 2])
            with c1:
                st.subheader("🛒 ORDEN RÁPIDA")
                t_trade = st.selectbox("Elegir Ticker", df_res['TICKER'])
                row = df_res[df_res['TICKER'] == t_trade].iloc[0]
                cant = st.number_input("Cantidad de Acciones", value=10, min_value=1)
                
                if st.button("🟢 COMPRAR AHORA (PROTEGIDO)", use_container_width=True):
                    try:
                        req = MarketOrderRequest(
                            symbol=t_trade, qty=cant, side=OrderSide.BUY, 
                            time_in_force=TimeInForce.GTC,
                            take_profit=TakeProfitRequest(limit_price=float(row['TAKE PROFIT'])),
                            stop_loss=StopLossRequest(stop_price=float(row['STOP LOSS']))
                        )
                        alpaca.submit_order(req)
                        st.success(f"Orden de {t_trade} ejecutada. SL: {row['STOP LOSS']}")
                    except Exception as e:
                        st.error(f"Error: {e}")
            with c2:
                st.markdown(f"""
                ### 📈 Análisis Técnico: {t_trade}
                * **Fuerza (RSI):** {row['RSI']}
                * **Posición VWAP:** {"Por encima (BULL)" if float(row['PRECIO']) > float(row['VWAP']) else "Por debajo (BEAR)"}
                * **Volumen:** Está moviendo {row['VOL / PROMEDIO']} más que su promedio reciente.
                """)
        else:
            st.warning(f"No hay explosiones detectadas con sensibilidad {sensibilidad}. Prueba bajándola o revisando los tickers.")

# --- 7. NOTAS DE SEGURIDAD ---
st.sidebar.divider()
st.sidebar.caption("Thunder Radar V90. Diseñado para Scalping y Day Trading en Small Caps.")
