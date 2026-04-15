import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime
import pytz
import time

# ─────────────────────────────────────────────
#  CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="THUNDER RADAR V90 ULTRA",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
#  ESTILOS ULTRA PRO
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');

html, body, [class*="css"] {
    background-color: #050a14 !important;
    color: #c9d1d9 !important;
    font-family: 'Share Tech Mono', monospace;
}

h1, h2, h3 { font-family: 'Orbitron', sans-serif !important; }

.stButton>button {
    width: 100%;
    border-radius: 4px;
    font-weight: bold;
    font-family: 'Orbitron', sans-serif;
    letter-spacing: 1px;
    border: 1px solid #30363d;
    transition: all 0.2s;
}
.stButton>button:hover { transform: translateY(-1px); box-shadow: 0 0 12px rgba(0,255,136,0.4); }

div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 12px;
}

.score-bar-up   { color: #00ff88; font-weight: bold; font-size: 1.1em; }
.score-bar-down { color: #ff4444; font-weight: bold; font-size: 1.1em; }
.badge-buy  { background:#00ff88; color:#000; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:0.75em; }
.badge-sell { background:#ff4444; color:#fff; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:0.75em; }
.badge-neutral { background:#ffc107; color:#000; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:0.75em; }
.badge-premarket  { background:#7c3aed; color:#fff; padding:2px 8px; border-radius:4px; font-size:0.75em; }
.badge-afterhours { background:#0369a1; color:#fff; padding:2px 8px; border-radius:4px; font-size:0.75em; }
.badge-regular    { background:#15803d; color:#fff; padding:2px 8px; border-radius:4px; font-size:0.75em; }

.header-glow {
    text-align: center;
    font-family: 'Orbitron', sans-serif;
    font-size: 2.2em;
    font-weight: 900;
    background: linear-gradient(90deg, #00ff88, #00b4d8, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 3px;
    margin-bottom: 0;
}

.subheader-dim { text-align:center; color:#8b949e; font-size:0.85em; margin-top:0; letter-spacing:4px; }

table { width: 100%; }
thead tr th { background-color: #161b22 !important; color: #00ff88 !important; font-family: 'Orbitron', sans-serif; font-size: 0.75em; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  CREDENCIALES ALPACA
# ─────────────────────────────────────────────
ALPACA_API_KEY    = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca():
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

alpaca = get_alpaca()

# ─────────────────────────────────────────────
#  UNIVERSO DE ACCIONES (200+)
# ─────────────────────────────────────────────
UNIVERSO_COMPLETO = [
    # Mega-cap tech
    "AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","NFLX","AMD","INTC",
    # Semiconductores
    "AVGO","QCOM","MU","AMAT","LRCX","KLAC","MRVL","ON","TXN","ADI",
    # Fintech / Cripto proxy
    "COIN","HOOD","MSTR","RIOT","MARA","HUT","CIFR","BTBT","CLSK","WULF",
    # EV / Clean Energy
    "NIO","XPEV","LI","RIVN","LCID","CHPT","BLNK","PLUG","FCEL","BE",
    # Biotech / Pharma
    "MRNA","BNTX","NVAX","VRTX","REGN","BIIB","GILD","ABBV","PFE","JNJ",
    # Meme / Alta volatilidad
    "GME","AMC","BBBY","KOSS","EXPR","BB","NOK","SNDL","CLOV","WISH",
    # Cloud / SaaS
    "CRM","NOW","SNOW","DDOG","ZS","CRWD","OKTA","PLTR","S","NET",
    # Retail / Consumer
    "WMT","TGT","COST","HD","LOW","NKE","SBUX","MCD","DIS","CMCSA",
    # Financiero
    "JPM","BAC","GS","MS","WFC","C","BLK","SCHW","AXP","V",
    # Healthcare
    "UNH","CVS","MCK","ABC","AET","HUM","CI","MOH","CNC","WCG",
    # Industrial / Defensa
    "BA","LMT","RTX","NOC","GD","CAT","DE","MMM","HON","GE",
    # Media / Entretenimiento
    "PARA","WBD","FOXA","NWSA","NYT","SPOT","ROKU","FUBO","SIRI","LUMN",
    # Speculative / Small cap alta vol
    "SOFI","UPST","AFRM","OPEN","OPENDOOR","LMND","ROOT","HIMS","BABA","JD",
    "TCOM","PDD","DIDI","TUYA","TIGR","FUTU","LNKD","GRAB","SEA","SHOP",
    # ETFs de momentum
    "QQQ","SPY","IWM","SOXL","TQQQ","ARKK","XLE","XLF","XLK","UVXY",
    # Más acciones volátiles
    "PTON","ZM","DOCU","TDOC","LYFT","UBER","DASH","ABNB","VRBO","W",
    "ETSY","EBAY","PINS","SNAP","TWTR","RBLX","U","MTTR","IONQ","RGTI",
]
# Deduplicar
UNIVERSO_COMPLETO = list(dict.fromkeys(UNIVERSO_COMPLETO))

# ─────────────────────────────────────────────
#  HELPERS DE SESIÓN DE MERCADO
# ─────────────────────────────────────────────
def get_market_session():
    tz  = pytz.timezone('US/Eastern')
    now = datetime.now(tz)
    pre_open     = now.replace(hour=4,  minute=0,  second=0, microsecond=0)
    market_open  = now.replace(hour=9,  minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0,  second=0, microsecond=0)
    after_close  = now.replace(hour=20, minute=0,  second=0, microsecond=0)

    if now < pre_open:        return "CERRADO"
    elif now < market_open:   return "PRE-MARKET"
    elif now < market_close:  return "REGULAR"
    elif now < after_close:   return "AFTER-HOURS"
    else:                     return "CERRADO"

SESSION_BADGES = {
    "PRE-MARKET":  "badge-premarket",
    "AFTER-HOURS": "badge-afterhours",
    "REGULAR":     "badge-regular",
    "CERRADO":     "badge-neutral",
}

session = get_market_session()

# ─────────────────────────────────────────────
#  CÁLCULOS TÉCNICOS COMPLETOS
# ─────────────────────────────────────────────
def calcular_indicadores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # EMAs
    df['ema_9']  = df['Close'].ewm(span=9,  adjust=False).mean()
    df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['Close'].ewm(span=50, adjust=False).mean()

    # VWAP (intraday)
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['vwap'] = (tp * df['Volume']).cumsum() / df['Volume'].cumsum()

    # RSI 14
    delta = df['Close'].diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['macd']        = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist']   = df['macd'] - df['macd_signal']

    # Bandas de Bollinger
    sma20 = df['Close'].rolling(20).mean()
    std20 = df['Close'].rolling(20).std()
    df['bb_upper'] = sma20 + 2 * std20
    df['bb_lower'] = sma20 - 2 * std20
    df['bb_mid']   = sma20

    # ATR 14
    hl  = df['High'] - df['Low']
    hc  = (df['High'] - df['Close'].shift(1)).abs()
    lc  = (df['Low']  - df['Close'].shift(1)).abs()
    df['atr'] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean()

    # Soporte y Resistencia (pivots simples con ventana de 20 velas)
    df['soporte']    = df['Low'].rolling(20).min()
    df['resistencia']= df['High'].rolling(20).max()

    # Volumen promedio 20 velas
    df['vol_avg20'] = df['Volume'].rolling(20).mean()

    # Stochastic %K %D
    low14  = df['Low'].rolling(14).min()
    high14 = df['High'].rolling(14).max()
    df['stoch_k'] = 100 * (df['Close'] - low14) / (high14 - low14).replace(0, np.nan)
    df['stoch_d'] = df['stoch_k'].rolling(3).mean()

    return df


def calcular_score(df: pd.DataFrame, session: str):
    """Devuelve (score_alcista 1-10, score_bajista 1-10, señal, detalles)"""
    a = df.iloc[-1]
    p = df.iloc[-2] if len(df) > 1 else df.iloc[-1]

    # ── Pesos según sesión ──────────────────────────────────────────
    # En pre/after los volúmenes son bajos → reducimos peso del volumen
    # y subimos sensibilidad de precio vs VWAP y EMAs cortas
    if session == "REGULAR":
        w_vwap, w_ema, w_rsi, w_vol, w_macd, w_bb, w_stoch = 2, 2, 1.5, 1.5, 1, 1, 1
    else:  # PRE / AFTER → más sensible a precio y EMAs
        w_vwap, w_ema, w_rsi, w_vol, w_macd, w_bb, w_stoch = 2.5, 2.5, 1.5, 0.5, 1, 1, 1

    up = down = 0.0
    detalles = {}

    # VWAP
    if a['Close'] > a['vwap']:
        up += w_vwap; detalles['VWAP'] = '▲ Precio sobre VWAP'
    else:
        down += w_vwap; detalles['VWAP'] = '▼ Precio bajo VWAP'

    # EMA cruce 9/20
    if a['ema_9'] > a['ema_20']:
        up += w_ema; detalles['EMA'] = '▲ EMA9 > EMA20 (alcista)'
    else:
        down += w_ema; detalles['EMA'] = '▼ EMA9 < EMA20 (bajista)'

    # EMA precio vs EMA50
    if a['Close'] > a['ema_50']:
        up += 0.5; detalles['EMA50'] = '▲ Sobre EMA50'
    else:
        down += 0.5; detalles['EMA50'] = '▼ Bajo EMA50'

    # RSI
    if a['rsi'] > 60:
        up += w_rsi; detalles['RSI'] = f"▲ RSI fuerte ({a['rsi']:.0f})"
    elif a['rsi'] < 40:
        down += w_rsi; detalles['RSI'] = f"▼ RSI débil ({a['rsi']:.0f})"
    elif a['rsi'] > 50:
        up += w_rsi * 0.5; detalles['RSI'] = f"→ RSI neutro-alcista ({a['rsi']:.0f})"
    else:
        down += w_rsi * 0.5; detalles['RSI'] = f"→ RSI neutro-bajista ({a['rsi']:.0f})"

    # Volumen vs promedio
    vol_ratio = a['Volume'] / a['vol_avg20'] if a['vol_avg20'] > 0 else 1
    if vol_ratio > 1.5:
        if a['Close'] >= p['Close']:
            up += w_vol; detalles['VOL'] = f"▲ Volumen explosivo ({vol_ratio:.1f}x avg)"
        else:
            down += w_vol; detalles['VOL'] = f"▼ Volumen bajista ({vol_ratio:.1f}x avg)"
    else:
        detalles['VOL'] = f"→ Volumen normal ({vol_ratio:.1f}x avg)"

    # MACD
    if a['macd_hist'] > 0 and a['macd_hist'] > p.get('macd_hist', 0):
        up += w_macd; detalles['MACD'] = '▲ MACD histograma creciente'
    elif a['macd_hist'] < 0 and a['macd_hist'] < p.get('macd_hist', 0):
        down += w_macd; detalles['MACD'] = '▼ MACD histograma cayendo'
    elif a['macd'] > a['macd_signal']:
        up += w_macd * 0.5; detalles['MACD'] = '→ MACD sobre señal'
    else:
        down += w_macd * 0.5; detalles['MACD'] = '→ MACD bajo señal'

    # Bollinger Bands
    bb_pos = (a['Close'] - a['bb_lower']) / (a['bb_upper'] - a['bb_lower'] + 1e-9)
    if bb_pos > 0.8:
        up += w_bb * 0.5; detalles['BB'] = f"▲ Precio en zona alta BB ({bb_pos:.0%})"
    elif bb_pos < 0.2:
        down += w_bb; detalles['BB'] = f"▼ Precio en zona baja BB ({bb_pos:.0%})"
    else:
        detalles['BB'] = f"→ BB zona media ({bb_pos:.0%})"

    # Stochastic
    if a['stoch_k'] > 80:
        detalles['STOCH'] = f"⚠️ Sobrecompra Stoch K={a['stoch_k']:.0f}"
        up -= 0.5
    elif a['stoch_k'] < 20:
        detalles['STOCH'] = f"⚠️ Sobreventa Stoch K={a['stoch_k']:.0f}"
        down -= 0.5
    elif a['stoch_k'] > a['stoch_d']:
        up += w_stoch; detalles['STOCH'] = f"▲ Stoch K>D ({a['stoch_k']:.0f})"
    else:
        down += w_stoch; detalles['STOCH'] = f"▼ Stoch K<D ({a['stoch_k']:.0f})"

    # Normalizar a 1-10
    max_score = w_vwap + w_ema + 0.5 + w_rsi + w_vol + w_macd + w_bb + w_stoch
    s_up   = max(1, min(10, round((up   / max_score) * 10)))
    s_down = max(1, min(10, round((down / max_score) * 10)))

    # Señal principal
    if s_up >= 7:
        senal = "COMPRA"
    elif s_down >= 7:
        senal = "VENTA"
    elif s_up >= 5:
        senal = "ALCISTA"
    elif s_down >= 5:
        senal = "BAJISTA"
    else:
        senal = "NEUTRO"

    return s_up, s_down, senal, detalles


def calcular_sl_tp_dinamico(df: pd.DataFrame, precio: float, senal: str, atr_mult_sl=2.0, atr_mult_tp=4.0):
    """Stop Loss y Take Profit basados en ATR + soporte/resistencia"""
    a = df.iloc[-1]
    atr = a['atr'] if not np.isnan(a['atr']) else precio * 0.01

    if senal in ("COMPRA", "ALCISTA"):
        sl = round(max(precio - atr * atr_mult_sl, a['soporte'] * 0.998), 4)
        tp = round(min(precio + atr * atr_mult_tp, a['resistencia'] * 0.998), 4)
    else:
        sl = round(min(precio + atr * atr_mult_sl, a['resistencia'] * 1.002), 4)
        tp = round(max(precio - atr * atr_mult_tp, a['soporte'] * 1.002), 4)

    rr = round(abs(tp - precio) / max(abs(precio - sl), 1e-6), 2)
    return sl, tp, rr


# ─────────────────────────────────────────────
#  ESCANEO PRINCIPAL
# ─────────────────────────────────────────────
def escanear_mercado(tickers, precio_min, precio_max, cambio_min_pct, session,
                     vol_min=0, top_n=50):
    """Descarga y analiza todos los tickers. Devuelve DataFrame de resultados."""
    interval = "1m" if session != "REGULAR" else "2m"
    period   = "1d"

    resultados = []
    progress   = st.progress(0, text="Descargando datos...")
    total      = len(tickers)

    # Descarga en lotes de 50 para no saturar yfinance
    chunk_size = 50
    dfs_raw    = {}

    for i in range(0, total, chunk_size):
        chunk = tickers[i:i+chunk_size]
        try:
            raw = yf.download(
                chunk, period=period, interval=interval,
                group_by='ticker', prepost=True, progress=False,
                threads=True, auto_adjust=True
            )
            for t in chunk:
                try:
                    if len(chunk) == 1:
                        dfs_raw[t] = raw.dropna()
                    else:
                        dfs_raw[t] = raw[t].dropna() if t in raw.columns.get_level_values(0) else pd.DataFrame()
                except Exception:
                    dfs_raw[t] = pd.DataFrame()
        except Exception:
            pass
        progress.progress(min((i + chunk_size) / total, 1.0),
                          text=f"Descargando... {min(i+chunk_size, total)}/{total}")

    progress.empty()
    analisis_bar = st.progress(0, text="Analizando señales...")

    for idx, t in enumerate(tickers):
        try:
            df = dfs_raw.get(t, pd.DataFrame())
            if df is None or len(df) < 20:
                continue

            df = calcular_indicadores(df)
            a  = df.iloc[-1]
            precio = float(a['Close'])

            if not (precio_min <= precio <= precio_max):
                continue

            # Filtro cambio % mínimo (vs apertura del día)
            precio_open = float(df['Open'].iloc[0])
            cambio_pct  = ((precio - precio_open) / precio_open) * 100 if precio_open > 0 else 0

            if abs(cambio_pct) < cambio_min_pct:
                continue

            # Filtro volumen mínimo
            vol_actual = int(a['Volume'])
            if vol_actual < vol_min:
                continue

            s_up, s_down, senal, detalles = calcular_score(df, session)
            sl, tp, rr = calcular_sl_tp_dinamico(df, precio, senal)

            vol_ratio = float(a['Volume'] / a['vol_avg20']) if a['vol_avg20'] > 0 else 1.0

            resultados.append({
                "Ticker"       : t,
                "Precio $"     : round(precio, 2),
                "Cambio %"     : round(cambio_pct, 2),
                "Score 🐂"     : s_up,
                "Score 🐻"     : s_down,
                "Señal"        : senal,
                "RSI"          : round(float(a['rsi']), 1),
                "MACD"         : round(float(a['macd']), 4),
                "Vol Ratio"    : round(vol_ratio, 1),
                "Soporte $"    : round(float(a['soporte']), 2),
                "Resistencia $": round(float(a['resistencia']), 2),
                "Stop Loss $"  : sl,
                "Take Profit $": tp,
                "R:R"          : rr,
                "ATR"          : round(float(a['atr']), 4),
                "_detalles"    : detalles,
                "_df"          : df,
            })
        except Exception:
            continue

        analisis_bar.progress((idx + 1) / total,
                              text=f"Analizando {t}... {idx+1}/{total}")

    analisis_bar.empty()

    df_res = pd.DataFrame(resultados)
    if df_res.empty:
        return df_res

    # Ordenar por score alcista desc
    df_res = df_res.sort_values(by="Score 🐂", ascending=False).head(top_n)
    return df_res


# ─────────────────────────────────────────────
#  FUNCIONES DE ALPACA
# ─────────────────────────────────────────────
def get_cuenta():
    try:
        return alpaca.get_account()
    except Exception as e:
        return None

def get_posiciones():
    try:
        return alpaca.get_all_positions()
    except Exception:
        return []

def cerrar_posicion(symbol):
    try:
        alpaca.close_position(symbol)
        return True, f"Posición {symbol} cerrada."
    except Exception as e:
        return False, str(e)

def enviar_orden_compra(symbol, qty, sl_price, tp_price):
    try:
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.GTC,
            take_profit=TakeProfitRequest(limit_price=round(tp_price, 2)),
            stop_loss=StopLossRequest(stop_price=round(sl_price, 2))
        )
        alpaca.submit_order(req)
        return True, f"✅ Orden BUY enviada: {symbol} | SL: ${sl_price} | TP: ${tp_price}"
    except Exception as e:
        return False, f"❌ Error: {e}"

def enviar_orden_venta(symbol, qty):
    try:
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.GTC,
        )
        alpaca.submit_order(req)
        return True, f"✅ Orden SELL enviada: {symbol}"
    except Exception as e:
        return False, f"❌ Error: {e}"


# ════════════════════════════════════════════════════════════
#  ENCABEZADO PRINCIPAL
# ════════════════════════════════════════════════════════════
st.markdown('<h1 class="header-glow">⚡ THUNDER RADAR V90 ULTRA</h1>', unsafe_allow_html=True)
st.markdown('<p class="subheader-dim">SCALPING · MOMENTUM · AI SIGNALS · ALPACA PAPER TRADING</p>', unsafe_allow_html=True)

badge_class = SESSION_BADGES.get(session, "badge-neutral")
col_s1, col_s2, col_s3 = st.columns([1,1,1])
with col_s1:
    st.markdown(f'<span class="{badge_class}">● SESIÓN: {session}</span>', unsafe_allow_html=True)
with col_s2:
    tz  = pytz.timezone('US/Eastern')
    now_et = datetime.now(tz).strftime("%H:%M:%S ET  |  %d/%m/%Y")
    st.markdown(f'<span style="color:#8b949e">🕐 {now_et}</span>', unsafe_allow_html=True)
with col_s3:
    cuenta = get_cuenta()
    if cuenta:
        equity = float(cuenta.equity)
        cash   = float(cuenta.cash)
        pnl    = float(cuenta.equity) - float(cuenta.last_equity)
        pnl_color = "#00ff88" if pnl >= 0 else "#ff4444"
        st.markdown(f'<span style="color:{pnl_color}">💰 Equity: ${equity:,.2f} | P&L: ${pnl:+,.2f}</span>', unsafe_allow_html=True)

st.divider()

# ════════════════════════════════════════════════════════════
#  BARRA LATERAL – CONFIGURACIÓN
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ CONFIGURACIÓN")

    modo_escaneo = st.selectbox("Modo de Escaneo", [
        "🔥 Momentum Explosión",
        "📈 Scalping Rápido",
        "📉 Señales de Venta",
        "🌅 Pre-Market Sensible",
        "🌆 After-Hours Sensible",
        "🎯 Tickers Manuales"
    ])

    st.markdown("---")
    st.markdown("**Filtros de Precio**")
    precio_min = st.number_input("Precio Mín $", value=1.0,   step=0.5,  min_value=0.01)
    precio_max = st.number_input("Precio Máx $", value=500.0, step=10.0, min_value=1.0)

    st.markdown("**Filtro Movimiento Mínimo**")
    if session == "REGULAR":
        cambio_min = st.slider("Cambio % mínimo desde apertura", 0.0, 10.0, 1.0, 0.1)
    else:
        cambio_min = st.slider("Cambio % mínimo (Pre/After)", 0.0, 5.0, 0.3, 0.1,
                               help="En Pre/After el umbral es más bajo por menor volumen")

    vol_min = st.number_input("Volumen mínimo por vela", value=5000, step=1000)

    st.markdown("**ATR Multiplicadores (SL / TP)**")
    atr_sl = st.slider("ATR × Stop Loss",   0.5, 5.0, 2.0, 0.5)
    atr_tp = st.slider("ATR × Take Profit", 1.0, 8.0, 4.0, 0.5)

    st.markdown("---")
    if modo_escaneo == "🎯 Tickers Manuales":
        tickers_txt = st.text_area("Tickers (sep. coma)", "AAPL,TSLA,NVDA,GME,COIN", height=100)
        lista_tickers = [t.strip().upper() for t in tickers_txt.split(",") if t.strip()]
    elif modo_escaneo == "🌅 Pre-Market Sensible":
        lista_tickers = UNIVERSO_COMPLETO
        cambio_min = min(cambio_min, 0.2)
    elif modo_escaneo == "🌆 After-Hours Sensible":
        lista_tickers = UNIVERSO_COMPLETO
        cambio_min = min(cambio_min, 0.2)
    else:
        lista_tickers = UNIVERSO_COMPLETO

    top_n = st.slider("Top resultados a mostrar", 10, 100, 30, 10)

    st.markdown("---")
    modo_auto = st.toggle("🤖 Modo Automático (Auto-Trade)", value=False)
    if modo_auto:
        auto_score_min  = st.slider("Score mínimo para auto-compra", 6, 10, 8)
        auto_qty        = st.number_input("Cantidad auto-orden", value=1, min_value=1)
        max_posiciones  = st.number_input("Máx. posiciones simultáneas", value=3, min_value=1)
        st.warning("⚠️ El auto-trading ejecuta órdenes reales en Paper.")

    st.markdown("---")
    auto_refresh = st.toggle("🔁 Auto-refresh (30 seg)", value=False)

# ════════════════════════════════════════════════════════════
#  PORTAFOLIO ACTIVO
# ════════════════════════════════════════════════════════════
st.subheader("💼 Portafolio Activo — P&L en Tiempo Real")

posiciones = get_posiciones()
if posiciones:
    pos_data = []
    for p in posiciones:
        pnl_pct = float(p.unrealized_plpc) * 100
        pnl_usd = float(p.unrealized_pl)
        color   = "🟢" if pnl_pct >= 0 else "🔴"
        pos_data.append({
            "Ticker"    : p.symbol,
            "Qty"       : p.qty,
            "Entrada $" : round(float(p.avg_entry_price), 2),
            "Actual $"  : round(float(p.current_price), 2),
            "P&L %"     : f"{color} {pnl_pct:+.2f}%",
            "P&L $"     : f"${pnl_usd:+.2f}",
            "Valor $"   : f"${float(p.market_value):,.2f}",
        })
    df_pos = pd.DataFrame(pos_data)
    st.dataframe(df_pos, use_container_width=True, hide_index=True)

    col_x1, col_x2, col_x3 = st.columns([2, 1, 1])
    with col_x1:
        t_cerrar = st.selectbox("Ticker para cerrar", [p['Ticker'] for p in pos_data])
    with col_x2:
        if st.button("🔴 CERRAR POSICIÓN", use_container_width=True):
            ok, msg = cerrar_posicion(t_cerrar)
            st.success(msg) if ok else st.error(msg)
    with col_x3:
        if st.button("🔴 CERRAR TODO", use_container_width=True):
            for p in posiciones:
                cerrar_posicion(p.symbol)
            st.warning("Cerrando todas las posiciones...")
else:
    st.info("No hay posiciones abiertas. ¡Busca oportunidades con el escáner! 🎯")

st.divider()

# ════════════════════════════════════════════════════════════
#  MOTOR DE ESCANEO
# ════════════════════════════════════════════════════════════
st.subheader("🔭 Motor de Escaneo de Mercado")

col_btn1, col_btn2 = st.columns([3, 1])
with col_btn1:
    iniciar = st.button("🚀 INICIAR ESCANEO COMPLETO", use_container_width=True)
with col_btn2:
    if st.button("🔄 Refresh Portafolio", use_container_width=True):
        st.rerun()

if iniciar:
    st.markdown(f"**Escaneando {len(lista_tickers)} activos en sesión {session}...**")
    df_res = escanear_mercado(
        lista_tickers, precio_min, precio_max, cambio_min, session, vol_min, top_n
    )

    if df_res.empty:
        st.warning("⚠️ No se detectaron oportunidades con los filtros actuales. Prueba reduciendo el cambio mínimo o ampliando el rango de precio.")
    else:
        # ── Columnas de visualización (sin columnas internas _)
        cols_vis = [c for c in df_res.columns if not c.startswith("_")]

        # Formatear señal con badges HTML
        def badge_senal(s):
            if s == "COMPRA":   return "🟢 COMPRA"
            elif s == "VENTA":  return "🔴 VENTA"
            elif s == "ALCISTA": return "🔵 ALCISTA"
            elif s == "BAJISTA": return "🟠 BAJISTA"
            else:               return "⚪ NEUTRO"

        df_show = df_res[cols_vis].copy()
        df_show["Señal"] = df_show["Señal"].apply(badge_senal)

        # Colorear Score
        def color_score(val):
            if val >= 8: return "background-color:#15803d; color:white"
            elif val >= 6: return "background-color:#1d4ed8; color:white"
            elif val >= 4: return "background-color:#92400e; color:white"
            else:          return "background-color:#7f1d1d; color:white"

        styled = df_show.style\
            .applymap(color_score, subset=["Score 🐂", "Score 🐻"])\
            .format({
                "Precio $"     : "${:.2f}",
                "Cambio %"     : "{:+.2f}%",
                "RSI"          : "{:.1f}",
                "Vol Ratio"    : "{:.1f}x",
                "Soporte $"    : "${:.2f}",
                "Resistencia $": "${:.2f}",
                "Stop Loss $"  : "${:.2f}",
                "Take Profit $": "${:.2f}",
                "R:R"          : "{:.2f}",
            })

        st.dataframe(styled, use_container_width=True, hide_index=True, height=450)

        # ── MODO AUTOMÁTICO ──────────────────────────────────────
        if modo_auto:
            st.subheader("🤖 Auto-Trade — Ejecutando señales ≥ score " + str(auto_score_min))
            pos_actuales = len(get_posiciones())
            candidatos   = df_res[df_res["Score 🐂"] >= auto_score_min]
            for _, row in candidatos.iterrows():
                if pos_actuales >= max_posiciones:
                    st.warning(f"Máximo de {max_posiciones} posiciones alcanzado.")
                    break
                ok, msg = enviar_orden_compra(row["Ticker"], auto_qty,
                                              row["Stop Loss $"], row["Take Profit $"])
                if ok: pos_actuales += 1
                st.write(msg)

        # ── PANEL DE EJECUCIÓN MANUAL ────────────────────────────
        st.divider()
        st.subheader("🛒 Ejecución Manual")

        col_e1, col_e2 = st.columns([1, 2])
        with col_e1:
            t_buy = st.selectbox("Ticker a Operar", df_res["Ticker"].tolist())
            row_sel = df_res[df_res["Ticker"] == t_buy].iloc[0]

            cant_m = st.number_input("Cantidad de Acciones", value=1, min_value=1, step=1)

            sl_m = st.number_input("Stop Loss $",   value=float(row_sel["Stop Loss $"]),  step=0.01)
            tp_m = st.number_input("Take Profit $", value=float(row_sel["Take Profit $"]), step=0.01)

            col_buy_b, col_sell_b = st.columns(2)
            with col_buy_b:
                if st.button("🟢 COMPRAR", use_container_width=True):
                    ok, msg = enviar_orden_compra(t_buy, cant_m, sl_m, tp_m)
                    st.success(msg) if ok else st.error(msg)
            with col_sell_b:
                if st.button("🔴 VENDER", use_container_width=True):
                    ok, msg = enviar_orden_venta(t_buy, cant_m)
                    st.success(msg) if ok else st.error(msg)

        with col_e2:
            st.markdown("### 📊 Análisis Detallado: " + t_buy)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Precio",     f"${row_sel['Precio $']:.2f}")
            m2.metric("Cambio %",   f"{row_sel['Cambio %']:+.2f}%")
            m3.metric("Score 🐂",   f"{row_sel['Score 🐂']}/10")
            m4.metric("Score 🐻",   f"{row_sel['Score 🐻']}/10")

            m5, m6, m7, m8 = st.columns(4)
            m5.metric("RSI",        f"{row_sel['RSI']}")
            m6.metric("Stop Loss",  f"${row_sel['Stop Loss $']:.2f}")
            m7.metric("Take Profit",f"${row_sel['Take Profit $']:.2f}")
            m8.metric("Ratio R:R",  f"{row_sel['R:R']:.2f}x")

            # Detalles de la señal
            detalles = row_sel.get("_detalles", {})
            if detalles:
                st.markdown("**📌 Detalle de la Señal:**")
                for k, v in detalles.items():
                    color = "#00ff88" if "▲" in v else ("#ff4444" if "▼" in v else "#ffc107")
                    st.markdown(f'<span style="color:{color}; font-size:0.85em">**{k}**: {v}</span>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  AUTO-REFRESH
# ════════════════════════════════════════════════════════════
if auto_refresh:
    time.sleep(30)
    st.rerun()

# ════════════════════════════════════════════════════════════
#  PIE DE PÁGINA
# ════════════════════════════════════════════════════════════
st.divider()
st.markdown("""
<div style="text-align:center; color:#8b949e; font-size:0.75em; font-family:'Share Tech Mono', monospace;">
⚡ THUNDER RADAR V90 ULTRA — PAPER TRADING MODE — Para uso educativo y experimental<br>
Los resultados pasados no garantizan rendimientos futuros. Opera con responsabilidad.
</div>
""", unsafe_allow_html=True)
