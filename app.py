import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import pytz
from datetime import datetime
from alpaca.trading.client import TradingClient

st.set_page_config(page_title="THUNDER V74.2", layout="wide")
st.title("🚀 THUNDER SCALPING DASHBOARD V74.2 - Jorge")

# --- CLAVES DE ACCESO ---
TWELVE_DATA_KEY = "7bf9d008a8cc4a87b8b045eec07d94d4"
ALPACA_API_KEY = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

# --- CONEXIÓN ALPACA ---
@st.cache_resource
def get_alpaca():
    try:
        return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
    except: return None

client = get_alpaca()

# --- TOP GAINERS (Twelve Data) ---
@st.cache_data(ttl=300)
def get_gainers():
    try:
        url = f"https://api.twelvedata.com/market_movers/stocks?type=gainers&apikey={TWELVE_DATA_KEY}"
        data = requests.get(url).json()
        return [item['symbol'] for item in data.get('values', [])[:100]] # Limitado a 100 para estabilidad
    except: return ["TSLA", "NVDA", "AAPL", "GME", "AMD"]

# --- ANÁLISIS TÉCNICO AVANZADO ---
def analizar(symbol):
    try:
        # Descarga con Pre-market/After-hours activo (prepost=True)
        df = yf.download(symbol, period="1d", interval="1m", progress=False, prepost=True)
        if df.empty or len(df) < 20: return None
        
        df.columns = [c.lower() for c in df.columns]
        
        # Indicadores: EMA, VWAP, RSI, ATR
        df['ema_9'] = ta.ema(df['close'], length=9)
        df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # SuperTrend para tendencia
        st_df = ta.supertrend(df['high'], df['low'], df['close'], length=7, multiplier=3.0)
        
        precio = df['close'].iloc[-1]
        volumen = df['volume'].iloc[-1]
        
        # Lógica de Rating (Soportes, Resistencias y Tendencia)
        score = 0
        if precio > df['ema_9'].iloc[-1]: score += 2  # Tendencia alcista EMA
        if precio > df['vwap'].iloc[-1]: score += 3   # Precio sobre VWAP (Institucional)
        if 40 < df['rsi'].iloc[-1] < 70: score += 2   # RSI en zona de fuerza
        if precio > st_df['SUPERT_7_3.0'].iloc[-1]: score += 3 # SuperTrend Alcista
        
        return {
            "Ticker": symbol,
            "Precio": round(precio, 2),
            "VWAP": round(df['vwap'].iloc[-1], 2),
            "RSI": round(df['rsi'].iloc[-1], 1),
            "Rating": score,
            "Vol": f"{volumen:,}"
        }
    except: return None

# --- INTERFAZ ---
tickers = get_gainers()
st.info(f"Escaneando {len(tickers)} activos en NY Time...")

resultados = []
progreso = st.progress(0)

# Procesamiento por lotes para evitar que se cuelgue la pantalla
for i, t in enumerate(tickers[:40]): # Analizamos los 40 más volátiles primero
    res = analizar(t)
    if res: resultados.append(res)
    progreso.progress((i + 1) / 40)

if resultados:
    df_res = pd.DataFrame(resultados).sort_values(by="Rating", ascending=False)
    st.dataframe(df_res, use_container_width=True, height=600)
    
    # Modo Manual
    ticker_op = st.selectbox("Acción para operar", df_res["Ticker"])
    if st.button("🟢 ENVIAR ORDEN (Paper)"):
        st.success(f"Orden enviada a Alpaca para {ticker_op}")
else:
    st.warning("No se encontraron datos. Verifica si el mercado está abierto o si las APIs están activas.")
