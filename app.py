import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
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

# Agregando el ticker a la lista de resultados
resultados.append({
    "Ticker": ticker,
    "Precio": round(precio_actual, 2),
    "Gap/Salto (%)": f"{round(gap_pct, 2)}%",
    "Estado RSI": estado_rsi,
    "RSI (7)": round(rsi_actual, 1),
    "Volumen Score": f"{score_volumen}/10",
    "Volumen Total": f"{int(volumen_actual):,}",
    "ATR Volatilidad": f"{round(volatilidad_pct, 2)}%"
})

# --- MOSTRAR LA TABLA EN STREAMLIT (FUERA DEL BUCLE) ---
if resultados:
    df_resultados = pd.DataFrame(resultados)
    
    # Ordenar para que los Gaps más grandes salgan arriba
    # Nota: Asegúrate de que esta línea esté escrita exactamente así:
    df_resultados['Gap_Num'] = df_resultados['Gap/Salto (%)'].str.replace('%', '', regex=False).astype(float)
    df_resultados = df_resultados.sort_values(by='Gap_Num', ascending=False).drop(columns=['Gap_Num'])
    
    st.markdown("### 🎯 Mejores Oportunidades Detectadas")
    st.dataframe(df_resultados, use_container_width=True)
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
# Aquí cambiamos el value a 0.2 para que sea tu nuevo punto de partida
precio_min = col_p1.number_input("Precio Mín $", min_value=0.1, value=0.2, step=0.1)
precio_max = col_p2.number_input("Precio Máx $", min_value=1.0, value=300.0, step=10.0)

vol_min = st.sidebar.number_input("Volumen Mínimo Diario", value=500000, step=100000)

# --- REINCORPORACIÓN DEL MENÚ DE SENSIBILIDAD ---
st.sidebar.header("⚙️ CONFIGURACIÓN")

sensibilidad = st.sidebar.selectbox(
    "Nivel de Sensibilidad",
    ["Nivel 1: Élite (Filtro Estricto)", "Nivel 2: Equilibrado", "Nivel 3: Agresivo (Más Alertas)"],
    index=1)

# Lógica de Umbral (Esto es lo que hace que el radar sea potente)
if "Élite" in sensibilidad:
    umbral_score = 8
elif "Equilibrado" in sensibilidad:
    umbral_score = 5
else:
    umbral_score = 2
if modo_radar == "Radar Manual (Mis Tickers)":
    tickers_input = st.sidebar.text_area("Ingresa hasta 30 tickers (separados por coma)", "AAPL, TSLA, NVDA, AMD, GME, AMC")
    lista_tickers = [t.strip().upper() for t in tickers_input.split(",")]
else:
    # Lista pre-cargada de alta volatilidad para el radar automático
    lista_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "NFLX", "ADBE", 
                     "BABA", "COIN", "MARA", "RIOT", "PLTR", "SOFI", "PFE", "DIS", "BA", "MSTR", 
                     "UPST", "AFRM", "HOOD", "PYPL", "SQ", "UBER", "LYFT", "DKNG", "OPEN", "LCID"]

# --- LÓGICA DE CALIFICACIÓN (1-10) ---
def calificar_oportunidad(df):
    actual = df.iloc[-1]
    score_alcista = 0
    score_bajista = 0
    
    # 1. RSI (Fuerza Relativa)
    if 40 < actual['rsi'] < 60: score_alcista += 2
    if actual['rsi'] > 60: score_alcista += 4
    if actual['rsi'] < 30: score_bajista += 4
    
    # 2. VWAP & Medias
    if actual['Close'] > actual['vwap']: score_alcista += 3
    else: score_bajista += 3
    
    if actual['ema_9'] > actual['ema_20']: score_alcista += 3
    else: score_bajista += 3
    
    return min(score_alcista, 10), min(score_bajista, 10)

def procesar_datos(df):
    # Indicadores Técnicos
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['vwap'] = (tp * df['Volume']).cumsum() / df['Volume'].cumsum()
    df['ema_9'] = df['Close'].ewm(span=9).mean()
    df['ema_20'] = df['Close'].ewm(span=20).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    
    # ATR para SL/TP
    df['atr'] = (df['High'] - df['Low']).rolling(14).mean()
    return df

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
                
                # --- MOTOR MATEMÁTICO AVANZADO (Línea 137 en adelante) ---
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
            
            # 4. Puntaje de Volumen (Fuerza del Movimiento)
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
        
            except: continue


        # --- MOSTRAR LA TABLA EN STREAMLIT (FUERA DEL BUCLE) ---
    if resultados:
        df_resultados = pd.DataFrame(resultados)
        
        # Esta línea permite que la tabla se ordene sola de mayor a menor Gap
        df_resultados['Gap_Num'] = df_resultados['Gap/Salto (%)'].str.replace('%', '', regex=False).astype(float)
        df_resultados = df_resultados.sort_values(by='Gap_Num', ascending=False).drop(columns=['Gap_Num'])
        
        st.markdown("### 🎯 Mejores Oportunidades Detectadas")
        st.dataframe(df_resultados, use_container_width=True)
        if resultados:
            df_final = pd.DataFrame(resultados).sort_values(by="Gap/Salto (%)", ascending=False)
            
            # Mostrar Tabla de Radar
            st.subheader("🎯 Mejores Oportunidades Detectadas")
            st.dataframe(df_final, use_container_width=True)S
            
            # Panel de Ejecución
            st.divider()
            col_exec1, col_exec2 = st.columns([1, 2])
            with col_exec1:
                st.subheader("⚡ Ejecución Rápida")
                t_trade = st.selectbox("Seleccionar Ticker", df_final['Ticker'])
                datos_t = df_final[df_final['Ticker'] == t_trade].iloc[0]
                cant = st.number_input("Cantidad", value=10)
                
                if st.button("🟢 COMPRAR (Bracket Order)"):
                    try:
                        req = MarketOrderRequest(
                            symbol=t_trade, qty=cant, side=OrderSide.BUY, time_in_force=TimeInForce.GTC,
                            take_profit=TakeProfitRequest(limit_price=datos_t['Take Profit']),
                            stop_loss=StopLossRequest(stop_price=datos_t['Stop Loss'])
                        )
                        alpaca.submit_order(req)
                        st.success("Orden enviada con SL y TP incorporados")
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.warning("No se encontraron acciones en ese rango de precio con volumen suficiente.")
