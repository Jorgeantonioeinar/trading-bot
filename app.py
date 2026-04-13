import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce

st.set_page_config(page_title="THUNDER V76", layout="wide")
st.title("⚡ THUNDER SCALPING DASHBOARD V76")

# --- CLAVES DE ALPACA ---
ALPACA_API_KEY = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca_client():
    try:
        return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
    except Exception as e:
        return None

client = get_alpaca_client()

# --- CONFIGURACIÓN DE ESTRATEGIA ---
st.sidebar.header("⚙️ Estrategia de Scalping")
sensibilidad = st.sidebar.selectbox("Nivel de Sensibilidad", ["Nivel 1: Seguro (1% Riesgo)", "Nivel 2: Balanceado (2% Riesgo)", "Nivel 3: Agresivo (3% Riesgo)"])

if "Seguro" in sensibilidad:
    sl_mult, tp_mult = 1.0, 2.0
elif "Balanceado" in sensibilidad:
    sl_mult, tp_mult = 1.5, 3.0
else:
    sl_mult, tp_mult = 2.0, 5.0

# --- FUNCIONES MATEMÁTICAS ---
def calcular_indicadores(df):
    df = df.copy()
    # VWAP
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['vwap'] = (tp * df['Volume']).cumsum() / df['Volume'].cumsum()
    
    # EMA
    df['ema_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ATR (Para Stop Loss Dinámico)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    return df

# --- DESCARGA MASIVA ANTI-CUELGUES ---
# El caché evita que la pantalla se congele cada vez que tocas un botón
@st.cache_data(ttl=60)
def obtener_datos_mercado():
    tickers_list = ["NVDA", "TSLA", "AMD", "SMCI", "MSTR", "COIN", "PLTR", "GME", "AMC", "AAPL"]
    tickers_str = " ".join(tickers_list)
    # Descarga masiva: 1 sola petición a Yahoo Finance
    data = yf.download(tickers_str, period="1d", interval="1m", group_by='ticker', prepost=True, progress=False)
    return data, tickers_list

# --- INTERFAZ PRINCIPAL ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 Escáner de Oportunidades")
    
    with st.spinner("Conectando con el mercado..."):
        data_all, tickers = obtener_datos_mercado()
        
    resultados = []
    
    for t in tickers:
        try:
            df = data_all[t].dropna()
            if len(df) < 20: continue
            
            df = calcular_indicadores(df)
            actual = df.iloc[-1]
            precio = actual['Close']
            
            # Filtro para evitar errores matemáticos si el ATR es cero o nulo
            atr = actual['atr'] if pd.notna(actual['atr']) and actual['atr'] > 0 else (precio * 0.005)
            
            estado = "Buscando..."
            score = 0
            
            if precio > actual['vwap'] and actual['ema_9'] > actual['ema_20'] and actual['rsi'] > 50:
                estado = "🚀 INICIO ALCISTA"
                score = 5
            elif actual['rsi'] > 80:
                estado = "⚠️ SOBRECOMPRA"
                score = -2
                
            resultados.append({
                "Ticker": t,
                "Precio": round(precio, 2),
                "Estado": estado,
                "RSI": round(actual['rsi'], 1),
                "Stop Loss": round(precio - (atr * sl_mult), 2),
                "Take Profit": round(precio + (atr * tp_mult), 2),
                "Score": score
            })
        except:
            continue

    if resultados:
        df_res = pd.DataFrame(resultados).sort_values(by="Score", ascending=False)
        st.dataframe(df_res, use_container_width=True)
    else:
        st.info("Esperando datos válidos del mercado...")

# --- PANEL DE EJECUCIÓN (ALPACA) ---
with col2:
    st.subheader("⚡ Terminal de Ejecución")
    st.info("Modo: Bracket Order Automática")
    
    if resultados:
        # Menú desplegable con las mejores opciones
        opciones = [f"{r['Ticker']} - Precio: ${r['Precio']}" for r in resultados]
        seleccion = st.selectbox("Selecciona Acción a Comprar", opciones)
        
        # Extraer el ticker seleccionado
        ticker_elegido = seleccion.split(" - ")[0]
        
        # Buscar los datos de esa acción en nuestra tabla
        datos_accion = next(item for item in resultados if item["Ticker"] == ticker_elegido)
        precio_actual = datos_accion["Precio"]
        sl_sugerido = datos_accion["Stop Loss"]
        tp_sugerido = datos_accion["Take Profit"]
        
        # Inputs para la orden
        cantidad = st.number_input("Cantidad de Acciones", min_value=1, value=10)
        
        st.markdown(f"**Stop Loss Dinámico:** ${sl_sugerido}")
        st.markdown(f"**Take Profit Dinámico:** ${tp_sugerido}")
        
        if st.button("🟢 ENVIAR ORDEN A ALPACA", use_container_width=True):
            if client is None:
                st.error("Error de conexión con Alpaca. Verifica tus claves.")
            else:
                try:
                    # Construir la orden Bracket (Compra + SL + TP)
                    order_data = MarketOrderRequest(
                        symbol=ticker_elegido,
                        qty=cantidad,
                        side=OrderSide.BUY,
                        time_in_force=TimeInForce.GTC,
                        take_profit=TakeProfitRequest(limit_price=tp_sugerido),
                        stop_loss=StopLossRequest(stop_price=sl_sugerido)
                    )
                    
                    # Enviar orden
                    orden = client.submit_order(order_data=order_data)
                    st.success(f"¡Orden enviada con éxito! Ticker: {ticker_elegido}")
                    st.balloons()
                except Exception as e:
                    st.error(f"La plataforma de Alpaca rechazó la orden. Detalle: {e}")
