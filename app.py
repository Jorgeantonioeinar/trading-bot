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

# --- LÓGICA DE CALIFICACIÓN (1-10) ---
def obtener_score(df):
    actual = df.iloc[-1]
    
    # Score Alcista
    score_up = 0
    if actual['Close'] > actual['vwap']: score_up += 3
    if actual['ema_9'] > actual['ema_20']: score_up += 3
    if actual['rsi'] > 55: score_up += 2
    
    # Score Bajista
    score_down = 0
    if actual['Close'] < actual['vwap']: score_down += 3
    if actual['ema_9'] < actual['ema_20']: score_down += 3
    if actual['rsi'] < 45: score_down += 2
    
    return min(score_up, 10), min(score_down, 10)

# --- DETERMINAR SESIÓN DE MERCADO ---
def get_market_session():
    tz = pytz.timezone('US/Eastern')
    now = datetime.now(tz)
    market_open = now.replace(hour=9, minute=30, second=0)
    market_close = now.replace(hour=16, minute=0, second=0)
    
    if now < market_open: return "PRE-MARKET"
    elif now > market_close: return "AFTER-HOURS"
    else: return "REGULAR"

session = get_market_session()

# --- BARRA LATERAL ---
st.sidebar.header(f"🏛️ ESTADO: {session}")
modo_radar = st.sidebar.selectbox("Filtro de Radar", ["Explosión Momentum", "Gap Up Scalping", "Personalizado"])
precio_min = st.sidebar.number_input("Precio Mín $", value=0.1, step=0.1)
precio_max = st.sidebar.number_input("Precio Máx $", value=150.0, step=1.0)
vol_filtro = st.sidebar.number_input("Filtro Vol. Base", value=5000, help="Acciones rápidas ignorarán este filtro")

if st.sidebar.toggle("Usar Mis Tickers", value=True):
    # text_input para respuesta inmediata al presionar Enter
    lista_tickers = st.sidebar.text_input("Lista (sep. por coma)", "AGAE, JZXN, KUST, TSLA, NVDA").split(",")
else:
    lista_tickers = ["TSLA", "NVDA", "AMD", "GME", "AMC", "MARA", "RIOT", "COIN", "PLTR", "SOFI", "MSTR"]

# --- INTERFAZ PRINCIPAL ---
col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    st.title("⚡ THUNDER RADAR V80 PRO")
with col_t2:
    if st.button("🔄 ACTUALIZAR PORTAFOLIO"):
        st.rerun()

# --- 1. SECCIÓN DE POSICIONES ACTIVAS (MONITOR DE P&L) ---
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
        
        c1, c2, c3 = st.columns(3)
        with c1:
            t_sell = st.selectbox("Ticker para Salida", [p['Ticker'] for p in pos_data])
        with c2:
            if st.button("🔴 VENTA INMEDIATA (Market)", use_container_width=True):
                alpaca.close_position(t_sell)
                st.warning(f"Cerrando posición en {t_sell}...")
    else:
        st.info("No tienes posiciones abiertas actualmente.")
except Exception as e:
    st.error(f"Error al cargar posiciones. Verifica tus claves: {e}")

st.divider()

# --- 2. RADAR DE MERCADO ---
if st.button("🚀 INICIAR ESCANEO DE MOMENTUM", use_container_width=True):
    with st.spinner(f"Escaneando con alta sensibilidad en {session}..."):
        # Descarga con prepost=True para ver Pre y After hours
        data_all = yf.download([t.strip().upper() for t in lista_tickers], period="2d", interval="1m", group_by='ticker', prepost=True, progress=False)
        resultados = []

        for t in lista_tickers:
            t = t.strip().upper()
            try:
                # Blindaje: Si la acción no existe o no tiene datos, la saltamos sin error
                if t not in data_all or data_all[t].empty: continue
                df = data_all[t].dropna()
                if len(df) < 20: continue
                
                actual = df.iloc[-1]
                precio = round(actual['Close'], 2)
                
                if not (precio_min <= precio <= precio_max): continue

                # MEJORA: Cálculo de Velocidad en 5 Minutos
                precio_hace_5m = df['Close'].iloc[-5]
                cambio_5m = ((precio - precio_hace_5m) / precio_hace_5m) * 100
                es_despegue = cambio_5m >= 1.5 # Si sube más de 1.5% en 5 mins, es explosión
                
                vol_actual = actual['Volume']
                
                # BYPASS DE VOLUMEN: Si es despegue, ignoramos el filtro de volumen
                if no es_despegue and vol_actual < vol_filtro: continue

                # Cálculos Técnicos (Mantenidos y protegidos)
                df['ema_9'] = df['Close'].ewm(span=9).mean()
                df['ema_20'] = df['Close'].ewm(span=20).mean()
                tp = (df['High'] + df['Low'] + df['Close']) / 3
                df['vwap'] = (tp * df['Volume']).cumsum() / (df['Volume'].cumsum() + 1)
                
                # RSI
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                df['rsi'] = 100 - (100 / (1 + (gain / loss)))
                
                # ATR para SL/TP Dinámico
                df['atr'] = (df['High'] - df['Low']).rolling(14).mean()
                
                # Lógica de Explosión (Momentum)
                gap_pct = ((precio - df['Open'].iloc[-1]) / df['Open'].iloc[-1]) * 100
                s_alcista, s_bajista = obtener_score(df)
                
                # Puntuación de Volumen Dinámica
                vol_promedio = df['Volume'].rolling(20).mean().iloc[-1]
                v_score = 10 if es_despegue else min(int((vol_actual / (vol_promedio + 1)) * 4), 10)

                # Estado RSI
                rsi_val = actual['rsi']
                estado_rsi = "🔥 SOBRECOMPRA" if rsi_val >= 70 else "🧊 SOBREVENTA" if rsi_val <= 30 else "⚖️ NEUTRAL"
                
                # Protección Dinámica (SL y TP sugeridos)
                volatilidad = actual['atr']
                sl_sugerido = round(precio - (volatilidad * 2), 2)
                tp_sugerido = round(precio + (volatilidad * 4), 2)

                resultados.append({
                    "Ticker": t,
                    "Precio": f"${precio}",
                    "Velocidad 5m ⚡": f"{round(cambio_5m, 2)}%",
                    "Score 🐂": s_alcista,
                    "Score 🐻": s_bajista,
                    "Gap %": round(gap_pct, 2),
                    "Estado RSI": estado_rsi,
                    "RSI": round(rsi_val, 1),
                    "ATR Volatilidad": round(volatilidad, 3),
                    "Stop Loss": sl_sugerido,
                    "Take Profit": tp_sugerido,
                    "Vol. Score": f"{v_score}/10",
                    "Volumen Real": int(vol_actual)
                })
            except Exception as e:
                # Si falla una acción específica, pasamos a la siguiente sin colapsar el programa
                continue

        if resultados:
            # Ordenamos primero por velocidad de despegue y luego por score alcista
            df_res = pd.DataFrame(resultados).sort_values(by=["Velocidad 5m ⚡", "Score 🐂"], ascending=[False, False])
            st.subheader("🎯 Oportunidades de Explosión Detectadas")
            st.dataframe(df_res, use_container_width=True)

            # --- 3. PANEL DE EJECUCIÓN ---
            st.divider()
            col_buy1, col_buy2 = st.columns([1, 2])
            with col_buy1:
                st.subheader("🛒 Compra Rápida")
                t_buy = st.selectbox("Ticker a Comprar", df_res['Ticker'])
                row = df_res[df_res['Ticker'] == t_buy].iloc[0]
                cant = st.number_input("Cantidad de Acciones", value=1, min_value=1)
                
                if st.button("🟢 EJECUTAR COMPRA PROTEGIDA", use_container_width=True):
                    try:
                        req = MarketOrderRequest(
                            symbol=t_buy, 
                            qty=cant, 
                            side=OrderSide.BUY, 
                            time_in_force=TimeInForce.GTC,
                            take_profit=TakeProfitRequest(limit_price=float(row['Take Profit'])),
                            stop_loss=StopLossRequest(stop_price=float(row['Stop Loss']))
                        )
                        alpaca.submit_order(req)
                        st.success(f"Orden Enviada: {t_buy} | SL: {row['Stop Loss']} | TP: {row['Take Profit']}")
                    except Exception as e:
                        st.error(f"Error de ejecución: {e}")
            
            with col_buy2:
                st.info(f"💡 **Análisis de {t_buy}**: Score de {row['Score 🐂']}/10 con una velocidad de subida de {row['Velocidad 5m ⚡']} en los últimos 5 minutos. El Stop Loss automático se ha fijado en ${row['Stop Loss']}.")
        else:
            st.warning("No se detecta momentum claro en este momento. Esperando explosión...")
