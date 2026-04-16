"""
THUNDER RADAR V91 ULTRA
- Detecta explosiones desde el PRIMER MINUTO de movimiento
- Incluye Penny Stocks, Small Caps y todo el mercado US
- Funciona en Regular, Pre-Market y After-Hours
- Conectado a Alpaca Paper Trading
"""

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

# ══════════════════════════════════════════════════════════
#  PÁGINA
# ══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="⚡ THUNDER RADAR V91",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');

html, body, [class*="css"] {
    background: #050a14 !important;
    color: #c9d1d9 !important;
    font-family: 'Share Tech Mono', monospace;
}
h1, h2, h3 { font-family: 'Orbitron', sans-serif !important; }

.stButton>button {
    width: 100%; border-radius: 4px; font-weight: bold;
    font-family: 'Orbitron', sans-serif; letter-spacing: 1px;
    border: 1px solid #30363d; transition: all .2s;
}
.stButton>button:hover {
    transform: translateY(-1px);
    box-shadow: 0 0 14px rgba(0,255,136,.5);
}
div[data-testid="metric-container"] {
    background: linear-gradient(135deg,#0d1117,#161b22);
    border: 1px solid #21262d; border-radius: 8px; padding: 12px;
}

/* TARJETA EXPLOSIÓN */
.boom-card {
    background: linear-gradient(135deg,#071a0e,#0d1117);
    border: 2px solid #00ff88; border-radius: 10px;
    padding: 12px 16px; margin: 5px 0;
    box-shadow: 0 0 16px #00ff8833;
}
.boom-card-sell {
    background: linear-gradient(135deg,#1a0707,#0d1117);
    border: 2px solid #ff4444; border-radius: 10px;
    padding: 12px 16px; margin: 5px 0;
    box-shadow: 0 0 16px #ff444433;
}

.score-10   { color:#00ff88; font-size:1.7em; font-weight:900; font-family:'Orbitron',sans-serif; }
.score-high { color:#7cfc00; font-size:1.4em; font-weight:700; }
.score-mid  { color:#ffc107; font-size:1.2em; font-weight:700; }
.score-low  { color:#ff6b6b; font-size:1.1em; }
.ticker-big { font-family:'Orbitron',sans-serif; font-size:1.3em; font-weight:900; color:#fff; }
.label-dim  { color:#8b949e; font-size:0.77em; }

.header-glow {
    text-align:center; font-family:'Orbitron',sans-serif; font-size:2.3em; font-weight:900;
    background: linear-gradient(90deg,#00ff88,#00b4d8,#7c3aed);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; letter-spacing:3px;
}
.sub-dim { text-align:center; color:#8b949e; font-size:.82em; letter-spacing:4px; margin-top:0; }

.badge { display:inline-block; padding:3px 12px; border-radius:20px; font-size:.78em; font-weight:bold; }
.b-regular    { background:#15803d; color:#fff; }
.b-premarket  { background:#7c3aed; color:#fff; }
.b-afterhours { background:#0369a1; color:#fff; }
.b-closed     { background:#374151; color:#fff; }

.dot-live { display:inline-block; width:9px; height:9px; background:#00ff88;
    border-radius:50%; margin-right:5px; animation:blink 1s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.15} }

hr.neon { border:none; border-top:1px solid #00ff8822; margin:14px 0; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  ALPACA
# ══════════════════════════════════════════════════════════
ALPACA_API_KEY    = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca():
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
alpaca = get_alpaca()

# ══════════════════════════════════════════════════════════
#  UNIVERSO EXTENDIDO — incluye penny stocks y small caps
#  (los que más se mueven en 5 minutos, como Webull Top Gainers)
# ══════════════════════════════════════════════════════════
# ── Mega / Large cap ──────────────────────────────────────
LARGE = [
    "AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","NFLX","AMD","INTC",
    "AVGO","QCOM","MU","AMAT","LRCX","SMCI","ON","TXN","ADI","MRVL",
    "JPM","BAC","GS","MS","WFC","C","V","PYPL","SCHW","AXP",
    "UNH","PFE","ABBV","MRK","JNJ","LLY","BMY","GILD","MRNA","BNTX",
    "BA","LMT","RTX","NOC","GD","CAT","DE","GE","HON","MMM",
    "WMT","TGT","COST","HD","NKE","MCD","SBUX","AMGN","ISRG","MDT",
]

# ── Cripto proxy / Alta volatilidad ──────────────────────
CRYPTO = [
    "COIN","HOOD","MSTR","RIOT","MARA","HUT","CIFR","BTBT","CLSK","WULF",
    "HIVE","IREN","BITF","SOS","BTCS","CORZ","ARBK","SATO","MIGI","BTDR",
]

# ── EV / Clean Energy ─────────────────────────────────────
EV = [
    "TSLA","NIO","XPEV","LI","RIVN","LCID","CHPT","BLNK","PLUG","FCEL",
    "BE","HYLN","GOEV","NKLA","WKHS","FSR","RIDE","SOLO","AYRO","ELMS",
]

# ── Biotech / Pharma (alta volatilidad por noticias FDA) ──
BIO = [
    "NVAX","VRTX","REGN","BIIB","SRPT","ACAD","SGEN","ALNY","BMRN","RARE",
    "FATE","CRSP","EDIT","NTLA","BEAM","VERV","PRME","BLUE","SAGE","ACMR",
    "OCGN","CLOV","HIMS","LMND","MNMD","ATAI","CMPS","SNDL","TLRY","CGON",
    "NEOS","BPMC","KRTX","DERM","PRAX","ARVN","KYMR","PCVX","MGTX","REPL",
]

# ── Meme / High momentum ──────────────────────────────────
MEME = [
    "GME","AMC","KOSS","BB","NOK","BBIG","SPCE","MULN","PHIL","IDEX",
    "CENN","EZGO","MVIS","PROG","ATER","NAKD","EXPR","KPLT","PAYA","CELH",
    "SKIN","ZYME","LGVN","VVOS","APCX","NXTP","JWSM","GFAI","BREA","SYRA",
]

# ── Cloud / SaaS ──────────────────────────────────────────
SAAS = [
    "CRM","NOW","SNOW","DDOG","ZS","CRWD","OKTA","PLTR","NET","HUBS",
    "BILL","GTLB","MDB","ESTC","CFLT","APPN","ALTR","PEGA","AZPN","VEEV",
]

# ── Small caps y penny stocks alta volatilidad ────────────
# Estos son los que aparecen en Webull Top Gainers 5min
PENNY = [
    # Biotech small cap muy volátiles
    "BRIA","EDTK","TGHL","ZSPC","WSHP","MYSE","ONFO","CTNT","RAIN","CPHI",
    "NCRA","LVLU","HNST","AEHL","RCAT","CRKN","STSS","NXGL","PAVS","BSLK",
    "GPUS","VRPX","GFAI","APCX","NXTP","QNRX","CRTX","SRTX","HALO","DXYN",
    "IINN","BFRI","BFST","ATNF","PRST","MULN","CENN","IDEX","ILUS","VISL",
    "TPVG","NVOS","XTIA","SGBX","ILUS","RSSS","INPX","GFAI","PAVS","TCRT",
    # Más volátiles frecuentes
    "OCGN","CLOV","SNDL","TLRY","AGEN","ADXS","AGRX","AKBA","ALLT","ALVR",
    "AMPIO","ANGI","APDN","APOG","APPN","AREC","ARGT","ARKO","ARLO","ARMO",
    "ARQQ","ARTW","ARVL","ASLN","ASRT","ATAI","ATEC","ATIF","ATLX","ATNI",
    "ATOM","ATOS","ATRC","ATSG","ATVI","AUDC","AUPH","AUVI","AVAH","AVAV",
    "AVCO","AVDL","AVEO","AVIR","AVNW","AVPT","AVRO","AVTE","AVXL","AVYA",
    "AXDX","AXGN","AXNX","AXON","AXSM","AXTI","AZEK","AZUL","AZYO","BCTX",
    # Space / Drones
    "ASTS","LUNR","RKLB","ACHR","JOBY","LILM","IONQ","RGTI","QUBT","ARQQ",
    # Fintech small
    "SOFI","UPST","AFRM","ROOT","OPFI","DAVE","GHLD","CURO","ATLC","EZCORP",
    # Retail especulativos
    "BBBY","EXPR","CONN","PRTY","BFST","CATO","DXLG","EXPR","GIII","HOFT",
]

# ── ETFs de alta volatilidad ──────────────────────────────
ETFS = [
    "QQQ","SPY","IWM","SOXL","TQQQ","ARKK","UVXY","SOXS","LABU","NAIL",
    "TNA","SPXL","UPRO","UDOW","MIDU","URTY","NUGT","DUST","JNUG","JDST",
]

# ── China ADR ─────────────────────────────────────────────
CHINA = [
    "BABA","JD","PDD","TCOM","GRAB","SE","TIGR","FUTU","NIO","XPEV",
    "LI","BILI","IQ","VIPS","BZUN","GOTU","TUYA","LKNCY","DIDI","TAL",
]

# ── Media / Entretenimiento ───────────────────────────────
MEDIA = [
    "PARA","WBD","FOXA","SPOT","ROKU","FUBO","SIRI","IMAX","NWSA","LUMN",
    "RBLX","U","SNAP","PINS","TWTR","MTTR","SKLZ","HUYA","DOYU","ATER",
]

# Universo total deduplicado
UNIVERSO_TOTAL = list(dict.fromkeys(
    LARGE + CRYPTO + EV + BIO + MEME + SAAS + PENNY + ETFS + CHINA + MEDIA
))

# ══════════════════════════════════════════════════════════
#  SESIÓN DE MERCADO
# ══════════════════════════════════════════════════════════
def get_session():
    tz  = pytz.timezone("US/Eastern")
    now = datetime.now(tz)
    h   = now.hour + now.minute / 60.0
    if   4.0  <= h < 9.5:  return "PRE-MARKET"
    elif 9.5  <= h < 16.0: return "REGULAR"
    elif 16.0 <= h < 20.0: return "AFTER-HOURS"
    else:                   return "CERRADO"

SESSION = get_session()

# Configuración por sesión
# (interval, period, prepost, cambio_min_dflt, vol_min_dflt)
SESSION_CFG = {
    "PRE-MARKET":  ("1m", "1d", True,  0.50, 100),
    "REGULAR":     ("1m", "1d", True,  0.50, 500),
    "AFTER-HOURS": ("1m", "1d", True,  0.30, 50),
    "CERRADO":     ("5m", "5d", False, 0.50, 100),
}

# ══════════════════════════════════════════════════════════
#  DESCARGA ROBUSTA — maneja MultiIndex y errores
# ══════════════════════════════════════════════════════════
def extraer_df(raw, ticker, chunk_size):
    """Extrae DataFrame limpio de la descarga de yfinance."""
    try:
        if chunk_size == 1:
            df = raw.copy()
        elif isinstance(raw.columns, pd.MultiIndex):
            lvl0 = raw.columns.get_level_values(0).unique()
            if ticker in lvl0:
                df = raw[ticker].copy()
            else:
                return None
        else:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna(how="all")
        # Verificar columnas mínimas
        needed = {"Close", "High", "Low", "Open", "Volume"}
        if not needed.issubset(set(df.columns)):
            return None
        df = df.dropna(subset=["Close", "Volume"])
        return df if len(df) >= 5 else None
    except Exception:
        return None


# ══════════════════════════════════════════════════════════
#  INDICADORES TÉCNICOS
# ══════════════════════════════════════════════════════════
def calcular_indicadores(df: pd.DataFrame):
    """Calcula todos los indicadores. Retorna df enriquecido o None."""
    try:
        df = df.copy()
        # Forzar Series 1D
        C = pd.to_numeric(df["Close"],  errors="coerce").squeeze()
        H = pd.to_numeric(df["High"],   errors="coerce").squeeze()
        L = pd.to_numeric(df["Low"],    errors="coerce").squeeze()
        O = pd.to_numeric(df["Open"],   errors="coerce").squeeze()
        V = pd.to_numeric(df["Volume"], errors="coerce").squeeze()

        if isinstance(C, pd.DataFrame): C = C.iloc[:,0]
        if isinstance(H, pd.DataFrame): H = H.iloc[:,0]
        if isinstance(L, pd.DataFrame): L = L.iloc[:,0]
        if isinstance(O, pd.DataFrame): O = O.iloc[:,0]
        if isinstance(V, pd.DataFrame): V = V.iloc[:,0]

        df["C"] = C.values
        df["H"] = H.values
        df["L"] = L.values
        df["O"] = O.values
        df["V"] = V.fillna(0).values

        n = len(df)
        if n < 5:
            return None

        # EMAs
        df["ema9"]  = df["C"].ewm(span=9,  adjust=False).mean()
        df["ema20"] = df["C"].ewm(span=20, adjust=False).mean()
        df["ema50"] = df["C"].ewm(span=min(50, n), adjust=False).mean()

        # VWAP (acumulado desde inicio del período)
        tp = (df["H"] + df["L"] + df["C"]) / 3
        cum_vol = df["V"].cumsum()
        df["vwap"] = np.where(cum_vol > 0, (tp * df["V"]).cumsum() / cum_vol, df["C"])

        # RSI 14
        delta = df["C"].diff()
        gain  = delta.where(delta > 0, 0.0).rolling(min(14,n)).mean()
        loss  = (-delta.where(delta < 0, 0.0)).rolling(min(14,n)).mean()
        df["rsi"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
        df["rsi"] = df["rsi"].fillna(50)

        # MACD
        span_s = min(12, n); span_l = min(26, n)
        ema12 = df["C"].ewm(span=span_s, adjust=False).mean()
        ema26 = df["C"].ewm(span=span_l, adjust=False).mean()
        df["macd"]   = ema12 - ema26
        df["macd_s"] = df["macd"].ewm(span=min(9,n), adjust=False).mean()
        df["macd_h"] = df["macd"] - df["macd_s"]

        # Bollinger
        roll = min(20, n)
        sma  = df["C"].rolling(roll).mean()
        std  = df["C"].rolling(roll).std()
        df["bb_up"] = sma + 2 * std
        df["bb_lo"] = sma - 2 * std

        # ATR
        hl = df["H"] - df["L"]
        hc = (df["H"] - df["C"].shift(1)).abs()
        lc = (df["L"] - df["C"].shift(1)).abs()
        df["atr"] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(min(14,n)).mean()
        df["atr"]  = df["atr"].fillna(df["C"] * 0.01)

        # Soporte y Resistencia — usar ventana dinámica
        w = min(20, n)
        df["sup"] = df["L"].rolling(w).min()
        df["res"] = df["H"].rolling(w).max()

        # Fallback: si soporte/resistencia es NaN usar precio actual
        last_c = float(df["C"].iloc[-1])
        df["sup"] = df["sup"].fillna(last_c * 0.97)
        df["res"] = df["res"].fillna(last_c * 1.03)

        # Volumen promedio
        df["vavg"] = df["V"].rolling(min(20,n)).mean().fillna(df["V"].mean())

        # Stochastic
        low14  = df["L"].rolling(min(14,n)).min()
        high14 = df["H"].rolling(min(14,n)).max()
        rng14  = (high14 - low14).replace(0, np.nan)
        df["stk"] = (100 * (df["C"] - low14) / rng14).fillna(50)
        df["std_k"] = df["stk"].rolling(min(3,n)).mean().fillna(50)

        return df

    except Exception:
        return None


# ══════════════════════════════════════════════════════════
#  SCORE DE EXPLOSIÓN 1-10
# ══════════════════════════════════════════════════════════
def get_val(row, col, default=0.0):
    try:
        v = row[col]
        f = float(v)
        return default if np.isnan(f) or np.isinf(f) else f
    except Exception:
        return default


def score_explosion(df, session: str):
    """Retorna (score_alcista 1-10, score_bajista 1-10, señal, detalles)."""
    if df is None or len(df) < 3:
        return 1, 1, "NEUTRO", {}

    a = df.iloc[-1]
    p = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    b = df.iloc[-3] if len(df) > 2 else p

    precio   = get_val(a, "C", 0)
    precio_p = get_val(p, "C", precio)
    precio_b = get_val(b, "C", precio_p)

    if precio <= 0:
        return 1, 1, "NEUTRO", {}

    # Pesos según sesión
    if session == "REGULAR":
        W = dict(vwap=2.0, ema=2.0, rsi=1.5, vol=2.0, macd=1.5, bb=0.5, stoch=0.5)
    else:
        # Pre/After: más sensible al precio vs VWAP y EMA, menos al volumen
        W = dict(vwap=2.5, ema=2.5, rsi=1.5, vol=0.5, macd=1.5, bb=0.5, stoch=0.5)

    up = down = 0.0
    det = {}

    # 1. VWAP
    vwap = get_val(a, "vwap", precio)
    pct_vwap = (precio - vwap) / vwap * 100
    if precio > vwap:
        up += W["vwap"]
        det["VWAP"] = f"▲ Precio {pct_vwap:+.2f}% sobre VWAP ${vwap:.3f}"
    else:
        down += W["vwap"]
        det["VWAP"] = f"▼ Precio {pct_vwap:+.2f}% bajo VWAP ${vwap:.3f}"

    # 2. EMA 9 vs 20
    e9  = get_val(a, "ema9",  precio)
    e20 = get_val(a, "ema20", precio)
    if e9 > e20:
        up += W["ema"]
        det["EMA"] = f"▲ EMA9 ({e9:.3f}) sobre EMA20 ({e20:.3f})"
    else:
        down += W["ema"]
        det["EMA"] = f"▼ EMA9 ({e9:.3f}) bajo EMA20 ({e20:.3f})"

    # 3. RSI
    rsi = get_val(a, "rsi", 50)
    if rsi > 65:
        up += W["rsi"]
        det["RSI"] = f"▲ RSI fuerte {rsi:.0f} — momentum"
    elif rsi > 55:
        up += W["rsi"] * 0.6
        det["RSI"] = f"▲ RSI positivo {rsi:.0f}"
    elif rsi < 35:
        down += W["rsi"]
        det["RSI"] = f"▼ RSI débil {rsi:.0f} — presión vendedora"
    elif rsi < 45:
        down += W["rsi"] * 0.6
        det["RSI"] = f"▼ RSI bajista {rsi:.0f}"
    else:
        det["RSI"] = f"→ RSI neutro {rsi:.0f}"

    # 4. Volumen vs promedio
    vavg  = get_val(a, "vavg", 1)
    vol_a = get_val(a, "V", 0)
    vratio = vol_a / max(vavg, 1)
    if vratio >= 3.0:
        if precio >= precio_p:
            up += W["vol"]
            det["VOL"] = f"⚡ VOL EXPLOSIVO {vratio:.1f}x — señal fuerte"
        else:
            down += W["vol"]
            det["VOL"] = f"⚡ VOL BAJISTA {vratio:.1f}x — presión"
    elif vratio >= 1.5:
        if precio >= precio_p:
            up += W["vol"] * 0.7
            det["VOL"] = f"▲ Vol elevado {vratio:.1f}x"
        else:
            down += W["vol"] * 0.7
            det["VOL"] = f"▼ Vol bajista {vratio:.1f}x"
    elif vratio >= 1.0:
        det["VOL"] = f"→ Vol normal {vratio:.1f}x"
    else:
        det["VOL"] = f"→ Vol bajo {vratio:.1f}x"

    # 5. MACD histograma — 3 velas consecutivas
    mh_a = get_val(a, "macd_h", 0)
    mh_p = get_val(p, "macd_h", 0)
    mh_b = get_val(b, "macd_h", 0)
    if mh_a > mh_p > mh_b and mh_a > 0:
        up += W["macd"]
        det["MACD"] = "▲ MACD histograma creciente — 3 velas consecutivas"
    elif mh_a < mh_p < mh_b and mh_a < 0:
        down += W["macd"]
        det["MACD"] = "▼ MACD histograma cayendo — 3 velas consecutivas"
    elif mh_a > 0:
        up += W["macd"] * 0.4
        det["MACD"] = "→ MACD positivo"
    else:
        down += W["macd"] * 0.4
        det["MACD"] = "→ MACD negativo"

    # 6. Bollinger Bands
    bb_up = get_val(a, "bb_up", precio * 1.02)
    bb_lo = get_val(a, "bb_lo", precio * 0.98)
    rng   = max(bb_up - bb_lo, 1e-9)
    bb_pos = (precio - bb_lo) / rng
    if bb_pos > 0.85:
        up += W["bb"]
        det["BB"] = f"▲ Rompiendo banda superior Bollinger ({bb_pos:.0%})"
    elif bb_pos < 0.15:
        down += W["bb"]
        det["BB"] = f"▼ Banda inferior Bollinger ({bb_pos:.0%})"
    else:
        det["BB"] = f"→ Zona media BB ({bb_pos:.0%})"

    # 7. Stochastic %K vs %D
    stk = get_val(a, "stk", 50)
    std = get_val(a, "std_k", 50)
    if 20 < stk < 80:
        if stk > std:
            up += W["stoch"]
            det["STOCH"] = f"▲ Stoch K={stk:.0f} > D={std:.0f}"
        else:
            down += W["stoch"]
            det["STOCH"] = f"▼ Stoch K={stk:.0f} < D={std:.0f}"
    elif stk >= 80:
        det["STOCH"] = f"⚠️ Sobrecompra K={stk:.0f}"
        up -= 0.3
    else:
        det["STOCH"] = f"⚠️ Sobreventa K={stk:.0f}"
        down -= 0.3

    # ── BONUS: Patrón de 3 velas alcistas/bajistas consecutivas ──
    # Este es el "primer minuto de arranque"
    c1 = get_val(df.iloc[-1], "C", precio);   o1 = get_val(df.iloc[-1], "O", c1)
    c2 = get_val(df.iloc[-2], "C", c1) if len(df)>1 else c1
    o2 = get_val(df.iloc[-2], "O", c2) if len(df)>1 else c2
    c3 = get_val(df.iloc[-3], "C", c2) if len(df)>2 else c2
    o3 = get_val(df.iloc[-3], "O", c3) if len(df)>2 else c3

    tres_alcistas = (c1>o1) and (c2>o2) and (c3>o3) and (c1>c2) and (c2>c3)
    tres_bajistas = (c1<o1) and (c2<o2) and (c3<o3) and (c1<c2) and (c2<c3)

    if tres_alcistas:
        up   += 2.0
        det["PATRÓN"] = "🔥 3 velas VERDES consecutivas — ARRANQUE CONFIRMADO"
    elif tres_bajistas:
        down += 2.0
        det["PATRÓN"] = "🔥 3 velas ROJAS consecutivas — CAÍDA CONFIRMADA"
    elif c1 > o1 and c2 > o2:
        up   += 0.8
        det["PATRÓN"] = "▲ 2 velas verdes — iniciando impulso"
    elif c1 < o1 and c2 < o2:
        down += 0.8
        det["PATRÓN"] = "▼ 2 velas rojas — presión bajista"
    else:
        det["PATRÓN"] = "→ Sin patrón de velas claro"

    # Normalizar 1-10
    max_pts = sum(W.values()) + 2.0
    s_up   = max(1, min(10, round((max(up,   0) / max_pts) * 10)))
    s_down = max(1, min(10, round((max(down, 0) / max_pts) * 10)))

    # Señal
    if   s_up >= 8:   senal = "🚀 EXPLOSIÓN ALCISTA"
    elif s_up >= 6:   senal = "📈 COMPRA"
    elif s_down >= 8: senal = "💥 CAÍDA"
    elif s_down >= 6: senal = "📉 VENTA"
    else:             senal = "⚪ NEUTRO"

    return s_up, s_down, senal, det


# ══════════════════════════════════════════════════════════
#  SL / TP DINÁMICO
# ══════════════════════════════════════════════════════════
def calc_sl_tp(df, precio, senal, mult_sl=2.0, mult_tp=4.0):
    try:
        a   = df.iloc[-1]
        atr = get_val(a, "atr", precio * 0.01)
        sup = get_val(a, "sup", precio * 0.97)
        res = get_val(a, "res", precio * 1.03)

        # Sanity check
        if sup <= 0 or sup >= precio:
            sup = precio * 0.97
        if res <= 0 or res <= precio:
            res = precio * 1.03

        alcista = any(x in senal for x in ["COMPRA", "ALCISTA", "EXPLOSIÓN"])
        if alcista:
            sl = round(max(precio - atr * mult_sl, sup * 0.998), 4)
            tp = round(min(precio + atr * mult_tp, res * 0.999), 4)
        else:
            sl = round(min(precio + atr * mult_sl, res * 1.002), 4)
            tp = round(max(precio - atr * mult_tp, sup * 1.001), 4)

        # Evitar SL/TP inválidos
        if sl <= 0: sl = round(precio * 0.97, 4)
        if tp <= 0: tp = round(precio * 1.06, 4)

        rr = round(abs(tp - precio) / max(abs(precio - sl), 1e-6), 2)
        return sl, tp, rr
    except Exception:
        sl = round(precio * 0.97, 4)
        tp = round(precio * 1.06, 4)
        return sl, tp, 2.0


# ══════════════════════════════════════════════════════════
#  ESCANEO MASIVO — descarga en lotes + análisis
# ══════════════════════════════════════════════════════════
def escanear(tickers, interval, period, prepost,
             cambio_min, vol_min, precio_min_f, precio_max_f,
             mult_sl, mult_tp, session, top_n=50):

    resultados   = []
    pb           = st.progress(0.0, text="⚡ Preparando escaneo...")
    total        = len(tickers)
    lote         = 40   # lote más grande para velocidad
    dfs_raw      = {}

    # ── FASE 1: Descarga ─────────────────────────────────
    for i in range(0, total, lote):
        chunk = tickers[i:i+lote]
        pct   = min((i + lote) / total * 0.5, 0.5)
        pb.progress(pct, text=f"📡 Descargando {min(i+lote, total)}/{total} tickers...")

        try:
            raw = yf.download(
                chunk,
                period=period,
                interval=interval,
                group_by="ticker",
                prepost=prepost,        # CRÍTICO: True para pre/after hours
                progress=False,
                auto_adjust=True,
                threads=True,
                timeout=30,
            )
            for t in chunk:
                dfs_raw[t] = extraer_df(raw, t, len(chunk))
        except Exception as e:
            # Si falla el lote, intentar individualmente
            for t in chunk:
                try:
                    single = yf.download(
                        t, period=period, interval=interval,
                        prepost=prepost, progress=False,
                        auto_adjust=True, threads=False, timeout=15
                    )
                    dfs_raw[t] = extraer_df(single, t, 1)
                except Exception:
                    dfs_raw[t] = None

    # ── FASE 2: Análisis ─────────────────────────────────
    for idx, t in enumerate(tickers):
        pct2 = 0.5 + (idx + 1) / total * 0.5
        pb.progress(pct2, text=f"🔍 Analizando {t} ({idx+1}/{total})...")

        try:
            raw_df = dfs_raw.get(t)
            if raw_df is None or len(raw_df) < 5:
                continue

            df = calcular_indicadores(raw_df)
            if df is None or len(df) < 3:
                continue

            precio = float(df["C"].iloc[-1])
            if precio <= 0:
                continue

            # Filtro precio
            if not (precio_min_f <= precio <= precio_max_f):
                continue

            # Cambio % desde apertura del día
            open_day   = float(df["O"].iloc[0]) if float(df["O"].iloc[0]) > 0 else precio
            cambio_dia = (precio - open_day) / open_day * 100

            # Cambio % última vela (= primer minuto de movimiento)
            precio_ant  = float(df["C"].iloc[-2]) if len(df) > 1 else precio
            cambio_vela = (precio - precio_ant) / max(precio_ant, 1e-9) * 100

            # Filtro movimiento:
            # → en REGULAR: cambio del día ≥ min
            # → en PRE/AFTER: acepta si vela ≥ 0.15% aunque día sea pequeño
            umbral_vela = max(0.15, cambio_min * 0.2)
            if session == "REGULAR":
                if abs(cambio_dia) < cambio_min and abs(cambio_vela) < umbral_vela:
                    continue
            else:
                # Más permisivo en pre/after
                if abs(cambio_dia) < cambio_min and abs(cambio_vela) < umbral_vela:
                    continue

            # Filtro volumen
            vol_a = float(df["V"].iloc[-1])
            if vol_a < vol_min:
                continue

            s_up, s_down, senal, det = score_explosion(df, session)
            _sl, _tp, rr = calc_sl_tp(df, precio, senal, mult_sl, mult_tp)

            vavg   = float(df["vavg"].iloc[-1])
            vratio = round(vol_a / max(vavg, 1), 1)
            rsi    = float(df["rsi"].iloc[-1])
            sup    = float(df["sup"].iloc[-1])
            res    = float(df["res"].iloc[-1])
            atr    = float(df["atr"].iloc[-1])

            resultados.append({
                "Ticker"    : t,
                "Precio $"  : round(precio, 4),
                "Δ Vela %"  : round(cambio_vela, 2),
                "Δ Día %"   : round(cambio_dia, 2),
                "Score 🐂"  : s_up,
                "Score 🐻"  : s_down,
                "Señal"     : senal,
                "RSI"       : round(rsi, 1),
                "Vol x"     : vratio,
                "Soporte $" : round(sup, 4),
                "Resist $"  : round(res, 4),
                "ATR"       : round(atr, 4),
                "SL $"      : _sl,
                "TP $"      : _tp,
                "R:R"       : rr,
                "_det"      : det,
                "_df"       : df,
            })
        except Exception:
            continue

    pb.empty()

    if not resultados:
        return pd.DataFrame()

    df_res = pd.DataFrame(resultados)
    df_res = df_res.sort_values("Score 🐂", ascending=False).reset_index(drop=True)
    return df_res.head(top_n)


# ══════════════════════════════════════════════════════════
#  ALPACA HELPERS
# ══════════════════════════════════════════════════════════
def get_cuenta():
    try:    return alpaca.get_account()
    except: return None

def get_posiciones():
    try:    return alpaca.get_all_positions()
    except: return []

def cerrar_posicion(sym):
    try:    alpaca.close_position(sym); return True, f"✅ Cerrada {sym}"
    except Exception as e: return False, str(e)

def orden_compra(sym, qty, sl, tp):
    try:
        req = MarketOrderRequest(
            symbol=sym, qty=qty, side=OrderSide.BUY, time_in_force=TimeInForce.GTC,
            take_profit=TakeProfitRequest(limit_price=round(float(tp), 2)),
            stop_loss=StopLossRequest(stop_price=round(float(sl), 2))
        )
        alpaca.submit_order(req)
        return True, f"✅ BUY {qty}x {sym} | SL ${sl} | TP ${tp}"
    except Exception as e:
        return False, f"❌ {e}"

def orden_venta(sym, qty):
    try:
        req = MarketOrderRequest(sym=sym, qty=qty, side=OrderSide.SELL, time_in_force=TimeInForce.GTC)
        alpaca.submit_order(req)
        return True, f"✅ SELL {qty}x {sym}"
    except Exception as e:
        return False, f"❌ {e}"


# ══════════════════════════════════════════════════════════
#  ENCABEZADO
# ══════════════════════════════════════════════════════════
st.markdown('<h1 class="header-glow">⚡ THUNDER RADAR V91 ULTRA</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-dim">EXPLOSIÓN EN TIEMPO REAL · PENNY STOCKS · SCALPING · ALPACA PAPER</p>',
            unsafe_allow_html=True)

badge_map = {"REGULAR":"b-regular","PRE-MARKET":"b-premarket",
             "AFTER-HOURS":"b-afterhours","CERRADO":"b-closed"}
tz_et   = pytz.timezone("US/Eastern")
hora_et = datetime.now(tz_et).strftime("%H:%M:%S ET")
cuenta  = get_cuenta()

hc1, hc2, hc3 = st.columns(3)
with hc1:
    st.markdown(
        f'<span class="badge {badge_map.get(SESSION,"b-closed")}">● {SESSION}</span>'
        f' &nbsp;<span class="dot-live"></span><span style="color:#8b949e;font-size:.78em">EN VIVO</span>',
        unsafe_allow_html=True)
with hc2:
    st.markdown(f'<span style="color:#8b949e">🕐 {hora_et}</span>', unsafe_allow_html=True)
with hc3:
    if cuenta:
        eq  = float(cuenta.equity)
        pnl = eq - float(cuenta.last_equity)
        col = "#00ff88" if pnl >= 0 else "#ff4444"
        st.markdown(f'<span style="color:{col}">💰 ${eq:,.2f} &nbsp;|&nbsp; P&L {pnl:+,.2f}</span>',
                    unsafe_allow_html=True)

st.markdown('<hr class="neon">', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  BARRA LATERAL
# ══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ CONFIGURACIÓN")

    modo = st.selectbox("Modo de Escaneo", [
        "🔥 Momentum Explosión — Todo el mercado",
        "💎 Penny Stocks + Small Caps",
        "📈 Large Cap Alcistas",
        "🌅 Pre-Market Sensible",
        "🌆 After-Hours Sensible",
        "🎯 Tickers Manuales",
    ])

    st.markdown("---")
    iv_cfg, per_cfg, pp_cfg, chg_dflt, vol_dflt = SESSION_CFG.get(SESSION, ("1m","1d",True,0.5,100))

    if "Pre-Market" in modo or "After" in modo or SESSION in ("PRE-MARKET","AFTER-HOURS"):
        chg_dflt = 0.20
        vol_dflt = 30

    precio_min_f = st.number_input("Precio Mín $", value=0.05, step=0.05, min_value=0.01,
                                   help="0.05 para incluir penny stocks")
    precio_max_f = st.number_input("Precio Máx $", value=800.0, step=10.0)

    lbl = "Δ% mínimo última vela" if SESSION != "REGULAR" else "Δ% mínimo desde apertura"
    cambio_min = st.slider(lbl, 0.0, 15.0, float(chg_dflt), 0.05,
                           help="Qué tanto debe moverse para aparecer en el radar")

    vol_min = st.number_input("Vol mínimo última vela", value=int(vol_dflt), step=10, min_value=0,
                              help="Baja a 0 para pre/after con poco volumen")

    top_n_f = st.slider("Top resultados", 10, 100, 40, 5)

    st.markdown("---")
    atr_sl = st.slider("ATR × Stop Loss",   0.5, 5.0, 2.0, 0.5)
    atr_tp = st.slider("ATR × Take Profit", 1.0, 8.0, 4.0, 0.5)

    st.markdown("---")
    # Selección de universo según modo
    if modo == "💎 Penny Stocks + Small Caps":
        lista_scan = list(dict.fromkeys(PENNY + MEME + BIO + CRYPTO + EV))
    elif modo == "📈 Large Cap Alcistas":
        lista_scan = list(dict.fromkeys(LARGE + SAAS + ETFS))
    elif modo == "🌅 Pre-Market Sensible":
        lista_scan = UNIVERSO_TOTAL
        cambio_min = min(cambio_min, 0.20)
        vol_min    = min(vol_min, 30)
    elif modo == "🌆 After-Hours Sensible":
        lista_scan = UNIVERSO_TOTAL
        cambio_min = min(cambio_min, 0.15)
        vol_min    = min(vol_min, 20)
    elif modo == "🎯 Tickers Manuales":
        txt = st.text_area("Tickers (sep. coma)",
                           "AAPL,TSLA,NVDA,GME,COIN,MARA,RIOT,SOFI,BRIA,TGHL", height=90)
        lista_scan = [t.strip().upper() for t in txt.split(",") if t.strip()]
    else:
        lista_scan = UNIVERSO_TOTAL

    st.info(f"📊 Universo: **{len(lista_scan)}** activos")
    st.info(f"🕐 Sesión: **{SESSION}** | Intervalo: **{iv_cfg}**")

    st.markdown("---")
    modo_auto = st.toggle("🤖 Auto-Trade", value=False)
    if modo_auto:
        auto_score = st.slider("Score mínimo", 7, 10, 8)
        auto_qty   = st.number_input("Acciones / orden", value=1, min_value=1)
        max_pos    = st.number_input("Máx posiciones", value=3, min_value=1)
        st.warning("⚠️ Ejecuta órdenes REALES en Paper.")

    st.markdown("---")
    auto_refresh = st.toggle("🔁 Auto-escaneo", value=False)
    refresh_seg  = 45 if SESSION == "REGULAR" else 55


# ══════════════════════════════════════════════════════════
#  PORTAFOLIO ACTIVO
# ══════════════════════════════════════════════════════════
st.subheader("💼 Portafolio Activo — P&L en Tiempo Real")
posiciones = get_posiciones()
if posiciones:
    rows = []
    for p in posiciones:
        pnl_p = float(p.unrealized_plpc) * 100
        pnl_u = float(p.unrealized_pl)
        ico   = "🟢" if pnl_p >= 0 else "🔴"
        rows.append({
            "Ticker":    p.symbol,
            "Qty":       p.qty,
            "Entrada $": round(float(p.avg_entry_price), 4),
            "Actual $":  round(float(p.current_price), 4),
            "P&L %":     f"{ico} {pnl_p:+.2f}%",
            "P&L $":     f"${pnl_u:+.2f}",
            "Valor $":   f"${float(p.market_value):,.2f}",
        })
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
            st.warning("Cerrando todo...")
else:
    st.info("Sin posiciones abiertas. ¡Usa el radar para encontrar oportunidades! 🎯")

st.markdown('<hr class="neon">', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  MOTOR DE ESCANEO
# ══════════════════════════════════════════════════════════
st.subheader("🔭 Radar de Explosión — Primer Minuto de Movimiento")

if "df_scan"   not in st.session_state: st.session_state.df_scan   = pd.DataFrame()
if "last_scan" not in st.session_state: st.session_state.last_scan = None

sb1, sb2 = st.columns([3,1])
with sb1: iniciar = st.button("🚀 INICIAR ESCANEO COMPLETO", use_container_width=True)
with sb2:
    if st.button("🔄 Refresh UI", use_container_width=True): st.rerun()

# Disparar escaneo
debe = iniciar or (
    auto_refresh
    and st.session_state.last_scan is not None
    and (time.time() - st.session_state.last_scan) >= refresh_seg
)

if debe:
    msg_scan = f"⚡ Escaneando {len(lista_scan)} activos en sesión {SESSION}..."
    with st.spinner(msg_scan):
        df_scan = escanear(
            lista_scan, iv_cfg, per_cfg, pp_cfg,
            cambio_min, vol_min,
            precio_min_f, precio_max_f,
            atr_sl, atr_tp, SESSION, top_n_f
        )
    st.session_state.df_scan   = df_scan
    st.session_state.last_scan = time.time()
    ts = datetime.now(tz_et).strftime("%H:%M:%S ET")
    st.success(f"✅ Escaneo completado a las {ts} — {len(df_scan)} señales encontradas")

df_scan = st.session_state.df_scan

# ══════════════════════════════════════════════════════════
#  RESULTADOS
# ══════════════════════════════════════════════════════════
if not df_scan.empty:

    boom  = df_scan[df_scan["Score 🐂"] >= 7]
    otros = df_scan[df_scan["Score 🐂"] <  7]

    # ── TARJETAS DE EXPLOSIÓN ────────────────────────────
    if not boom.empty:
        cnt_str = f"({len(boom)} señales)"
        st.markdown(f"### 🔥 EXPLOSIONES DETECTADAS {cnt_str}")

        for _, row in boom.iterrows():
            s     = int(row["Score 🐂"])
            cls   = "score-10" if s==10 else ("score-high" if s>=8 else "score-mid")
            dc    = "#00ff88" if row["Δ Vela %"] >= 0 else "#ff4444"
            dd    = "#00ff88" if row["Δ Día %"]  >= 0 else "#ff4444"
            card  = "boom-card" if "ALCIST" in row["Señal"] or "COMPRA" in row["Señal"] or "EXPLOS" in row["Señal"] else "boom-card-sell"

            st.markdown(f"""
            <div class="{card}">
              <span class="ticker-big">⚡ {row['Ticker']}</span>
              &nbsp;&nbsp;<span class="{cls}">{s}/10</span>
              &nbsp;&nbsp;<span style="color:#a78bfa;font-size:.9em">{row['Señal']}</span>
              <br style="margin:4px">
              <span class="label-dim">Precio</span>&nbsp;<b style="color:#fff">${row['Precio $']}</b>
              &nbsp;|&nbsp;
              <span class="label-dim">Δ Vela</span>&nbsp;<b style="color:{dc}">{row['Δ Vela %']:+.2f}%</b>
              &nbsp;|&nbsp;
              <span class="label-dim">Δ Día</span>&nbsp;<b style="color:{dd}">{row['Δ Día %']:+.2f}%</b>
              &nbsp;|&nbsp;
              <span class="label-dim">RSI</span>&nbsp;{row['RSI']}
              &nbsp;|&nbsp;
              <span class="label-dim">Vol</span>&nbsp;{row['Vol x']}x
              &nbsp;|&nbsp;
              <span class="label-dim">SL</span>&nbsp;<span style="color:#ff6b6b">${row['SL $']}</span>
              &nbsp;|&nbsp;
              <span class="label-dim">TP</span>&nbsp;<span style="color:#00ff88">${row['TP $']}</span>
              &nbsp;|&nbsp;
              <span class="label-dim">R:R</span>&nbsp;{row['R:R']}x
            </div>
            """, unsafe_allow_html=True)

    # ── TABLA COMPLETA ───────────────────────────────────
    st.markdown("### 📋 Tabla Completa del Radar")
    cols = ["Ticker","Precio $","Δ Vela %","Δ Día %","Score 🐂","Score 🐻",
            "Señal","RSI","Vol x","Soporte $","Resist $","SL $","TP $","R:R"]
    df_show = df_scan[cols].copy()

    def c_score(v):
        if v >= 8:   return "background-color:#15803d;color:white"
        elif v >= 6: return "background-color:#1d4ed8;color:white"
        elif v >= 4: return "background-color:#92400e;color:white"
        else:        return "background-color:#7f1d1d;color:white"

    def c_delta(v):
        return f"color:{'#00ff88' if v>=0 else '#ff4444'};font-weight:bold"

    fmt = {
        "Precio $":"${:.4f}","Δ Vela %":"{:+.2f}%","Δ Día %":"{:+.2f}%",
        "RSI":"{:.1f}","Vol x":"{:.1f}x","Soporte $":"${:.4f}",
        "Resist $":"${:.4f}","SL $":"${:.4f}","TP $":"${:.4f}","R:R":"{:.2f}"
    }

    try:
        styled = (df_show.style
                  .map(c_score, subset=["Score 🐂","Score 🐻"])
                  .map(c_delta, subset=["Δ Vela %","Δ Día %"])
                  .format(fmt))
    except Exception:
        try:
            styled = (df_show.style
                      .applymap(c_score, subset=["Score 🐂","Score 🐻"])
                      .applymap(c_delta, subset=["Δ Vela %","Δ Día %"])
                      .format(fmt))
        except Exception:
            styled = df_show.style.format(fmt)

    st.dataframe(styled, use_container_width=True, hide_index=True, height=450)

    # ── AUTO-TRADE ───────────────────────────────────────
    if modo_auto:
        st.markdown("### 🤖 Auto-Trade")
        n_pos      = len(get_posiciones())
        candidatos = df_scan[df_scan["Score 🐂"] >= auto_score]
        if candidatos.empty:
            st.info(f"Sin candidatos con score ≥ {auto_score}")
        for _, row in candidatos.iterrows():
            if n_pos >= max_pos:
                st.warning(f"Máx {max_pos} posiciones alcanzado."); break
            ok, msg = orden_compra(row["Ticker"], auto_qty, row["SL $"], row["TP $"])
            if ok: n_pos += 1
            st.write(msg)

    # ── EJECUCIÓN MANUAL ─────────────────────────────────
    st.markdown('<hr class="neon">', unsafe_allow_html=True)
    st.markdown("### 🛒 Ejecución Manual")

    ce1, ce2 = st.columns([1, 2])
    with ce1:
        t_op  = st.selectbox("Ticker a operar", df_scan["Ticker"].tolist())
        rsel  = df_scan[df_scan["Ticker"] == t_op].iloc[0]
        qty_m = st.number_input("Cantidad de acciones", value=1, min_value=1, step=1)
        sl_m  = st.number_input("Stop Loss $",   value=float(rsel["SL $"]),  step=0.001, format="%.4f")
        tp_m  = st.number_input("Take Profit $", value=float(rsel["TP $"]),  step=0.001, format="%.4f")
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
        st.markdown(f"### 📊 Análisis Detallado: {t_op}")
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Precio $",  f"${rsel['Precio $']:.4f}")
        m2.metric("Δ Vela",    f"{rsel['Δ Vela %']:+.2f}%")
        m3.metric("Score 🐂",  f"{rsel['Score 🐂']}/10")
        m4.metric("R:R",       f"{rsel['R:R']}x")
        m5,m6,m7,m8 = st.columns(4)
        m5.metric("RSI",       f"{rsel['RSI']}")
        m6.metric("SL $",      f"${rsel['SL $']:.4f}")
        m7.metric("TP $",      f"${rsel['TP $']:.4f}")
        m8.metric("Vol x avg", f"{rsel['Vol x']}x")

        det = rsel.get("_det", {})
        if det:
            st.markdown("**📌 Detalle de la señal:**")
            for k, v in det.items():
                c = "#00ff88" if "▲" in v else ("#ff4444" if "▼" in v else "#ffc107")
                st.markdown(
                    f'<span style="color:{c};font-size:.82em"><b>{k}</b>: {v}</span>',
                    unsafe_allow_html=True)

elif st.session_state.last_scan is not None:
    st.warning("""
    ⚠️ **Sin señales con los filtros actuales.** Prueba:
    - Bajar el **Δ% mínimo** (slider) a 0.10 o menos
    - Bajar el **Volumen mínimo** a 0 o 10
    - Cambiar a modo **Penny Stocks + Small Caps**
    - Verificar que el mercado esté abierto (pre/after/regular)
    """)
else:
    st.info("👆 Pulsa **🚀 INICIAR ESCANEO COMPLETO** para comenzar.")

# ══════════════════════════════════════════════════════════
#  AUTO-REFRESH LOOP
# ══════════════════════════════════════════════════════════
if auto_refresh:
    time.sleep(refresh_seg)
    st.rerun()

# ══════════════════════════════════════════════════════════
#  PIE DE PÁGINA
# ══════════════════════════════════════════════════════════
st.markdown('<hr class="neon">', unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#8b949e;font-size:.71em;font-family:'Share Tech Mono',monospace">
⚡ THUNDER RADAR V91 ULTRA — PAPER TRADING — Solo uso educativo y experimental<br>
Los resultados pasados no garantizan rendimientos futuros. Invierte con responsabilidad.
</div>
""", unsafe_allow_html=True)
