import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime
import pytz

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS ---
st.set_page_config(page_title="THUNDER RADAR V80 - ULTRA PRO", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #1e2130; padding: 10px; border-radius: 8px; border: 1px solid #4a4d61; }
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; height: 3em; }
    .buy-btn { background-color: #2e7d32 !important; color: white !important; }
    .sell-btn { background-color: #c62828 !important; color: white !important; }
    .stDataFrame { border: 1px solid #4a4d61; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN A ALPACA ---
ALPACA_API_KEY = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca():
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

alpaca = get_alpaca()

# --- 3. FUNCIONES LÓGICAS (SCORING Y SESIÓN) ---
def obtener_score(df):
    if len(df) < 1: return 0, 0
    actual = df.iloc[-1]
    
    # Score Alcista (Toros)
    score_up = 0
    if actual['Close'] > actual['vwap']: score_up += 3
    if actual['ema_9'] > actual['ema_20']: score_up += 3
    if actual['rsi'] > 55: score_up += 2
    if actual['Close'] > actual['ema_9']: score_up += 2
    
    # Score Bajista (Osos)
    score_down = 0
    if actual['Close'] < actual['vwap']: score_down += 3
    if actual['ema_9'] < actual['ema_20']: score_down += 3
    if actual['rsi'] < 45: score_down += 2
    if actual['Close'] < actual['ema_9']: score_down += 2
    
    return min(score_up, 10), min(score_down, 10)

def get_market_session():
    tz = pytz.timezone('US/Eastern')
    now = datetime.now(tz)
    market_open = now.replace(hour=9, minute=30, second=0)
    market_close = now.replace(hour=16, minute=0, second=0)
    
    if now < market_open: return "PRE-MARKET"
    elif now > market_close: return "AFTER-HOURS"
    else: return "REGULAR"

session = get_market_session()

# --- 4. BARRA LATERAL (FILTROS) ---
st.sidebar.header(f"🏛️ ESTADO: {session}")
modo_radar = st.sidebar.selectbox("Filtro de Radar", ["Explosión Momentum", "Gap Up Scalping", "Personalizado"])
precio_min = st.sidebar.number_input("Precio Mín $", value=0.1, step=0.1)
precio_max = st.sidebar.number_input("Precio Máx $", value=150.0, step=1.0)
vol_filtro = st.sidebar.number_input("Filtro Vol. Base", value=5000)

usar_custom = st.sidebar.toggle("Usar Mis Tickers", value=True)
if usar_custom:
    lista_raw = st.sidebar.text_input("Lista (sep. por coma)", "AGAE, JZXN, KUST, CING, TPET, PEGY, TSLA, NVDA")
    lista_tickers = [x.strip().upper() for x in lista_raw.split(",") if x.strip()]
else:
    lista_tickers = ["TSLA", "NVDA", "AMD", "GME", "AMC", "MARA", "RIOT", "COIN", "PLTR", "SOFI", "MSTR"]

# --- 5. INTERFAZ PRINCIPAL ---
col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    st.title("⚡ THUNDER RADAR V80 PRO")
with col_t2:
    if st.button("🔄 ACTUALIZAR PORTAFOLIO"):
        st.rerun()

# --- 6. MONITOR DE POSICIONES ACTIVAS ---
st.subheader("💼 Mis Posiciones en Tiempo Real")
try:
    positions = alpaca.get_all_positions()
    if positions:
        pos_data = []
        for p in positions:
            p_n_l = float(p.unrealized_plpc) * 100
            pos_data.append({
                "Ticker": p.symbol,
                "Cant": p.qty,
                "Entrada": round(float(p.avg_entry_price), 2),
                "Precio Act.": round(float(p.current_price), 2),
                "P&L %": f"{round(p_n_l, 2)}%",
                "Valor Total": f"${round(float(p.market_value), 2)}"
            })
        df_pos = pd.DataFrame(pos_data)
        st.dataframe(df_pos, use_container_width=True)
        
        c1, c2, _ = st.columns([2, 2, 1])
        with c1:
            t_sell = st.selectbox("Ticker para Salida", [p['Ticker'] for p in pos_data])
        with c2:
            if st.button("🔴 VENTA INMEDIATA (Market)"):
                alpaca.close_position(t_sell)
                st.warning(f"Cerrando posición en {t_sell}...")
    else:
        st.info("No tienes posiciones abiertas.")
except Exception as e:
    st.error(f"Error Alpaca: {e}")

st.divider()

# --- 7. MOTOR DE ESCANEO (RADAR) ---
if st.button("🚀 INICIAR ESCANEO DE MOMENTUM", use_container_width=True):
    with st.spinner(f"Analizando {len(lista_tickers)} tickers en modo {modo_radar}..."):
        data_all = yf.download(lista_tickers, period="2d", interval="1m", group_by='ticker', prepost=True, progress=False)
        resultados = []

        for t in lista_tickers:
            try:
                if t not in data_all or data_all[t].empty: continue
                df = data_all[t].dropna().copy()
                if len(df) < 20: continue
                
                # Cálculos Técnicos
                df['ema_9'] = df['Close'].ewm(span=9).mean()
                df['ema_20'] = df['Close'].ewm(span=20).mean()
                tp = (df['High'] + df['Low'] + df['Close']) / 3
                df['vwap'] = (tp * df['Volume']).cumsum() / (df['Volume'].cumsum() + 1)
                
                # RSI e Indicadores de Volatilidad
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                df['rsi'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
                df['atr'] = (df['High'] - df['Low']).rolling(14).mean()
                
                actual = df.iloc[-1]
                precio = round(actual['Close'], 2)
                vol_actual = actual['Volume']
                
                # Lógica de Velocidad y Gaps
                precio_hace_5m = df['Close'].iloc[-5]
                cambio_5m = ((precio - precio_hace_5m) / precio_hace_5m) * 100
                gap_pct = ((precio - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
                
                # FILTRADO DINÁMICO SEGÚN EL MODO SELECCIONADO
                pasa = False
                if modo_radar == "Explosión Momentum":
                    if cambio_5m >= 1.2 or actual['rsi'] > 65: pasa = True
                elif modo_radar == "Gap Up Scalping":
                    if gap_pct >= 2.0: pasa = True
                else: # Personalizado
                    if vol_actual >= vol_filtro and (precio_min <= precio <= precio_max): pasa = True
                
                if not pasa: continue

                s_alcista, s_bajista = obtener_score(df)
                vol_promedio = df['Volume'].rolling(20).mean().iloc[-1]
                v_score = min(int((vol_actual / (vol_promedio + 1)) * 4), 10)
                
                resultados.append({
                    "Ticker": t,
                    "Precio": precio,
                    "Velocidad 5m ⚡": f"{round(cambio_5m, 2)}%",
                    "Score 🐂": s_alcista,
                    "Score 🐻": s_bajista,
                    "Gap %": round(gap_pct, 2),
                    "RSI": round(actual['rsi'], 1),
                    "Stop Loss": round(precio - (actual['atr'] * 2), 2),
                    "Take Profit": round(precio + (actual['atr'] * 4), 2),
                    "Vol. Score": f"{v_score}/10",
                    "Volumen Real": int(vol_actual)
                })
            except:
                continue

        if resultados:
            df_res = pd.DataFrame(resultados).sort_values(by="Score 🐂", ascending=False)
            st.subheader(f"🎯 Oportunidades: {modo_radar}")
            st.dataframe(df_res, use_container_width=True)

            # --- 8. PANEL DE COMPRA RÁPIDA ---
            st.divider()
            c_buy1, c_buy2 = st.columns([1, 2])
            with c_buy1:
                t_buy = st.selectbox("Ticker a Comprar", df_res['Ticker'])
                row = df_res[df_res['Ticker'] == t_buy].iloc[0]
                cant = st.number_input("Cantidad", value=1, min_value=1)
                
                if st.button("🟢 EJECUTAR COMPRA PROTEGIDA"):
                    try:
                        req = MarketOrderRequest(
                            symbol=t_buy, qty=cant, side=OrderSide.BUY, 
                            time_in_force=TimeInForce.GTC,
                            take_profit=TakeProfitRequest(limit_price=float(row['Take Profit'])),
                            stop_loss=StopLossRequest(stop_price=float(row['Stop Loss']))
                        )
                        alpaca.submit_order(req)
                        st.success(f"Orden Enviada: {t_buy}")
                    except Exception as e:
                        st.error(f"Error: {e}")
            with c_buy2:
                st.info(f"Análisis de {t_buy}: Score Bull {row['Score 🐂']}/10. RSI en {row['RSI']}. Sugerencia: SL en {row['Stop Loss']}.")
        else:
            st.warning("No se encontraron acciones que cumplan el criterio de este modo.")
