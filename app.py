import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime
import pytz

# ===================== CONFIGURACIÓN =====================
st.set_page_config(page_title="THUNDER RADAR V82 - AUTO DETECTOR", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #1e2130; padding: 12px; border-radius: 10px; border: 2px solid #4a4d61; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 52px; }
    </style>
    """, unsafe_allow_html=True)

# ===================== CLAVES ALPACA =====================
ALPACA_API_KEY = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca():
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

alpaca = get_alpaca()

# ===================== LÓGICA DE SCORE =====================
def obtener_score(df, gap_pct, ratio_vol):
    actual = df.iloc[-1]
    score_up = 0
    if actual['Close'] > actual.get('vwap', actual['Close']): score_up += 3
    if actual['ema_9'] > actual['ema_20']: score_up += 3
    if actual['rsi'] > 55: score_up += 2
    if actual['Volume'] > df['Volume'].rolling(20).mean().iloc[-1]: score_up += 2
    
    # DETECCIÓN FUERTE DE DESPEGUE
    if gap_pct > 0.5: score_up += 3
    if gap_pct > 1.0: score_up += 2
    if ratio_vol > 3.0: score_up += 2
    
    if actual['rsi'] > 80: score_up = max(0, score_up - 2)
    return min(score_up, 10), 0

# ===================== SESIÓN =====================
def get_market_session():
    tz = pytz.timezone('US/Eastern')
    now = datetime.now(tz)
    if now < now.replace(hour=9, minute=30, second=0): return "PRE-MARKET"
    elif now > now.replace(hour=16, minute=0, second=0): return "AFTER-HOURS"
    else: return "REGULAR"

session = get_market_session()

# ===================== BARRA LATERAL =====================
st.sidebar.header(f"🏛️ ESTADO: {session} 🌍")
modo_radar = st.sidebar.selectbox("🔍 Filtro de Radar", 
                                 ["Gap Up Scalping", "Explosión Momentum", "Personalizado"], index=0)

st.sidebar.subheader("📊 Filtros de Precio")
precio_min = st.sidebar.number_input("Precio Mín $", value=0.01, step=0.01)
precio_max = st.sidebar.number_input("Precio Máx $", value=150.0, step=1.0)

st.sidebar.subheader("📈 FILTRO DE VOLUMEN")
vol_min = st.sidebar.number_input("Volumen Mín por barra 5m", value=500, step=100,
                                 help="Bájalo más si quieres ver pops con volumen muy bajo")
vol_max = st.sidebar.number_input("Volumen Máx por barra 5m (opcional)", value=999999999, step=10000)

st.sidebar.subheader("⚙️ Sensibilidad Radar")
sensibilidad = st.sidebar.slider("Score mínimo para alertar", 3, 8, 4,
                                help="4 es ideal para pre-market/after-hours")

if st.sidebar.toggle("Usar Mis Tickers (manual)"):
    tickers_input = st.sidebar.text_input("Lista de tickers (separados por coma)", 
                                         "IMMP,BIRD,AGAE,VSA,JXZN,KUST,UPC,ATHR",
                                         help="Pega aquí los de Webull Top Gainers")
    lista_tickers = [x.strip().upper() for x in tickers_input.split(",") if x.strip()]
else:
    # LISTA AMPLIADA CON LOS QUE ESTÁN EXPLOTANDO HOY + 60+ volátiles
    lista_tickers = ["IMMP","BIRD","AGAE","VSA","JXZN","KUST","UPC","ATHR","TSLA","NVDA","AMD","GME","AMC","MARA",
                     "RIOT","COIN","PLTR","SOFI","MSTR","UPST","AFRM","HOOD","BABA","NIO","LCID","RIVN","NKLA",
                     "SOUN","SMCI","ASTS","LUNR","RKLB","OKLO","QBTS","IONQ","SERV","BITF","HUT","CLSK","WULF",
                     "IREN","SNAL","PMNT","AVNS","TVTX","XNDU","BE","RGTI","JBLU"]

# ===================== INTERFAZ =====================
col1, col2 = st.columns([3, 1])
with col1:
    st.title("⚡ THUNDER RADAR V82 - AUTO DETECTOR")
    st.caption("Ahora detecta los mismos que Webull • Pre-Market / After-Hours / Regular")
with col2:
    if st.button("🔄 ACTUALIZAR TODO", use_container_width=True):
        st.rerun()

# Posiciones (sin cambios)
st.subheader("💼 Mis Posiciones en Tiempo Real")
try:
    positions = alpaca.get_all_positions()
    if positions:
        # ... (mismo código de posiciones que antes)
        pos_data = []
        for p in positions:
            pnl = float(p.unrealized_plpc) * 100
            pos_data.append({
                "Ticker": p.symbol, "Cant": p.qty, "Entrada": round(float(p.avg_entry_price), 2),
                "Precio Act.": round(float(p.current_price), 2),
                "P&L %": f"{round(pnl, 2)}%", "Valor": f"${round(float(p.market_value), 2)}"
            })
        st.dataframe(pd.DataFrame(pos_data), use_container_width=True)
        c1, c2 = st.columns(2)
        with c1: t_sell = st.selectbox("Cerrar posición", [p['Ticker'] for p in pos_data])
        with c2:
            if st.button("🔴 VENTA INMEDIATA (Market)", type="secondary"):
                alpaca.close_position(t_sell)
                st.success(f"✅ {t_sell} cerrada")
                st.rerun()
    else:
        st.info("No tienes posiciones abiertas.")
except Exception as e:
    st.error(f"Error posiciones: {e}")

st.divider()

if st.button("🚀 INICIAR ESCANEO DE MOMENTUM", use_container_width=True, type="primary"):
    with st.spinner(f"Escaneando {session} en tiempo real..."):
        data_all = yf.download(lista_tickers, period="2d", interval="5m", group_by='ticker', prepost=True, progress=False)
        
        resultados = []
        for t in lista_tickers:
            try:
                t = t.strip().upper()
                df = data_all[t].dropna()
                if len(df) < 20: continue

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
                precio = round(actual['Close'], 2)
                
                if not (precio_min <= precio <= precio_max): continue
                if not (vol_min <= actual['Volume'] <= vol_max): continue
                
                gap_pct = ((actual['Close'] - df['Open'].iloc[-1]) / df['Open'].iloc[-1]) * 100
                vol_promedio = df['Volume'].rolling(20).mean().iloc[-1]
                ratio_vol = actual['Volume'] / vol_promedio if vol_promedio > 0 else 0
                
                s_alcista, _ = obtener_score(df, gap_pct, ratio_vol)
                
                if s_alcista < sensibilidad: continue
                
                estado_rsi = "🔥 SOBRECOMPRA" if actual['rsi'] >= 70 else "🧊 SOBREVENTA" if actual['rsi'] <= 30 else "⚖️ NEUTRAL"
                v_score = min(int(ratio_vol * 4), 10)
                atr = actual['atr']
                sl = round(precio - (atr * 2), 2)
                tp = round(precio + (atr * 4), 2)
                
                resultados.append({
                    "Ticker": t, "Precio": precio, "Score 🐂": s_alcista,
                    "Gap Pop %": round(gap_pct, 2), "Estado RSI": estado_rsi, "RSI": round(actual['rsi'], 1),
                    "ATR": f"${round(atr, 3)}", "Stop Loss": sl, "Take Profit": tp,
                    "Vol Score": f"{v_score}/10", "Volumen": int(actual['Volume']), "Ratio Vol": round(ratio_vol, 2)
                })
            except:
                continue
        
        if resultados:
            df_res = pd.DataFrame(resultados)
            
            if modo_radar == "Gap Up Scalping":
                df_res = df_res[df_res["Gap Pop %"] > 0.3].sort_values(by="Gap Pop %", ascending=False)
                st.success("🎯 MODO GAP UP SCALPING - Detectando despegues fuertes")
            elif modo_radar == "Explosión Momentum":
                df_res = df_res.sort_values(by="Score 🐂", ascending=False)
            else:
                df_res = df_res.sort_values(by=["Score 🐂", "Gap Pop %"], ascending=False)
            
            st.subheader("🎯 OPORTUNIDADES DE DESPEGUE DETECTADAS")
            st.dataframe(df_res, use_container_width=True, height=500)
            
            # Panel de compra rápida (sin cambios)
            st.divider()
            col_buy1, col_buy2 = st.columns([1, 2])
            with col_buy1:
                st.subheader("🛒 COMPRA RÁPIDA")
                t_buy = st.selectbox("Seleccionar ticker", df_res['Ticker'].tolist())
                row = df_res[df_res['Ticker'] == t_buy].iloc[0]
                cant = st.number_input("Cantidad de acciones", value=1, min_value=1)
                if st.button("🟢 EJECUTAR COMPRA PROTEGIDA (SL + TP)", use_container_width=True, type="primary"):
                    try:
                        req = MarketOrderRequest(symbol=t_buy, qty=cant, side=OrderSide.BUY,
                                                 time_in_force=TimeInForce.GTC,
                                                 take_profit=TakeProfitRequest(limit_price=row['Take Profit']),
                                                 stop_loss=StopLossRequest(stop_price=row['Stop Loss']))
                        alpaca.submit_order(req)
                        st.success(f"✅ ¡ORDEN ENVIADA! {t_buy} | SL: ${row['Stop Loss']} | TP: ${row['Take Profit']}")
                    except Exception as e:
                        st.error(f"❌ Error Alpaca: {e}")
            with col_buy2:
                st.info(f"**Análisis de {t_buy}**\nScore: **{row['Score 🐂']}/10**  •  Despegue: **{row['Gap Pop %']}%**  •  Volumen: **{row['Vol Score']}**")
        else:
            st.warning("🚫 No se detectaron despegues fuertes.")
            st.info("**Tip:** Activa 'Usar Mis Tickers' y pega los símbolos de Webull Top Gainers (ej: IMMP,BIRD,AGAE,VSA,JXZN,KUST...)")
