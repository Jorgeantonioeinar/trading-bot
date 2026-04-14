import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="THUNDER RADAR V80", layout="wide")

# --- ESTILOS PROFESIONALES ---
st.markdown("""
    <style>
    .metric-card { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #4a4d61; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #2e7d32; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- CLAVES DE ACCESO (SILENCIOSAS) ---
ALPACA_API_KEY = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca():
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

alpaca = get_alpaca()

# --- BARRA LATERAL: CONFIGURACIÓN DEL RADAR ---
st.sidebar.header("⚙️ CONFIGURACIÓN DEL RADAR")
modo_radar = st.sidebar.radio("Modo de Búsqueda", ["Radar Automático (S&P 500 / NASDAQ)", "Radar Manual (Mis Tickers)"])

col_p1, col_p2 = st.sidebar.columns(2)
precio_min = col_p1.number_input("Precio Mín $", min_value=0.1, value=0.2, step=0.1)
precio_max = col_p2.number_input("Precio Máx $", min_value=1.0, value=300.0, step=10.0)
vol_min = st.sidebar.number_input("Volumen Mínimo Diario", value=500000, step=100000)

st.sidebar.header("⚙️ CONFIGURACIÓN")
sensibilidad = st.sidebar.selectbox(
    "Nivel de Sensibilidad",
    ["Nivel 1: Élite (Filtro Estricto)", "Nivel 2: Equilibrado", "Nivel 3: Agresivo (Más Alertas)"],
    index=1)

if modo_radar == "Radar Manual (Mis Tickers)":
    tickers_input = st.sidebar.text_area("Ingresa hasta 30 tickers (separados por coma)", "AAPL, TSLA, NVDA, AMD, GME, AMC")
    lista_tickers = [t.strip().upper() for t in tickers_input.split(",")]
else:
    lista_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "NFLX", "ADBE", 
                     "BABA", "COIN", "MARA", "RIOT", "PLTR", "SOFI", "PFE", "DIS", "BA", "MSTR", 
                     "UPST", "AFRM", "HOOD", "PYPL", "SQ", "UBER", "LYFT", "DKNG", "OPEN", "LCID"]

# --- INTERFAZ PRINCIPAL ---
st.title("⚡ THUNDER PROFESSIONAL RADAR V80")

if st.button("🚀 INICIAR ESCANEO DE MERCADO"):
    with st.spinner("Analizando tendencias y volúmenes..."):
        data_all = yf.download(lista_tickers, period="2d", interval="5m", group_by='ticker', progress=False)
        resultados = []

        for t in lista_tickers:
            try:
                df = data_all[t].dropna()
                if df.empty or len(df) < 20: continue
                
                # --- MOTOR MATEMÁTICO AVANZADO ---
                precio_actual = df['Close'].iloc[-1]
                precio_apertura = df['Open'].iloc[-1]
                
                # 1. Detector de Gaps / Explosión
                gap_pct = ((precio_actual - precio_apertura) / precio_apertura) * 100
                
                # 2. RSI 7 Periodos (Scalping Rápido)
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
                rs = gain / loss
                rsi_actual = 100 - (100 / (1 + rs)).iloc[-1]
                
                # 3. Volatilidad ATR %
                df['Rango'] = df['High'] - df['Low']
                atr_actual = df['Rango'].rolling(window=7).mean().iloc[-1]
                volatilidad_pct = (atr_actual / precio_actual) * 100
                
                # 4. Puntaje de Volumen
                volumen_actual = df['Volume'].iloc[-1]
                volumen_promedio = df['Volume'].rolling(window=20).mean().iloc[-1]
                score_volumen = min(10, int((volumen_actual / (volumen_promedio + 1)) * 5))

                # 5. Clasificación de Estado
                if 60 <= rsi_actual <= 75:
                    estado_rsi = "✅ ZONA ÓPTIMA"
                elif rsi_actual > 75:
                    estado_rsi = "🔥 SOBRECOMPRA"
                else:
                    estado_rsi = "⚖️ NEUTRAL"

                # --- GUARDAR RESULTADOS EN LA LISTA ---
                resultados.append({
                    "Ticker": t,
                    "Precio": round(precio_actual, 2),
                    "Gap/Salto (%)": f"{round(gap_pct, 2)}%",
                    "Estado RSI": estado_rsi,
                    "RSI (7)": round(rsi_actual, 1),
                    "Volumen Score": f"{score_volumen}/10",
                    "Volumen Total": f"{int(volumen_actual):,}",
                    "ATR Volatilidad": f"{round(volatilidad_pct, 2)}%"
                })
            except:
                continue

    # --- MOSTRAR LA TABLA Y EJECUCIÓN ---
    if resultados:
        df_resultados = pd.DataFrame(resultados)
        
        # Ordenar por Gap
        df_resultados['Gap_Num'] = df_resultados['Gap/Salto (%)'].str.replace('%', '', regex=False).astype(float)
        df_final = df_resultados.sort_values(by='Gap_Num', ascending=False).drop(columns=['Gap_Num'])
        
        st.markdown("### 🎯 Mejores Oportunidades Detectadas")
        st.dataframe(df_final, use_container_width=True)
        
        # Panel de Ejecución
        st.divider()
        col_exec1, col_exec2 = st.columns([1, 2])
        with col_exec1:
            st.subheader("⚡ Ejecución Rápida")
            t_trade = st.selectbox("Seleccionar Ticker", df_final['Ticker'])
            cant = st.number_input("Cantidad", value=10)
            
            # Cambiado a Market Order simple para evitar errores por falta de datos de Stop Loss en la tabla
            if st.button("🟢 COMPRAR (Market Order)"):
                try:
                    req = MarketOrderRequest(
                        symbol=t_trade, qty=cant, side=OrderSide.BUY, time_in_force=TimeInForce.GTC
                    )
                    alpaca.submit_order(req)
                    st.success(f"Orden enviada al mercado para {t_trade}")
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.warning("No se encontraron acciones que cumplan con los filtros.")
