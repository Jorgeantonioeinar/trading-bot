import streamlit as st
import pandas as pd
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime
import pytz

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Thunder Professional Radar", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .metric-card { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #4a4d61; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #2e7d32; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CLAVES DE ACCESO (SILENCIOSAS) ---
# NOTA: En producción, es mejor usar variables de entorno (st.secrets)
ALPACA_API_KEY = "PK0KUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca():
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

alpaca = get_alpaca()

# --- FUNCIONES DE ANÁLISIS ---
def calcular_rsi(series, period=7):
    delta = series.diff(1)
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calcular_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(window=period).mean()

# --- BARRA LATERAL: CONFIGURACIÓN ---
st.sidebar.title("⚙️ CONFIGURACIÓN DEL RADAR")
modo_busqueda = st.sidebar.radio("Modo de Búsqueda", ["Radar Automático (S&P 500 / NASDAQ)", "Radar Manual (Mis Tickers)"])

col1, col2 = st.sidebar.columns(2)
precio_min = col1.number_input("Precio Mín $", value=0.20, step=1.0)
precio_max = col2.number_input("Precio Máx $", value=300.00, step=1.0)

volumen_minimo = st.sidebar.number_input("Volumen Mínimo Diario", value=500000, step=100000)

st.sidebar.subheader("⚙️ CONFIGURACIÓN")
nivel_sensibilidad = st.sidebar.selectbox("Nivel de Sensibilidad", ["Nivel 1: Conservador", "Nivel 2: Equilibrado", "Nivel 3: Agresivo"], index=1)

# --- INTERFAZ PRINCIPAL ---
st.title("⚡ THUNDER PROFESSIONAL RADAR VOU")

# Detectar estado del mercado
tz = pytz.timezone('US/Eastern')
now = datetime.now(tz)
hora_actual = now.time()

if datetime.strptime("04:00", "%H:%M").time() <= hora_actual < datetime.strptime("09:30", "%H:%M").time():
    st.info(f"🕒 **PRE-MARKET ACTIVO** (Hora EST: {hora_actual.strftime('%H:%M')}) - Analizando datos con Prepost=True")
elif datetime.strptime("09:30", "%H:%M").time() <= hora_actual < datetime.strptime("16:00", "%H:%M").time():
    st.success(f"🟢 **MERCADO ABIERTO** (Hora EST: {hora_actual.strftime('%H:%M')})")
elif datetime.strptime("16:00", "%H:%M").time() <= hora_actual <= datetime.strptime("20:00", "%H:%M").time():
    st.warning(f"🌙 **AFTER-HOURS ACTIVO** (Hora EST: {hora_actual.strftime('%H:%M')}) - Analizando datos con Prepost=True")
else:
    st.error(f"🔴 **MERCADO CERRADO** (Hora EST: {hora_actual.strftime('%H:%M')})")

if st.button("🚀 INICIAR ESCANEO DE MERCADO"):
    with st.spinner("Escaneando mercado en tiempo real (incluyendo Pre/After Hours)..."):
        
        # Lista de ejemplo (puedes ampliarla o cargarla desde un CSV)
        tickers_a_escanear = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AMD", "PLTR", "SOFI", "RIOT", "HOOD", "UBER", "LYFT"]
        resultados = []

        for t in tickers_a_escanear:
            try:
                # Descargar datos intradía incluyendo PRE y AFTER HOURS (prepost=True)
                ticker_data = yf.Ticker(t)
                df = ticker_data.history(period="5d", interval="15m", prepost=True)
                
                if df.empty or len(df) < 20:
                    continue
                
                # Precios y Variaciones
                precio_actual = df['Close'].iloc[-1]
                precio_anterior = df['Close'].iloc[-2]
                
                # Filtro de precio
                if not (precio_min <= precio_actual <= precio_max):
                    continue
                
                gap_pct = ((precio_actual - precio_anterior) / precio_anterior) * 100
                
                # Volumen
                volumen_actual = df['Volume'].iloc[-1]
                volumen_promedio = df['Volume'].rolling(window=20).mean().iloc[-1]
                
                # Si el volumen promedio es 0 o NaN, saltar
                if pd.isna(volumen_promedio) or volumen_promedio == 0:
                    continue
                
                score_volumen = min(10, int((volumen_actual / (volumen_promedio + 1)) * 5))
                
                # Cálculo de Indicadores
                df['RSI'] = calcular_rsi(df['Close'], 7)
                df['ATR'] = calcular_atr(df, 14)
                
                rsi_actual = df['RSI'].iloc[-1]
                atr_actual = df['ATR'].iloc[-1]
                
                if pd.isna(rsi_actual) or pd.isna(atr_actual):
                    continue

                volatilidad_pct = (atr_actual / precio_actual) * 100

                # Clasificación de Estado
                if 60 <= rsi_actual <= 75:
                    estado_rsi = "✅ ZONA ÓPTIMA"
                elif rsi_actual > 75:
                    estado_rsi = "🔥 SOBRECOMPRA"
                else:
                    estado_rsi = "⚖️ NEUTRAL"

                # Guardar resultados
                resultados.append({
                    "Ticker": t,
                    "Precio": round(precio_actual, 2),
                    "Gap/Salto (%)": f"{round(gap_pct, 2)}%",
                    "Estado RSI": estado_rsi,
                    "RSI (7)": round(rsi_actual, 1),
                    "Volumen Score": f"{score_volumen}/10",
                    "Volumen Total": f"{int(volumen_actual):,}",
                    "ATR Volatilidad": f"{round(volatilidad_pct, 2)}%",
                    "Fuerza": score_volumen + (1 if 60 <= rsi_actual <= 75 else 0) # Métrica interna para ordenar
                })

            except Exception as e:
                # Esto soluciona tu error de sintaxis anterior. 
                # Si ocurre un error con un ticker, simplemente lo ignora y pasa al siguiente.
                continue

        # --- MOSTRAR RESULTADOS ---
        if resultados:
            df_final = pd.DataFrame(resultados).sort_values(by="Fuerza", ascending=False)
            
            st.subheader("🎯 Mejores Oportunidades Detectadas")
            st.dataframe(df_final.drop(columns=["Fuerza"]), use_container_width=True)

            # --- PANEL DE EJECUCIÓN ---
            st.divider()
            col_exec1, col_exec2 = st.columns([1, 2])
            
            with col_exec1:
                st.subheader("⚡ Ejecución Rápida")
                t_trade = st.selectbox("Seleccionar Ticker", df_final['Ticker'])
                cant = st.number_input("Cantidad", value=10, min_value=1)
                
                # Parámetros básicos para SL y TP (Ajustables según tu estrategia)
                precio_ticker = float(df_final[df_final['Ticker'] == t_trade]['Precio'].iloc[0])
                tp_price = round(precio_ticker * 1.05, 2) # Take Profit 5% arriba
                sl_price = round(precio_ticker * 0.98, 2) # Stop Loss 2% abajo

                if st.button("🟢 COMPRAR (Bracket Order)"):
                    try:
                        req = MarketOrderRequest(
                            symbol=t_trade,
                            qty=cant,
                            side=OrderSide.BUY,
                            time_in_force=TimeInForce.GTC,
                            take_profit=TakeProfitRequest(limit_price=tp_price),
                            stop_loss=StopLossRequest(stop_price=sl_price)
                        )
                        alpaca.submit_order(req)
                        st.success(f"Orden enviada para {cant} acciones de {t_trade} con SL y TP incorporados.")
                    except Exception as e:
                        st.error(f"Error al enviar la orden: {e}")
        else:
            st.warning("No se encontraron acciones en ese rango de precio con volumen suficiente bajo los parámetros actuales.")
