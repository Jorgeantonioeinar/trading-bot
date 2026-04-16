"""
╔══════════════════════════════════════════════════════════════════╗
║        THUNDER RADAR V92 — MOTOR DE ACELERACIÓN                 ║
║                                                                  ║
║  ✅ Universo DINÁMICO: obtiene TODOS los stocks de NYSE/NASDAQ   ║
║     via Twelve Data (gratis, sin API key) + Yahoo Finance        ║
║  ✅ Solo ACCIONES (no ETF, no cripto, no forex)                  ║
║  ✅ Incluye ADRs (acciones extranjeras en bolsa USA)             ║
║  ✅ Detecta el MOMENTO EXACTO de despegue (no cuando ya subió)   ║
║  ✅ Motor: RVOL × Aceleración de Precio × Confirmación técnica   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime, timedelta
import pytz
import time
import warnings
warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════
#  CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="⚡ THUNDER RADAR V92",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
html,body,[class*="css"]{background:#030810!important;color:#c9d1d9!important;font-family:'Share Tech Mono',monospace;}
h1,h2,h3{font-family:'Orbitron',sans-serif!important;}
.stButton>button{width:100%;border-radius:4px;font-weight:bold;font-family:'Orbitron',sans-serif;
    letter-spacing:1px;border:1px solid #30363d;transition:all .2s;}
.stButton>button:hover{transform:translateY(-1px);box-shadow:0 0 16px rgba(0,255,136,.6);}
div[data-testid="metric-container"]{background:linear-gradient(135deg,#0a0f1a,#141b27);
    border:1px solid #1e2739;border-radius:8px;padding:12px;}

/* ── TARJETAS ── */
.card-launch{background:linear-gradient(135deg,#061510,#0a0f1a);border:2px solid #00ff88;
    border-radius:10px;padding:14px 18px;margin:6px 0;box-shadow:0 0 18px #00ff8855;}
.card-watch{background:linear-gradient(135deg,#0f100a,#0a0f1a);border:1px solid #ffc107;
    border-radius:10px;padding:12px 16px;margin:4px 0;}
.card-neutral{background:#0a0c10;border:1px solid #1e2739;border-radius:8px;padding:10px 14px;margin:3px 0;}

.sc10{color:#00ff88;font-size:1.8em;font-weight:900;font-family:'Orbitron',sans-serif;}
.sc8 {color:#39ff14;font-size:1.5em;font-weight:800;}
.sc6 {color:#ffc107;font-size:1.3em;font-weight:700;}
.sc4 {color:#ff6b6b;font-size:1.1em;}
.tkr {font-family:'Orbitron',sans-serif;font-size:1.3em;font-weight:900;color:#fff;}
.lbl {color:#8b949e;font-size:0.76em;}
.rvol-fire{color:#ff4500;font-weight:900;}
.rvol-hi  {color:#ff8c00;font-weight:700;}
.rvol-ok  {color:#ffc107;}

.hdr{text-align:center;font-family:'Orbitron',sans-serif;font-size:2.1em;font-weight:900;
    background:linear-gradient(90deg,#00ff88,#00d4ff,#ff4500);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:3px;}
.sub{text-align:center;color:#8b949e;font-size:.79em;letter-spacing:3px;}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:.75em;font-weight:bold;}
.b-reg{background:#15803d;color:#fff;}.b-pre{background:#7c3aed;color:#fff;}
.b-aft{background:#0369a1;color:#fff;}.b-cls{background:#374151;color:#fff;}
.dot{display:inline-block;width:9px;height:9px;background:#00ff88;border-radius:50%;
    margin-right:5px;animation:blink 1s infinite;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.1}}
hr.n{border:none;border-top:1px solid #00ff8822;margin:14px 0;}
.info-box{background:linear-gradient(135deg,#0a0f1a,#111827);border:1px solid #00ff8833;
    border-radius:8px;padding:10px 14px;margin:6px 0;font-size:.80em;}
.status-ok {color:#00ff88;font-weight:bold;}
.status-err{color:#ff4444;font-weight:bold;}
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

# ══════════════════════════════════════════════════════════
#  OBTENER UNIVERSO DINÁMICO DE ACCIONES
#  Fuente: Twelve Data (gratis, sin API key) — devuelve
#  todos los stocks listados en NYSE / NASDAQ / AMEX
#  incluyendo ADRs (acciones extranjeras)
# ══════════════════════════════════════════════════════════
TWELVE_DATA_URL = "https://api.twelvedata.com/stocks"

@st.cache_data(ttl=3600)   # Cache 1 hora — la lista de tickers no cambia cada minuto
def obtener_universo_dinamico() -> list[str]:
    """
    Descarga la lista completa de acciones de NYSE + NASDAQ + AMEX
    usando Twelve Data (endpoint público, sin API key).
    Filtra: solo 'Common Stock' — excluye ETF, fondo, cripto, forex.
    Devuelve lista de símbolos.
    """
    tickers_total = []
    exchanges = ["NYSE", "NASDAQ", "AMEX"]

    for exc in exchanges:
        try:
            params = {
                "exchange": exc,
                "type":     "Common Stock",   # ← solo acciones reales
                "format":   "JSON",
            }
            r = requests.get(TWELVE_DATA_URL, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if "data" in data:
                    for item in data["data"]:
                        sym = item.get("symbol", "").strip().upper()
                        # Filtros básicos: no slash (warrants), largo razonable
                        if sym and "/" not in sym and len(sym) <= 5 and sym.isalpha():
                            tickers_total.append(sym)
        except Exception:
            pass

    tickers_total = list(dict.fromkeys(tickers_total))  # deduplicar

    # Si Twelve Data falla (sin conexión), usar lista de respaldo
    if len(tickers_total) < 100:
        tickers_total = _universo_respaldo()

    return tickers_total


def _universo_respaldo() -> list[str]:
    """
    Lista de respaldo con ~600 acciones volátiles conocidas.
    Se usa solo si Twelve Data no está disponible.
    Solo acciones (no ETF, no cripto, no forex).
    """
    return list(dict.fromkeys([
        # ── Large cap tech
        "AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","NFLX","AMD","INTC",
        "AVGO","QCOM","MU","AMAT","LRCX","SMCI","ON","TXN","ADI","MRVL",
        # ── Financiero
        "JPM","BAC","GS","MS","WFC","C","V","PYPL","SCHW","AXP","COF","SYF",
        # ── Salud / Pharma
        "PFE","ABBV","MRK","JNJ","LLY","BMY","GILD","MRNA","BNTX","NVAX",
        "VRTX","REGN","BIIB","SRPT","ACAD","HIMS","OCGN","SGEN","ALNY",
        # ── Biotech pequeñas (alta volatilidad)
        "FATE","CRSP","EDIT","NTLA","BEAM","VERV","BLUE","SAGE","ACMR",
        "MNMD","ATAI","CMPS","PRME","BPMC","KRTX","DERM","PRAX","ARVN","KYMR",
        "PCVX","MGTX","REPL","LGVN","VVOS","SYRA","APCX","NXTP","QNRX",
        "CRTX","SRTX","HALO","DXYN","IINN","BFRI","BFST","ATNF","PRST",
        # ── Cripto proxy (acciones, no cripto directamente)
        "COIN","HOOD","MSTR","RIOT","MARA","HUT","CIFR","BTBT","CLSK","WULF",
        "HIVE","IREN","BITF","BTCS","CORZ","ARBK","SATO","MIGI",
        # ── EV / Energía limpia
        "RIVN","LCID","CHPT","BLNK","PLUG","FCEL","BE","HYLN","GOEV","NKLA",
        "WKHS","FSR","SOLO","NIO","XPEV","LI","AYRO",
        # ── Meme / Alta volatilidad histórica
        "GME","AMC","KOSS","BB","NOK","BBIG","SPCE","MULN","IDEX","CENN",
        "MVIS","PROG","ATER","NAKD","EXPR","KPLT","CELH","SKIN","LGVN",
        # ── China ADR (acciones chinas en bolsa USA)
        "BABA","JD","PDD","TCOM","GRAB","SE","TIGR","FUTU","BILI","IQ",
        "VIPS","BZUN","GOTU","TUYA","TAL","DIDI","EDU","YMM","LAIX","DOYU",
        # ── Small/Micro caps volátiles
        "RSSS","NCRA","TGHL","BRIA","EDTK","ZSPC","WSHP","MYSE","ONFO",
        "CTNT","RAIN","CPHI","LVLU","HNST","AEHL","RCAT","CRKN","STSS",
        "NXGL","PAVS","BSLK","GPUS","VRPX","GFAI","SGBX","INPX","TCRT",
        "CLOV","SNDL","TLRY","AGEN","ADXS","AGRX","AKBA","ALLT","ALVR",
        "AMPIO","APDN","AREC","ARKO","ARLO","ARQQ","ARVL","ASLN","ASRT",
        "ATAI","ATIF","ATLX","ATNI","ATOM","ATOS","AUDC","AUPH","AUVI",
        "AVAH","AVCO","AVDL","AVEO","AVIR","AVNW","AVPT","AVRO","AVTE",
        "AVXL","AXDX","AXGN","AXNX","AXSM","AZEK","BCTX",
        # ── Espacio / Drones / Quantum
        "ASTS","LUNR","RKLB","ACHR","JOBY","LILM","IONQ","RGTI","QUBT",
        "MNTS","ASTR","SPIR","NKLA","MTTR","SKLZ",
        # ── Fintech pequeñas
        "SOFI","UPST","AFRM","ROOT","OPFI","DAVE","GHLD","CURO","ATLC",
        # ── Retail / Consumer
        "WMT","TGT","COST","HD","NKE","MCD","SBUX","ETSY","EBAY","W",
        "PTON","DOCU","ZM","TDOC","LYFT","UBER","DASH","ABNB","DKNG",
        # ── Media / Entretenimiento
        "PARA","WBD","FOXA","SPOT","ROKU","FUBO","SIRI","IMAX","NWSA",
        "RBLX","U","SNAP","PINS","DIS","CMCSA",
        # ── Industrial / Defensa
        "BA","LMT","RTX","NOC","GD","CAT","DE","GE","HON","MMM",
        # ── Cloud / SaaS
        "CRM","NOW","SNOW","DDOG","ZS","CRWD","OKTA","PLTR","NET","HUBS",
        "BILL","GTLB","MDB","CFLT","APPN","VEEV","AZPN",
        # ── Semiconductores
        "QCOM","MU","AMAT","LRCX","KLAC","MRVL","ON","TXN","ADI",
        # ── Tickers súper volátiles recientes
        "MGRT","YJ","ZBAI","MTEX","WSHP","MYSE","ONFO","CTNT","RAIN",
        "CPHI","NCRA","LVLU","AEHL","RCAT","CRKN","STSS","NXGL","BSLK",
    ]))


# ── Filtro para excluir no-acciones que puedan colarse
EXCLUDE_KEYWORDS = {
    # ETF / fondo (por si acaso)
    "ETF","FUND","TRUST","REIT","MLP","LP","INDEX",
}

def es_accion_valida(sym: str) -> bool:
    """Filtra símbolos que probablemente sean ETF o instrumentos no permitidos."""
    if not sym or not sym.isalpha():
        return False
    if len(sym) > 5:
        return False
    # Excluir símbolos de una sola letra (generalmente son índices)
    if len(sym) == 1:
        return False
    return True


# ══════════════════════════════════════════════════════════
#  PRE-FILTRO RÁPIDO (YAHOO FINANCE SCREENER)
#  Antes de escanear con datos de 1min, hacemos un pre-filtro
#  rápido descargando datos de 1 día para ver qué stocks
#  ya tienen movimiento/volumen relevante hoy
# ══════════════════════════════════════════════════════════
@st.cache_data(ttl=300)   # Cache 5 min
def prefiltro_activos(todos_tickers: list, precio_min: float, precio_max: float,
                      n_max: int = 400) -> list:
    """
    Descarga datos de 1 día (5min interval) para el universo completo.
    Devuelve los N tickers con mayor actividad relativa hoy.
    Esto reduce el universo a los candidatos más activos AHORA.
    """
    if not todos_tickers:
        return []

    activos = []
    lote = 100

    pb = st.progress(0.0, text="🔍 Pre-filtro: buscando stocks activos hoy...")

    for i in range(0, len(todos_tickers), lote):
        chunk = todos_tickers[i:i+lote]
        pct   = min((i + lote) / len(todos_tickers), 1.0)
        pb.progress(pct, text=f"🔍 Pre-filtro: {min(i+lote, len(todos_tickers))}/{len(todos_tickers)}...")

        try:
            raw = yf.download(
                chunk,
                period="1d",
                interval="5m",
                group_by="ticker",
                prepost=True,
                progress=False,
                auto_adjust=True,
                threads=True,
                timeout=20,
            )

            for t in chunk:
                try:
                    if len(chunk) == 1:
                        df_t = raw.copy()
                    elif isinstance(raw.columns, pd.MultiIndex) and t in raw.columns.get_level_values(0):
                        df_t = raw[t].copy()
                    else:
                        continue

                    if isinstance(df_t.columns, pd.MultiIndex):
                        df_t.columns = df_t.columns.get_level_values(0)

                    df_t = df_t.dropna(subset=["Close","Volume"])
                    if len(df_t) < 2:
                        continue

                    precio = float(df_t["Close"].iloc[-1])
                    if not (precio_min <= precio <= precio_max):
                        continue

                    vol_total = float(df_t["Volume"].sum())
                    if vol_total <= 0:
                        continue

                    # Calcular actividad relativa:
                    # vol_última_vela / vol_promedio → RVOL del prefiltro
                    vol_ult  = float(df_t["Volume"].iloc[-1])
                    vol_prom = float(df_t["Volume"].mean())
                    rvol_pre = vol_ult / max(vol_prom, 1)

                    # Cambio del día
                    open_d   = float(df_t["Open"].iloc[0])
                    cambio_d = (precio - open_d) / max(open_d, 1e-9) * 100

                    activos.append({
                        "ticker"   : t,
                        "precio"   : precio,
                        "rvol_pre" : rvol_pre,
                        "cambio_d" : cambio_d,
                        "vol_total": vol_total,
                    })
                except Exception:
                    continue
        except Exception:
            continue

    pb.empty()

    if not activos:
        return todos_tickers[:n_max]

    # Ordenar por RVOL pre-filtro (los que más se están moviendo AHORA)
    activos.sort(key=lambda x: abs(x["rvol_pre"]) * (1 + abs(x["cambio_d"]) * 0.1), reverse=True)

    return [a["ticker"] for a in activos[:n_max]]


# ══════════════════════════════════════════════════════════
#  EXTRACCIÓN SEGURA DE DATAFRAME
# ══════════════════════════════════════════════════════════
def extraer_df(raw, ticker: str, n_chunk: int) -> pd.DataFrame | None:
    try:
        if n_chunk == 1:
            df = raw.copy()
        elif isinstance(raw.columns, pd.MultiIndex):
            if ticker in raw.columns.get_level_values(0):
                df = raw[ticker].copy()
            else:
                return None
        else:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        needed = {"Close","High","Low","Open","Volume"}
        if not needed.issubset(set(df.columns)):
            return None

        df = df.dropna(subset=["Close","Volume"])
        return df if len(df) >= 5 else None
    except Exception:
        return None


# ══════════════════════════════════════════════════════════
#  INDICADORES TÉCNICOS
# ══════════════════════════════════════════════════════════
def calcular_indicadores(df: pd.DataFrame) -> pd.DataFrame | None:
    try:
        df = df.copy()

        def to_series(col):
            s = pd.to_numeric(df[col], errors="coerce").squeeze()
            if isinstance(s, pd.DataFrame): s = s.iloc[:,0]
            return s

        C = to_series("Close")
        H = to_series("High")
        L = to_series("Low")
        O = to_series("Open")
        V = to_series("Volume").fillna(0)

        df["C"] = C.values
        df["H"] = H.values
        df["L"] = L.values
        df["O"] = O.values
        df["V"] = V.values

        n = len(df)
        if n < 3: return None

        # EMAs
        df["ema9"]  = df["C"].ewm(span=min(9,n),  adjust=False).mean()
        df["ema20"] = df["C"].ewm(span=min(20,n), adjust=False).mean()

        # VWAP
        tp         = (df["H"] + df["L"] + df["C"]) / 3
        cum_vol    = df["V"].cumsum()
        df["vwap"] = np.where(cum_vol > 0, (tp * df["V"]).cumsum() / cum_vol, df["C"])

        # RSI
        delta      = df["C"].diff()
        gain       = delta.where(delta>0, 0.0).rolling(min(14,n)).mean()
        loss       = (-delta.where(delta<0, 0.0)).rolling(min(14,n)).mean()
        df["rsi"]  = (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50)

        # MACD
        df["macd"]   = (df["C"].ewm(span=min(12,n),adjust=False).mean()
                       - df["C"].ewm(span=min(26,n),adjust=False).mean())
        df["macd_s"] = df["macd"].ewm(span=min(9,n),adjust=False).mean()
        df["macd_h"] = df["macd"] - df["macd_s"]

        # Bollinger
        roll       = min(20,n)
        sma        = df["C"].rolling(roll).mean()
        std        = df["C"].rolling(roll).std()
        df["bb_up"]= sma + 2*std
        df["bb_lo"]= sma - 2*std

        # ATR
        hl  = df["H"] - df["L"]
        hc  = (df["H"] - df["C"].shift(1)).abs()
        lc  = (df["L"] - df["C"].shift(1)).abs()
        df["atr"] = pd.concat([hl,hc,lc],axis=1).max(axis=1).rolling(min(14,n)).mean()
        df["atr"] = df["atr"].fillna(df["C"] * 0.01)

        # Soporte / Resistencia
        w          = min(20,n)
        df["sup"]  = df["L"].rolling(w).min().fillna(df["C"] * 0.97)
        df["res"]  = df["H"].rolling(w).max().fillna(df["C"] * 1.03)

        # ── MOTOR DE ACELERACIÓN ──────────────────────────────
        # RVOL: volumen última vela vs promedio últimas 10 velas
        df["vavg10"] = df["V"].rolling(min(10,n)).mean().fillna(df["V"].mean())
        df["rvol"]   = df["V"] / df["vavg10"].replace(0, 1)

        # Velocidad de precio: % cambio entre velas consecutivas
        df["vel"]  = df["C"].pct_change() * 100          # % última vela
        df["vel2"] = df["C"].pct_change(2) * 100         # % últimas 2 velas
        df["vel3"] = df["C"].pct_change(3) * 100         # % últimas 3 velas

        # Aceleración: ¿la velocidad está aumentando?
        df["acel"] = df["vel"] - df["vel"].shift(1)      # positivo = acelerando

        # Stochastic
        low14      = df["L"].rolling(min(14,n)).min()
        high14     = df["H"].rolling(min(14,n)).max()
        df["stk"]  = (100*(df["C"]-low14)/(high14-low14+1e-9)).fillna(50)
        df["std_k"]= df["stk"].rolling(min(3,n)).mean().fillna(50)

        return df
    except Exception:
        return None


# ══════════════════════════════════════════════════════════
#  MOTOR DE ACELERACIÓN — SCORE 1-10
#  ⭐ LÓGICA CENTRAL DEL SISTEMA ⭐
#
#  NO medimos cuánto subió en el día.
#  Medimos VELOCIDAD + VOLUMEN de los últimos 60-120 segundos.
# ══════════════════════════════════════════════════════════
def g(row, col, default=0.0):
    """Get float value safely."""
    try:
        v = float(row[col])
        return default if (np.isnan(v) or np.isinf(v)) else v
    except Exception:
        return default


def motor_aceleracion(df: pd.DataFrame, session: str) -> tuple:
    """
    Retorna (score_alcista 1-10, score_bajista 1-10, señal, detalles, rvol_actual)

    PONDERACIÓN:
    ┌────────────────────────────────────────────┬───────┐
    │ Factor                                     │ Peso  │
    ├────────────────────────────────────────────┼───────┤
    │ 1. RVOL (volumen relativo última vela)     │  30%  │
    │ 2. Velocidad de precio (última vela %)     │  25%  │
    │ 3. Aceleración (velocidad creciente)       │  20%  │
    │ 4. Dirección técnica (VWAP/EMA)            │  15%  │
    │ 5. Confirmación (RSI/MACD/patrón velas)    │  10%  │
    └────────────────────────────────────────────┴───────┘
    """
    if df is None or len(df) < 3:
        return 1, 1, "NEUTRO", {}, 0

    a = df.iloc[-1]
    p = df.iloc[-2] if len(df)>1 else df.iloc[-1]
    b = df.iloc[-3] if len(df)>2 else p

    precio = g(a,"C",0)
    if precio <= 0:
        return 1, 1, "NEUTRO", {}, 0

    up = down = 0.0
    det = {}

    # ────────────────────────────────────────────────────────
    # FACTOR 1: RVOL — Relative Volume (PESO 30%)
    # ¿El volumen de esta vela es explosivo vs el promedio?
    # ────────────────────────────────────────────────────────
    rvol = g(a,"rvol",1)
    if rvol >= 10:
        up += 3.0; down += 0.5   # podría ser en cualquier dirección
        det["RVOL"] = f"🔥🔥🔥 RVOL = {rvol:.1f}x — EXPLOSIÓN DE VOLUMEN"
    elif rvol >= 5:
        up += 2.2; down += 0.3
        det["RVOL"] = f"🔥🔥 RVOL = {rvol:.1f}x — Volumen muy alto"
    elif rvol >= 3:
        up += 1.5
        det["RVOL"] = f"🔥 RVOL = {rvol:.1f}x — Volumen elevado"
    elif rvol >= 1.5:
        up += 0.8
        det["RVOL"] = f"▲ RVOL = {rvol:.1f}x — Volumen sobre promedio"
    else:
        det["RVOL"] = f"→ RVOL = {rvol:.1f}x — Volumen normal"

    # ────────────────────────────────────────────────────────
    # FACTOR 2: VELOCIDAD de precio última vela (PESO 25%)
    # ¿Cuánto % se movió en la última vela de 1 minuto?
    # ────────────────────────────────────────────────────────
    vel = g(a,"vel",0)    # % cambio última vela
    if vel >= 3.0:
        up += 2.5
        det["VEL"] = f"🚀 Velocidad última vela = +{vel:.2f}% — DESPEGUE"
    elif vel >= 1.5:
        up += 2.0
        det["VEL"] = f"▲▲ Velocidad = +{vel:.2f}% — Fuerte"
    elif vel >= 0.5:
        up += 1.2
        det["VEL"] = f"▲ Velocidad = +{vel:.2f}% — Positivo"
    elif vel <= -3.0:
        down += 2.5
        det["VEL"] = f"💥 Velocidad = {vel:.2f}% — CAÍDA RÁPIDA"
    elif vel <= -1.5:
        down += 2.0
        det["VEL"] = f"▼▼ Velocidad = {vel:.2f}% — Bajando fuerte"
    elif vel <= -0.5:
        down += 1.2
        det["VEL"] = f"▼ Velocidad = {vel:.2f}% — Bajando"
    else:
        det["VEL"] = f"→ Velocidad = {vel:.2f}% — Sin movimiento claro"

    # ────────────────────────────────────────────────────────
    # FACTOR 3: ACELERACIÓN — ¿la velocidad está aumentando? (PESO 20%)
    # Si vel vela actual > vel vela anterior = acelerando = señal temprana
    # ────────────────────────────────────────────────────────
    vel_a  = g(a,"vel",0)
    vel_p  = g(p,"vel",0)
    vel_b  = g(b,"vel",0)
    acel   = vel_a - vel_p         # aceleración actual
    acel_p = vel_p - vel_b         # aceleración anterior

    if vel_a > 0 and vel_p > 0 and vel_a > vel_p:
        up += 2.0
        det["ACEL"] = f"⚡ ACELERANDO: {vel_p:+.2f}% → {vel_a:+.2f}% — SEÑAL TEMPRANA"
    elif vel_a > 0 and vel_a > vel_p:
        up += 1.0
        det["ACEL"] = f"▲ Velocidad aumentando: {vel_p:+.2f}% → {vel_a:+.2f}%"
    elif vel_a < 0 and vel_p < 0 and vel_a < vel_p:
        down += 2.0
        det["ACEL"] = f"⚡ ACELERANDO CAÍDA: {vel_p:+.2f}% → {vel_a:+.2f}%"
    elif vel_a < 0 and vel_a < vel_p:
        down += 1.0
        det["ACEL"] = f"▼ Caída acelerando: {vel_p:+.2f}% → {vel_a:+.2f}%"
    else:
        det["ACEL"] = f"→ Sin aceleración clara"

    # ────────────────────────────────────────────────────────
    # FACTOR 4: DIRECCIÓN TÉCNICA — VWAP y EMA (PESO 15%)
    # ────────────────────────────────────────────────────────
    vwap = g(a,"vwap",precio)
    e9   = g(a,"ema9",precio)
    e20  = g(a,"ema20",precio)

    tec_up = 0
    if precio > vwap:   tec_up += 1
    if e9 > e20:        tec_up += 1

    if tec_up == 2:
        up += 1.5
        det["TEC"] = "▲▲ Precio sobre VWAP y EMA9>EMA20 — alcista"
    elif tec_up == 1:
        up += 0.7
        det["TEC"] = "▲ Técnico parcialmente alcista"
    else:
        down += 1.0
        det["TEC"] = "▼ Bajo VWAP y EMA9<EMA20 — bajista"

    # ────────────────────────────────────────────────────────
    # FACTOR 5: CONFIRMACIÓN — RSI + patrón de 2-3 velas (PESO 10%)
    # ────────────────────────────────────────────────────────
    rsi  = g(a,"rsi",50)
    c1   = g(df.iloc[-1],"C",precio)
    o1   = g(df.iloc[-1],"O",c1)
    c2   = g(df.iloc[-2],"C",c1) if len(df)>1 else c1
    o2   = g(df.iloc[-2],"O",c2) if len(df)>1 else c2
    c3   = g(df.iloc[-3],"C",c2) if len(df)>2 else c2
    o3   = g(df.iloc[-3],"O",c3) if len(df)>2 else c3

    tres_alcistas = (c1>o1) and (c2>o2) and (c3>o3) and (c1>c2) and (c2>c3)
    dos_alcistas  = (c1>o1) and (c2>o2) and (c1>c2)
    tres_bajistas = (c1<o1) and (c2<o2) and (c3<o3) and (c1<c2) and (c2<c3)
    dos_bajistas  = (c1<o1) and (c2<o2) and (c1<c2)

    if tres_alcistas:
        up += 1.0
        det["VELAS"] = "🟢🟢🟢 3 velas verdes — confirmación"
    elif dos_alcistas:
        up += 0.5
        det["VELAS"] = "🟢🟢 2 velas verdes — iniciando"
    elif tres_bajistas:
        down += 1.0
        det["VELAS"] = "🔴🔴🔴 3 velas rojas — caída confirmada"
    elif dos_bajistas:
        down += 0.5
        det["VELAS"] = "🔴🔴 2 velas rojas — presión bajista"
    else:
        det["VELAS"] = "→ Sin patrón de velas definido"

    if   55 < rsi < 80:   up   += 0.5; det["RSI"] = f"▲ RSI {rsi:.0f}"
    elif rsi >= 80:        up   -= 0.3; det["RSI"] = f"⚠️ RSI sobrecompra {rsi:.0f}"
    elif 20 < rsi < 45:   down += 0.5; det["RSI"] = f"▼ RSI {rsi:.0f}"
    elif rsi <= 20:        down -= 0.3; det["RSI"] = f"⚠️ RSI sobreventa {rsi:.0f}"
    else:                  det["RSI"] = f"→ RSI neutro {rsi:.0f}"

    # ────────────────────────────────────────────────────────
    # NORMALIZAR 1-10
    # ────────────────────────────────────────────────────────
    max_pts = 3.0 + 2.5 + 2.0 + 1.5 + 1.5   # suma máxima teórica
    s_up   = max(1, min(10, round(max(up,   0) / max_pts * 10)))
    s_down = max(1, min(10, round(max(down, 0) / max_pts * 10)))

    # Señal
    if   s_up >= 9:   senal = "🚀 DESPEGUE — COMPRA AHORA"
    elif s_up >= 7:   senal = "⚡ EXPLOSIÓN ALCISTA"
    elif s_up >= 5:   senal = "📈 IMPULSO ALCISTA"
    elif s_down >= 9: senal = "💥 CAÍDA RÁPIDA"
    elif s_down >= 7: senal = "📉 PRESIÓN BAJISTA"
    elif s_down >= 5: senal = "▼ BAJISTA"
    else:             senal = "⚪ NEUTRO / ESPERA"

    return s_up, s_down, senal, det, rvol


# ══════════════════════════════════════════════════════════
#  SL / TP DINÁMICO
# ══════════════════════════════════════════════════════════
def calc_sl_tp(df, precio, senal, mult_sl=2.0, mult_tp=4.0):
    try:
        a   = df.iloc[-1]
        atr = float(a["atr"]) if not np.isnan(a["atr"]) else precio*0.01
        sup = float(a["sup"]) if not np.isnan(a["sup"]) else precio*0.97
        res = float(a["res"]) if not np.isnan(a["res"]) else precio*1.03
        if sup <= 0 or sup >= precio: sup = precio * 0.97
        if res <= 0 or res <= precio: res = precio * 1.03
        alcista = any(x in senal for x in ["DESPEGUE","COMPRA","ALCISTA","IMPULSO","EXPLOS"])
        if alcista:
            sl = round(max(precio - atr*mult_sl, sup*0.998), 4)
            tp = round(min(precio + atr*mult_tp, res*0.999), 4)
        else:
            sl = round(min(precio + atr*mult_sl, res*1.002), 4)
            tp = round(max(precio - atr*mult_tp, sup*1.001), 4)
        if sl <= 0: sl = round(precio*0.97, 4)
        if tp <= 0: tp = round(precio*1.06, 4)
        rr = round(abs(tp-precio)/max(abs(precio-sl),1e-6), 2)
        return sl, tp, rr
    except Exception:
        return round(precio*0.97,4), round(precio*1.06,4), 2.0


# ══════════════════════════════════════════════════════════
#  ESCANEO DE ACELERACIÓN — MOTOR PRINCIPAL
# ══════════════════════════════════════════════════════════
def escanear_aceleracion(tickers: list, precio_min: float, precio_max: float,
                          rvol_min: float, vel_min: float,
                          mult_sl: float, mult_tp: float,
                          session: str, top_n: int = 50) -> pd.DataFrame:
    """
    Descarga datos de 1 minuto y aplica el Motor de Aceleración.
    Filtra por RVOL mínimo y velocidad de precio mínima.
    """
    if not tickers:
        return pd.DataFrame()

    resultados = []
    pb         = st.progress(0.0, text="⚡ Motor de Aceleración iniciando...")
    total      = len(tickers)
    lote       = 50
    dfs_raw    = {}

    # Intervalo y prepost según sesión
    interval = "1m"
    period   = "1d"
    prepost  = True  # SIEMPRE True para pre/after-hours

    # ── Fase 1: Descarga en lotes ─────────────────────────
    for i in range(0, total, lote):
        chunk = tickers[i:i+lote]
        pct   = min((i+lote)/total*0.45, 0.45)
        pb.progress(pct, text=f"📡 Descargando {min(i+lote,total)}/{total}...")

        try:
            raw = yf.download(
                chunk,
                period=period,
                interval=interval,
                group_by="ticker",
                prepost=prepost,
                progress=False,
                auto_adjust=True,
                threads=True,
                timeout=25,
            )
            for t in chunk:
                dfs_raw[t] = extraer_df(raw, t, len(chunk))
        except Exception:
            # Reintento individual
            for t in chunk:
                try:
                    s = yf.download(t, period=period, interval=interval,
                                    prepost=prepost, progress=False,
                                    auto_adjust=True, threads=False, timeout=15)
                    dfs_raw[t] = extraer_df(s, t, 1)
                except Exception:
                    dfs_raw[t] = None

    # ── Fase 2: Análisis ─────────────────────────────────
    for idx, t in enumerate(tickers):
        pct2 = 0.45 + (idx+1)/total*0.55
        pb.progress(pct2, text=f"🔬 Analizando aceleración: {t} ({idx+1}/{total})")

        try:
            raw_df = dfs_raw.get(t)
            if raw_df is None or len(raw_df) < 5:
                continue

            df = calcular_indicadores(raw_df)
            if df is None or len(df) < 3:
                continue

            precio = float(df["C"].iloc[-1])
            if not (precio_min <= precio <= precio_max):
                continue

            # Cambio del día (informativo, no filtro)
            open_d    = float(df["O"].iloc[0]) if float(df["O"].iloc[0]) > 0 else precio
            cambio_d  = (precio - open_d) / max(open_d,1e-9) * 100

            # Velocidad última vela
            vel_ult   = float(df["vel"].iloc[-1]) if not np.isnan(df["vel"].iloc[-1]) else 0
            rvol_ult  = float(df["rvol"].iloc[-1]) if not np.isnan(df["rvol"].iloc[-1]) else 0

            # ── FILTROS DE ACELERACIÓN ──────────────────────
            # 1. RVOL debe superar el mínimo configurado
            if rvol_ult < rvol_min:
                continue
            # 2. Debe haber movimiento de precio en la última vela
            if abs(vel_ult) < vel_min:
                continue

            s_up, s_down, senal, det, rvol = motor_aceleracion(df, session)
            _sl, _tp, rr = calc_sl_tp(df, precio, senal, mult_sl, mult_tp)

            vavg10 = float(df["vavg10"].iloc[-1])
            rsi    = float(df["rsi"].iloc[-1])
            sup    = float(df["sup"].iloc[-1])
            res    = float(df["res"].iloc[-1])
            vel2   = float(df["vel2"].iloc[-1]) if not np.isnan(df["vel2"].iloc[-1]) else 0
            acel   = float(df["acel"].iloc[-1]) if not np.isnan(df["acel"].iloc[-1]) else 0

            resultados.append({
                "Ticker"   : t,
                "Precio $" : round(precio, 4),
                "RVOL"     : round(rvol_ult, 1),
                "Vel 1v %": round(vel_ult, 2),   # % movimiento última vela (=1 minuto)
                "Vel 2v %": round(vel2, 2),       # % últimas 2 velas (=2 minutos)
                "Acel"     : round(acel, 3),      # aceleración (+ = aumentando)
                "Δ Día %"  : round(cambio_d, 2),
                "Score 🐂" : s_up,
                "Score 🐻" : s_down,
                "Señal"    : senal,
                "RSI"      : round(rsi, 1),
                "Soporte $": round(sup, 4),
                "Resist $" : round(res, 4),
                "SL $"     : _sl,
                "TP $"     : _tp,
                "R:R"      : rr,
                "_det"     : det,
                "_df"      : df,
            })
        except Exception:
            continue

    pb.empty()

    if not resultados:
        return pd.DataFrame()

    df_res = pd.DataFrame(resultados)
    # Ordenar por: Score alcista primero, luego RVOL, luego velocidad
    df_res = df_res.sort_values(
        by=["Score 🐂","RVOL","Vel 1v %"],
        ascending=[False, False, False]
    ).reset_index(drop=True)
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

def cerrar_pos(sym):
    try:    alpaca.close_position(sym); return True, f"✅ Cerrada {sym}"
    except Exception as e: return False, str(e)

def orden_buy(sym, qty, sl, tp):
    try:
        alpaca.submit_order(MarketOrderRequest(
            symbol=sym, qty=qty, side=OrderSide.BUY, time_in_force=TimeInForce.GTC,
            take_profit=TakeProfitRequest(limit_price=round(float(tp),2)),
            stop_loss=StopLossRequest(stop_price=round(float(sl),2))
        ))
        return True, f"✅ BUY {qty}x {sym} | SL ${sl:.4f} | TP ${tp:.4f}"
    except Exception as e: return False, f"❌ {e}"

def orden_sell(sym, qty):
    try:
        alpaca.submit_order(MarketOrderRequest(
            symbol=sym, qty=qty, side=OrderSide.SELL, time_in_force=TimeInForce.GTC
        ))
        return True, f"✅ SELL {qty}x {sym}"
    except Exception as e: return False, f"❌ {e}"


# ══════════════════════════════════════════════════════════
#  ENCABEZADO
# ══════════════════════════════════════════════════════════
st.markdown('<h1 class="hdr">⚡ THUNDER RADAR V92</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub">MOTOR DE ACELERACIÓN · RVOL + VELOCIDAD · DESPEGUE EN 1 MINUTO · ALPACA PAPER</p>',
            unsafe_allow_html=True)

badge_map = {"REGULAR":"b-reg","PRE-MARKET":"b-pre","AFTER-HOURS":"b-aft","CERRADO":"b-cls"}
tz_et    = pytz.timezone("US/Eastern")
hora_et  = datetime.now(tz_et).strftime("%H:%M:%S ET")
cuenta   = get_cuenta()

hc1,hc2,hc3 = st.columns(3)
with hc1:
    st.markdown(
        f'<span class="badge {badge_map.get(SESSION,"b-cls")}">● {SESSION}</span>'
        f' &nbsp;<span class="dot"></span><span style="color:#8b949e;font-size:.76em">EN VIVO</span>',
        unsafe_allow_html=True)
with hc2:
    st.markdown(f'<span style="color:#8b949e">🕐 {hora_et}</span>', unsafe_allow_html=True)
with hc3:
    if cuenta:
        eq  = float(cuenta.equity)
        pnl = eq - float(cuenta.last_equity)
        col = "#00ff88" if pnl>=0 else "#ff4444"
        st.markdown(f'<span style="color:{col}">💰 ${eq:,.2f} | P&L {pnl:+,.2f}</span>',
                    unsafe_allow_html=True)

st.markdown('<hr class="n">', unsafe_allow_html=True)

# Explicación del motor
st.markdown("""
<div class="info-box">
<b style="color:#00ff88">⚡ MOTOR DE ACELERACIÓN — Cómo funciona:</b><br>
<span style="color:#c9d1d9">
• <b style="color:#ff4500">RVOL</b> (Relative Volume): vol. última vela ÷ promedio últimas 10 velas.
  Si RVOL ≥ 3x = algo está pasando <b>AHORA MISMO</b>.<br>
• <b style="color:#00d4ff">Vel 1v %</b>: % que se movió el precio en la ÚLTIMA vela de 1 minuto.
  Esto mide <b>velocidad</b>, no el cambio total del día.<br>
• <b style="color:#ffc107">Acel</b>: ¿la velocidad está <b>aumentando</b>?
  Si vel actual > vel anterior = acelerando = señal temprana de despegue.<br>
• <b>Universo dinámico</b>: obtiene TODOS los stocks de NYSE/NASDAQ/AMEX via Twelve Data (gratis).
  Solo acciones reales (no ETF, no cripto, no forex).
</span>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  BARRA LATERAL
# ══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ CONFIGURACIÓN")

    # ── Universo dinámico ─────────────────────────────────
    st.markdown("**📊 Universo de Acciones**")
    usar_dinamico = st.toggle("🌐 Obtener lista completa NYSE/NASDAQ", value=True,
                              help="Usa Twelve Data para obtener TODOS los stocks. Si falla, usa lista de respaldo.")

    modo = st.selectbox("Modo de Escaneo", [
        "🔥 Todo el mercado (dinámico)",
        "💎 Penny + Small Caps",
        "📈 Large Cap",
        "🎯 Mis tickers (manual)",
    ])

    st.markdown("---")
    precio_min_f = st.number_input("Precio Mín $", value=0.05, step=0.05, min_value=0.01)
    precio_max_f = st.number_input("Precio Máx $", value=500.0, step=10.0)

    st.markdown("---")
    st.markdown("**⚡ Filtros Motor de Aceleración**")
    rvol_min = st.slider(
        "RVOL mínimo (volumen relativo)",
        min_value=1.0, max_value=20.0, value=2.0, step=0.5,
        help="RVOL = vol. última vela ÷ promedio 10 velas. 2x = doble del promedio."
    )
    vel_min = st.slider(
        "Velocidad mínima última vela (%)",
        min_value=0.0, max_value=5.0, value=0.10, step=0.05,
        help="% mínimo que debe moverse el precio en la última vela de 1 minuto."
    )

    st.markdown("---")
    pre_filtro_n = st.slider(
        "Candidatos del pre-filtro",
        min_value=50, max_value=500, value=200, step=50,
        help="De todos los stocks, el pre-filtro selecciona los N más activos hoy para analizar en detalle."
    )
    top_n_f = st.slider("Top resultados finales", 10, 80, 40, 5)

    st.markdown("---")
    atr_sl = st.slider("ATR × Stop Loss",   0.5, 5.0, 2.0, 0.5)
    atr_tp = st.slider("ATR × Take Profit", 1.0, 8.0, 4.0, 0.5)

    st.markdown("---")
    if modo == "🎯 Mis tickers (manual)":
        txt = st.text_area("Tickers (coma)", "AAPL,TSLA,NVDA,GME,COIN,MARA,SOFI,NIO,BRIA", height=80)
        lista_manual = [t.strip().upper() for t in txt.split(",") if t.strip()]
    else:
        lista_manual = []

    st.markdown("---")
    modo_auto = st.toggle("🤖 Auto-Trade", value=False)
    if modo_auto:
        auto_score = st.slider("Score mínimo auto-compra", 7, 10, 8)
        auto_qty   = st.number_input("Acciones / orden", value=1, min_value=1)
        max_pos    = st.number_input("Máx posiciones", value=3, min_value=1)
        st.warning("⚠️ Ejecuta órdenes reales en Paper.")

    st.markdown("---")
    auto_refresh = st.toggle("🔁 Auto-escaneo continuo", value=False)
    refresh_seg  = 60

# ══════════════════════════════════════════════════════════
#  OBTENER UNIVERSO Y HACER PRE-FILTRO
# ══════════════════════════════════════════════════════════
if "universo_cargado" not in st.session_state:
    st.session_state.universo_cargado = []
    st.session_state.universo_status  = "❌ No cargado"

# Cargar universo si se pide
col_u1, col_u2 = st.columns([3,1])
with col_u1:
    cargar_universo = st.button("🌐 CARGAR UNIVERSO COMPLETO (NYSE + NASDAQ + AMEX)", use_container_width=True)
with col_u2:
    n_u = len(st.session_state.universo_cargado)
    color_u = "#00ff88" if n_u > 0 else "#ff4444"
    st.markdown(f'<span style="color:{color_u}">📊 {n_u} stocks cargados</span>', unsafe_allow_html=True)

if cargar_universo or (usar_dinamico and len(st.session_state.universo_cargado) == 0):
    with st.spinner("🌐 Descargando lista completa de NYSE + NASDAQ + AMEX..."):
        universo_raw = obtener_universo_dinamico()
        # Filtrar símbolos válidos (solo acciones)
        universo_limpio = [s for s in universo_raw if es_accion_valida(s)]
        st.session_state.universo_cargado = universo_limpio
        n_total = len(universo_limpio)
        if n_total > 100:
            st.success(f"✅ {n_total:,} acciones cargadas (NYSE + NASDAQ + AMEX). Solo Common Stocks.")
            st.session_state.universo_status = f"✅ {n_total:,} acciones"
        else:
            st.warning(f"⚠️ Solo se cargaron {n_total} tickers. Usando lista de respaldo ampliada.")
            st.session_state.universo_status = f"⚠️ {n_total} (respaldo)"

# Determinar lista a escanear según modo
universo_completo = st.session_state.universo_cargado or _universo_respaldo()

if modo == "🎯 Mis tickers (manual)":
    lista_scan = lista_manual
elif modo == "💎 Penny + Small Caps":
    # Filtrar por precio bajo del universo completo (proxy para penny/small)
    lista_scan = universo_completo  # el filtro de precio $0.05-$10 lo hace el motor
elif modo == "📈 Large Cap":
    # Usar solo los tickers conocidos de large cap
    LARGE_KNOWN = [
        "AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","NFLX","AMD","INTC",
        "AVGO","QCOM","MU","JPM","BAC","GS","MS","WFC","V","PYPL",
        "UNH","PFE","ABBV","MRK","LLY","BMY","BA","LMT","CAT","DE",
        "WMT","TGT","HD","NKE","MCD","SBUX","DIS","CMCSA","AMGN","ISRG"
    ]
    lista_scan = LARGE_KNOWN
else:
    lista_scan = universo_completo

st.markdown('<hr class="n">', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  PORTAFOLIO ACTIVO
# ══════════════════════════════════════════════════════════
st.subheader("💼 Portafolio Activo")
posiciones = get_posiciones()
if posiciones:
    rows = []
    for p in posiciones:
        pnl_p = float(p.unrealized_plpc) * 100
        pnl_u = float(p.unrealized_pl)
        ico   = "🟢" if pnl_p >= 0 else "🔴"
        rows.append({"Ticker":p.symbol,"Qty":p.qty,
                     "Entrada $":round(float(p.avg_entry_price),4),
                     "Actual $": round(float(p.current_price),4),
                     "P&L %":    f"{ico} {pnl_p:+.2f}%",
                     "P&L $":    f"${pnl_u:+.2f}",
                     "Valor $":  f"${float(p.market_value):,.2f}"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    px1,px2,px3 = st.columns([2,1,1])
    with px1: t_close = st.selectbox("Ticker a cerrar", [r["Ticker"] for r in rows])
    with px2:
        if st.button("🔴 Cerrar posición"):
            ok,msg = cerrar_pos(t_close)
            st.success(msg) if ok else st.error(msg)
    with px3:
        if st.button("🔴 Cerrar TODO"):
            [cerrar_pos(p.symbol) for p in posiciones]
            st.warning("Cerrando todo...")
else:
    st.info("Sin posiciones abiertas. ¡Detecta despegues con el radar! 🚀")

st.markdown('<hr class="n">', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  MOTOR DE ESCANEO
# ══════════════════════════════════════════════════════════
st.subheader("🔭 Motor de Aceleración — Detecta el Despegue en el Primer Minuto")

# Estado
if "df_scan"   not in st.session_state: st.session_state.df_scan   = pd.DataFrame()
if "last_scan" not in st.session_state: st.session_state.last_scan = None
if "prefiltro" not in st.session_state: st.session_state.prefiltro = []

sb1, sb2, sb3 = st.columns([2,1,1])
with sb1: iniciar = st.button("🚀 INICIAR ESCANEO — DETECTAR DESPEGUES", use_container_width=True)
with sb2: hacer_prefiltro = st.button("🔬 PRE-FILTRO RÁPIDO", use_container_width=True,
                                       help="Reduce el universo a los stocks más activos AHORA")
with sb3:
    if st.button("🔄 Refresh UI", use_container_width=True): st.rerun()

# Pre-filtro rápido
if hacer_prefiltro and lista_scan:
    st.markdown(f"**Pre-filtrando {len(lista_scan):,} stocks → seleccionando top {pre_filtro_n} más activos...**")
    candidatos = prefiltro_activos(lista_scan, precio_min_f, precio_max_f, pre_filtro_n)
    st.session_state.prefiltro = candidatos
    st.success(f"✅ Pre-filtro completado: {len(candidatos)} candidatos seleccionados para escaneo detallado.")

# Determinar qué lista usar para el escaneo detallado
if st.session_state.prefiltro:
    lista_escaneo = st.session_state.prefiltro
    st.info(f"📊 Usando pre-filtro: **{len(lista_escaneo)} candidatos** (de {len(lista_scan):,} totales)")
else:
    # Si no hay pre-filtro, limitar el universo para no tardar demasiado
    lista_escaneo = lista_scan[:300] if len(lista_scan) > 300 else lista_scan
    if len(lista_scan) > 300:
        st.warning(f"⚠️ Universo grande ({len(lista_scan):,} stocks). Usando primeros 300. "
                   "Usa **🔬 PRE-FILTRO RÁPIDO** para mejores resultados.")

# Disparar escaneo
debe = iniciar or (
    auto_refresh
    and st.session_state.last_scan is not None
    and (time.time() - st.session_state.last_scan) >= refresh_seg
)

if debe:
    if not lista_escaneo:
        st.error("❌ No hay tickers para escanear. Carga el universo primero.")
    else:
        info_msg = (
            f"⚡ Escaneando **{len(lista_escaneo)} stocks** | "
            f"Sesión: **{SESSION}** | "
            f"RVOL mínimo: **{rvol_min}x** | "
            f"Vel. mínima: **{vel_min}%/vela**"
        )
        st.markdown(info_msg)

        with st.spinner("⚡ Motor de Aceleración corriendo..."):
            df_scan = escanear_aceleracion(
                lista_escaneo,
                precio_min_f, precio_max_f,
                rvol_min, vel_min,
                atr_sl, atr_tp,
                SESSION, top_n_f
            )
        st.session_state.df_scan   = df_scan
        st.session_state.last_scan = time.time()
        ts = datetime.now(tz_et).strftime("%H:%M:%S ET")
        n  = len(df_scan)
        if n > 0:
            st.success(f"✅ {ts} — **{n} despegues detectados**")
        else:
            st.warning(f"⚠️ {ts} — Sin señales. Baja el RVOL mínimo o la velocidad mínima.")

df_scan = st.session_state.df_scan

# ══════════════════════════════════════════════════════════
#  MOSTRAR RESULTADOS
# ══════════════════════════════════════════════════════════
if not df_scan.empty:

    despegues = df_scan[df_scan["Score 🐂"] >= 7]
    vigilar   = df_scan[(df_scan["Score 🐂"] >= 5) & (df_scan["Score 🐂"] < 7)]
    resto     = df_scan[df_scan["Score 🐂"] < 5]

    # ── DESPEGUES (score ≥ 7) ────────────────────────────
    if not despegues.empty:
        st.markdown(f"### 🚀 DESPEGUES DETECTADOS — {len(despegues)} señales")

        for _, row in despegues.iterrows():
            s   = int(row["Score 🐂"])
            cls = "sc10" if s==10 else ("sc8" if s>=8 else "sc6")
            dc  = "#00ff88" if row["Vel 1v %"]>=0 else "#ff4444"
            dd  = "#00ff88" if row["Δ Día %"]>=0  else "#ff4444"
            rv  = float(row["RVOL"])
            rcl = "rvol-fire" if rv>=10 else ("rvol-hi" if rv>=5 else "rvol-ok")
            ac  = float(row["Acel"])
            acel_txt = f"▲ {ac:+.3f}" if ac > 0 else f"▼ {ac:+.3f}"
            acel_col = "#00ff88" if ac > 0 else "#ff4444"

            st.markdown(f"""
            <div class="card-launch">
              <span class="tkr">⚡ {row['Ticker']}</span>
              &nbsp;&nbsp;<span class="{cls}">{s}/10</span>
              &nbsp;&nbsp;<span style="color:#a78bfa;font-size:.88em">{row['Señal']}</span>
              <br>
              <span class="lbl">Precio</span> <b style="color:#fff">${row['Precio $']}</b>
              &nbsp;|&nbsp;
              <span class="lbl">RVOL</span> <span class="{rcl}">{rv:.1f}x</span>
              &nbsp;|&nbsp;
              <span class="lbl">Vel 1min</span> <b style="color:{dc}">{row['Vel 1v %']:+.2f}%</b>
              &nbsp;|&nbsp;
              <span class="lbl">Vel 2min</span> <b style="color:{dc}">{row['Vel 2v %']:+.2f}%</b>
              &nbsp;|&nbsp;
              <span class="lbl">Acel</span> <b style="color:{acel_col}">{acel_txt}</b>
              &nbsp;|&nbsp;
              <span class="lbl">RSI</span> {row['RSI']}
              &nbsp;|&nbsp;
              <span class="lbl">Δ Día</span> <span style="color:{dd}">{row['Δ Día %']:+.2f}%</span>
              <br>
              <span class="lbl">SL</span> <span style="color:#ff6b6b">${row['SL $']}</span>
              &nbsp;|&nbsp;
              <span class="lbl">TP</span> <span style="color:#00ff88">${row['TP $']}</span>
              &nbsp;|&nbsp;
              <span class="lbl">R:R</span> {row['R:R']}x
            </div>
            """, unsafe_allow_html=True)

    # ── EN VIGILANCIA (score 5-6) ────────────────────────
    if not vigilar.empty:
        with st.expander(f"👁️ EN VIGILANCIA — {len(vigilar)} señales (score 5-6)"):
            for _, row in vigilar.iterrows():
                rv  = float(row["RVOL"])
                dc  = "#00ff88" if row["Vel 1v %"]>=0 else "#ff4444"
                st.markdown(f"""
                <div class="card-watch">
                  <span class="tkr" style="font-size:1.1em">{row['Ticker']}</span>
                  &nbsp;<span class="sc6">{int(row['Score 🐂'])}/10</span>
                  &nbsp;<span style="color:#8b949e;font-size:.83em">{row['Señal']}</span>
                  &nbsp;|&nbsp;
                  <span class="lbl">Precio</span> ${row['Precio $']}
                  &nbsp;|&nbsp;
                  <span class="lbl">RVOL</span> <b>{rv:.1f}x</b>
                  &nbsp;|&nbsp;
                  <span class="lbl">Vel 1min</span> <span style="color:{dc}">{row['Vel 1v %']:+.2f}%</span>
                  &nbsp;|&nbsp;
                  <span class="lbl">RSI</span> {row['RSI']}
                </div>
                """, unsafe_allow_html=True)

    # ── TABLA COMPLETA ───────────────────────────────────
    st.markdown("### 📋 Tabla Completa del Radar")

    cols_vis = ["Ticker","Precio $","RVOL","Vel 1v %","Vel 2v %","Acel",
                "Δ Día %","Score 🐂","Score 🐻","Señal","RSI",
                "Soporte $","Resist $","SL $","TP $","R:R"]
    df_show  = df_scan[cols_vis].copy()

    def c_score(v):
        if v>=8:   return "background-color:#15803d;color:white"
        elif v>=6: return "background-color:#1d4ed8;color:white"
        elif v>=4: return "background-color:#92400e;color:white"
        else:      return "background-color:#7f1d1d;color:white"

    def c_vel(v):
        return f"color:{'#00ff88' if v>=0 else '#ff4444'};font-weight:bold"

    def c_rvol(v):
        if v>=10:  return "color:#ff4500;font-weight:900"
        elif v>=5: return "color:#ff8c00;font-weight:700"
        elif v>=3: return "color:#ffc107;font-weight:bold"
        else:      return "color:#8b949e"

    fmt = {
        "Precio $":"${:.4f}","RVOL":"{:.1f}x","Vel 1v %":"{:+.2f}%",
        "Vel 2v %":"{:+.2f}%","Acel":"{:+.3f}","Δ Día %":"{:+.2f}%",
        "RSI":"{:.1f}","Soporte $":"${:.4f}","Resist $":"${:.4f}",
        "SL $":"${:.4f}","TP $":"${:.4f}","R:R":"{:.2f}"
    }

    try:
        styled = (df_show.style
                  .map(c_score, subset=["Score 🐂","Score 🐻"])
                  .map(c_vel,   subset=["Vel 1v %","Vel 2v %","Δ Día %"])
                  .map(c_rvol,  subset=["RVOL"])
                  .format(fmt))
    except Exception:
        try:
            styled = (df_show.style
                      .applymap(c_score, subset=["Score 🐂","Score 🐻"])
                      .applymap(c_vel,   subset=["Vel 1v %","Vel 2v %","Δ Día %"])
                      .applymap(c_rvol,  subset=["RVOL"])
                      .format(fmt))
        except Exception:
            styled = df_show.style.format(fmt)

    st.dataframe(styled, use_container_width=True, hide_index=True, height=420)

    # ── AUTO-TRADE ───────────────────────────────────────
    if modo_auto:
        st.markdown("### 🤖 Auto-Trade")
        n_pos  = len(get_posiciones())
        cands  = df_scan[df_scan["Score 🐂"] >= auto_score]
        if cands.empty:
            st.info(f"Sin candidatos con score ≥ {auto_score}")
        for _, row in cands.iterrows():
            if n_pos >= max_pos:
                st.warning(f"Máx {max_pos} posiciones."); break
            ok, msg = orden_buy(row["Ticker"], auto_qty, row["SL $"], row["TP $"])
            if ok: n_pos += 1
            st.write(msg)

    # ── EJECUCIÓN MANUAL ─────────────────────────────────
    st.markdown('<hr class="n">', unsafe_allow_html=True)
    st.markdown("### 🛒 Ejecución Manual")
    ce1,ce2 = st.columns([1,2])
    with ce1:
        t_op  = st.selectbox("Ticker a operar", df_scan["Ticker"].tolist())
        rsel  = df_scan[df_scan["Ticker"]==t_op].iloc[0]
        qty_m = st.number_input("Cantidad", value=1, min_value=1, step=1)
        sl_m  = st.number_input("SL $", value=float(rsel["SL $"]), step=0.001, format="%.4f")
        tp_m  = st.number_input("TP $", value=float(rsel["TP $"]), step=0.001, format="%.4f")
        b1,b2 = st.columns(2)
        with b1:
            if st.button("🟢 COMPRAR", use_container_width=True):
                ok,msg = orden_buy(t_op, qty_m, sl_m, tp_m)
                st.success(msg) if ok else st.error(msg)
        with b2:
            if st.button("🔴 VENDER", use_container_width=True):
                ok,msg = orden_sell(t_op, qty_m)
                st.success(msg) if ok else st.error(msg)

    with ce2:
        st.markdown(f"### 📊 {t_op} — Análisis de Aceleración")
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Precio $",   f"${rsel['Precio $']:.4f}")
        m2.metric("RVOL",       f"{rsel['RVOL']:.1f}x")
        m3.metric("Vel 1min",   f"{rsel['Vel 1v %']:+.2f}%")
        m4.metric("Score 🐂",   f"{rsel['Score 🐂']}/10")
        m5,m6,m7,m8 = st.columns(4)
        m5.metric("RSI",        f"{rsel['RSI']}")
        m6.metric("SL $",       f"${rsel['SL $']:.4f}")
        m7.metric("TP $",       f"${rsel['TP $']:.4f}")
        m8.metric("R:R",        f"{rsel['R:R']}x")

        det = rsel.get("_det", {})
        if det:
            st.markdown("**📌 Detalle del motor:**")
            for k, v in det.items():
                c = "#00ff88" if "▲" in v or "🚀" in v or "⚡" in v or "🔥" in v else (
                    "#ff4444" if "▼" in v or "💥" in v else "#ffc107")
                st.markdown(
                    f'<span style="color:{c};font-size:.81em"><b>{k}</b>: {v}</span>',
                    unsafe_allow_html=True)

elif st.session_state.last_scan is not None:
    st.warning("""
    ⚠️ **Sin señales de aceleración detectadas.** Prueba:
    - Bajar **RVOL mínimo** a 1.5x o menos
    - Bajar **Velocidad mínima** a 0.05%
    - Usar **🔬 PRE-FILTRO RÁPIDO** primero
    - Verificar que el mercado esté activo (regular, pre o after-hours)
    - En horas de mercado cerrado, hay menos movimiento
    """)
else:
    st.info("**Flujo recomendado:**\n"
            "1️⃣ Pulsa **🌐 CARGAR UNIVERSO** para obtener todos los stocks\n"
            "2️⃣ Pulsa **🔬 PRE-FILTRO RÁPIDO** para encontrar los más activos hoy\n"
            "3️⃣ Pulsa **🚀 INICIAR ESCANEO** para detectar despegues")

# ══════════════════════════════════════════════════════════
#  AUTO-REFRESH
# ══════════════════════════════════════════════════════════
if auto_refresh:
    time.sleep(refresh_seg)
    st.rerun()

# ══════════════════════════════════════════════════════════
#  PIE
# ══════════════════════════════════════════════════════════
st.markdown('<hr class="n">', unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#8b949e;font-size:.70em;font-family:'Share Tech Mono',monospace">
⚡ THUNDER RADAR V92 ULTRA — PAPER TRADING — Solo uso educativo y experimental<br>
Los resultados pasados no garantizan rendimientos futuros. El trading conlleva riesgo de pérdida.
</div>""", unsafe_allow_html=True)
