import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import pytz
from datetime import datetime
from alpaca.trading.client import TradingClient

st.set_page_config(page_title="THUNDER V75", layout="wide")
st.title("⚡ THUNDER SCALPING DASHBOARD V75 - Jorge")

# --- CLAVES ---
TWELVE_DATA_KEY = "7bf9d008a8cc4a87b8b045eec07d94d4"
ALPACA_API_KEY = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

# --- CONFIGURACIÓN DE SENSIBILIDAD ---
with st.sidebar:
    st.header("⚙️ Estrategia")
    sensibilidad = st.selectbox("Sensibilidad", ["Nivel 1: Elite (Seguro)", "Nivel 2: Balanceado", "Nivel 3: Agresivo (Riesgo)"])
    st.info("💡 El Stop Loss y Take Profit se calculan dinámicamente usando el ATR (Volatilidad del momento).")

# Ajuste de multiplicadores según el riesgo
if "Elite" in sensibilidad:
    sl_mult, tp_mult, min_vol = 1.0, 2.0, 50000
elif "Balanceado" in sensibilidad:
    sl_mult, tp_mult, min_vol = 1.5, 3.0, 30000
else:
    sl_mult, tp_mult, min_vol = 2.0, 5.0, 10000

# --- FUNCIONES MATEMÁTICAS PURAS (Sin librerías externas que den error) ---
def calcular_indicadores(df):
    # VWAP (Precio Promedio Ponderado por Volumen)
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['vwap'] = (df['tp'] * df['volume']).cumsum() / df['volume'].cumsum()
    
    # EMA 9 y EMA 20 (Tendencia a corto plazo)
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    
    # RSI 14 (Fuerza y Momentum)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ATR 14 (Stop Loss Dinámico)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    return df

# --- ANÁLISIS DEL TICKER ---
def analizar_scalping(symbol):
    try:
        # Descarga rápida y ligera
        df = yf.download(symbol, period="1d", interval="1m", progress=False, prepost=True)
        if df.empty or len(df) < 20: return None
        
        df.columns = [c.lower() for c in df.columns]
        df = calcular_indicadores(df)
        
        # Últimos datos
        actual = df.iloc[-1]
        anterior = df.iloc[-2]
        
        precio = actual['close']
        volumen = actual['volume']
        cambio_pct = ((precio / df['close'].iloc[0]) - 1) * 100
        
        if volumen < min_vol: return None # Filtro de liquidez
        
        # --- LÓGICA DE DETECCIÓN DE TENDENCIA ---
        estado = "Buscando..."
        score = 0
        
        # 1. Inicio de tendencia alcista fuerte
        if precio > actual['vwap'] and actual['ema_9'] > actual['ema_20'] and actual['rsi'] > 50:
            estado = "🚀 INICIO TENDENCIA ALCISTA"
            score += 5
            
            # Detectar subidas explosivas (>3% en minutos)
            if cambio_pct > 3.0:
                estado = "🔥 EXPLOSIÓN ALCISTA (BREAKOUT)"
                score += 3
                
        # 2. Fin de tendencia / Posible caída
        elif actual['rsi'] > 80 and precio < actual['ema_9']:
            estado = "⚠️ FIN DE TENDENCIA (SOBRECOMPRA)"
            score -= 5
            
        # --- CÁLCULO DE RIESGO (TP y SL) ---
        atr = actual['atr'] if pd.notna(actual['atr']) else (precio * 0.01)
        stop_loss = precio - (atr * sl_mult)
        take_profit = precio + (atr * tp_mult)
        
        return {
            "Ticker": symbol,
            "Precio": round(precio, 3),
            "Cambio %": round(cambio_pct, 2),
            "Estado del Activo": estado,
            "RSI": round(actual['rsi'], 1),
            "Stop Loss": round(stop_loss, 3),
            "Take Profit": round(take_profit, 3),
            "Score": score
        }
    except Exception as e:
        return None

# --- EJECUCIÓN PRINCIPAL ---
st.subheader("Buscando oportunidades en el mercado...")

# Usamos una lista estática de alta volatilidad si TwelveData falla para garantizar datos
tickers_volatiles = ["NVDA", "TSLA", "AMD", "SMCI", "MSTR", "COIN", "MARA", "RIOT", "PLTR", "ARM", "SOUN", "GME", "AMC", "RDDT", "DJT"]

resultados = []
progreso = st.progress(0)

# Limitamos a 15 acciones ultrarrápidas para que la nube no colapse
for i, t in enumerate(tickers_volatiles):
    res = analizar_scalping(t)
    if res: resultados.append(res)
    progreso.progress((i + 1) / len(tickers_volatiles))

if resultados:
    df_res = pd.DataFrame(resultados).sort_values(by="Score", ascending=False)
    
    # Formato visual
    def color_estado(val):
        if "INICIO" in val or "EXPLOSIÓN" in val: return 'color: #00FF00; font-weight: bold'
        if "FIN" in val: return 'color: #FF0000; font-weight: bold'
        return 'color: gray'
        
    st.dataframe(df_res.style.map(color_estado, subset=['Estado del Activo']), use_container_width=True, height=500)
    
else:
    st.warning("No se detectaron movimientos fuertes bajo estos parámetros.")
