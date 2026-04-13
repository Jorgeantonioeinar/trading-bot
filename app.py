import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import pytz
from datetime import datetime
from alpaca.trading.client import TradingClient

st.set_page_config(page_title="THUNDER V74.1", layout="wide")
st.title("🚀 THUNDER SCALPING DASHBOARD V74.1 - Jorge")

# --- CONFIGURACIÓN DE CLAVES ---
TWELVE_DATA_KEY = "7bf9d008a8cc4a87b8b045eec07d94d4"
ALPACA_API_KEY = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

# --- CONEXIÓN ALPACA ---
@st.cache_resource
def get_alpaca():
    try:
        return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
    except:
        return None

client = get_alpaca()

# --- BUSCADOR DE TOP GAINERS (Twelve Data) ---
@st.cache_data(ttl=300)
def get_top_gainers():
    try:
        url = f"https://api.twelvedata.com/market_movers/stocks?type=gainers&apikey={TWELVE_DATA_KEY}"
        data = requests.get(url).json()
        return [item['symbol'] for item in data.get('values', [])[:200]]
    except:
        return ["TSLA", "NVDA", "AMD", "AAPL", "GME", "AMC"]

# --- MOTOR DE ANÁLISIS TÉCNICO ---
def analizar_ticker(symbol):
    try:
        # Descarga rápida de datos (1 día, intervalo 1 min)
        df = yf.download(symbol, period="1d", interval="1m", progress=False, prepost=True)
        if df.empty or len(df) < 20: return None
        
        df.columns = [c.lower() for c in df.columns]
        
        # --- INDICADORES ---
        df['ema_9'] = ta.ema(df['close'], length=9)
        df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        df['rsi'] = ta.rsi(df['close'], length=14)
        # SuperTrend
        st_df = ta.supertrend(df['high'], df['low'], df['close'], length=7, multiplier=3)
        
        precio = df['close'].iloc[-1]
        cambio = ((precio / df['close'].iloc[0]) - 1) * 100
        volumen = df['volume'].iloc[-1]
        
        # --- LÓGICA DE RATINGS ---
        score = 0
        if precio > df['ema_9'].iloc[-1]: score += 2
        if precio > df['vwap'].iloc[-1]: score += 3
        if df['rsi'].iloc[-1] < 70 and df['rsi'].iloc[-1] > 40: score += 2
        if precio > st_df['SUPERT_7_3.0'].iloc[-1]: score += 3
        
        return {
            "Ticker": symbol,
            "Precio": round(precio, 2),
            "Cambio%": round(cambio, 2),
            "VWAP": round(df['vwap'].iloc[-1], 2),
            "RSI": round(df['rsi'].iloc[-1], 1),
            "Rating": score,
            "Vol": f"{volumen:,}"
        }
    except:
        return None

# --- UI PRINCIPAL ---
tickers = get_top_gainers()
st.info(f"Analizando {len(tickers)} acciones en tiempo real...")

resultados = []
progress_bar = st.progress(0)

# Analizamos solo los primeros 50 para evitar que Streamlit se bloquee por tiempo
for i, t in enumerate(tickers[:50]):
    res = analizar_ticker(t)
    if res: resultados.append(res)
    progress_bar.progress((i + 1) / 50)

if resultados:
    df_res = pd.DataFrame(resultados).sort_values(by="Rating", ascending=False)
    st.dataframe(df_res, use_container_width=True)
else:
    st.error("No se pudieron obtener datos. Verifica tu conexión o el horario del mercado.")
