import streamlit as st
import pandas as pd
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime
import pytz

st.set_page_config(page_title="THUNDER RADAR V83 - DEBUG", layout="wide")

st.markdown("<style>.stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 52px; }</style>", unsafe_allow_html=True)

# ===================== CLAVES =====================
ALPACA_API_KEY = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca():
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

alpaca = get_alpaca()

# ===================== SCORE =====================
def obtener_score(df, gap_pct, ratio_vol):
    actual = df.iloc[-1]
    score = 0
    if actual['Close'] > actual.get('vwap', actual['Close']): score += 3
    if 'ema_9' in actual and 'ema_20' in actual and actual['ema_9'] > actual['ema_20']: score += 3
    if actual['rsi'] > 52: score += 2
    if actual['Volume'] > df['Volume'].rolling(20).mean().iloc[-1]: score += 2
    
    if gap_pct > 0.8: score += 4
    if gap_pct > 2.0: score += 3
    if ratio_vol > 2.5: score += 3
    
    return min(score, 10)

def get_market_session():
    tz = pytz.timezone('US/Eastern')
    now = datetime.now(tz)
    if now < now.replace(hour=9, minute=30): return "PRE-MARKET"
    elif now > now.replace(hour=16, minute=0): return "AFTER-HOURS"
    else: return "REGULAR"

session = get_market_session()

# ===================== SIDEBAR =====================
st.sidebar.header(f"🏛️ {session}")
modo = st.sidebar.selectbox("Filtro", ["Gap Up Scalping", "Explosión Momentum"], index=0)

st.sidebar.subheader("Precio")
precio_min = st.sidebar.number_input("Precio Mín $", value=0.01, step=0.01)
precio_max = st.sidebar.number_input("Precio Máx $", value=200.0, step=1.0)

st.sidebar.subheader("Volumen")
vol_min = st.sidebar.number_input("Volumen Mín 5m", value=100, step=50, help="Bájalo mucho en pre-market")
vol_max = st.sidebar.number_input("Volumen Máx", value=999999999, step=10000)

sensibilidad = st.sidebar.slider("Sensibilidad (Score mínimo)", 3, 9, 4)

usar_manual = st.sidebar.toggle("Usar Mis Tickers")
if usar_manual:
    tickers_str = st.sidebar.text_input("Tickers (coma)", "IMMP,BIRD,AGAE,VSA,JXZN,KUST,UPC,ATHR,TSLA,NVDA")
    lista_tickers = [x.strip().upper() for x in tickers_str.split(",") if x.strip()]
else:
    lista_tickers = ["IMMP","BIRD","AGAE","VSA","JXZN","KUST","UPC","ATHR","TSLA","NVDA","AMD","GME","AMC","MARA","RIOT",
                     "COIN","PLTR","SOFI","MSTR","UPST","AFRM","HOOD","BABA","NIO","LCID","RIVN","SOUN","SMCI","ASTS",
                     "LUNR","RKLB","OKLO","QBTS","IONQ","SERV","BITF","HUT","CLSK","WULF","IREN"]

# ===================== MAIN =====================
st.title("⚡ THUNDER RADAR V83 - DEBUG MODE")
st.caption("Pre-Market / After-Hours • Detectando como Webull")

if st.button("🚀 INICIAR ESCANEO DE MOMENTUM", type="primary", use_container_width=True):
    with st.spinner(f"Escaneando {session}..."):
        progress = st.progress(0)
        resultados = []
        total = len(lista_tickers)
        
        for i, t in enumerate(lista_tickers):
            progress.progress((i+1)/total)
            try:
                df = yf.download(t, period="2d", interval="5m", prepost=True, progress=False)
                df = df.dropna()
                
                if len(df) < 15:
                    st.write(f"⚠️ {t}: Pocos datos ({len(df)} velas)")
                    continue
                
                # Cálculos
                df['ema_9'] = df['Close'].ewm(span=9).mean()
                df['ema_20'] = df['Close'].ewm(span=20).mean()
                tp = (df['High'] + df['Low'] + df['Close']) / 3
                df['vwap'] = (tp * df['Volume']).cumsum() / df['Volume'].cumsum()
                
                delta = df['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = -delta.where(delta < 0, 0).rolling(14).mean()
                df['rsi'] = 100 - (100 / (1 + (gain / loss)))
                
                df['atr'] = (df['High'] - df['Low']).rolling(14).mean()
                
                actual = df.iloc[-1]
                precio = round(float(actual['Close']), 2)
                
                if not (precio_min <= precio <= precio_max): continue
                if not (vol_min <= int(actual['Volume']) <= vol_max): continue
                
                gap_pct = ((actual['Close'] - actual['Open']) / actual['Open']) * 100
                vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
                ratio_vol = actual['Volume'] / vol_avg if vol_avg > 0 else 0
                
                score = obtener_score(df, gap_pct, ratio_vol)
                
                if score < sensibilidad: continue
                
                estado = "🔥 SOBRECOMPRA" if actual['rsi'] >= 70 else "🧊 SOBREVENTA" if actual['rsi'] <= 30 else "⚖️ NEUTRAL"
                
                resultados.append({
                    "Ticker": t,
                    "Precio": precio,
                    "Score": score,
                    "Gap %": round(gap_pct, 2),
                    "Volumen": int(actual['Volume']),
                    "Ratio Vol": round(ratio_vol, 2),
                    "RSI": round(float(actual['rsi']), 1),
                    "ATR": round(float(actual['atr']), 3)
                })
                
            except Exception as e:
                st.write(f"❌ Error {t}: {str(e)[:80]}")
                continue
        
        progress.empty()
        
        if resultados:
            df_res = pd.DataFrame(resultados).sort_values(by="Score", ascending=False)
            st.success(f"✅ Encontradas {len(df_res)} oportunidades!")
            st.dataframe(df_res, use_container_width=True, height=600)
            
            # Compra rápida
            st.divider()
            col1, col2 = st.columns([1,2])
            with col1:
                st.subheader("🛒 Compra Rápida")
                ticker_compra = st.selectbox("Elegir", df_res['Ticker'])
                qty = st.number_input("Cantidad", 1, 1000, 1)
                if st.button("🟢 EJECUTAR COMPRA + SL/TP", type="primary"):
                    row = df_res[df_res['Ticker'] == ticker_compra].iloc[0]
                    try:
                        req = MarketOrderRequest(
                            symbol=ticker_compra, qty=qty, side=OrderSide.BUY,
                            time_in_force=TimeInForce.GTC,
                            take_profit=TakeProfitRequest(limit_price=row.get('Take Profit', row['Precio']*1.05)),
                            stop_loss=StopLossRequest(stop_price=row.get('Stop Loss', row['Precio']*0.95))
                        )
                        alpaca.submit_order(req)
                        st.success(f"Orden enviada: {ticker_compra}")
                    except Exception as ex:
                        st.error(f"Error Alpaca: {ex}")
        else:
            st.error("🚫 **Ninguna oportunidad encontrada**")
            st.info("""
            **Consejos para Pre-Market:**
            1. Baja Volumen Mín a **100** o **50**
            2. Baja Sensibilidad a **3** o **4**
            3. Activa "Usar Mis Tickers" y pega los de Webull: `IMMP,BIRD,AGAE,VSA,JXZN,KUST`
            4. Pulsa ACTUALIZAR TODO y vuelve a escanear
            """)

st.caption("V83 - Con depuración visible • Dime qué ves después de probar")
