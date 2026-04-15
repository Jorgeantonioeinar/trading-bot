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
import warnings
warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════
#  PÁGINA
# ══════════════════════════════════════════════════════════════
st.set_page_config(page_title="⚡ THUNDER RADAR V90", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
html, body, [class*="css"] { background:#050a14 !important; color:#c9d1d9 !important; font-family:'Share Tech Mono',monospace; }
h1,h2,h3 { font-family:'Orbitron',sans-serif !important; }
.stButton>button { width:100%; border-radius:4px; font-weight:bold; font-family:'Orbitron',sans-serif;
    letter-spacing:1px; border:1px solid #30363d; transition:all .2s; }
.stButton>button:hover { transform:translateY(-1px); box-shadow:0 0 14px rgba(0,255,136,.5); }
div[data-testid="metric-container"] { background:linear-gradient(135deg,#0d1117,#161b22);
    border:1px solid #21262d; border-radius:8px; padding:12px; }
.boom-card {
    background:linear-gradient(135deg,#0a1f12,#0d1117);
    border:2px solid #00ff88; border-radius:10px; padding:14px 18px; margin:6px 0;
    box-shadow: 0 0 14px #00ff8844;
}
.boom-card-warn {
    background:linear-gradient(135deg,#1f1a0a,#0d1117);
    border:2px solid #ffc107; border-radius:10px; padding:14px 18px; margin:6px 0;
}
.score-10   { color:#00ff88; font-size:1.6em; font-weight:900; font-family:'Orbitron',sans-serif; }
.score-high { color:#7cfc00; font-size:1.4em; font-weight:700; }
.score-mid  { color:#ffc107; font-size:1.2em; font-weight:700; }
.ticker-name { font-family:'Orbitron',sans-serif; font-size:1.25em; font-weight:700; color:#fff; }
.label-dim { color:#8b949e; font-size:0.78em; }
.header-glow {
    text-align:center; font-family:'Orbitron',sans-serif; font-size:2.2em; font-weight:900;
    background:linear-gradient(90deg,#00ff88,#00b4d8,#7c3aed);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; letter-spacing:3px;
}
.subheader-dim { text-align:center; color:#8b949e; font-size:.83em; letter-spacing:4px; margin-top:0; }
.session-badge { display:inline-block; padding:3px 12px; border-radius:20px; font-size:.8em; font-weight:bold; }
.badge-regular    { background:#15803d; color:#fff; }
.badge-premarket  { background:#7c3aed; color:#fff; }
.badge-afterhours { background:#0369a1; color:#fff; }
.badge-closed     { background:#374151; color:#fff; }
.live-dot { display:inline-block; width:9px; height:9px; background:#00ff88;
    border-radius:50%; margin-right:6px; animation:blink 1s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.15} }
.divider-neon { border:none; border-top:1px solid #00ff8833; margin:16px 0; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  ALPACA
# ══════════════════════════════════════════════════════════════
ALPACA_API_KEY    = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca():
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
alpaca = get_alpaca()

# ══════════════════════════════════════════════════════════════
#  UNIVERSO 220+ TICKERS
# ══════════════════════════════════════════════════════════════
UNIVERSO = [
    "AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","NFLX","AMD","INTC",
    "AVGO","QCOM","MU","AMAT","LRCX","KLAC","MRVL","ON","TXN","ADI","SMCI",
    "COIN","HOOD","MSTR","RIOT","MARA","HUT","CIFR","BTBT","CLSK","WULF","HIVE",
    "NIO","XPEV","LI","RIVN","LCID","CHPT","BLNK","PLUG","FCEL","BE","HYLN",
    "MRNA","BNTX","NVAX","VRTX","REGN","BIIB","GILD","ABBV","PFE","SRPT","ACAD",
    "GME","AMC","KOSS","BB","NOK","SNDL","BBIG","SPCE","NKLA","MULN",
    "CRM","NOW","SNOW","DDOG","ZS","CRWD","OKTA","PLTR","NET","HUBS","BILL",
    "SOFI","UPST","AFRM","OPEN","LMND","ROOT","HIMS","OPFI","DAVE",
    "BABA","JD","PDD","TCOM","GRAB","SE","TIGR","FUTU",
    "IONQ","RGTI","QUBT","ASTS","LUNR","RKLB","ACHR","JOBY","LILM",
    "WMT","TGT","COST","HD","LOW","NKE","SBUX","MCD","ETSY","EBAY",
    "PARA","WBD","FOXA","SPOT","ROKU","FUBO","SIRI","IMAX","NWSA","LUMN",
    "QQQ","SPY","IWM","SOXL","TQQQ","ARKK","UVXY","SOXS","LABU","NAIL",
    "BA","LMT","RTX","NOC","GD","CAT","DE","GE","HON","MMM",
    "JPM","BAC","GS","MS","WFC","C","BLK","SCHW","AXP","V","PYPL",
    "UNH","CVS","HUM","CI","ISRG","BSX","MDT","EW","ZBH","DXCM",
    "CLOV","WKHS","FSR","GOEV","IDEX","MVIS","PROG","ATER","CELH","SKIN",
    "RBLX","U","SNAP","PINS","HOOD","RIVN","LCID","SPCE","ASTR","MNTS",
]
UNIVERSO = list(dict.fromkeys(UNIVERSO))

# ══════════════════════════════════════════════════════════════
#  SESIÓN DE MERCADO
# ══════════════════════════════════════════════════════════════
def get_session():
    tz  = pytz.timezone("US/Eastern")
    now = datetime.now(tz)
    h   = now.hour + now.minute / 60.0
    if   4.0 <= h < 9.5:  return "PRE-MARKET"
    elif 9.5 <= h < 16.0: return "REGULAR"
    elif 16.0<= h < 20.0: return "AFTER-HOURS"
    else:                  return "CERRADO"

SESSION = get_session()

# Config por sesión: (interval, period, prepost, cambio_min_dflt, vol_min_dflt)
SESSION_CFG = {
    "PRE-MARKET":  ("1m","1d", True,  0.25, 300),
    "REGULAR":     ("1m","1d", True,  0.80, 2000),
    "AFTER-HOURS": ("1m","1d", True,  0.15, 200),
    "CERRADO":     ("5m","5d", False, 0.50, 500),
}

# ══════════════════════════════════════════════════════════════
#  INDICADORES TÉCNICOS
# ══════════════════════════════════════════════════════════════
def calcular_indicadores(df: pd.DataFrame):
    try:
        df = df.copy()
        if len(df) < 5:
            return None

        # Aplanar MultiIndex si existe
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Asegurar que son Series 1D
        close = df["Close"].squeeze()
        high  = df["High"].squeeze()
        low   = df["Low"].squeeze()
        vol   = df["Volume"].squeeze()

        if isinstance(close, pd.DataFrame): close = close.iloc[:,0]
        if isinstance(high,  pd.DataFrame): high  = high.iloc[:,0]
        if isinstance(low,   pd.DataFrame): low   = low.iloc[:,0]
        if isinstance(vol,   pd.DataFrame): vol   = vol.iloc[:,0]

        df["close"] = close.values
        df["high"]  = high.values
        df["low"]   = low.values
        df["vol"]   = vol.values

        c = df["close"]
        h = df["high"]
        l = df["low"]
        v = df["vol"]

        df["ema9"]  = c.ewm(span=9,  adjust=False).mean()
        df["ema20"] = c.ewm(span=20, adjust=False).mean()
        df["ema50"] = c.ewm(span=50, adjust=False).mean()

        tp = (h + l + c) / 3
        df["vwap"] = (tp * v).cumsum() / v.cumsum().replace(0, np.nan)

        delta = c.diff()
        gain  = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss  = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        df["rsi"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))

        ema12 = c.ewm(span=12, adjust=False).mean()
        ema26 = c.ewm(span=26, adjust=False).mean()
        df["macd"]   = ema12 - ema26
        df["macd_s"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_h"] = df["macd"] - df["macd_s"]

        sma20 = c.rolling(20).mean()
        std20 = c.rolling(20).std()
        df["bb_up"] = sma20 + 2 * std20
        df["bb_lo"] = sma20 - 2 * std20

        hl  = h - l
        hc  = (h - c.shift(1)).abs()
        lc  = (l - c.shift(1)).abs()
        df["atr"]  = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean()
        df["sup"]  = l.rolling(20).min()
        df["res"]  = h.rolling(20).max()
        df["vavg"] = v.rolling(20).mean()

        low14  = l.rolling(14).min()
        high14 = h.rolling(14).max()
        df["stk"] = 100 * (c - low14) / (high14 - low14 + 1e-9)
        df["std_k"] = df["stk"].rolling(3).mean()

        return df.dropna(subset=["close"])
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
#  SCORE EXPLOSIÓN 1-10
# ══════════════════════════════════════════════════════════════
def score_explosion(df, session: str):
    if df is None or len(df) < 5:
        return 1, 1, "NEUTRO", {}

    def safe(row, col, default=0.0):
        try:
            v = row[col]
            return float(v) if not (isinstance(v, float) and np.isnan(v)) else default
        except Exception:
            return default

    a = df.iloc[-1]
    p = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    b = df.iloc[-3] if len(df) > 2 else p

    precio   = safe(a, "close", 0)
    precio_p = safe(p, "close", precio)
    precio_b = safe(b, "close", precio_p)

    if session == "REGULAR":
        W = dict(vwap=2.0, ema=2.0, rsi=1.5, vol=2.0, macd=1.5, bb=0.5, stoch=0.5)
    else:
        W = dict(vwap=2.5, ema=2.5, rsi=1.5, vol=0.8, macd=1.5, bb=0.5, stoch=0.5)

    up = down = 0.0
    det = {}

    # 1. VWAP
    vwap = safe(a, "vwap", precio)
    if precio > vwap:
        up += W["vwap"]; det["VWAP"] = f"▲ Precio sobre VWAP ${vwap:.3f}"
    else:
        down += W["vwap"]; det["VWAP"] = f"▼ Precio bajo VWAP ${vwap:.3f}"

    # 2. EMA9 vs EMA20
    e9  = safe(a, "ema9",  precio)
    e20 = safe(a, "ema20", precio)
    if e9 > e20:
        up += W["ema"]; det["EMA"] = f"▲ EMA9 ({e9:.3f}) > EMA20 ({e20:.3f})"
    else:
        down += W["ema"]; det["EMA"] = f"▼ EMA9 ({e9:.3f}) < EMA20 ({e20:.3f})"

    # 3. RSI
    rsi = safe(a, "rsi", 50)
    if rsi > 60:
        up += W["rsi"]; det["RSI"] = f"▲ RSI fuerte {rsi:.0f}"
    elif rsi < 40:
        down += W["rsi"]; det["RSI"] = f"▼ RSI débil {rsi:.0f}"
    elif rsi >= 50:
        up += W["rsi"] * 0.5; det["RSI"] = f"→ RSI {rsi:.0f}"
    else:
        down += W["rsi"] * 0.5; det["RSI"] = f"→ RSI {rsi:.0f}"

    # 4. Volumen explosivo
    vavg   = safe(a, "vavg", 1)
    vol_a  = safe(a, "vol", 0)
    vratio = vol_a / max(vavg, 1)
    if vratio >= 2.0:
        if precio >= precio_p:
            up += W["vol"]; det["VOL"] = f"⚡ Volumen EXPLOSIVO {vratio:.1f}x"
        else:
            down += W["vol"]; det["VOL"] = f"⚡ Volumen BAJISTA {vratio:.1f}x"
    elif vratio >= 1.3:
        if precio >= precio_p:
            up += W["vol"] * 0.6; det["VOL"] = f"▲ Vol elevado {vratio:.1f}x"
        else:
            down += W["vol"] * 0.6; det["VOL"] = f"▼ Vol elevado bajista {vratio:.1f}x"
    else:
        det["VOL"] = f"→ Vol normal {vratio:.1f}x"

    # 5. MACD histograma 3 velas
    mh_a = safe(a, "macd_h", 0)
    mh_p = safe(p, "macd_h", 0)
    mh_b = safe(b, "macd_h", 0)
    if mh_a > mh_p > mh_b and mh_a > 0:
        up += W["macd"]; det["MACD"] = "▲ MACD hist. subiendo 3 velas consecutivas"
    elif mh_a < mh_p < mh_b and mh_a < 0:
        down += W["macd"]; det["MACD"] = "▼ MACD hist. cayendo 3 velas consecutivas"
    elif mh_a > 0:
        up += W["macd"] * 0.4; det["MACD"] = "→ MACD positivo"
    else:
        down += W["macd"] * 0.4; det["MACD"] = "→ MACD negativo"

    # 6. Bollinger Bands
    bb_up = safe(a, "bb_up", precio * 1.02)
    bb_lo = safe(a, "bb_lo", precio * 0.98)
    bb_pos = (precio - bb_lo) / max(bb_up - bb_lo, 1e-9)
    if bb_pos > 0.85:
        up += W["bb"]; det["BB"] = f"▲ Rompiendo banda superior Bollinger"
    elif bb_pos < 0.15:
        down += W["bb"]; det["BB"] = f"▼ Precio en banda inferior Bollinger"
    else:
        det["BB"] = f"→ Zona media Bollinger {bb_pos:.0%}"

    # 7. Stochastic
    stk = safe(a, "stk", 50)
    std = safe(a, "std_k", 50)
    if 20 < stk < 80:
        if stk > std:
            up += W["stoch"]; det["STOCH"] = f"▲ Stoch K={stk:.0f} > D={std:.0f}"
        else:
            down += W["stoch"]; det["STOCH"] = f"▼ Stoch K={stk:.0f} < D={std:.0f}"
    elif stk >= 80:
        det["STOCH"] = f"⚠️ Sobrecompra K={stk:.0f}"
    else:
        det["STOCH"] = f"⚠️ Sobreventa K={stk:.0f}"

    # 8. BONUS: 3 velas alcistas / bajistas consecutivas (patrón de explosión)
    c1 = safe(df.iloc[-1], "close", 0); o1 = safe(df.iloc[-1], "Open",  c1)
    c2 = safe(df.iloc[-2], "close", c1) if len(df) > 1 else c1
    o2 = safe(df.iloc[-2], "Open",  c2) if len(df) > 1 else c2
    c3 = safe(df.iloc[-3], "close", c2) if len(df) > 2 else c2
    o3 = safe(df.iloc[-3], "Open",  c3) if len(df) > 2 else c3

    tres_up   = (c1 > o1) and (c2 > o2) and (c3 > o3) and (c1 > c2 > c3)
    tres_down = (c1 < o1) and (c2 < o2) and (c3 < o3) and (c1 < c2 < c3)

    if tres_up:
        up   += 1.5; det["VELAS"] = "🔥 3 velas verdes consecutivas — ARRANQUE"
    elif tres_down:
        down += 1.5; det["VELAS"] = "🔥 3 velas rojas consecutivas — CAÍDA"
    else:
        det["VELAS"] = "→ Sin patrón de 3 velas"

    max_pts = sum(W.values()) + 1.5
    s_up   = max(1, min(10, round((up   / max_pts) * 10)))
    s_down = max(1, min(10, round((down / max_pts) * 10)))

    if   s_up >= 8:   senal = "🚀 EXPLOSIÓN ALCISTA"
    elif s_up >= 6:   senal = "📈 COMPRA"
    elif s_down >= 8: senal = "💥 EXPLOSIÓN BAJISTA"
    elif s_down >= 6: senal = "📉 VENTA"
    else:             senal = "⚪ NEUTRO"

    return s_up, s_down, senal, det


# ══════════════════════════════════════════════════════════════
#  SL / TP DINÁMICO
# ══════════════════════════════════════════════════════════════
def sl_tp_din(df, precio, senal, mult_sl=2.0, mult_tp=4.0):
    try:
        a   = df.iloc[-1]
        atr = float(a["atr"]) if not np.isnan(a["atr"]) else precio * 0.01
        sup = float(a["sup"]) if not np.isnan(a["sup"]) else precio * 0.97
        res = float(a["res"]) if not np.isnan(a["res"]) else precio * 1.03
    except Exception:
        atr = precio * 0.01; sup = precio * 0.97; res = precio * 1.03

    alcista = any(x in senal for x in ["COMPRA", "ALCISTA", "EXPLOSIÓN AL"])
    if alcista:
        sl = round(max(precio - atr * mult_sl, sup * 0.998), 4)
        tp = round(min(precio + atr * mult_tp, res * 0.999), 4)
    else:
        sl = round(min(precio + atr * mult_sl, res * 1.002), 4)
        tp = round(max(precio - atr * mult_tp, sup * 1.001), 4)
    rr = round(abs(tp - precio) / max(abs(precio - sl), 1e-6), 2)
    return sl, tp, rr


# ══════════════════════════════════════════════════════════════
#  ESCANEO MASIVO
# ══════════════════════════════════════════════════════════════
def escanear(tickers, interval, period, prepost, cambio_min, vol_min, mult_sl, mult_tp, session, top_n=40):
    resultados   = []
    progress_bar = st.progress(0.0, text="⚡ Iniciando descarga...")
    total        = len(tickers)
    lote         = 30
    dfs          = {}

    # ── DESCARGA EN LOTES ────────────────────────────────────
    for i in range(0, total, lote):
        chunk = tickers[i:i+lote]
        pct   = min((i + lote) / total * 0.5, 0.5)
        progress_bar.progress(pct, text=f"📡 Descargando {min(i+lote,total)}/{total}...")
        try:
            raw = yf.download(
                chunk, period=period, interval=interval,
                group_by="ticker", prepost=prepost,
                progress=False, auto_adjust=True, threads=True
            )
            for t in chunk:
                try:
                    if len(chunk) == 1:
                        dfs[t] = raw.copy()
                    else:
                        lvl0 = raw.columns.get_level_values(0)
                        if t in lvl0:
                            dfs[t] = raw[t].copy()
                        else:
                            dfs[t] = pd.DataFrame()
                except Exception:
                    dfs[t] = pd.DataFrame()
        except Exception:
            for t in chunk:
                dfs[t] = pd.DataFrame()

    # ── ANÁLISIS ─────────────────────────────────────────────
    for idx, t in enumerate(tickers):
        pct2 = 0.5 + (idx + 1) / total * 0.5
        progress_bar.progress(pct2, text=f"🔍 {t} ({idx+1}/{total})")
        try:
            raw_df = dfs.get(t, pd.DataFrame())
            if raw_df is None or len(raw_df) < 8:
                continue

            df = calcular_indicadores(raw_df)
            if df is None or len(df) < 5:
                continue

            precio = float(df["close"].iloc[-1])
            if precio <= 0:
                continue

            # Cambio % desde apertura del día
            open_day   = float(df["Open"].iloc[0]) if "Open" in df.columns else precio
            cambio_dia = ((precio - open_day) / open_day * 100) if open_day > 0 else 0

            # Cambio % en la última vela (primer minuto de movimiento)
            precio_ant  = float(df["close"].iloc[-2]) if len(df) > 1 else precio
            cambio_vela = ((precio - precio_ant) / precio_ant * 100) if precio_ant > 0 else 0

            # Filtro volumen
            vol_a  = float(df["vol"].iloc[-1])
            if vol_a < vol_min:
                continue

            # Filtro movimiento: al menos cambio_min en el día O 1/3 en última vela
            if abs(cambio_dia) < cambio_min and abs(cambio_vela) < max(cambio_min * 0.25, 0.10):
                continue

            s_up, s_down, senal, det = score_explosion(df, session)
            _sl, _tp, rr = sl_tp_din(df, precio, senal, mult_sl, mult_tp)

            vavg   = float(df["vavg"].iloc[-1]) if not np.isnan(df["vavg"].iloc[-1]) else 1
            vratio = round(vol_a / max(vavg, 1), 1)
            rsi    = float(df["rsi"].iloc[-1])  if not np.isnan(df["rsi"].iloc[-1])  else 0
            sup    = float(df["sup"].iloc[-1])  if not np.isnan(df["sup"].iloc[-1])  else 0
            res    = float(df["res"].iloc[-1])  if not np.isnan(df["res"].iloc[-1])  else 0

            resultados.append({
                "Ticker"    : t,
                "Precio $"  : round(precio, 3),
                "Δ Vela %"  : round(cambio_vela, 2),
                "Δ Día %"   : round(cambio_dia, 2),
                "Score 🐂"  : s_up,
                "Score 🐻"  : s_down,
                "Señal"     : senal,
                "RSI"       : round(rsi, 1),
                "Vol x"     : vratio,
                "Soporte $" : round(sup, 2),
                "Resist $"  : round(res, 2),
                "SL $"      : _sl,
                "TP $"      : _tp,
                "R:R"       : rr,
                "_det"      : det,
                "_df"       : df,
            })
        except Exception:
            continue

    progress_bar.empty()

    if not resultados:
        return pd.DataFrame()

    df_res = pd.DataFrame(resultados).sort_values("Score 🐂", ascending=False).reset_index(drop=True)
    return df_res.head(top_n)


# ══════════════════════════════════════════════════════════════
#  ALPACA HELPERS
# ══════════════════════════════════════════════════════════════
def get_cuenta():
    try:    return alpaca.get_account()
    except: return None

def get_posiciones():
    try:    return alpaca.get_all_positions()
    except: return []

def cerrar_posicion(symbol):
    try:    alpaca.close_position(symbol); return True, f"Posición {symbol} cerrada ✅"
    except Exception as e: return False, str(e)

def orden_compra(symbol, qty, sl_p, tp_p):
    try:
        req = MarketOrderRequest(
            symbol=symbol, qty=qty,
            side=OrderSide.BUY, time_in_force=TimeInForce.GTC,
            take_profit=TakeProfitRequest(limit_price=round(float(tp_p), 2)),
            stop_loss=StopLossRequest(stop_price=round(float(sl_p), 2))
        )
        alpaca.submit_order(req)
        return True, f"✅ BUY {qty} {symbol} | SL ${sl_p} | TP ${tp_p}"
    except Exception as e:
        return False, f"❌ {e}"

def orden_venta(symbol, qty):
    try:
        req = MarketOrderRequest(symbol=symbol, qty=qty, side=OrderSide.SELL, time_in_force=TimeInForce.GTC)
        alpaca.submit_order(req)
        return True, f"✅ SELL {qty} {symbol}"
    except Exception as e:
        return False, f"❌ {e}"


# ══════════════════════════════════════════════════════════════
#  ENCABEZADO PRINCIPAL
# ══════════════════════════════════════════════════════════════
st.markdown('<h1 class="header-glow">⚡ THUNDER RADAR V90 ULTRA</h1>', unsafe_allow_html=True)
st.markdown('<p class="subheader-dim">DETECCIÓN DE EXPLOSIÓN EN TIEMPO REAL · SCALPING · ALPACA PAPER TRADING</p>', unsafe_allow_html=True)

badges = {"REGULAR":"badge-regular","PRE-MARKET":"badge-premarket",
          "AFTER-HOURS":"badge-afterhours","CERRADO":"badge-closed"}
tz_et   = pytz.timezone("US/Eastern")
hora_et = datetime.now(tz_et).strftime("%H:%M:%S ET")
cuenta  = get_cuenta()

hc1, hc2, hc3 = st.columns(3)
with hc1:
    st.markdown(
        f'<span class="session-badge {badges.get(SESSION,"badge-closed")}">● {SESSION}</span>'
        f' &nbsp; <span class="live-dot"></span><span style="color:#8b949e;font-size:.8em">EN VIVO</span>',
        unsafe_allow_html=True)
with hc2:
    st.markdown(f'<span style="color:#8b949e">🕐 {hora_et}</span>', unsafe_allow_html=True)
with hc3:
    if cuenta:
        equity = float(cuenta.equity)
        pnl    = equity - float(cuenta.last_equity)
        col    = "#00ff88" if pnl >= 0 else "#ff4444"
        st.markdown(f'<span style="color:{col}">💰 ${equity:,.2f} &nbsp;|&nbsp; P&L {pnl:+,.2f}</span>',
                    unsafe_allow_html=True)

st.markdown('<hr class="divider-neon">', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  BARRA LATERAL
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ CONFIGURACIÓN")

    modo = st.selectbox("Modo de Escaneo", [
        "🔥 Momentum Explosión",
        "📈 Top Alcistas",
        "📉 Top Bajistas",
        "🌅 Pre-Market Sensible",
        "🌆 After-Hours Sensible",
        "🎯 Tickers Manuales",
    ])

    st.markdown("---")
    intervalo_cfg, periodo_cfg, prepost_cfg, cambio_dflt, vol_dflt = SESSION_CFG.get(
        SESSION, ("1m","1d",True,0.5,500))

    if modo in ("🌅 Pre-Market Sensible","🌆 After-Hours Sensible"):
        cambio_dflt = 0.10
        vol_dflt    = 150

    precio_min_f = st.number_input("Precio Mín $", value=0.10, step=0.10, min_value=0.01)
    precio_max_f = st.number_input("Precio Máx $", value=800.0, step=10.0)

    label_c = "Δ% mínimo (última vela)" if SESSION != "REGULAR" else "Δ% mínimo desde apertura"
    cambio_min = st.slider(label_c, 0.0, 10.0, float(cambio_dflt), 0.05,
                           help="Umbral de movimiento para aparecer en el radar")
    vol_min    = st.number_input("Volumen mínimo por vela", value=int(vol_dflt), step=50, min_value=0)
    top_n_f    = st.slider("Top resultados a mostrar", 10, 80, 30, 5)

    st.markdown("---")
    atr_sl = st.slider("ATR × Stop Loss",   0.5, 5.0, 2.0, 0.5)
    atr_tp = st.slider("ATR × Take Profit", 1.0, 8.0, 4.0, 0.5)

    st.markdown("---")
    if modo == "🎯 Tickers Manuales":
        txt = st.text_area("Tickers (coma)", "AAPL,TSLA,NVDA,GME,COIN,MARA,RIOT,SOFI", height=90)
        lista_scan = [t.strip().upper() for t in txt.split(",") if t.strip()]
    else:
        lista_scan = UNIVERSO

    st.info(f"📊 Universo: **{len(lista_scan)}** activos")

    st.markdown("---")
    modo_auto = st.toggle("🤖 Auto-Trade", value=False)
    if modo_auto:
        auto_score = st.slider("Score mínimo auto-compra", 7, 10, 8)
        auto_qty   = st.number_input("Acciones por orden", value=1, min_value=1)
        max_pos    = st.number_input("Máx posiciones", value=3, min_value=1)
        st.warning("⚠️ Ejecuta órdenes reales en Paper.")

    st.markdown("---")
    auto_refresh = st.toggle("🔁 Auto-escaneo continuo", value=False)
    refresh_seg  = 45 if SESSION == "REGULAR" else 60


# ══════════════════════════════════════════════════════════════
#  PORTAFOLIO ACTIVO
# ══════════════════════════════════════════════════════════════
st.subheader("💼 Portafolio Activo — P&L en Tiempo Real")
posiciones = get_posiciones()
if posiciones:
    rows = []
    for p in posiciones:
        pnl_p = float(p.unrealized_plpc) * 100
        pnl_u = float(p.unrealized_pl)
        ico   = "🟢" if pnl_p >= 0 else "🔴"
        rows.append({"Ticker":p.symbol,"Qty":p.qty,
                     "Entrada $":round(float(p.avg_entry_price),2),
                     "Actual $": round(float(p.current_price),2),
                     "P&L %":    f"{ico} {pnl_p:+.2f}%",
                     "P&L $":    f"${pnl_u:+.2f}",
                     "Valor $":  f"${float(p.market_value):,.2f}"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    px1, px2, px3 = st.columns([2,1,1])
    with px1: t_close = st.selectbox("Ticker a cerrar", [r["Ticker"] for r in rows])
    with px2:
        if st.button("🔴 Cerrar posición"):
            ok, msg = cerrar_posicion(t_close)
            st.success(msg) if ok else st.error(msg)
    with px3:
        if st.button("🔴 Cerrar TODO"):
            [cerrar_posicion(p.symbol) for p in posiciones]
            st.warning("Cerrando todas las posiciones...")
else:
    st.info("Sin posiciones abiertas. ¡Busca con el radar! 🎯")

st.markdown('<hr class="divider-neon">', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  MOTOR DE ESCANEO
# ══════════════════════════════════════════════════════════════
st.subheader("🔭 Radar de Explosión")

if "df_scan"   not in st.session_state: st.session_state.df_scan   = pd.DataFrame()
if "last_scan" not in st.session_state: st.session_state.last_scan = None

sb1, sb2 = st.columns([3,1])
with sb1: iniciar = st.button("🚀 INICIAR ESCANEO COMPLETO", use_container_width=True)
with sb2:
    if st.button("🔄 Refresh UI", use_container_width=True): st.rerun()

# ── Disparar escaneo ─────────────────────────────────────────
debe_escanear = iniciar or (
    auto_refresh and
    st.session_state.last_scan is not None and
    (time.time() - st.session_state.last_scan) >= refresh_seg
)

if debe_escanear:
    with st.spinner(f"⚡ Escaneando {len(lista_scan)} activos en sesión {SESSION}..."):
        df_scan = escanear(
            lista_scan, intervalo_cfg, periodo_cfg, prepost_cfg,
            cambio_min, vol_min, atr_sl, atr_tp, SESSION, top_n_f
        )
    st.session_state.df_scan   = df_scan
    st.session_state.last_scan = time.time()

df_scan = st.session_state.df_scan

# ── MOSTRAR RESULTADOS ───────────────────────────────────────
if not df_scan.empty:

    boom  = df_scan[df_scan["Score 🐂"] >= 7]
    otros = df_scan[df_scan["Score 🐂"] <  7]

    # ── TARJETAS DE EXPLOSIÓN ────────────────────────────────
    if not boom.empty:
        st.markdown(f"### 🔥 EXPLOSIONES DETECTADAS — {len(boom)} señales")
        for _, row in boom.iterrows():
            s = int(row["Score 🐂"])
            cls = "score-10" if s == 10 else ("score-high" if s >= 8 else "score-mid")
            dc = "#00ff88" if row["Δ Vela %"] >= 0 else "#ff4444"
            dd = "#00ff88" if row["Δ Día %"]  >= 0 else "#ff4444"
            st.markdown(f"""
            <div class="boom-card">
              <span class="ticker-name">⚡ {row['Ticker']}</span>
              &nbsp;&nbsp;<span class="{cls}">{s}/10</span>
              &nbsp;&nbsp;<span style="color:#a78bfa;font-size:.9em">{row['Señal']}</span>
              <br>
              <span class="label-dim">Precio</span> <b style="color:#fff">${row['Precio $']}</b>
              &nbsp;|&nbsp;
              <span class="label-dim">Δ Vela</span>
              <b style="color:{dc}">{row['Δ Vela %']:+.2f}%</b>
              &nbsp;|&nbsp;
              <span class="label-dim">Δ Día</span>
              <b style="color:{dd}">{row['Δ Día %']:+.2f}%</b>
              &nbsp;|&nbsp;
              <span class="label-dim">RSI</span> {row['RSI']}
              &nbsp;|&nbsp;
              <span class="label-dim">Vol</span> {row['Vol x']}x
              &nbsp;|&nbsp;
              <span class="label-dim">SL</span> <span style="color:#ff6b6b">${row['SL $']}</span>
              &nbsp;|&nbsp;
              <span class="label-dim">TP</span> <span style="color:#00ff88">${row['TP $']}</span>
              &nbsp;|&nbsp;
              <span class="label-dim">R:R</span> {row['R:R']}x
            </div>""", unsafe_allow_html=True)

    # ── TABLA COMPLETA ───────────────────────────────────────
    st.markdown("### 📋 Tabla completa del radar")
    cols_vis = ["Ticker","Precio $","Δ Vela %","Δ Día %","Score 🐂","Score 🐻",
                "Señal","RSI","Vol x","Soporte $","Resist $","SL $","TP $","R:R"]
    df_show  = df_scan[cols_vis].copy()

    def col_score(val):
        if val >= 8:   return "background-color:#15803d;color:white"
        elif val >= 6: return "background-color:#1d4ed8;color:white"
        elif val >= 4: return "background-color:#92400e;color:white"
        else:          return "background-color:#7f1d1d;color:white"

    def col_delta(val):
        c = "#00ff88" if val >= 0 else "#ff4444"
        return f"color:{c};font-weight:bold"

    fmt = {"Precio $":"${:.3f}","Δ Vela %":"{:+.2f}%","Δ Día %":"{:+.2f}%",
           "RSI":"{:.1f}","Vol x":"{:.1f}x","Soporte $":"${:.2f}",
           "Resist $":"${:.2f}","SL $":"${:.2f}","TP $":"${:.2f}","R:R":"{:.2f}"}

    # ── COMPATIBILIDAD PANDAS >= 2.1 y < 2.1 ────────────────
    try:
        styled = (df_show.style
                  .map(col_score, subset=["Score 🐂","Score 🐻"])
                  .map(col_delta, subset=["Δ Vela %","Δ Día %"])
                  .format(fmt))
    except Exception:
        try:
            styled = (df_show.style
                      .applymap(col_score, subset=["Score 🐂","Score 🐻"])
                      .applymap(col_delta, subset=["Δ Vela %","Δ Día %"])
                      .format(fmt))
        except Exception:
            styled = df_show.style.format(fmt)

    st.dataframe(styled, use_container_width=True, hide_index=True, height=420)

    # ── AUTO-TRADE ───────────────────────────────────────────
    if modo_auto:
        st.markdown("### 🤖 Auto-Trade en ejecución")
        n_pos = len(get_posiciones())
        for _, row in df_scan[df_scan["Score 🐂"] >= auto_score].iterrows():
            if n_pos >= max_pos:
                st.warning(f"Máximo de {max_pos} posiciones alcanzado.")
                break
            ok, msg = orden_compra(row["Ticker"], auto_qty, row["SL $"], row["TP $"])
            if ok: n_pos += 1
            st.write(msg)

    # ── EJECUCIÓN MANUAL ─────────────────────────────────────
    st.markdown('<hr class="divider-neon">', unsafe_allow_html=True)
    st.markdown("### 🛒 Ejecución Manual")
    ce1, ce2 = st.columns([1,2])
    with ce1:
        t_op  = st.selectbox("Ticker a operar", df_scan["Ticker"].tolist())
        rsel  = df_scan[df_scan["Ticker"] == t_op].iloc[0]
        qty_m = st.number_input("Cantidad acciones", value=1, min_value=1, step=1)
        sl_m  = st.number_input("Stop Loss $",   value=float(rsel["SL $"]),  step=0.01)
        tp_m  = st.number_input("Take Profit $", value=float(rsel["TP $"]),  step=0.01)
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🟢 COMPRAR", use_container_width=True):
                ok, msg = orden_compra(t_op, qty_m, sl_m, tp_m)
                st.success(msg) if ok else st.error(msg)
        with b2:
            if st.button("🔴 VENDER", use_container_width=True):
                ok, msg = orden_venta(t_op, qty_m)
                st.success(msg) if ok else st.error(msg)

    with ce2:
        st.markdown(f"### 📊 Análisis: {t_op}")
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Precio $",   f"${rsel['Precio $']:.3f}")
        m2.metric("Δ Vela",     f"{rsel['Δ Vela %']:+.2f}%")
        m3.metric("Score 🐂",   f"{rsel['Score 🐂']}/10")
        m4.metric("R:R",        f"{rsel['R:R']}x")
        m5,m6,m7,m8 = st.columns(4)
        m5.metric("RSI",        f"{rsel['RSI']}")
        m6.metric("SL $",       f"${rsel['SL $']:.2f}")
        m7.metric("TP $",       f"${rsel['TP $']:.2f}")
        m8.metric("Vol x avg",  f"{rsel['Vol x']}x")

        det = rsel.get("_det", {})
        if det:
            st.markdown("**📌 Detalle de señal:**")
            for k, v in det.items():
                c = "#00ff88" if "▲" in v else ("#ff4444" if "▼" in v else "#ffc107")
                st.markdown(
                    f'<span style="color:{c};font-size:.82em"><b>{k}</b>: {v}</span>',
                    unsafe_allow_html=True)

elif st.session_state.last_scan is not None:
    st.warning("⚠️ Sin señales con los filtros actuales. Reduce el Δ% mínimo o el volumen mínimo.")
else:
    st.info("👆 Pulsa **🚀 INICIAR ESCANEO COMPLETO** para comenzar.")

# ══════════════════════════════════════════════════════════════
#  AUTO-REFRESH LOOP
# ══════════════════════════════════════════════════════════════
if auto_refresh:
    time.sleep(refresh_seg)
    st.rerun()

# ══════════════════════════════════════════════════════════════
#  PIE
# ══════════════════════════════════════════════════════════════
st.markdown('<hr class="divider-neon">', unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#8b949e;font-size:.72em;font-family:'Share Tech Mono',monospace">
⚡ THUNDER RADAR V90 ULTRA — PAPER TRADING — Solo para uso educativo y experimental<br>
Los resultados pasados no garantizan rendimientos futuros. Opera con responsabilidad.
</div>""", unsafe_allow_html=True)
