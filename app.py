"""
╔══════════════════════════════════════════════════════════════════╗
║        THUNDER RADAR V93 — MOTOR MULTI-SESIÓN                   ║
║                                                                  ║
║  SESIONES:                                                       ║
║  ● PRE-MARKET   04:00-09:29 ET  → filtros ultra sensibles        ║
║  ● REGULAR      09:30-15:59 ET  → filtros normales               ║
║  ● AFTER-HOURS  16:00-19:59 ET  → filtros sensibles              ║
║                                                                  ║
║  MOTOR DE SEÑAL:                                                 ║
║  ✅ RVOL calculado DENTRO de cada sesión                         ║
║  ✅ Supertrend (confirma dirección)                              ║
║  ✅ Aceleración de precio (1min, 2min, 3min)                     ║
║  ✅ Pre-filtro por % cambio vs cierre anterior                   ║
║  ✅ Universo dinámico NYSE+NASDAQ+AMEX via Twelve Data           ║
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
from datetime import datetime
import pytz
import time
import warnings
warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════
st.set_page_config(page_title="⚡ THUNDER RADAR V93", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
html,body,[class*="css"]{background:#030810!important;color:#c9d1d9!important;
    font-family:'Share Tech Mono',monospace;}
h1,h2,h3{font-family:'Orbitron',sans-serif!important;}
.stButton>button{width:100%;border-radius:4px;font-weight:bold;
    font-family:'Orbitron',sans-serif;letter-spacing:1px;border:1px solid #30363d;transition:all .2s;}
.stButton>button:hover{transform:translateY(-1px);box-shadow:0 0 16px rgba(0,255,136,.6);}
div[data-testid="metric-container"]{background:linear-gradient(135deg,#0a0f1a,#141b27);
    border:1px solid #1e2739;border-radius:8px;padding:12px;}
.card-fire{background:linear-gradient(135deg,#060f08,#0a0f1a);border:2px solid #00ff88;
    border-radius:10px;padding:13px 17px;margin:5px 0;box-shadow:0 0 20px #00ff8844;}
.card-hot{background:linear-gradient(135deg,#0f0a06,#0a0f1a);border:2px solid #ff8c00;
    border-radius:10px;padding:12px 16px;margin:4px 0;box-shadow:0 0 12px #ff8c0033;}
.card-watch{background:#0a0c10;border:1px solid #ffc10744;border-radius:8px;
    padding:10px 14px;margin:3px 0;}
.sc10{color:#00ff88;font-size:1.8em;font-weight:900;font-family:'Orbitron',sans-serif;}
.sc8 {color:#39ff14;font-size:1.5em;font-weight:800;}
.sc6 {color:#ffc107;font-size:1.3em;font-weight:700;}
.sc4 {color:#ff6b6b;font-size:1.1em;}
.tkr{font-family:'Orbitron',sans-serif;font-size:1.25em;font-weight:900;color:#fff;}
.lbl{color:#8b949e;font-size:.75em;}
.up  {color:#00ff88;font-weight:bold;}
.dn  {color:#ff4444;font-weight:bold;}
.hdr{text-align:center;font-family:'Orbitron',sans-serif;font-size:2.1em;font-weight:900;
    background:linear-gradient(90deg,#00ff88,#00d4ff,#ff4500);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:3px;}
.sub{text-align:center;color:#8b949e;font-size:.78em;letter-spacing:3px;}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:.74em;font-weight:bold;}
.b-reg{background:#15803d;color:#fff;}.b-pre{background:#7c3aed;color:#fff;}
.b-aft{background:#0369a1;color:#fff;}.b-cls{background:#374151;color:#fff;}
.dot{display:inline-block;width:9px;height:9px;background:#00ff88;border-radius:50%;
    margin-right:5px;animation:blink 1s infinite;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.1}}
hr.n{border:none;border-top:1px solid #00ff8822;margin:12px 0;}
.ibox{background:linear-gradient(135deg,#0a0f1a,#111827);border:1px solid #00ff8833;
    border-radius:8px;padding:10px 14px;margin:6px 0;font-size:.79em;}
/* Supertrend indicators */
.st-bull{color:#00ff88;font-weight:bold;}
.st-bear{color:#ff4444;font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  ALPACA
# ══════════════════════════════════════════════════════
ALPACA_API_KEY    = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET_KEY = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca():
    return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
alpaca = get_alpaca()

# ══════════════════════════════════════════════════════
#  SESIÓN DE MERCADO
# ══════════════════════════════════════════════════════
def get_session():
    tz  = pytz.timezone("US/Eastern")
    now = datetime.now(tz)
    h   = now.hour + now.minute / 60.0
    if   4.0  <= h < 9.5:  return "PRE-MARKET"
    elif 9.5  <= h < 16.0: return "REGULAR"
    elif 16.0 <= h < 20.0: return "AFTER-HOURS"
    else:                   return "CERRADO"

SESSION = get_session()

# ══════════════════════════════════════════════════════
#  UNIVERSO DINÁMICO — Twelve Data (gratis, sin API key)
# ══════════════════════════════════════════════════════
RESPALDO = list(dict.fromkeys([
    # ── Large cap
    "AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","NFLX","AMD","INTC",
    "AVGO","QCOM","MU","JPM","BAC","GS","V","PYPL","WFC","C",
    # ── Biotech / Pharma (alta volatilidad en pre-market por FDA)
    "PFE","ABBV","MRK","LLY","BMY","GILD","MRNA","BNTX","NVAX","VRTX",
    "REGN","BIIB","SRPT","ACAD","HIMS","OCGN","FATE","CRSP","EDIT","BEAM",
    "SAGE","ACMR","MNMD","ATAI","BPMC","KRTX","PRAX","ARVN","PCVX","REPL",
    "LGVN","VVOS","SYRA","QNRX","CRTX","SRTX","HALO","IINN","BFRI","ATNF",
    # ── Cripto-proxy (acciones, no cripto)
    "COIN","HOOD","MSTR","RIOT","MARA","HUT","CIFR","BTBT","CLSK","WULF","IREN",
    # ── EV
    "RIVN","LCID","CHPT","BLNK","PLUG","FCEL","BE","GOEV","NKLA","WKHS",
    "NIO","XPEV","LI","FSR","SOLO",
    # ── Meme / alta volatilidad
    "GME","AMC","KOSS","BB","NOK","BBIG","SPCE","MULN","IDEX","CENN",
    "MVIS","PROG","ATER","NAKD","EXPR","KPLT","CELH","SKIN",
    # ── China ADR
    "BABA","JD","PDD","TCOM","GRAB","SE","TIGR","FUTU","BILI","IQ","VIPS",
    "BZUN","GOTU","TUYA","TAL","DOYU","HUYA","YMM","LAIX",
    # ── Space/Drones/Quantum
    "ASTS","LUNR","RKLB","ACHR","JOBY","IONQ","RGTI","QUBT","MNTS","ASTR",
    # ── Fintech small
    "SOFI","UPST","AFRM","ROOT","OPFI","DAVE","GHLD","CURO","ATLC",
    # ── Small/Micro caps muy volátiles (frecuentes en Webull Top Gainers)
    "PBM","YJ","ILLR","SCAG","BLIV","ABTS","DLHC","WSHP","MYSE","ONFO",
    "CTNT","RAIN","CPHI","NCRA","LVLU","HNST","AEHL","RCAT","CRKN","STSS",
    "NXGL","PAVS","BSLK","GPUS","VRPX","GFAI","SGBX","INPX","TCRT","RSSS",
    "ISPC","UCAR","ABLV","YXT","ZBAI","MTEX","MGRT","BRIA","EDTK","TGHL",
    "ZSPC","OCGN","CLOV","SNDL","TLRY","AGEN","ADXS","ALVR","AMPIO","APDN",
    "ARQQ","ARVL","ASLN","ASRT","ATAI","ATIF","ATOM","ATOS","AUPH","AUVI",
    "AVAH","AVCO","AVDL","AVEO","AVIR","AVPT","AVRO","AVTE","AVXL",
    # ── Cloud/SaaS
    "CRM","NOW","SNOW","DDOG","ZS","CRWD","OKTA","PLTR","NET","HUBS","BILL",
    # ── Retail/Consumer
    "WMT","TGT","COST","HD","NKE","MCD","ETSY","EBAY","PTON","DASH","ABNB",
    # ── Media
    "PARA","WBD","SPOT","ROKU","FUBO","SIRI","RBLX","U","SNAP","PINS","DIS",
    # ── Industrial/Defensa
    "BA","LMT","RTX","CAT","DE","GE","HON",
]))

@st.cache_data(ttl=3600)
def obtener_universo() -> list:
    """Obtiene todos los stocks NYSE+NASDAQ+AMEX via Twelve Data."""
    tickers = []
    for exc in ["NYSE","NASDAQ","AMEX"]:
        try:
            r = requests.get(
                "https://api.twelvedata.com/stocks",
                params={"exchange":exc,"type":"Common Stock","format":"JSON"},
                timeout=15
            )
            if r.status_code == 200:
                data = r.json()
                if "data" in data:
                    for item in data["data"]:
                        sym = item.get("symbol","").strip().upper()
                        if sym and sym.isalpha() and 1 < len(sym) <= 5:
                            tickers.append(sym)
        except Exception:
            pass
    tickers = list(dict.fromkeys(tickers))
    return tickers if len(tickers) > 200 else RESPALDO

# ══════════════════════════════════════════════════════
#  EXTRACCIÓN SEGURA DE DATAFRAME
# ══════════════════════════════════════════════════════
def extraer_df(raw, ticker, n_chunk):
    try:
        df = raw.copy() if n_chunk==1 else (
            raw[ticker].copy()
            if isinstance(raw.columns, pd.MultiIndex)
               and ticker in raw.columns.get_level_values(0)
            else None
        )
        if df is None: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        needed = {"Close","High","Low","Open","Volume"}
        if not needed.issubset(set(df.columns)): return None
        df = df.dropna(subset=["Close","Volume"])
        return df if len(df) >= 3 else None
    except Exception:
        return None

# ══════════════════════════════════════════════════════
#  SUPERTREND
# ══════════════════════════════════════════════════════
def calcular_supertrend(df: pd.DataFrame, periodo=10, multiplicador=3.0):
    """
    Supertrend clásico.
    Retorna columnas: 'st_up' (soporte), 'st_dn' (resistencia), 'st_dir' (1=alcista, -1=bajista)
    """
    try:
        h = df["H"] if "H" in df.columns else pd.to_numeric(df["High"], errors="coerce")
        l = df["L"] if "L" in df.columns else pd.to_numeric(df["Low"],  errors="coerce")
        c = df["C"] if "C" in df.columns else pd.to_numeric(df["Close"],errors="coerce")

        n = len(df)
        if n < periodo + 2:
            df["st_dir"] = 1
            df["st_val"] = c * 0.98
            return df

        # ATR
        hl  = h - l
        hc  = (h - c.shift(1)).abs()
        lc  = (l - c.shift(1)).abs()
        atr = pd.concat([hl,hc,lc],axis=1).max(axis=1).rolling(periodo).mean()

        hl2       = (h + l) / 2
        upper_raw = hl2 + multiplicador * atr
        lower_raw = hl2 - multiplicador * atr

        upper = upper_raw.copy()
        lower = lower_raw.copy()

        for i in range(1, n):
            upper.iloc[i] = min(upper_raw.iloc[i], upper.iloc[i-1]) if c.iloc[i-1] <= upper.iloc[i-1] else upper_raw.iloc[i]
            lower.iloc[i] = max(lower_raw.iloc[i], lower.iloc[i-1]) if c.iloc[i-1] >= lower.iloc[i-1] else lower_raw.iloc[i]

        direction = pd.Series(index=df.index, dtype=float)
        direction.iloc[0] = 1
        for i in range(1, n):
            prev_dir = direction.iloc[i-1]
            if prev_dir == 1:
                direction.iloc[i] = 1 if c.iloc[i] >= lower.iloc[i] else -1
            else:
                direction.iloc[i] = -1 if c.iloc[i] <= upper.iloc[i] else 1

        df["st_dir"] = direction.values
        df["st_up"]  = lower.values   # línea de soporte (dirección alcista)
        df["st_dn"]  = upper.values   # línea de resistencia (dirección bajista)
        df["st_val"] = np.where(direction == 1, lower.values, upper.values)

        return df
    except Exception:
        df["st_dir"] = 1
        df["st_val"] = (df["C"] if "C" in df.columns else df["Close"]) * 0.98
        return df

# ══════════════════════════════════════════════════════
#  INDICADORES TÉCNICOS COMPLETOS
# ══════════════════════════════════════════════════════
def calcular_indicadores(df: pd.DataFrame, session: str):
    try:
        df = df.copy()
        def ts(col):
            s = pd.to_numeric(df[col], errors="coerce").squeeze()
            return s.iloc[:,0] if isinstance(s, pd.DataFrame) else s

        C,H,L,O,V = ts("Close"), ts("High"), ts("Low"), ts("Open"), ts("Volume").fillna(0)
        df["C"],df["H"],df["L"],df["O"],df["V"] = C.values,H.values,L.values,O.values,V.values
        n = len(df)
        if n < 3: return None

        # EMAs
        df["ema9"]  = df["C"].ewm(span=min(9,n),  adjust=False).mean()
        df["ema20"] = df["C"].ewm(span=min(20,n), adjust=False).mean()

        # VWAP intradiario
        tp         = (df["H"]+df["L"]+df["C"])/3
        cumvol     = df["V"].cumsum()
        df["vwap"] = np.where(cumvol>0,(tp*df["V"]).cumsum()/cumvol, df["C"])

        # RSI
        d  = df["C"].diff()
        g  = d.where(d>0,0.0).rolling(min(14,n)).mean()
        ls = (-d.where(d<0,0.0)).rolling(min(14,n)).mean()
        df["rsi"] = (100 - 100/(1+g/ls.replace(0,np.nan))).fillna(50)

        # MACD
        df["macd"]   = (df["C"].ewm(span=min(12,n),adjust=False).mean()
                       -df["C"].ewm(span=min(26,n),adjust=False).mean())
        df["macd_s"] = df["macd"].ewm(span=min(9,n),adjust=False).mean()
        df["macd_h"] = df["macd"] - df["macd_s"]

        # ATR y soporte/resistencia
        hl  = df["H"]-df["L"]
        hc  = (df["H"]-df["C"].shift(1)).abs()
        lc  = (df["L"]-df["C"].shift(1)).abs()
        df["atr"] = pd.concat([hl,hc,lc],axis=1).max(axis=1).rolling(min(14,n)).mean().fillna(df["C"]*0.01)
        w = min(20,n)
        df["sup"] = df["L"].rolling(w).min().fillna(df["C"]*0.97)
        df["res"] = df["H"].rolling(w).max().fillna(df["C"]*1.03)

        # ── RVOL adaptado a sesión ────────────────────────
        # En pre/after, comparamos vs promedio de esa misma sesión
        # En regular, promedio de últimas 10 velas intradiarias
        if session == "REGULAR":
            w_rvol = min(10, n)
        else:
            # Pre/after: comparar vs toda la sesión actual disponible
            w_rvol = max(3, min(n-1, n))

        df["vavg"] = df["V"].rolling(w_rvol).mean().fillna(df["V"].mean())
        df["rvol"] = (df["V"] / df["vavg"].replace(0,1)).fillna(1)

        # ── VELOCIDAD de precio (% cambio por vela) ───────
        df["vel1"] = df["C"].pct_change(1) * 100
        df["vel2"] = df["C"].pct_change(2) * 100
        df["vel3"] = df["C"].pct_change(3) * 100
        df["acel"] = df["vel1"] - df["vel1"].shift(1)

        # ── SUPERTREND ────────────────────────────────────
        df = calcular_supertrend(df, periodo=min(10,n-1), multiplicador=3.0)

        # Stochastic
        low14  = df["L"].rolling(min(14,n)).min()
        high14 = df["H"].rolling(min(14,n)).max()
        df["stk"] = (100*(df["C"]-low14)/(high14-low14+1e-9)).fillna(50)
        df["std_k"]= df["stk"].rolling(min(3,n)).mean().fillna(50)

        return df
    except Exception:
        return None

# ══════════════════════════════════════════════════════
#  MOTOR DE SEÑAL V93
#
#  DIFERENCIA CLAVE vs versiones anteriores:
#  → El "% cambio del día" NO es filtro principal
#  → EL FILTRO PRINCIPAL es: ¿hay actividad AHORA?
#    medida por RVOL + Velocidad de precio
#  → Supertrend confirma dirección
# ══════════════════════════════════════════════════════
def g(row, col, default=0.0):
    try:
        v = float(row[col])
        return default if (np.isnan(v) or np.isinf(v)) else v
    except Exception:
        return default

def motor_senal(df, session: str):
    """Retorna (score_up, score_dn, senal, detalles, rvol, vel1, st_dir)"""
    if df is None or len(df) < 3:
        return 1,1,"NEUTRO",{},0,0,0

    a = df.iloc[-1]
    p = df.iloc[-2] if len(df)>1 else df.iloc[-1]
    b = df.iloc[-3] if len(df)>2 else p

    precio = g(a,"C",0)
    if precio <= 0: return 1,1,"NEUTRO",{},0,0,0

    up = dn = 0.0
    det = {}

    # ── 1. RVOL (30%) ─────────────────────────────────
    rvol = g(a,"rvol",1)
    if rvol >= 10:
        up += 3.0
        det["RVOL"] = f"🔥🔥🔥 RVOL={rvol:.1f}x — VOLUMEN EXPLOSIVO"
    elif rvol >= 5:
        up += 2.3
        det["RVOL"] = f"🔥🔥 RVOL={rvol:.1f}x — Muy alto"
    elif rvol >= 2.5:
        up += 1.6
        det["RVOL"] = f"🔥 RVOL={rvol:.1f}x — Elevado"
    elif rvol >= 1.5:
        up += 0.9
        det["RVOL"] = f"▲ RVOL={rvol:.1f}x — Sobre promedio"
    else:
        det["RVOL"] = f"→ RVOL={rvol:.1f}x — Normal"

    # ── 2. VELOCIDAD precio última vela (25%) ─────────
    vel1 = g(a,"vel1",0)
    if vel1 >= 5:
        up += 2.5
        det["VEL"] = f"🚀🚀 Vel={vel1:+.2f}%/min — COHETE"
    elif vel1 >= 2:
        up += 2.0
        det["VEL"] = f"🚀 Vel={vel1:+.2f}%/min — Fuerte"
    elif vel1 >= 0.5:
        up += 1.2
        det["VEL"] = f"▲ Vel={vel1:+.2f}%/min — Positivo"
    elif vel1 >= 0.1:
        up += 0.5
        det["VEL"] = f"▲ Vel={vel1:+.2f}%/min — Lento pero positivo"
    elif vel1 <= -5:
        dn += 2.5
        det["VEL"] = f"💥 Vel={vel1:+.2f}%/min — CAÍDA"
    elif vel1 <= -2:
        dn += 2.0
        det["VEL"] = f"▼▼ Vel={vel1:+.2f}%/min — Cayendo"
    elif vel1 <= -0.1:
        dn += 0.8
        det["VEL"] = f"▼ Vel={vel1:+.2f}%/min — Bajando"
    else:
        det["VEL"] = f"→ Vel={vel1:+.2f}%/min — Plano"

    # ── 3. ACELERACIÓN (20%) ──────────────────────────
    v1 = g(a,"vel1",0); v2 = g(p,"vel1",0); v3 = g(b,"vel1",0)
    if v1 > 0 and v2 > 0 and v1 > v2 > 0:
        up += 2.0
        det["ACEL"] = f"⚡ Acelerando: {v2:+.2f}% → {v1:+.2f}%/min"
    elif v1 > 0 and v1 > v2:
        up += 1.0
        det["ACEL"] = f"▲ Vel aumentando: {v2:+.2f}% → {v1:+.2f}%"
    elif v1 < 0 and v1 < v2:
        dn += 1.0
        det["ACEL"] = f"▼ Caída acelerando: {v2:+.2f}% → {v1:+.2f}%"
    else:
        det["ACEL"] = f"→ Sin aceleración ({v1:+.2f}%)"

    # ── 4. SUPERTREND (20%) ───────────────────────────
    st_dir = g(a,"st_dir",1)
    st_val = g(a,"st_val",precio)
    dist   = abs(precio - st_val) / max(precio,1e-9) * 100
    if st_dir == 1:
        up += 2.0
        det["SUPERT"] = f"✅ Supertrend ALCISTA — soporte ${st_val:.3f} ({dist:.1f}% abajo)"
    else:
        dn += 2.0
        det["SUPERT"] = f"❌ Supertrend BAJISTA — resist ${st_val:.3f} ({dist:.1f}% arriba)"

    # Cambio de dirección Supertrend = señal muy fuerte
    st_dir_prev = g(p,"st_dir",st_dir)
    if st_dir == 1 and st_dir_prev == -1:
        up += 1.5
        det["SUPERT"] += " ⚡ CRUCE ALCISTA RECIENTE"
    elif st_dir == -1 and st_dir_prev == 1:
        dn += 1.5
        det["SUPERT"] += " ⚡ CRUCE BAJISTA RECIENTE"

    # ── 5. CONFIRMACIÓN TÉCNICA (10%) ─────────────────
    vwap = g(a,"vwap",precio)
    e9   = g(a,"ema9",precio)
    e20  = g(a,"ema20",precio)
    rsi  = g(a,"rsi",50)
    mh   = g(a,"macd_h",0)
    mh_p = g(p,"macd_h",0)

    conf = 0.0
    if precio > vwap:       conf += 0.3
    if e9 > e20:            conf += 0.3
    if mh > mh_p and mh>0: conf += 0.3
    if 50 < rsi < 80:       conf += 0.2
    if rsi >= 80:           conf -= 0.2  # sobrecompra
    if rsi <= 20:           conf -= 0.2  # sobreventa

    if conf >= 0.8:
        up += 1.0
        det["TEC"] = f"▲▲ Técnico muy alcista (VWAP,EMA,MACD,RSI={rsi:.0f})"
    elif conf >= 0.3:
        up += 0.5
        det["TEC"] = f"▲ Técnico alcista parcial (RSI={rsi:.0f})"
    elif conf <= -0.3:
        dn += 0.5
        det["TEC"] = f"▼ Técnico bajista (RSI={rsi:.0f})"
    else:
        det["TEC"] = f"→ Técnico neutro (RSI={rsi:.0f})"

    # ── PATRÓN DE VELAS (bonus) ────────────────────────
    c1=g(df.iloc[-1],"C",precio); o1=g(df.iloc[-1],"O",c1)
    c2=g(df.iloc[-2],"C",c1) if len(df)>1 else c1
    o2=g(df.iloc[-2],"O",c2) if len(df)>1 else c2
    c3=g(df.iloc[-3],"C",c2) if len(df)>2 else c2
    o3=g(df.iloc[-3],"O",c3) if len(df)>2 else c3

    if (c1>o1) and (c2>o2) and (c3>o3) and (c1>c2>c3):
        up += 1.0
        det["VELAS"] = "🟢🟢🟢 3 velas verdes — arranque confirmado"
    elif (c1>o1) and (c2>o2) and (c1>c2):
        up += 0.5
        det["VELAS"] = "🟢🟢 2 velas verdes"
    elif (c1<o1) and (c2<o2) and (c3<o3) and (c1<c2<c3):
        dn += 1.0
        det["VELAS"] = "🔴🔴🔴 3 velas rojas"
    elif (c1<o1) and (c2<o2):
        dn += 0.5
        det["VELAS"] = "🔴🔴 2 velas rojas"
    else:
        det["VELAS"] = "→ Sin patrón"

    # Normalizar 1-10
    mx = 3.0+2.5+2.0+3.5+1.5   # max teórico
    s_up = max(1, min(10, round(max(up,0)/mx*10)))
    s_dn = max(1, min(10, round(max(dn,0)/mx*10)))

    if   s_up>=9:  senal="🚀 DESPEGUE — COMPRA AHORA"
    elif s_up>=7:  senal="⚡ EXPLOSIÓN ALCISTA"
    elif s_up>=5:  senal="📈 IMPULSO ALCISTA"
    elif s_dn>=9:  senal="💥 CAÍDA FUERTE"
    elif s_dn>=7:  senal="📉 SEÑAL BAJISTA"
    elif s_dn>=5:  senal="▼ BAJISTA"
    else:          senal="⚪ NEUTRO"

    return s_up, s_dn, senal, det, rvol, vel1, int(st_dir)

# ══════════════════════════════════════════════════════
#  SL / TP DINÁMICO
# ══════════════════════════════════════════════════════
def calc_sl_tp(df, precio, senal, msl=2.0, mtp=4.0):
    try:
        a   = df.iloc[-1]
        atr = g(a,"atr",precio*0.01)
        sup = g(a,"sup",precio*0.97)
        res = g(a,"res",precio*1.03)
        st  = g(a,"st_val",0)

        if sup<=0 or sup>=precio: sup=precio*0.97
        if res<=0 or res<=precio: res=precio*1.03

        alcista = any(x in senal for x in ["DESPEGUE","COMPRA","ALCISTA","IMPULSO","EXPLOS"])
        if alcista:
            # SL debajo del Supertrend si está más cerca
            sl_base = max(precio-atr*msl, sup*0.998)
            if 0 < st < precio: sl_base = max(sl_base, st*0.998)
            sl = round(sl_base, 4)
            tp = round(min(precio+atr*mtp, res*0.999), 4)
        else:
            sl = round(min(precio+atr*msl, res*1.002), 4)
            tp = round(max(precio-atr*mtp, sup*1.001), 4)

        if sl<=0: sl=round(precio*0.97,4)
        if tp<=0: tp=round(precio*1.06,4)
        rr=round(abs(tp-precio)/max(abs(precio-sl),1e-6),2)
        return sl,tp,rr
    except Exception:
        return round(precio*0.97,4), round(precio*1.06,4), 2.0

# ══════════════════════════════════════════════════════
#  PRE-FILTRO: detectar stocks activos AHORA
#  Usa cambio % vs cierre anterior (ideal para pre-market)
# ══════════════════════════════════════════════════════
@st.cache_data(ttl=120)  # Cache 2 min
def prefiltro_rapido(tickers: list, precio_min: float, precio_max: float,
                     cambio_min_pct: float, n_max: int, session: str) -> list:
    """
    Pre-filtro rápido: descarga datos de 5min del día actual + ayer
    para calcular el % cambio vs cierre anterior.
    Retorna los N tickers con mayor movimiento AHORA.
    """
    activos = []
    lote    = 100
    pb      = st.progress(0.0, text="🔍 Pre-filtro rápido...")

    for i in range(0, len(tickers), lote):
        chunk = tickers[i:i+lote]
        pb.progress(min((i+lote)/len(tickers),1.0),
                    text=f"🔍 Pre-filtro: {min(i+lote,len(tickers))}/{len(tickers)}...")
        try:
            raw = yf.download(
                chunk, period="2d", interval="5m",
                group_by="ticker", prepost=True,
                progress=False, auto_adjust=True, threads=True, timeout=20
            )
            for t in chunk:
                try:
                    df_t = extraer_df(raw, t, len(chunk))
                    if df_t is None or len(df_t) < 2: continue

                    precio  = float(df_t["Close"].iloc[-1])
                    if not (precio_min <= precio <= precio_max): continue

                    # Cierre de ayer = último precio del día anterior
                    # Buscamos el primer dato de hoy
                    tz_et = pytz.timezone("US/Eastern")
                    now_et = datetime.now(tz_et)
                    hoy    = now_et.date()
                    df_t.index = pd.to_datetime(df_t.index)
                    try:
                        df_t.index = df_t.index.tz_convert("US/Eastern")
                    except Exception:
                        try:
                            df_t.index = df_t.index.tz_localize("US/Eastern")
                        except Exception:
                            pass

                    ayer   = df_t[df_t.index.date < hoy]
                    hoy_df = df_t[df_t.index.date == hoy]

                    if len(ayer) > 0 and len(hoy_df) > 0:
                        cierre_ayer = float(ayer["Close"].iloc[-1])
                        precio_act  = float(hoy_df["Close"].iloc[-1])
                        cambio_pct  = (precio_act - cierre_ayer) / max(cierre_ayer,1e-9) * 100
                    else:
                        # Fallback: cambio vs apertura
                        open_d     = float(df_t["Open"].iloc[0])
                        cambio_pct = (precio - open_d) / max(open_d,1e-9) * 100

                    # En pre/after market el cambio puede ser pequeño; incluimos todo
                    if session in ("PRE-MARKET","AFTER-HOURS"):
                        incluir = abs(cambio_pct) >= cambio_min_pct or abs(cambio_pct) >= 0.1
                    else:
                        incluir = abs(cambio_pct) >= cambio_min_pct

                    if not incluir: continue

                    vol_ult  = float(df_t["Volume"].iloc[-1])
                    vol_prom = float(df_t["Volume"].mean())
                    rvol_pre = vol_ult / max(vol_prom,1)

                    activos.append({
                        "ticker"   : t,
                        "precio"   : precio,
                        "cambio"   : cambio_pct,
                        "rvol_pre" : rvol_pre,
                    })
                except Exception:
                    continue
        except Exception:
            continue

    pb.empty()
    if not activos:
        return tickers[:n_max]

    activos.sort(key=lambda x: abs(x["cambio"]) + abs(x["rvol_pre"])*0.5, reverse=True)
    return [a["ticker"] for a in activos[:n_max]]

# ══════════════════════════════════════════════════════
#  ESCANEO PRINCIPAL — Motor de Aceleración + Supertrend
# ══════════════════════════════════════════════════════
def escanear(tickers, precio_min, precio_max, rvol_min, vel_min,
             msl, mtp, session, top_n):

    if not tickers: return pd.DataFrame()

    resultados = []
    pb    = st.progress(0.0, text="⚡ Escaneando con Motor de Aceleración + Supertrend...")
    total = len(tickers)
    lote  = 50
    dfs   = {}

    # ── Descarga datos de 1 minuto ─────────────────────
    for i in range(0, total, lote):
        chunk = tickers[i:i+lote]
        pb.progress(min((i+lote)/total*0.45,0.45),
                    text=f"📡 Descargando {min(i+lote,total)}/{total}...")
        try:
            raw = yf.download(
                chunk, period="1d", interval="1m",
                group_by="ticker", prepost=True,
                progress=False, auto_adjust=True, threads=True, timeout=25
            )
            for t in chunk:
                dfs[t] = extraer_df(raw, t, len(chunk))
        except Exception:
            for t in chunk:
                try:
                    s = yf.download(t, period="1d", interval="1m",
                                    prepost=True, progress=False,
                                    auto_adjust=True, threads=False, timeout=15)
                    dfs[t] = extraer_df(s, t, 1)
                except Exception:
                    dfs[t] = None

    # ── Análisis ───────────────────────────────────────
    for idx, t in enumerate(tickers):
        pb.progress(0.45+(idx+1)/total*0.55,
                    text=f"🔬 Supertrend+Aceleración: {t} ({idx+1}/{total})")
        try:
            raw_df = dfs.get(t)
            if raw_df is None or len(raw_df) < 5: continue

            df = calcular_indicadores(raw_df, session)
            if df is None or len(df) < 3: continue

            precio = float(df["C"].iloc[-1])
            if not (precio_min <= precio <= precio_max): continue

            rvol = float(df["rvol"].iloc[-1]) if not np.isnan(df["rvol"].iloc[-1]) else 0
            vel1 = float(df["vel1"].iloc[-1]) if not np.isnan(df["vel1"].iloc[-1]) else 0

            # ── FILTROS ADAPTATIVOS por sesión ───────────
            # PRE/AFTER: muy permisivos porque el volumen es bajo
            # REGULAR: más exigentes
            if session == "REGULAR":
                if rvol < rvol_min: continue
                if abs(vel1) < vel_min: continue
            else:
                # En pre/after: basta con RVOL ≥ 1.2 O vel ≥ 0.05%
                ok_rvol = rvol >= max(1.2, rvol_min * 0.4)
                ok_vel  = abs(vel1) >= max(0.05, vel_min * 0.3)
                if not (ok_rvol or ok_vel): continue

            s_up, s_dn, senal, det, rvol, vel1, st_dir = motor_senal(df, session)

            # En pre/after queremos ver TODAS las señales aunque score sea bajo
            if session == "REGULAR" and s_up < 3 and s_dn < 3: continue

            _sl, _tp, rr = calc_sl_tp(df, precio, senal, msl, mtp)

            # Cambio vs apertura del día
            open_d   = float(df["O"].iloc[0]) if float(df["O"].iloc[0])>0 else precio
            cambio_d = (precio-open_d)/max(open_d,1e-9)*100

            rsi = float(df["rsi"].iloc[-1])
            sup = float(df["sup"].iloc[-1])
            res = float(df["res"].iloc[-1])
            vel2= float(df["vel2"].iloc[-1]) if not np.isnan(df["vel2"].iloc[-1]) else 0
            acel= float(df["acel"].iloc[-1]) if not np.isnan(df["acel"].iloc[-1]) else 0
            st_val = float(df["st_val"].iloc[-1]) if "st_val" in df.columns else 0

            st_txt = "🟢 ALCISTA" if st_dir==1 else "🔴 BAJISTA"

            resultados.append({
                "Ticker"    : t,
                "Precio $"  : round(precio,4),
                "RVOL"      : round(rvol,1),
                "Vel 1m %"  : round(vel1,2),
                "Vel 2m %"  : round(vel2,2),
                "Acel"      : round(acel,3),
                "Supertrend": st_txt,
                "ST $"      : round(st_val,4),
                "Δ Día %"   : round(cambio_d,2),
                "Score 🐂"  : s_up,
                "Score 🐻"  : s_dn,
                "Señal"     : senal,
                "RSI"       : round(rsi,1),
                "Soporte $" : round(sup,4),
                "Resist $"  : round(res,4),
                "SL $"      : _sl,
                "TP $"      : _tp,
                "R:R"       : rr,
                "_det"      : det,
                "_df"       : df,
            })
        except Exception:
            continue

    pb.empty()
    if not resultados: return pd.DataFrame()

    df_res = pd.DataFrame(resultados)
    df_res = df_res.sort_values(
        ["Score 🐂","RVOL","Vel 1m %"], ascending=[False,False,False]
    ).reset_index(drop=True)
    return df_res.head(top_n)

# ══════════════════════════════════════════════════════
#  ALPACA HELPERS
# ══════════════════════════════════════════════════════
def get_cuenta():
    try:    return alpaca.get_account()
    except: return None

def get_pos():
    try:    return alpaca.get_all_positions()
    except: return []

def cerrar(sym):
    try:    alpaca.close_position(sym); return True,f"✅ Cerrada {sym}"
    except Exception as e: return False,str(e)

def buy(sym,qty,sl,tp):
    try:
        alpaca.submit_order(MarketOrderRequest(
            symbol=sym, qty=qty, side=OrderSide.BUY, time_in_force=TimeInForce.GTC,
            take_profit=TakeProfitRequest(limit_price=round(float(tp),2)),
            stop_loss=StopLossRequest(stop_price=round(float(sl),2))
        ))
        return True,f"✅ BUY {qty}x {sym} | SL ${sl} | TP ${tp}"
    except Exception as e: return False,f"❌ {e}"

def sell(sym,qty):
    try:
        alpaca.submit_order(MarketOrderRequest(
            symbol=sym, qty=qty, side=OrderSide.SELL, time_in_force=TimeInForce.GTC
        ))
        return True,f"✅ SELL {qty}x {sym}"
    except Exception as e: return False,f"❌ {e}"

# ══════════════════════════════════════════════════════
#  ENCABEZADO
# ══════════════════════════════════════════════════════
st.markdown('<h1 class="hdr">⚡ THUNDER RADAR V93</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub">SUPERTREND + ACELERACIÓN + RVOL · MULTI-SESIÓN · ALPACA PAPER</p>',
            unsafe_allow_html=True)

badge = {"REGULAR":"b-reg","PRE-MARKET":"b-pre","AFTER-HOURS":"b-aft","CERRADO":"b-cls"}
tz_et   = pytz.timezone("US/Eastern")
hora_et = datetime.now(tz_et).strftime("%H:%M:%S ET")
cuenta  = get_cuenta()

hc1,hc2,hc3 = st.columns(3)
with hc1:
    st.markdown(
        f'<span class="badge {badge.get(SESSION,"b-cls")}">● {SESSION}</span>'
        f' &nbsp;<span class="dot"></span>'
        f'<span style="color:#8b949e;font-size:.75em">EN VIVO</span>',
        unsafe_allow_html=True)
with hc2:
    st.markdown(f'<span style="color:#8b949e">🕐 {hora_et}</span>',unsafe_allow_html=True)
with hc3:
    if cuenta:
        eq  = float(cuenta.equity)
        pnl = eq-float(cuenta.last_equity)
        col = "#00ff88" if pnl>=0 else "#ff4444"
        st.markdown(f'<span style="color:{col}">💰 ${eq:,.2f} | P&L {pnl:+,.2f}</span>',
                    unsafe_allow_html=True)

# Info del motor
if SESSION == "PRE-MARKET":
    st.markdown("""<div class="ibox">
    <b style="color:#7c3aed">🌅 PRE-MARKET ACTIVO (04:00-09:29 ET)</b> — 
    Los filtros son ultra-sensibles. El motor busca cualquier movimiento con volumen relativo.
    <b style="color:#00ff88">Supertrend</b> confirma la dirección del impulso.
    Stocks como PBM, YXT, WSHP aparecen aquí cuando despegan.
    </div>""", unsafe_allow_html=True)
elif SESSION == "AFTER-HOURS":
    st.markdown("""<div class="ibox">
    <b style="color:#0369a1">🌆 AFTER-HOURS ACTIVO (16:00-19:59 ET)</b> —
    Filtros sensibles para volumen bajo. El motor detecta reacciones a earnings y noticias.
    </div>""", unsafe_allow_html=True)
elif SESSION == "REGULAR":
    st.markdown("""<div class="ibox">
    <b style="color:#15803d">📈 MERCADO REGULAR (09:30-15:59 ET)</b> —
    Hora de máxima oportunidad. RVOL + Supertrend + Velocidad operando a plena potencia.
    </div>""", unsafe_allow_html=True)
else:
    st.markdown("""<div class="ibox">
    <b style="color:#8b949e">🌙 MERCADO CERRADO</b> — 
    Pre-market abre a las 4:00 AM ET. Mercado regular a las 9:30 AM ET.
    Puedes cargar el universo y hacer el pre-filtro ahora para estar listo.
    </div>""", unsafe_allow_html=True)

st.markdown('<hr class="n">', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  BARRA LATERAL
# ══════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ CONFIGURACIÓN")

    modo = st.selectbox("Modo", [
        "🔥 Todo el mercado",
        "💎 Penny + Small Caps",
        "📈 Large Cap",
        "🎯 Manual",
    ])

    st.markdown("---")
    precio_min_f = st.number_input("Precio Mín $", value=0.05, step=0.05, min_value=0.01)
    precio_max_f = st.number_input("Precio Máx $", value=500.0, step=10.0)

    # ── Filtros adaptativos según sesión ───────────────
    st.markdown("**⚡ Motor de Aceleración**")

    if SESSION in ("PRE-MARKET","AFTER-HOURS"):
        rvol_default = 1.2
        vel_default  = 0.05
        st.info(f"Sesión {SESSION}: filtros ultra-sensibles")
    else:
        rvol_default = 2.0
        vel_default  = 0.10

    rvol_min = st.slider("RVOL mínimo", 1.0, 15.0, rvol_default, 0.1,
                         help="1.5 = 50% más volumen que promedio. En pre-market usar 1.2")
    vel_min  = st.slider("Velocidad mín %/vela", 0.0, 3.0, vel_default, 0.01,
                         help="0.05 = apenas 0.05% por minuto. Suficiente para pre-market")

    st.markdown("---")
    st.markdown("**📊 Supertrend**")
    st_periodo = st.slider("Período Supertrend", 5, 20, 10, 1)
    st_mult    = st.slider("Multiplicador ATR", 1.0, 5.0, 3.0, 0.5)

    st.markdown("---")
    cambio_pf = st.slider("Pre-filtro: Δ% mín vs cierre ayer", 0.0, 10.0, 0.5, 0.1,
                           help="Para pre-market bajar a 0.5 o 0.1")
    n_prefiltro = st.slider("Candidatos del pre-filtro", 50, 500, 200, 25)
    top_n_f     = st.slider("Top resultados finales", 10, 80, 40, 5)

    st.markdown("---")
    atr_sl = st.slider("ATR × Stop Loss",   0.5, 5.0, 2.0, 0.5)
    atr_tp = st.slider("ATR × Take Profit", 1.0, 8.0, 4.0, 0.5)

    st.markdown("---")
    if modo == "🎯 Manual":
        txt = st.text_area("Tickers",
            "PBM,YJ,ILLR,SCAG,BLIV,ABTS,WSHP,YXT,ISPC,UCAR,ABLV,BRIA,TGHL", height=80)
        lista_manual = [t.strip().upper() for t in txt.split(",") if t.strip()]
    else:
        lista_manual = []

    st.markdown("---")
    modo_auto = st.toggle("🤖 Auto-Trade", value=False)
    if modo_auto:
        auto_score = st.slider("Score mín auto-compra", 6, 10, 7)
        auto_qty   = st.number_input("Acciones/orden", value=1, min_value=1)
        max_pos    = st.number_input("Máx posiciones", value=3, min_value=1)
        st.warning("⚠️ Ejecuta órdenes en Paper.")

    st.markdown("---")
    auto_refresh = st.toggle("🔁 Auto-escaneo", value=False)
    refresh_seg  = 45 if SESSION=="REGULAR" else 60

# ══════════════════════════════════════════════════════
#  CARGAR UNIVERSO
# ══════════════════════════════════════════════════════
if "universo"  not in st.session_state: st.session_state.universo  = []
if "prefiltro" not in st.session_state: st.session_state.prefiltro = []
if "df_scan"   not in st.session_state: st.session_state.df_scan   = pd.DataFrame()
if "last_scan" not in st.session_state: st.session_state.last_scan = None

cu1,cu2,cu3 = st.columns([2,1,1])
with cu1:
    if st.button("🌐 CARGAR UNIVERSO NYSE+NASDAQ+AMEX", use_container_width=True):
        with st.spinner("🌐 Descargando lista de stocks..."):
            u = obtener_universo()
            st.session_state.universo = u
            st.session_state.prefiltro = []   # resetear prefiltro
        st.success(f"✅ {len(u):,} stocks cargados")
with cu2:
    n_u = len(st.session_state.universo)
    col_u = "#00ff88" if n_u>100 else "#ff4444"
    st.markdown(f'<span style="color:{col_u}">📊 {n_u:,} stocks</span>', unsafe_allow_html=True)
with cu3:
    n_pf = len(st.session_state.prefiltro)
    col_p = "#00ff88" if n_pf>0 else "#8b949e"
    st.markdown(f'<span style="color:{col_p}">🔬 {n_pf} candidatos</span>', unsafe_allow_html=True)

# Auto-cargar universo si está vacío
if len(st.session_state.universo) == 0:
    st.session_state.universo = RESPALDO

# Determinar universo según modo
if modo == "🎯 Manual":
    universo_base = lista_manual
elif modo == "💎 Penny + Small Caps":
    universo_base = st.session_state.universo  # filtro de precio lo hace el motor
elif modo == "📈 Large Cap":
    universo_base = [s for s in st.session_state.universo
                     if s in ["AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","NFLX",
                               "AMD","INTC","AVGO","QCOM","JPM","BAC","GS","V","WFC"]]
else:
    universo_base = st.session_state.universo

# ══════════════════════════════════════════════════════
#  PRE-FILTRO
# ══════════════════════════════════════════════════════
st.markdown('<hr class="n">', unsafe_allow_html=True)

pf1,pf2,pf3 = st.columns([2,1,1])
with pf1:
    if st.button("🔬 PRE-FILTRO — detectar stocks activos AHORA", use_container_width=True):
        n_base = len(universo_base)
        st.markdown(f"**Pre-filtrando {n_base:,} stocks...**")
        candidatos = prefiltro_rapido(
            universo_base, precio_min_f, precio_max_f,
            cambio_pf, n_prefiltro, SESSION
        )
        st.session_state.prefiltro = candidatos
        st.success(f"✅ {len(candidatos)} candidatos seleccionados de {n_base:,}")
with pf2:
    st.markdown(f'<span style="color:#8b949e;font-size:.8em">Δ% mín: {cambio_pf}%</span>',
                unsafe_allow_html=True)
with pf3:
    if st.button("🗑️ Limpiar prefiltro"):
        st.session_state.prefiltro = []
        st.rerun()

# Lista final para escanear
if st.session_state.prefiltro:
    lista_scan = st.session_state.prefiltro
    st.info(f"🔬 **{len(lista_scan)} candidatos** del pre-filtro (de {len(universo_base):,} totales)")
elif modo == "🎯 Manual":
    lista_scan = lista_manual
    st.info(f"🎯 Modo manual: {len(lista_scan)} tickers")
else:
    # Sin prefiltro: usar primeros 300 del universo
    lista_scan = universo_base[:300]
    st.warning(
        f"⚠️ Sin pre-filtro activo. Usando {len(lista_scan)} primeros tickers. "
        "Usa **🔬 PRE-FILTRO** para mejores resultados en pre/after market."
    )

# ══════════════════════════════════════════════════════
#  PORTAFOLIO
# ══════════════════════════════════════════════════════
st.markdown('<hr class="n">', unsafe_allow_html=True)
st.subheader("💼 Portafolio Activo")
posiciones = get_pos()
if posiciones:
    rows = []
    for p in posiciones:
        pnl_p = float(p.unrealized_plpc)*100
        pnl_u = float(p.unrealized_pl)
        ico   = "🟢" if pnl_p>=0 else "🔴"
        rows.append({"Ticker":p.symbol,"Qty":p.qty,
                     "Entrada $":round(float(p.avg_entry_price),4),
                     "Actual $": round(float(p.current_price),4),
                     "P&L %":   f"{ico} {pnl_p:+.2f}%",
                     "P&L $":   f"${pnl_u:+.2f}",
                     "Valor $": f"${float(p.market_value):,.2f}"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    px1,px2,px3 = st.columns([2,1,1])
    with px1: t_close = st.selectbox("Ticker a cerrar",[r["Ticker"] for r in rows])
    with px2:
        if st.button("🔴 Cerrar pos."):
            ok,msg=cerrar(t_close); st.success(msg) if ok else st.error(msg)
    with px3:
        if st.button("🔴 Cerrar TODO"):
            [cerrar(p.symbol) for p in posiciones]; st.warning("Cerrando...")
else:
    st.info("Sin posiciones. ¡Detecta despegues! 🚀")

# ══════════════════════════════════════════════════════
#  ESCANEO PRINCIPAL
# ══════════════════════════════════════════════════════
st.markdown('<hr class="n">', unsafe_allow_html=True)
st.subheader("🔭 Motor de Aceleración + Supertrend")

sb1,sb2,sb3 = st.columns([2,1,1])
with sb1: iniciar = st.button("🚀 INICIAR ESCANEO — DETECTAR DESPEGUES", use_container_width=True)
with sb2:
    if st.button("🔄 Refresh", use_container_width=True): st.rerun()
with sb3:
    if st.session_state.last_scan:
        ts = datetime.fromtimestamp(st.session_state.last_scan)
        ts_et = ts.astimezone(tz_et).strftime("%H:%M:%S")
        st.markdown(f'<span style="color:#8b949e;font-size:.75em">Último: {ts_et} ET</span>',
                    unsafe_allow_html=True)

debe = iniciar or (
    auto_refresh
    and st.session_state.last_scan is not None
    and (time.time()-st.session_state.last_scan)>=refresh_seg
)

if debe:
    if not lista_scan:
        st.error("❌ No hay tickers. Carga el universo primero.")
    else:
        st.markdown(
            f"⚡ Escaneando **{len(lista_scan)} stocks** | Sesión: **{SESSION}** | "
            f"RVOL≥**{rvol_min}x** | Vel≥**{vel_min}%**/vela | Supertrend período={st_periodo}"
        )
        with st.spinner("⚡ Analizando..."):
            df_scan = escanear(
                lista_scan, precio_min_f, precio_max_f,
                rvol_min, vel_min, atr_sl, atr_tp, SESSION, top_n_f
            )
        st.session_state.df_scan   = df_scan
        st.session_state.last_scan = time.time()
        ts_str = datetime.now(tz_et).strftime("%H:%M:%S ET")
        n = len(df_scan)
        if n>0: st.success(f"✅ {ts_str} — **{n} señales detectadas**")
        else:   st.warning(f"⚠️ {ts_str} — Sin señales. Baja RVOL o velocidad mínima.")

df_scan = st.session_state.df_scan

# ══════════════════════════════════════════════════════
#  MOSTRAR RESULTADOS
# ══════════════════════════════════════════════════════
if not df_scan.empty:

    despegues = df_scan[df_scan["Score 🐂"] >= 7]
    impulsos  = df_scan[(df_scan["Score 🐂"]>=5)&(df_scan["Score 🐂"]<7)]

    # ── TARJETAS DESPEGUE ────────────────────────────
    if not despegues.empty:
        st.markdown(f"### 🚀 DESPEGUES — {len(despegues)} señales")
        for _, row in despegues.iterrows():
            s   = int(row["Score 🐂"])
            cls = "sc10" if s==10 else ("sc8" if s>=8 else "sc6")
            rv  = float(row["RVOL"])
            vc  = "#00ff88" if row["Vel 1m %"]>=0 else "#ff4444"
            dc  = "#00ff88" if row["Δ Día %"]>=0  else "#ff4444"
            st_col = "#00ff88" if "ALCISTA" in str(row["Supertrend"]) else "#ff4444"
            card = "card-fire" if s>=7 else "card-hot"
            st.markdown(f"""
            <div class="{card}">
              <span class="tkr">⚡ {row['Ticker']}</span>
              &nbsp;&nbsp;<span class="{cls}">{s}/10</span>
              &nbsp;&nbsp;<span style="color:#a78bfa;font-size:.86em">{row['Señal']}</span>
              &nbsp;&nbsp;<span style="color:{st_col};font-size:.82em">{row['Supertrend']}</span>
              <br>
              <span class="lbl">Precio</span> <b style="color:#fff">${row['Precio $']}</b>
              &nbsp;|&nbsp;
              <span class="lbl">RVOL</span>
              <b style="color:{'#ff4500' if rv>=10 else ('#ff8c00' if rv>=5 else '#ffc107')}">{rv:.1f}x</b>
              &nbsp;|&nbsp;
              <span class="lbl">Vel 1min</span> <b style="color:{vc}">{row['Vel 1m %']:+.2f}%</b>
              &nbsp;|&nbsp;
              <span class="lbl">Vel 2min</span> <b style="color:{vc}">{row['Vel 2m %']:+.2f}%</b>
              &nbsp;|&nbsp;
              <span class="lbl">Acel</span> <b style="color:{'#00ff88' if row['Acel']>0 else '#ff4444'}">{row['Acel']:+.3f}</b>
              &nbsp;|&nbsp;
              <span class="lbl">Δ Día</span> <span style="color:{dc}">{row['Δ Día %']:+.2f}%</span>
              &nbsp;|&nbsp;
              <span class="lbl">RSI</span> {row['RSI']}
              &nbsp;|&nbsp;
              <span class="lbl">ST$</span> {row['ST $']}
              <br>
              <span class="lbl">SL</span> <span style="color:#ff6b6b">${row['SL $']}</span>
              &nbsp;|&nbsp;
              <span class="lbl">TP</span> <span style="color:#00ff88">${row['TP $']}</span>
              &nbsp;|&nbsp;
              <span class="lbl">R:R</span> {row['R:R']}x
            </div>""", unsafe_allow_html=True)

    # ── IMPULSOS (score 5-6) ─────────────────────────
    if not impulsos.empty:
        with st.expander(f"👁️ IMPULSOS EN FORMACIÓN — {len(impulsos)} señales (score 5-6)"):
            for _, row in impulsos.iterrows():
                vc  = "#00ff88" if row["Vel 1m %"]>=0 else "#ff4444"
                st_col = "#00ff88" if "ALCISTA" in str(row["Supertrend"]) else "#ff4444"
                st.markdown(f"""
                <div class="card-watch">
                  <span class="tkr" style="font-size:1.05em">{row['Ticker']}</span>
                  &nbsp;<span class="sc6">{int(row['Score 🐂'])}/10</span>
                  &nbsp;<span style="color:#8b949e;font-size:.80em">{row['Señal']}</span>
                  &nbsp;<span style="color:{st_col};font-size:.78em">{row['Supertrend']}</span>
                  &nbsp;|&nbsp;${row['Precio $']}
                  &nbsp;|&nbsp;<b>RVOL</b> {row['RVOL']}x
                  &nbsp;|&nbsp;<b style="color:{vc}">{row['Vel 1m %']:+.2f}%/min</b>
                  &nbsp;|&nbsp;<b>RSI</b> {row['RSI']}
                  &nbsp;|&nbsp;<b>SL</b> ${row['SL $']}
                  &nbsp;|&nbsp;<b>TP</b> ${row['TP $']}
                </div>""", unsafe_allow_html=True)

    # ── TABLA COMPLETA ───────────────────────────────
    st.markdown("### 📋 Tabla Completa del Radar")
    cols = ["Ticker","Precio $","RVOL","Vel 1m %","Vel 2m %","Acel","Supertrend",
            "ST $","Δ Día %","Score 🐂","Score 🐻","Señal","RSI",
            "Soporte $","Resist $","SL $","TP $","R:R"]
    df_show = df_scan[cols].copy()

    def cs(v):
        if v>=8:   return "background-color:#15803d;color:white"
        elif v>=6: return "background-color:#1d4ed8;color:white"
        elif v>=4: return "background-color:#92400e;color:white"
        else:      return "background-color:#7f1d1d;color:white"

    def cv(v):
        return f"color:{'#00ff88' if v>=0 else '#ff4444'};font-weight:bold"

    def cr(v):
        if v>=10:  return "color:#ff4500;font-weight:900"
        elif v>=5: return "color:#ff8c00;font-weight:700"
        elif v>=2: return "color:#ffc107;font-weight:bold"
        else:      return "color:#8b949e"

    fmt = {"Precio $":"${:.4f}","RVOL":"{:.1f}x","Vel 1m %":"{:+.2f}%",
           "Vel 2m %":"{:+.2f}%","Acel":"{:+.3f}","ST $":"${:.4f}",
           "Δ Día %":"{:+.2f}%","RSI":"{:.1f}",
           "Soporte $":"${:.4f}","Resist $":"${:.4f}",
           "SL $":"${:.4f}","TP $":"${:.4f}","R:R":"{:.2f}"}

    try:
        styled = (df_show.style
                  .map(cs, subset=["Score 🐂","Score 🐻"])
                  .map(cv, subset=["Vel 1m %","Vel 2m %","Δ Día %"])
                  .map(cr, subset=["RVOL"])
                  .format(fmt))
    except Exception:
        try:
            styled = (df_show.style
                      .applymap(cs, subset=["Score 🐂","Score 🐻"])
                      .applymap(cv, subset=["Vel 1m %","Vel 2m %","Δ Día %"])
                      .applymap(cr, subset=["RVOL"])
                      .format(fmt))
        except Exception:
            styled = df_show.style.format(fmt)

    st.dataframe(styled, use_container_width=True, hide_index=True, height=430)

    # ── AUTO-TRADE ───────────────────────────────────
    if modo_auto:
        st.markdown("### 🤖 Auto-Trade")
        n_pos = len(get_pos())
        for _, row in df_scan[df_scan["Score 🐂"]>=auto_score].iterrows():
            if n_pos>=max_pos:
                st.warning(f"Máx {max_pos} pos."); break
            ok,msg = buy(row["Ticker"],auto_qty,row["SL $"],row["TP $"])
            if ok: n_pos+=1
            st.write(msg)

    # ── EJECUCIÓN MANUAL ─────────────────────────────
    st.markdown('<hr class="n">', unsafe_allow_html=True)
    st.markdown("### 🛒 Ejecución Manual")
    ce1,ce2 = st.columns([1,2])
    with ce1:
        t_op  = st.selectbox("Ticker", df_scan["Ticker"].tolist())
        rsel  = df_scan[df_scan["Ticker"]==t_op].iloc[0]
        qty_m = st.number_input("Cantidad",value=1,min_value=1,step=1)
        sl_m  = st.number_input("SL $",value=float(rsel["SL $"]),step=0.001,format="%.4f")
        tp_m  = st.number_input("TP $",value=float(rsel["TP $"]),step=0.001,format="%.4f")
        b1,b2 = st.columns(2)
        with b1:
            if st.button("🟢 COMPRAR",use_container_width=True):
                ok,msg=buy(t_op,qty_m,sl_m,tp_m); st.success(msg) if ok else st.error(msg)
        with b2:
            if st.button("🔴 VENDER",use_container_width=True):
                ok,msg=sell(t_op,qty_m); st.success(msg) if ok else st.error(msg)

    with ce2:
        st.markdown(f"### 📊 {t_op} — Supertrend + Aceleración")
        st_dir_val = rsel.get("Supertrend","")
        st_col2 = "#00ff88" if "ALCISTA" in str(st_dir_val) else "#ff4444"
        st.markdown(f'<b style="color:{st_col2};font-size:1.1em">{st_dir_val}</b> '
                    f'— Soporte/Resistencia ST: <b>${rsel["ST $"]}</b>',
                    unsafe_allow_html=True)
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Precio $",  f"${rsel['Precio $']:.4f}")
        m2.metric("RVOL",      f"{rsel['RVOL']:.1f}x")
        m3.metric("Vel 1min",  f"{rsel['Vel 1m %']:+.2f}%")
        m4.metric("Score 🐂",  f"{rsel['Score 🐂']}/10")
        m5,m6,m7,m8 = st.columns(4)
        m5.metric("RSI",       f"{rsel['RSI']}")
        m6.metric("SL $",      f"${rsel['SL $']:.4f}")
        m7.metric("TP $",      f"${rsel['TP $']:.4f}")
        m8.metric("R:R",       f"{rsel['R:R']}x")

        det = rsel.get("_det",{})
        if det:
            st.markdown("**📌 Detalle del motor:**")
            for k,v in det.items():
                c = ("#00ff88" if any(x in v for x in ["▲","🚀","⚡","🔥","✅","🟢"])
                     else ("#ff4444" if any(x in v for x in ["▼","💥","❌","🔴"])
                           else "#ffc107"))
                st.markdown(f'<span style="color:{c};font-size:.80em"><b>{k}</b>: {v}</span>',
                             unsafe_allow_html=True)

elif st.session_state.last_scan is not None:
    st.warning("""
    ⚠️ **Sin señales.** Ajusta los filtros:
    - Baja **RVOL mínimo** a 1.2x o menos
    - Baja **Velocidad mínima** a 0.03%
    - Baja **Pre-filtro Δ%** a 0.1%
    - Usa **🔬 PRE-FILTRO** primero
    - En pre/after: el volumen es bajo, usa filtros ultra-sensibles
    """)
else:
    st.markdown("""
    ### 📋 Flujo recomendado para pre-market / regular:

    **1️⃣** Pulsa **🌐 CARGAR UNIVERSO** (una vez al día)

    **2️⃣** Pulsa **🔬 PRE-FILTRO** → selecciona los 200 más activos ahora

    **3️⃣** Pulsa **🚀 INICIAR ESCANEO** → detecta despegues con Supertrend

    > En pre-market (4:00-9:30 AM ET) el **pre-filtro** usa `Δ%` vs cierre de ayer.
    > Así captura stocks como PBM +79%, YXT +67% que despegan antes de que abra el mercado.
    """)

# ══════════════════════════════════════════════════════
if auto_refresh:
    time.sleep(refresh_seg)
    st.rerun()

st.markdown('<hr class="n">', unsafe_allow_html=True)
st.markdown("""<div style="text-align:center;color:#8b949e;font-size:.69em;
font-family:'Share Tech Mono',monospace">
⚡ THUNDER RADAR V93 — PAPER TRADING — Uso educativo y experimental<br>
Los resultados pasados no garantizan rendimientos futuros. Opera con responsabilidad.
</div>""", unsafe_allow_html=True)
