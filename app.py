"""
THUNDER RADAR V97 — UNIVERSO COMPLETO
======================================
FUENTES COMBINADAS (todas gratuitas):
  1. Twelve Data  → universo completo NYSE+NASDAQ+AMEX (5,000+ acciones)
  2. Yahoo Finance → top gainers del día en tiempo real
  3. Detector 5min → momentum de los últimos 5 minutos (como Webull)
  4. yfinance 1min → indicadores técnicos para señal de despegue
  5. Alpaca Paper  → ejecución de órdenes con SL/TP dinámico

FLUJO:
  Paso 1: Carga universo completo via Twelve Data
  Paso 2: Yahoo Finance trae top gainers del día
  Paso 3: Pre-filtro rápido 5min sobre TODO el universo
  Paso 4: Motor de señal 1min sobre los candidatos
  Resultado: Despegues detectados con Score 1-10
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

# ══════════════════════════════════════════════════════════════
st.set_page_config(page_title="⚡ THUNDER RADAR V97", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
html,body,[class*="css"]{background:#030810!important;color:#c9d1d9!important;
    font-family:'Share Tech Mono',monospace;}
h1,h2,h3{font-family:'Orbitron',sans-serif!important;}
.stButton>button{width:100%;border-radius:4px;font-weight:bold;
    font-family:'Orbitron',sans-serif;letter-spacing:1px;
    border:1px solid #30363d;transition:all .2s;}
.stButton>button:hover{transform:translateY(-1px);box-shadow:0 0 16px #00ff8866;}
div[data-testid="metric-container"]{
    background:linear-gradient(135deg,#0a0f1a,#141b27);
    border:1px solid #1e2739;border-radius:8px;padding:12px;}
.card-fire{background:linear-gradient(135deg,#061510,#0a0f1a);
    border:2px solid #00ff88;border-radius:10px;padding:13px 17px;margin:5px 0;
    box-shadow:0 0 20px #00ff8855;}
.card-5min{background:linear-gradient(135deg,#100806,#0a0f1a);
    border:2px solid #ff4500;border-radius:10px;padding:13px 17px;margin:5px 0;
    box-shadow:0 0 18px #ff450044;}
.card-hot{background:linear-gradient(135deg,#100a06,#0a0f1a);
    border:2px solid #ff8c00;border-radius:10px;padding:11px 15px;margin:4px 0;}
.card-watch{background:#090b0f;border:1px solid #ffc10733;
    border-radius:8px;padding:9px 13px;margin:3px 0;}
.s10{color:#00ff88;font-size:1.9em;font-weight:900;font-family:'Orbitron',sans-serif;}
.s8{color:#39ff14;font-size:1.5em;font-weight:800;}
.s6{color:#ffc107;font-size:1.3em;font-weight:700;}
.tkr{font-family:'Orbitron',sans-serif;font-size:1.25em;font-weight:900;color:#fff;}
.lbl{color:#8b949e;font-size:.73em;}
.hdr{text-align:center;font-family:'Orbitron',sans-serif;font-size:2.1em;font-weight:900;
    background:linear-gradient(90deg,#00ff88,#00d4ff,#ff4500);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:3px;}
.sub{text-align:center;color:#8b949e;font-size:.76em;letter-spacing:3px;}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:.73em;font-weight:bold;}
.b-reg{background:#15803d;color:#fff;}.b-pre{background:#7c3aed;color:#fff;}
.b-aft{background:#0369a1;color:#fff;}.b-cls{background:#374151;color:#fff;}
.dot{display:inline-block;width:9px;height:9px;background:#00ff88;border-radius:50%;
    margin-right:5px;animation:blink 1s infinite;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.1}}
hr.n{border:none;border-top:1px solid #00ff8822;margin:12px 0;}
.ibox{background:#0a0f1a;border:1px solid #00ff8833;border-radius:8px;
    padding:10px 14px;margin:6px 0;font-size:.79em;line-height:1.6em;}
.step-box{background:#0a0f1a;border:1px solid #1e2739;border-radius:8px;
    padding:12px 16px;margin:4px 0;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  ALPACA
# ══════════════════════════════════════════════════════════════
ALPACA_KEY    = "PKOKUMRZBCA2YJKVZIATSPGV5J"
ALPACA_SECRET = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"

@st.cache_resource
def get_alpaca():
    return TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)
alpaca = get_alpaca()

# ══════════════════════════════════════════════════════════════
#  SESIÓN
# ══════════════════════════════════════════════════════════════
def get_session():
    tz = pytz.timezone("US/Eastern")
    h  = datetime.now(tz).hour + datetime.now(tz).minute / 60.0
    if   4.0  <= h < 9.5:  return "PRE-MARKET"
    elif 9.5  <= h < 16.0: return "REGULAR"
    elif 16.0 <= h < 20.0: return "AFTER-HOURS"
    else:                   return "CERRADO"

SESSION = get_session()

# ══════════════════════════════════════════════════════════════
#  LISTA RESPALDO (si Twelve Data y Yahoo fallan)
# ══════════════════════════════════════════════════════════════
RESPALDO = list(dict.fromkeys([
    "SDOT","BLZE","CLRB","STRL","BIYA","EVER","JLHL","NXTS","MRDN","UK",
    "NA","SLOT","NEXR","ATER","BBBY","SBLX","SKK","CNSP","PN","CRE",
    "ELPW","GBTG","SSM","HCAI","RLYB","MNDR","GME","AMC","KOSS","BB",
    "NOK","BBIG","SPCE","MULN","MVIS","PROG","NAKD","EXPR","KPLT","CELH",
    "OCGN","CLOV","SNDL","TLRY","AGEN","MNMD","ATAI","NVAX","MRNA","BNTX",
    "SRPT","ACAD","HIMS","CRSP","EDIT","COIN","HOOD","MSTR","RIOT","MARA",
    "HUT","CIFR","BTBT","CLSK","WULF","IREN","RIVN","LCID","CHPT","BLNK",
    "PLUG","FCEL","GOEV","NIO","XPEV","LI","BABA","JD","PDD","TCOM",
    "TIGR","FUTU","BILI","ASTS","LUNR","RKLB","ACHR","JOBY","IONQ","RGTI",
    "SOFI","UPST","AFRM","ROOT","AAPL","MSFT","NVDA","TSLA","AMD","META",
    "AMZN","GOOGL","AVGO","QCOM","MU","SMCI","PLTR","CRM","SNOW","DDOG",
    "CRWD","PTON","DOCU","ZM","LYFT","UBER","DASH","ABNB","DKNG","RBLX",
    "SNAP","PINS","PARA","WBD","ROKU","FUBO","SIRI","WKHS","NKLA","FSR",
    "BRIA","EDTK","TGHL","ZSPC","PBM","WSHP","MYSE","ONFO","CTNT","RAIN",
    "CPHI","NCRA","LVLU","RCAT","CRKN","BSLK","GPUS","GFAI","INPX","RSSS",
    "ISPC","UCAR","ABLV","YXT","ZBAI","MTEX","MGRT","SLQT","VOYG","IMOS",
]))

# ══════════════════════════════════════════════════════════════
#  FUENTE 1: TWELVE DATA — UNIVERSO COMPLETO
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def cargar_universo_twelve() -> list:
    """
    Descarga lista completa de acciones NYSE+NASDAQ+AMEX via Twelve Data.
    Gratis, sin API key. Retorna lista de símbolos (solo Common Stock).
    """
    tickers = []
    for exc in ["NYSE", "NASDAQ", "AMEX"]:
        try:
            r = requests.get(
                "https://api.twelvedata.com/stocks",
                params={"exchange": exc, "type": "Common Stock", "format": "JSON"},
                timeout=15
            )
            if r.status_code == 200:
                for item in r.json().get("data", []):
                    s = item.get("symbol", "").strip().upper()
                    if s and s.isalpha() and 2 <= len(s) <= 5:
                        tickers.append(s)
        except Exception:
            pass
    result = list(dict.fromkeys(tickers))
    return result if len(result) > 500 else RESPALDO

# ══════════════════════════════════════════════════════════════
#  FUENTE 2: YAHOO FINANCE — TOP GAINERS TIEMPO REAL
# ══════════════════════════════════════════════════════════════
YH = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "Accept": "application/json"}

def yahoo_screen(sid: str, n: int = 100) -> list:
    for base in ["https://query1.finance.yahoo.com",
                 "https://query2.finance.yahoo.com"]:
        try:
            r = requests.get(
                f"{base}/v1/finance/screener/predefined/saved",
                headers=YH,
                params={"scrIds": sid, "count": n, "formatted": "false"},
                timeout=12
            )
            if r.status_code == 200:
                quotes = (r.json().get("finance", {})
                           .get("result", [{}])[0]
                           .get("quotes", []))
                out = []
                for q in quotes:
                    s = q.get("symbol", "").strip().upper()
                    if s and s.isalpha() and 1 <= len(s) <= 5:
                        out.append(s)
                if out:
                    return out
        except Exception:
            pass
    return []

def obtener_yahoo_gainers() -> dict:
    day_g  = yahoo_screen("day_gainers",       100)
    active = yahoo_screen("most_actives",      100)
    small  = yahoo_screen("small_cap_gainers", 100)
    todos  = list(dict.fromkeys(day_g + active + small))
    return {
        "day_gainers": day_g,
        "most_actives": active,
        "small_cap": small,
        "todos": todos,
        "n_day": len(day_g),
        "n_active": len(active),
        "n_small": len(small),
        "n_total": len(todos),
    }

# ══════════════════════════════════════════════════════════════
#  EXTRACTOR SEGURO DE DATAFRAME (corrige bug RVOL=0)
# ══════════════════════════════════════════════════════════════
def xdf(raw, ticker: str, n_tickers: int):
    try:
        if n_tickers == 1:
            df = raw.copy()
        else:
            if not isinstance(raw.columns, pd.MultiIndex):
                return None
            lvl0 = raw.columns.get_level_values(0).unique().tolist()
            lvl1 = raw.columns.get_level_values(1).unique().tolist()
            if ticker in lvl1:
                df = raw.xs(ticker, axis=1, level=1)
            elif ticker in lvl0:
                df = raw[ticker].copy()
            else:
                return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        needed = {"Close", "High", "Low", "Open", "Volume"}
        if not needed.issubset(set(df.columns)):
            return None
        df = df.dropna(subset=["Close", "Volume"])
        return df if len(df) >= 3 else None
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════
#  PASO A: PRE-FILTRO RÁPIDO 5min
#  Descarga datos de 5min para TODO el universo.
#  Calcula % cambio reciente SIN timezone math.
#  Retorna top N más activos.
# ══════════════════════════════════════════════════════════════
def prefiltro_5min(universo: list,
                   precio_min: float, precio_max: float,
                   n_max: int = 300,
                   label: str = "") -> pd.DataFrame:
    """
    Descarga datos 5min para todo el universo.
    Calcula:
      - Δ% reciente (últimas 30 velas = ~2.5 horas)
      - Δ% últimas 2 velas (= últimos 10 min)
      - Δ% última vela (= últimos 5 min)
      - RVOL 5min
    Devuelve DataFrame ordenado por actividad.
    """
    resultados = []
    total = len(universo)
    lote  = 100
    pb    = st.progress(0.0, text=f"📡 Pre-filtro 5min {label}...")

    for i in range(0, total, lote):
        chunk = universo[i:i+lote]
        pb.progress(min((i+lote)/total, 1.0),
                    text=f"📡 Pre-filtro: {min(i+lote,total)}/{total}...")
        try:
            raw = yf.download(
                chunk, period="1d", interval="5m",
                group_by="ticker", prepost=True,
                progress=False, auto_adjust=True,
                threads=True, timeout=20
            )
            for t in chunk:
                try:
                    df = xdf(raw, t, len(chunk))
                    if df is None or len(df) < 4:
                        continue
                    precio = float(df["Close"].iloc[-1])
                    if not (precio_min <= precio <= precio_max):
                        continue

                    c1 = float(df["Close"].iloc[-1])
                    c2 = float(df["Close"].iloc[-2])
                    c3 = float(df["Close"].iloc[-3])

                    # Δ% últimos 5 min (última vela)
                    d5m  = (c1 - c2) / max(c2, 1e-9) * 100
                    # Δ% últimos 10 min (2 velas)
                    d10m = (c1 - c3) / max(c3, 1e-9) * 100
                    # Δ% reciente (últimas 30 velas ~2.5h)
                    lb   = min(30, len(df) - 1)
                    cbase= float(df["Close"].iloc[-(lb+1)])
                    drec = (c1 - cbase) / max(cbase, 1e-9) * 100

                    # RVOL 5min
                    vol_ult  = float(df["Volume"].iloc[-1])
                    vol_prom = float(df["Volume"].mean())
                    rvol5    = vol_ult / max(vol_prom, 1)

                    # Acelerando: última vela > anterior
                    v1 = (c1-c2)/max(c2,1e-9)*100
                    v2 = (c2-c3)/max(c3,1e-9)*100
                    acel = v1 > v2

                    # Score de actividad
                    score = (min(abs(d5m),20)/20*35 +
                             min(rvol5,10)/10*30 +
                             (20 if acel and d5m>0 else 0) +
                             min(abs(drec),40)/40*15)

                    resultados.append({
                        "Ticker"   : t,
                        "Precio $" : round(precio, 4),
                        "Δ 5min %" : round(d5m, 2),
                        "Δ 10min %": round(d10m, 2),
                        "Δ Reciente%": round(drec, 2),
                        "RVOL 5m"  : round(rvol5, 1),
                        "Acel"     : "⚡ SÍ" if (acel and d5m>0) else "→ NO",
                        "Score"    : round(score, 1),
                        "Vol"      : int(vol_ult),
                    })
                except Exception:
                    continue
        except Exception:
            continue

    pb.empty()
    if not resultados:
        return pd.DataFrame()

    df_r = pd.DataFrame(resultados)
    df_r = df_r.sort_values("Score", ascending=False).reset_index(drop=True)
    return df_r.head(n_max)

# ══════════════════════════════════════════════════════════════
#  SUPERTREND
# ══════════════════════════════════════════════════════════════
def supertrend(df, per=10, mult=3.0):
    try:
        h = df["H"]; l = df["L"]; c = df["C"]
        n = len(df)
        if n < per + 2:
            df["st_dir"] = 1; df["st_val"] = c*0.98; df["st_cross"] = 0
            return df
        hl = h-l
        hc = (h-c.shift(1)).abs()
        lc = (l-c.shift(1)).abs()
        atr = pd.concat([hl,hc,lc],axis=1).max(axis=1).rolling(per).mean()
        mid = (h+l)/2
        ubr = mid+mult*atr; lbr = mid-mult*atr
        ub = ubr.copy(); lb = lbr.copy()
        for i in range(1,n):
            ub.iloc[i] = min(ubr.iloc[i],ub.iloc[i-1]) if c.iloc[i-1]<=ub.iloc[i-1] else ubr.iloc[i]
            lb.iloc[i] = max(lbr.iloc[i],lb.iloc[i-1]) if c.iloc[i-1]>=lb.iloc[i-1] else lbr.iloc[i]
        d = pd.Series(1.0, index=df.index)
        for i in range(1,n):
            if d.iloc[i-1]==1:
                d.iloc[i] = 1 if c.iloc[i]>=lb.iloc[i] else -1
            else:
                d.iloc[i] = -1 if c.iloc[i]<=ub.iloc[i] else 1
        df["st_dir"]   = d.values
        df["st_val"]   = np.where(d==1, lb.values, ub.values)
        df["st_cross"] = (d!=d.shift(1)).fillna(False).astype(int).values
        return df
    except Exception:
        df["st_dir"]=1; df["st_val"]=df.get("C",df["Close"])*0.98; df["st_cross"]=0
        return df

# ══════════════════════════════════════════════════════════════
#  INDICADORES TÉCNICOS 1min
# ══════════════════════════════════════════════════════════════
def indicadores(df_raw, st_per, st_mult):
    try:
        df = df_raw.copy()
        def ts(col):
            x = pd.to_numeric(df[col], errors="coerce").squeeze()
            return x.iloc[:,0] if isinstance(x, pd.DataFrame) else x
        C,H,L,O,V = ts("Close"),ts("High"),ts("Low"),ts("Open"),ts("Volume").fillna(0)
        df["C"]=C.values; df["H"]=H.values; df["L"]=L.values
        df["O"]=O.values; df["V"]=V.values
        n = len(df)
        if n < 3: return None

        df["e9"]  = df["C"].ewm(span=min(9,n),  adjust=False).mean()
        df["e20"] = df["C"].ewm(span=min(20,n), adjust=False).mean()
        tp = (df["H"]+df["L"]+df["C"])/3
        cv = df["V"].cumsum()
        df["vwap"] = np.where(cv>0,(tp*df["V"]).cumsum()/cv, df["C"])

        d  = df["C"].diff()
        g  = d.where(d>0,0.0).rolling(min(14,n)).mean()
        ls = (-d.where(d<0,0.0)).rolling(min(14,n)).mean()
        df["rsi"] = (100-100/(1+g/ls.replace(0,np.nan))).fillna(50)

        df["macd"]   = (df["C"].ewm(span=min(12,n),adjust=False).mean()
                       -df["C"].ewm(span=min(26,n),adjust=False).mean())
        df["macd_s"] = df["macd"].ewm(span=min(9,n),adjust=False).mean()
        df["macd_h"] = df["macd"]-df["macd_s"]

        hl = df["H"]-df["L"]
        hc = (df["H"]-df["C"].shift(1)).abs()
        lc = (df["L"]-df["C"].shift(1)).abs()
        df["atr"] = (pd.concat([hl,hc,lc],axis=1).max(axis=1)
                       .rolling(min(14,n)).mean().fillna(df["C"]*0.01))
        w = min(20,n)
        df["sup"] = df["L"].rolling(w).min().fillna(df["C"]*0.97)
        df["res"] = df["H"].rolling(w).max().fillna(df["C"]*1.03)

        # RVOL corregido
        wv = min(10, n-1)
        vavg = df["V"].rolling(wv).mean() if wv>=2 else pd.Series(df["V"].mean(), index=df.index)
        vavg = vavg.fillna(df["V"].mean()).replace(0, df["V"].mean()).replace(0, 1)
        df["vavg"] = vavg
        df["rvol"] = df["V"] / df["vavg"]

        df["v1"] = df["C"].pct_change(1)*100
        df["v2"] = df["C"].pct_change(2)*100
        df["v3"] = df["C"].pct_change(3)*100
        df["ac"] = df["v1"]-df["v1"].shift(1)

        df = supertrend(df, st_per, st_mult)
        return df
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════
#  MOTOR DE SEÑAL — SCORE 1-10
# ══════════════════════════════════════════════════════════════
def gv(row, col, default=0.0):
    try:
        v = float(row[col])
        return default if (np.isnan(v) or np.isinf(v)) else v
    except Exception:
        return default

def motor(df, session, cambio_dia, es_yahoo, chg_5m):
    if df is None or len(df) < 3:
        return 1,1,"⚪ NEUTRO",{},0.0,0.0,1

    a = df.iloc[-1]
    p = df.iloc[-2] if len(df)>1 else df.iloc[-1]
    precio = gv(a,"C")
    if precio <= 0: return 1,1,"⚪ NEUTRO",{},0.0,0.0,1

    up = dn = 0.0
    det = {}

    # 1. RVOL (22%)
    rv = gv(a,"rvol",1)
    if rv>=10:   up+=2.2; det["RVOL"]=f"🔥🔥🔥 {rv:.1f}x EXPLOSIVO"
    elif rv>=5:  up+=1.8; det["RVOL"]=f"🔥🔥 {rv:.1f}x Muy alto"
    elif rv>=2.5:up+=1.2; det["RVOL"]=f"🔥 {rv:.1f}x Elevado"
    elif rv>=1.3:up+=0.6; det["RVOL"]=f"▲ {rv:.1f}x Sobre promedio"
    else:        det["RVOL"]=f"→ {rv:.1f}x Normal"

    # 2. VELOCIDAD 1min (22%)
    v1 = gv(a,"v1")
    if v1>=3:    up+=2.2; det["VEL"]=f"🚀🚀 {v1:+.2f}%/min COHETE"
    elif v1>=1:  up+=1.6; det["VEL"]=f"🚀 {v1:+.2f}%/min Fuerte"
    elif v1>=0.2:up+=0.9; det["VEL"]=f"▲ {v1:+.2f}%/min Positivo"
    elif v1>=0.03:up+=0.3;det["VEL"]=f"▲ {v1:+.2f}%/min Leve"
    elif v1<=-3: dn+=2.2; det["VEL"]=f"💥 {v1:+.2f}%/min CAÍDA"
    elif v1<=-1: dn+=1.6; det["VEL"]=f"▼▼ {v1:+.2f}%/min Bajando"
    elif v1<=-0.03:dn+=0.5;det["VEL"]=f"▼ {v1:+.2f}%/min Leve baja"
    else:        det["VEL"]=f"→ {v1:+.2f}%/min Plano"

    # 3. ACELERACIÓN (18%)
    va,vb = gv(a,"v1"),gv(p,"v1")
    if va>0 and vb>=0 and va>vb:
        up+=1.8; det["ACEL"]=f"⚡ Acelerando {vb:+.2f}%→{va:+.2f}%"
    elif va>0 and va>vb:
        up+=0.9; det["ACEL"]=f"▲ Vel subiendo {vb:+.2f}%→{va:+.2f}%"
    elif va<0 and vb<=0 and va<vb:
        dn+=1.8; det["ACEL"]=f"⚡ Cayendo {vb:+.2f}%→{va:+.2f}%"
    elif va<0 and va<vb:
        dn+=0.9; det["ACEL"]=f"▼ Caída {vb:+.2f}%→{va:+.2f}%"
    else:
        det["ACEL"]="→ Sin aceleración"

    # 4. SUPERTREND (18%)
    st_dir  = gv(a,"st_dir",1)
    st_val  = gv(a,"st_val",precio)
    st_crux = int(gv(a,"st_cross",0))
    dist    = abs(precio-st_val)/max(precio,1e-9)*100
    if st_dir==1:
        up+=1.8; det["ST"]=f"✅ ALCISTA soporte ${st_val:.4f} ({dist:.1f}%↓)"
        if st_crux: up+=1.4; det["ST"]+=" 🔔 CRUCE ALCISTA"
    else:
        dn+=1.8; det["ST"]=f"❌ BAJISTA resist ${st_val:.4f} ({dist:.1f}%↑)"
        if st_crux: dn+=1.4; det["ST"]+=" 🔔 CRUCE BAJISTA"

    # 5. TÉCNICO (10%)
    vwap=gv(a,"vwap",precio); e9=gv(a,"e9",precio); e20=gv(a,"e20",precio)
    rsi=gv(a,"rsi",50); mh=gv(a,"macd_h",0); mhp=gv(p,"macd_h",0)
    pts = ((0.3 if precio>vwap else 0)+(0.3 if e9>e20 else 0)+
           (0.3 if mh>mhp and mh>0 else 0)+(0.2 if 50<rsi<80 else 0)+
           (-0.3 if rsi>=80 or rsi<=20 else 0))
    if pts>=0.7:   up+=1.0; det["TEC"]=f"▲▲ Alcista (RSI={rsi:.0f},VWAP✓,EMA✓)"
    elif pts>=0.3: up+=0.5; det["TEC"]=f"▲ Parcial (RSI={rsi:.0f})"
    elif pts<=-0.2:dn+=0.5; det["TEC"]=f"▼ Bajista (RSI={rsi:.0f})"
    else:          det["TEC"]=f"→ Neutro (RSI={rsi:.0f})"

    # 6. BONUS: Yahoo Top Gainer (10%)
    if es_yahoo:
        if cambio_dia>=50:   up+=2.0; det["YAHOO"]=f"🏆🏆 TOP GAINER {cambio_dia:+.1f}%"
        elif cambio_dia>=20: up+=1.5; det["YAHOO"]=f"🏆 Top Gainer {cambio_dia:+.1f}%"
        elif cambio_dia>=5:  up+=1.0; det["YAHOO"]=f"▲ Gainer fuerte {cambio_dia:+.1f}%"
        else:                up+=0.5; det["YAHOO"]=f"▲ Gainer {cambio_dia:+.1f}%"

    # 7. BONUS: Momentum 5min (10%)
    if chg_5m>=5:   up+=1.5; det["5MIN"]=f"🔥 +{chg_5m:.2f}% en 5min TOP"
    elif chg_5m>=2: up+=1.0; det["5MIN"]=f"⚡ +{chg_5m:.2f}% en 5min"
    elif chg_5m>=0.5:up+=0.4;det["5MIN"]=f"▲ +{chg_5m:.2f}% en 5min"
    elif chg_5m!=0:  det["5MIN"]=f"→ {chg_5m:+.2f}% en 5min"

    # 8. Patrón velas
    c1=gv(df.iloc[-1],"C"); o1=gv(df.iloc[-1],"O",c1)
    c2=gv(df.iloc[-2],"C",c1) if len(df)>1 else c1
    o2=gv(df.iloc[-2],"O",c2) if len(df)>1 else c2
    c3=gv(df.iloc[-3],"C",c2) if len(df)>2 else c2
    o3=gv(df.iloc[-3],"O",c3) if len(df)>2 else c3
    if (c1>o1)and(c2>o2)and(c3>o3)and(c1>c2>c3):
        up+=0.8; det["VELAS"]="🟢🟢🟢 3 verdes"
    elif (c1>o1)and(c2>o2)and(c1>c2):
        up+=0.4; det["VELAS"]="🟢🟢 2 verdes"
    elif (c1<o1)and(c2<o2)and(c3<o3)and(c1<c2<c3):
        dn+=0.8; det["VELAS"]="🔴🔴🔴 3 rojas"
    elif (c1<o1)and(c2<o2):
        dn+=0.4; det["VELAS"]="🔴🔴 2 rojas"
    else:
        det["VELAS"]="→ Sin patrón"

    mx = 2.2+2.2+1.8+3.2+1.0+2.0+1.5+0.8
    su = max(1,min(10,round(max(up,0)/mx*10)))
    sd = max(1,min(10,round(max(dn,0)/mx*10)))

    if   su>=9: senal="🚀 DESPEGUE — COMPRA AHORA"
    elif su>=7: senal="⚡ EXPLOSIÓN ALCISTA"
    elif su>=5: senal="📈 IMPULSO ALCISTA"
    elif sd>=9: senal="💥 CAÍDA FUERTE"
    elif sd>=7: senal="📉 SEÑAL BAJISTA"
    elif sd>=5: senal="▼ BAJISTA"
    else:       senal="⚪ NEUTRO"

    return su,sd,senal,det,rv,v1,int(st_dir)

# ══════════════════════════════════════════════════════════════
#  SL / TP DINÁMICO
# ══════════════════════════════════════════════════════════════
def sltp(df, precio, senal, msl, mtp):
    try:
        a=df.iloc[-1]
        atr=gv(a,"atr",precio*0.015)
        sup=gv(a,"sup",precio*0.97); res=gv(a,"res",precio*1.03)
        stv=gv(a,"st_val",0)
        if sup<=0 or sup>=precio: sup=precio*0.97
        if res<=0 or res<=precio: res=precio*1.03
        alc = any(x in senal for x in ["DESPEGUE","COMPRA","ALCISTA","IMPULSO","EXPLOS"])
        if alc:
            sl = max(precio-atr*msl, sup*0.998)
            if 0<stv<precio: sl=max(sl,stv*0.997)
            sl=round(sl,4); tp=round(min(precio+atr*mtp,res*0.999),4)
        else:
            sl=round(min(precio+atr*msl,res*1.002),4)
            tp=round(max(precio-atr*mtp,sup*1.001),4)
        if sl<=0: sl=round(precio*0.97,4)
        if tp<=0: tp=round(precio*1.06,4)
        rr=round(abs(tp-precio)/max(abs(precio-sl),1e-9),2)
        return sl,tp,rr
    except Exception:
        return round(precio*0.97,4),round(precio*1.06,4),2.0

# ══════════════════════════════════════════════════════════════
#  ESCANEO FINAL 1min
# ══════════════════════════════════════════════════════════════
def escanear_1min(candidatos: dict,
                  precio_min, precio_max,
                  rvol_min, vel_min,
                  msl, mtp, session,
                  st_per, st_mult, top_n) -> pd.DataFrame:
    """
    candidatos: {ticker: {"cambio_dia":float, "es_yahoo":bool, "chg_5m":float}}
    """
    if not candidatos: return pd.DataFrame()

    tickers = list(candidatos.keys())
    res = []; total=len(tickers); lote=50; dfs={}
    pb = st.progress(0.0, text="⚡ Descargando datos 1min...")

    for i in range(0,total,lote):
        chunk=tickers[i:i+lote]
        pb.progress(min((i+lote)/total*0.45,0.45),
                    text=f"📡 1min {min(i+lote,total)}/{total}...")
        try:
            raw=yf.download(chunk,period="1d",interval="1m",
                            group_by="ticker",prepost=True,
                            progress=False,auto_adjust=True,
                            threads=True,timeout=25)
            for t in chunk:
                dfs[t]=xdf(raw,t,len(chunk))
        except Exception:
            for t in chunk:
                try:
                    s=yf.download(t,period="1d",interval="1m",
                                  prepost=True,progress=False,
                                  auto_adjust=True,threads=False,timeout=12)
                    dfs[t]=xdf(s,t,1)
                except Exception:
                    dfs[t]=None

    for idx,t in enumerate(tickers):
        pb.progress(0.45+(idx+1)/total*0.55,
                    text=f"🔬 {t} ({idx+1}/{total})...")
        try:
            raw_df=dfs.get(t)
            if raw_df is None or len(raw_df)<5: continue
            df=indicadores(raw_df,st_per,st_mult)
            if df is None: continue
            precio=float(df["C"].iloc[-1])
            if not (precio_min<=precio<=precio_max): continue

            rv  = float(df["rvol"].iloc[-1]) if not np.isnan(df["rvol"].iloc[-1]) else 1.0
            vel1= float(df["v1"].iloc[-1])   if not np.isnan(df["v1"].iloc[-1])   else 0.0

            info     = candidatos.get(t,{})
            cd       = info.get("cambio_dia",0.0)
            es_yahoo = info.get("es_yahoo",False)
            chg5     = info.get("chg_5m",0.0)

            # Filtros adaptativos
            if es_yahoo or chg5>=2.0:
                pasa=(rv>=max(1.0,rvol_min*0.25)) or (abs(vel1)>=max(0.01,vel_min*0.15))
            elif session=="REGULAR":
                pasa=(rv>=rvol_min) and (abs(vel1)>=vel_min)
            else:
                pasa=(rv>=max(1.1,rvol_min*0.4)) or (abs(vel1)>=max(0.02,vel_min*0.25))
            if not pasa: continue

            su,sd,senal,det,rv,vel1,st_dir=motor(df,session,cd,es_yahoo,chg5)

            if session=="REGULAR" and not es_yahoo and chg5<1.0 and su<3 and sd<3:
                continue

            _sl,_tp,rr=sltp(df,precio,senal,msl,mtp)
            open_d=float(df["O"].iloc[0]) if float(df["O"].iloc[0])>0 else precio
            cd_real=(precio-open_d)/max(open_d,1e-9)*100
            rsi=float(df["rsi"].iloc[-1])
            sup=float(df["sup"].iloc[-1]); res_=float(df["res"].iloc[-1])
            vel2=float(df["v2"].iloc[-1]) if not np.isnan(df["v2"].iloc[-1]) else 0
            ac=float(df["ac"].iloc[-1])   if not np.isnan(df["ac"].iloc[-1]) else 0
            stv=float(df["st_val"].iloc[-1]) if "st_val" in df.columns else 0
            st_tx="🟢 ALCISTA" if st_dir==1 else "🔴 BAJISTA"

            if   es_yahoo and chg5>=2: fuente="🏆🔥 Yahoo+5min"
            elif es_yahoo:             fuente="🏆 Yahoo"
            elif chg5>=2:              fuente="🔥 5min"
            else:                      fuente="📋 Universo"

            res.append({
                "Ticker"    :t,
                "Fuente"    :fuente,
                "Precio $"  :round(precio,4),
                "RVOL"      :round(rv,1),
                "Vel 1m %"  :round(vel1,2),
                "Vel 2m %"  :round(vel2,2),
                "Δ 5m %"    :round(chg5,2),
                "Acel"      :round(ac,3),
                "Supertrend":st_tx,
                "ST $"      :round(stv,4),
                "Δ Día %"   :round(cd if cd!=0 else cd_real,2),
                "Score 🐂"  :su,
                "Score 🐻"  :sd,
                "Señal"     :senal,
                "RSI"       :round(rsi,1),
                "Soporte $" :round(sup,4),
                "Resist $"  :round(res_,4),
                "SL $"      :_sl,
                "TP $"      :_tp,
                "R:R"       :rr,
                "_det"      :det,
                "_df"       :df,
            })
        except Exception:
            continue

    pb.empty()
    if not res: return pd.DataFrame()

    df_r=pd.DataFrame(res)
    pmap={"🏆🔥 Yahoo+5min":0,"🏆 Yahoo":1,"🔥 5min":2,"📋 Universo":3}
    df_r["_p"]=df_r["Fuente"].map(pmap).fillna(4)
    df_r=df_r.sort_values(["_p","Score 🐂","RVOL","Vel 1m %"],
                           ascending=[True,False,False,False])
    return df_r.drop(columns=["_p"]).reset_index(drop=True).head(top_n)

# ══════════════════════════════════════════════════════════════
#  ALPACA HELPERS
# ══════════════════════════════════════════════════════════════
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
            symbol=sym,qty=qty,side=OrderSide.BUY,time_in_force=TimeInForce.GTC,
            take_profit=TakeProfitRequest(limit_price=round(float(tp),2)),
            stop_loss=StopLossRequest(stop_price=round(float(sl),2))))
        return True,f"✅ BUY {qty}x {sym} SL=${sl} TP=${tp}"
    except Exception as e: return False,f"❌ {e}"
def sell(sym,qty):
    try:
        alpaca.submit_order(MarketOrderRequest(
            symbol=sym,qty=qty,side=OrderSide.SELL,time_in_force=TimeInForce.GTC))
        return True,f"✅ SELL {qty}x {sym}"
    except Exception as e: return False,f"❌ {e}"

# ══════════════════════════════════════════════════════════════
#  ENCABEZADO
# ══════════════════════════════════════════════════════════════
st.markdown('<h1 class="hdr">⚡ THUNDER RADAR V97</h1>',unsafe_allow_html=True)
st.markdown('<p class="sub">UNIVERSO COMPLETO · YAHOO TOP GAINERS · MOMENTUM 5MIN · SUPERTREND · ALPACA PAPER</p>',
            unsafe_allow_html=True)

bm={"REGULAR":"b-reg","PRE-MARKET":"b-pre","AFTER-HOURS":"b-aft","CERRADO":"b-cls"}
tz_et=pytz.timezone("US/Eastern")
hora_et=datetime.now(tz_et).strftime("%H:%M:%S ET")
cuenta=get_cuenta()

h1,h2,h3=st.columns(3)
with h1:
    st.markdown(f'<span class="badge {bm.get(SESSION,"b-cls")}">● {SESSION}</span>'
                f' &nbsp;<span class="dot"></span>'
                f'<span style="color:#8b949e;font-size:.73em">EN VIVO</span>',
                unsafe_allow_html=True)
with h2:
    st.markdown(f'<span style="color:#8b949e">🕐 {hora_et}</span>',unsafe_allow_html=True)
with h3:
    if cuenta:
        eq=float(cuenta.equity); pnl=eq-float(cuenta.last_equity)
        col="#00ff88" if pnl>=0 else "#ff4444"
        st.markdown(f'<span style="color:{col}">💰 ${eq:,.2f} | P&L {pnl:+,.2f}</span>',
                    unsafe_allow_html=True)

st.markdown("""<div class="ibox">
<b style="color:#00ff88">V97 — UNIVERSO COMPLETO:</b>
Combina <b>Twelve Data (5,000+ acciones)</b> +
<b>Yahoo Finance Top Gainers (tiempo real)</b> +
<b>Detector Momentum 5min (Webull style)</b> +
<b>Motor de señal 1min con Supertrend + RVOL corregido</b> +
<b>SL/TP dinámico automático → Alpaca Paper</b>
</div>""",unsafe_allow_html=True)
st.markdown('<hr class="n">',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  BARRA LATERAL
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ CONFIGURACIÓN")
    precio_min_f=st.number_input("Precio Mín $",value=0.05,step=0.05,min_value=0.01)
    precio_max_f=st.number_input("Precio Máx $",value=500.0,step=10.0)
    st.markdown("**⚡ Motor de Aceleración**")
    dflt_rv=1.2 if SESSION in("PRE-MARKET","AFTER-HOURS","CERRADO") else 1.5
    dflt_vl=0.05 if SESSION in("PRE-MARKET","AFTER-HOURS","CERRADO") else 0.10
    rvol_min=st.slider("RVOL mínimo",1.0,15.0,dflt_rv,0.1)
    vel_min =st.slider("Velocidad mín %/vela",0.0,3.0,dflt_vl,0.01)
    st.markdown("**📊 Supertrend**")
    st_per =st.slider("Período",5,20,10,1)
    st_mult=st.slider("Multiplicador ATR",1.0,5.0,3.0,0.5)
    st.markdown("**🔥 Detector 5min**")
    min_chg5=st.slider("Δ% mínimo para 5min",0.5,10.0,2.0,0.5)
    n_prefiltro=st.slider("Candidatos del pre-filtro",100,500,250,50,
                          help="De los 5,000+ stocks, cuántos pasar al escaneo 1min")
    top_n_f=st.slider("Resultados finales",10,80,50,5)
    st.markdown("**🔒 SL / TP**")
    atr_sl=st.slider("ATR × Stop Loss",0.5,5.0,2.0,0.5)
    atr_tp=st.slider("ATR × Take Profit",1.0,8.0,4.0,0.5)
    st.markdown("---")
    tickers_extra=st.text_area("Tickers extra (manual)",
                                "SDOT,BLZE,CLRB,STRL,BIYA,JLHL,NXTS,MRDN",height=55)
    st.markdown("---")
    modo_auto=st.toggle("🤖 Auto-Trade",value=False)
    if modo_auto:
        auto_score=st.slider("Score mín",6,10,7)
        auto_qty=st.number_input("Acciones/orden",value=1,min_value=1)
        max_pos=st.number_input("Máx posiciones",value=3,min_value=1)
        st.warning("⚠️ Ejecuta órdenes en Paper.")
    auto_ref=st.toggle("🔁 Auto-escaneo",value=False)
    ref_seg=45 if SESSION=="REGULAR" else 60

# ══════════════════════════════════════════════════════════════
#  ESTADO
# ══════════════════════════════════════════════════════════════
for k,v in [("universo",RESPALDO),("yahoo_data",{}),
            ("prefiltro_df",pd.DataFrame()),
            ("candidatos",{}),("df_scan",pd.DataFrame()),
            ("last_scan",None),("last_yahoo",None),
            ("last_prefiltro",None)]:
    if k not in st.session_state:
        st.session_state[k]=v

# ══════════════════════════════════════════════════════════════
#  PASO 1: CARGAR UNIVERSO COMPLETO
# ══════════════════════════════════════════════════════════════
st.subheader("📡 Paso 1 — Universo Completo NYSE+NASDAQ+AMEX (Twelve Data)")

p1a,p1b,p1c=st.columns([2,1,1])
with p1a:
    if st.button("🌐 CARGAR UNIVERSO COMPLETO (5,000+ acciones)",use_container_width=True):
        with st.spinner("🌐 Cargando universo via Twelve Data..."):
            u=cargar_universo_twelve()
            st.session_state.universo=u
            st.session_state.prefiltro_df=pd.DataFrame()
            st.session_state.candidatos={}
        if len(u)>500:
            st.success(f"✅ {len(u):,} acciones cargadas (NYSE+NASDAQ+AMEX)")
        else:
            st.warning(f"⚠️ Solo {len(u)} tickers. Usando lista respaldo.")
with p1b:
    n_u=len(st.session_state.universo)
    c_u="#00ff88" if n_u>500 else "#ffc107"
    st.markdown(f'<span style="color:{c_u}">📊 {n_u:,} stocks</span>',unsafe_allow_html=True)
with p1c:
    if st.button("ℹ️ Usar respaldo",use_container_width=True):
        st.session_state.universo=RESPALDO
        st.rerun()

# Añadir extras manuales al universo
extras=[x.strip().upper() for x in tickers_extra.split(",") if x.strip()]
universo_final=list(dict.fromkeys(st.session_state.universo+extras))

st.markdown('<hr class="n">',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PASO 2: YAHOO FINANCE TOP GAINERS
# ══════════════════════════════════════════════════════════════
st.subheader("🏆 Paso 2 — Top Gainers Yahoo Finance (tiempo real)")

p2a,p2b=st.columns([3,1])
with p2a:
    if st.button("🏆 OBTENER TOP GAINERS YAHOO (= Webull Top Gainers)",use_container_width=True):
        with st.spinner("🏆 Conectando a Yahoo Finance..."):
            yd=obtener_yahoo_gainers()
            st.session_state.yahoo_data=yd
            st.session_state.last_yahoo=time.time()
        c1_,c2_,c3_=st.columns(3)
        c1_.markdown(f'<span style="color:{"#00ff88" if yd["n_day"]>0 else "#ff4444"}">'
                     f'{"✅" if yd["n_day"]>0 else "❌"} Día: {yd["n_day"]}</span>',
                     unsafe_allow_html=True)
        c2_.markdown(f'<span style="color:{"#00ff88" if yd["n_active"]>0 else "#ff4444"}">'
                     f'{"✅" if yd["n_active"]>0 else "❌"} Activos: {yd["n_active"]}</span>',
                     unsafe_allow_html=True)
        c3_.markdown(f'<span style="color:{"#00ff88" if yd["n_small"]>0 else "#ff4444"}">'
                     f'{"✅" if yd["n_small"]>0 else "❌"} Small: {yd["n_small"]}</span>',
                     unsafe_allow_html=True)
        if yd["n_total"]>0:
            st.success(f"✅ {yd['n_total']} stocks de Yahoo Finance obtenidos")
        else:
            st.warning("⚠️ Yahoo no respondió. El universo completo se usará igualmente.")
with p2b:
    n_yd=len(st.session_state.yahoo_data.get("todos",[]))
    ts_y=""
    if st.session_state.last_yahoo:
        ts_y=datetime.fromtimestamp(st.session_state.last_yahoo)\
                     .astimezone(tz_et).strftime("%H:%M ET")
    col_y="#00ff88" if n_yd>0 else "#8b949e"
    st.markdown(f'<span style="color:{col_y}">🏆 {n_yd} | {ts_y}</span>',unsafe_allow_html=True)

if st.session_state.yahoo_data.get("todos"):
    yt=st.session_state.yahoo_data["todos"]
    st.markdown(f'<div class="ibox" style="color:#00ff88">'
                f'<b>Yahoo Top:</b> {" · ".join(yt[:30])}{"..." if len(yt)>30 else ""}</div>',
                unsafe_allow_html=True)

st.markdown('<hr class="n">',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PASO 3: PRE-FILTRO 5min SOBRE TODO EL UNIVERSO
# ══════════════════════════════════════════════════════════════
st.subheader("🔥 Paso 3 — Pre-filtro 5min sobre todo el universo (como Webull 5min)")

p3a,p3b=st.columns([3,1])
with p3a:
    if st.button(f"🔥 DETECTAR MOMENTUM 5MIN ({len(universo_final):,} stocks)",
                 use_container_width=True):
        st.markdown(f"**Analizando {len(universo_final):,} acciones con datos de 5min...**")
        df_pf=prefiltro_5min(universo_final,precio_min_f,precio_max_f,n_prefiltro)
        st.session_state.prefiltro_df=df_pf
        st.session_state.last_prefiltro=time.time()
        if not df_pf.empty:
            st.success(f"✅ {len(df_pf)} candidatos con momentum activo")
        else:
            st.warning("⚠️ Sin candidatos. Baja el umbral de precio o amplía el rango.")
with p3b:
    n_pf=len(st.session_state.prefiltro_df)
    ts_pf=""
    if st.session_state.last_prefiltro:
        ts_pf=datetime.fromtimestamp(st.session_state.last_prefiltro)\
                      .astimezone(tz_et).strftime("%H:%M ET")
    col_pf="#ff4500" if n_pf>0 else "#8b949e"
    st.markdown(f'<span style="color:{col_pf}">🔥 {n_pf} | {ts_pf}</span>',unsafe_allow_html=True)

# Mostrar tabla pre-filtro
chg5_map={}
if not st.session_state.prefiltro_df.empty:
    pf=st.session_state.prefiltro_df
    for _,row in pf.iterrows():
        chg5_map[row["Ticker"]]=float(row["Δ 5min %"])

    cols_pf=["Ticker","Precio $","Δ 5min %","Δ 10min %","Δ Reciente%","RVOL 5m","Acel","Score"]
    pf_sh=pf[cols_pf].head(20).copy()
    def cd5(v): return f"color:{'#00ff88' if v>=0 else '#ff4444'};font-weight:bold"
    def cr5(v):
        if v>=5: return "color:#ff4500;font-weight:900"
        elif v>=3: return "color:#ff8c00;font-weight:700"
        elif v>=2: return "color:#ffc107;font-weight:bold"
        else: return "color:#8b949e"
    fmt5={"Precio $":"${:.4f}","Δ 5min %":"{:+.2f}%","Δ 10min %":"{:+.2f}%",
          "Δ Reciente%":"{:+.2f}%","RVOL 5m":"{:.1f}x","Score":"{:.1f}"}
    try:
        st5=(pf_sh.style.map(cd5,subset=["Δ 5min %","Δ 10min %","Δ Reciente%"])
             .map(cr5,subset=["RVOL 5m"]).format(fmt5))
    except Exception:
        try:
            st5=(pf_sh.style.applymap(cd5,subset=["Δ 5min %","Δ 10min %","Δ Reciente%"])
                 .applymap(cr5,subset=["RVOL 5m"]).format(fmt5))
        except Exception:
            st5=pf_sh.style.format(fmt5)
    st.dataframe(st5,use_container_width=True,hide_index=True,height=280)

st.markdown('<hr class="n">',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  CONSTRUIR CANDIDATOS COMBINADOS
# ══════════════════════════════════════════════════════════════
def construir_candidatos():
    """
    Combina Yahoo Top Gainers + Pre-filtro 5min + Universo.
    Retorna dict: {ticker: {"cambio_dia":float, "es_yahoo":bool, "chg_5m":float}}
    """
    cands={}

    # Yahoo top gainers (prioridad 1)
    for t in st.session_state.yahoo_data.get("todos",[]):
        cands[t]={"cambio_dia":0.0,"es_yahoo":True,"chg_5m":chg5_map.get(t,0.0)}

    # Pre-filtro 5min (prioridad 2)
    if not st.session_state.prefiltro_df.empty:
        for _,row in st.session_state.prefiltro_df.iterrows():
            t=row["Ticker"]
            if t not in cands:
                cands[t]={"cambio_dia":0.0,"es_yahoo":False,"chg_5m":float(row["Δ 5min %"])}
            else:
                cands[t]["chg_5m"]=float(row["Δ 5min %"])

    # Extras manuales
    for t in extras:
        if t not in cands:
            cands[t]={"cambio_dia":0.0,"es_yahoo":False,"chg_5m":chg5_map.get(t,0.0)}

    # Si hay muy pocos candidatos, añadir del universo completo
    if len(cands) < 50:
        for t in universo_final[:200]:
            if t not in cands:
                cands[t]={"cambio_dia":0.0,"es_yahoo":False,"chg_5m":0.0}

    return cands

# ══════════════════════════════════════════════════════════════
#  PORTAFOLIO
# ══════════════════════════════════════════════════════════════
st.subheader("💼 Portafolio Activo — P&L en Tiempo Real")
posiciones=get_pos()
if posiciones:
    rows=[]
    for p in posiciones:
        pp=float(p.unrealized_plpc)*100; pu=float(p.unrealized_pl)
        ico="🟢" if pp>=0 else "🔴"
        rows.append({"Ticker":p.symbol,"Qty":p.qty,
                     "Entrada $":round(float(p.avg_entry_price),4),
                     "Actual $": round(float(p.current_price),4),
                     "P&L %":f"{ico} {pp:+.2f}%","P&L $":f"${pu:+.2f}",
                     "Valor $":f"${float(p.market_value):,.2f}"})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    px1,px2,px3=st.columns([2,1,1])
    with px1: tc=st.selectbox("Ticker a cerrar",[r["Ticker"] for r in rows])
    with px2:
        if st.button("🔴 Cerrar pos."):
            ok,msg=cerrar(tc); st.success(msg) if ok else st.error(msg)
    with px3:
        if st.button("🔴 Cerrar TODO"):
            [cerrar(p.symbol) for p in posiciones]; st.warning("Cerrando...")
else:
    st.info("Sin posiciones. ¡Detecta el despegue! 🚀")

st.markdown('<hr class="n">',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PASO 4: ESCANEO FINAL 1min
# ══════════════════════════════════════════════════════════════
st.subheader("🔭 Paso 4 — Motor de Señal 1min (Supertrend + RVOL + Aceleración)")

candidatos=construir_candidatos()
n_cands=len(candidatos)
n_yahoo_c=sum(1 for v in candidatos.values() if v.get("es_yahoo"))
n_5m_c=sum(1 for v in candidatos.values() if v.get("chg_5m",0)>=2)

sb1,sb2,sb3=st.columns([2,1,1])
with sb1:
    iniciar=st.button(f"🚀 INICIAR ESCANEO FINAL ({n_cands} candidatos)",
                      use_container_width=True)
with sb2:
    if st.button("🔄 Refresh UI",use_container_width=True): st.rerun()
with sb3:
    if st.session_state.last_scan:
        ts_s=datetime.fromtimestamp(st.session_state.last_scan)\
                     .astimezone(tz_et).strftime("%H:%M:%S ET")
        st.markdown(f'<span style="color:#8b949e;font-size:.73em">Último:{ts_s}</span>',
                    unsafe_allow_html=True)

st.markdown(f"⚡ **{n_cands} candidatos** | "
            f"🏆 {n_yahoo_c} Yahoo | 🔥 {n_5m_c} con 5min activo | "
            f"Sesión: **{SESSION}** | RVOL≥{rvol_min}x | Vel≥{vel_min}%")

debe=(iniciar or
      (auto_ref and st.session_state.last_scan is not None and
       (time.time()-st.session_state.last_scan)>=ref_seg))

if debe:
    if not candidatos:
        st.error("❌ Sin candidatos. Completa los pasos 1, 2 y 3 primero.")
    else:
        with st.spinner("⚡ Motor de señal corriendo..."):
            df_scan=escanear_1min(
                candidatos,precio_min_f,precio_max_f,
                rvol_min,vel_min,atr_sl,atr_tp,
                SESSION,st_per,st_mult,top_n_f)
        st.session_state.df_scan=df_scan
        st.session_state.last_scan=time.time()
        ts_ok=datetime.now(tz_et).strftime("%H:%M:%S ET")
        n=len(df_scan)
        if n>0:
            ny=len(df_scan[df_scan["Fuente"].str.contains("Yahoo",na=False)])
            n5=len(df_scan[df_scan["Fuente"].str.contains("5min",na=False)])
            st.success(f"✅ {ts_ok} — **{n} señales** "
                       f"(🏆 {ny} Yahoo · 🔥 {n5} 5min · 📋 {n-ny-n5} universo)")
        else:
            st.warning(f"⚠️ {ts_ok} — Sin señales. "
                       "Baja RVOL a 1.0x y Velocidad a 0.0%. "
                       "Completa los pasos 2 y 3 para tener mejores candidatos.")

df_scan=st.session_state.df_scan

# ══════════════════════════════════════════════════════════════
#  MOSTRAR RESULTADOS
# ══════════════════════════════════════════════════════════════
if not df_scan.empty:

    despegues=df_scan[df_scan["Score 🐂"]>=7]
    impulsos =df_scan[(df_scan["Score 🐂"]>=5)&(df_scan["Score 🐂"]<7)]

    # Tarjetas de despegue
    if not despegues.empty:
        st.markdown(f"### 🚀 DESPEGUES — {len(despegues)} señales")
        for _,row in despegues.iterrows():
            s  =int(row["Score 🐂"])
            cls="s10" if s==10 else("s8" if s>=8 else "s6")
            rv =float(row["RVOL"])
            vc ="#00ff88" if row["Vel 1m %"]>=0 else "#ff4444"
            d5c="#00ff88" if row["Δ 5m %"]>=0   else "#ff4444"
            dc ="#00ff88" if row["Δ Día %"]>=0   else "#ff4444"
            stc="#00ff88" if "ALCISTA" in str(row["Supertrend"]) else "#ff4444"
            fuente=str(row["Fuente"])
            if "Yahoo" in fuente and "5min" in fuente:
                fb='<span style="background:#7c3aed;color:#fff;padding:1px 7px;border-radius:4px;font-size:.70em">🏆🔥 Yahoo+5min</span>'
                card="card-fire"
            elif "Yahoo" in fuente:
                fb='<span style="background:#1d4ed8;color:#fff;padding:1px 7px;border-radius:4px;font-size:.70em">🏆 Yahoo</span>'
                card="card-fire"
            elif "5min" in fuente:
                fb='<span style="background:#b91c1c;color:#fff;padding:1px 7px;border-radius:4px;font-size:.70em">🔥 5min</span>'
                card="card-5min"
            else:
                fb='<span style="background:#374151;color:#aaa;padding:1px 7px;border-radius:4px;font-size:.70em">📋 Universo</span>'
                card="card-hot"
            rcl=("color:#ff4500;font-weight:900" if rv>=10
                 else("color:#ff8c00;font-weight:700" if rv>=5 else "color:#ffc107"))

            st.markdown(f"""
            <div class="{card}">
              <span class="tkr">⚡ {row['Ticker']}</span>
              &nbsp;{fb}
              &nbsp;&nbsp;<span class="{cls}">{s}/10</span>
              &nbsp;&nbsp;<span style="color:#a78bfa;font-size:.84em">{row['Señal']}</span>
              &nbsp;&nbsp;<span style="color:{stc};font-size:.79em">{row['Supertrend']}</span>
              <br>
              <span class="lbl">Precio</span> <b style="color:#fff">${row['Precio $']}</b>
              &nbsp;|&nbsp;<span class="lbl">RVOL</span> <b style="{rcl}">{rv:.1f}x</b>
              &nbsp;|&nbsp;<span class="lbl">Vel 1min</span> <b style="color:{vc}">{row['Vel 1m %']:+.2f}%</b>
              &nbsp;|&nbsp;<span class="lbl">Vel 2min</span> <b style="color:{vc}">{row['Vel 2m %']:+.2f}%</b>
              &nbsp;|&nbsp;<span class="lbl">Δ 5min</span> <b style="color:{d5c}">{row['Δ 5m %']:+.2f}%</b>
              &nbsp;|&nbsp;<span class="lbl">Δ Día</span> <b style="color:{dc}">{row['Δ Día %']:+.2f}%</b>
              &nbsp;|&nbsp;<span class="lbl">RSI</span> {row['RSI']}
              &nbsp;|&nbsp;<span class="lbl">ST$</span> {row['ST $']}
              <br>
              <span class="lbl">SL</span> <b style="color:#ff6b6b">${row['SL $']}</b>
              &nbsp;|&nbsp;<span class="lbl">TP</span> <b style="color:#00ff88">${row['TP $']}</b>
              &nbsp;|&nbsp;<span class="lbl">R:R</span> {row['R:R']}x
            </div>""",unsafe_allow_html=True)

    # Impulsos
    if not impulsos.empty:
        with st.expander(f"👁️ IMPULSOS EN FORMACIÓN ({len(impulsos)} — score 5-6)"):
            for _,row in impulsos.iterrows():
                vc="#00ff88" if row["Vel 1m %"]>=0 else "#ff4444"
                stc="#00ff88" if "ALCISTA" in str(row["Supertrend"]) else "#ff4444"
                f_=str(row["Fuente"])
                fb="🏆🔥" if("Yahoo" in f_ and "5min" in f_) else("🏆" if "Yahoo" in f_ else("🔥" if "5min" in f_ else "📋"))
                st.markdown(f"""
                <div class="card-watch">
                  <b class="tkr" style="font-size:1.05em">{fb} {row['Ticker']}</b>
                  &nbsp;<span class="s6">{int(row['Score 🐂'])}/10</span>
                  &nbsp;<span style="color:#8b949e;font-size:.77em">{row['Señal']}</span>
                  &nbsp;<span style="color:{stc};font-size:.74em">{row['Supertrend']}</span>
                  &nbsp;|&nbsp;${row['Precio $']}
                  &nbsp;|&nbsp;<b>RVOL</b> {row['RVOL']}x
                  &nbsp;|&nbsp;<b style="color:{vc}">{row['Vel 1m %']:+.2f}%/min</b>
                  &nbsp;|&nbsp;<b>Δ5m</b> {row['Δ 5m %']:+.1f}%
                  &nbsp;|&nbsp;<b>Δ Día</b> {row['Δ Día %']:+.1f}%
                  &nbsp;|&nbsp;<b>RSI</b> {row['RSI']}
                  &nbsp;|&nbsp;<b style="color:#ff6b6b">SL</b>${row['SL $']}
                  &nbsp;<b style="color:#00ff88">TP</b>${row['TP $']}
                </div>""",unsafe_allow_html=True)

    # Tabla completa
    st.markdown("### 📋 Tabla Completa del Radar")
    cols_t=["Ticker","Fuente","Precio $","RVOL","Vel 1m %","Vel 2m %",
            "Δ 5m %","Acel","Supertrend","ST $","Δ Día %",
            "Score 🐂","Score 🐻","Señal","RSI",
            "Soporte $","Resist $","SL $","TP $","R:R"]
    df_sh=df_scan[cols_t].copy()

    def cs(v):
        if v>=8:   return "background-color:#15803d;color:white"
        elif v>=6: return "background-color:#1d4ed8;color:white"
        elif v>=4: return "background-color:#92400e;color:white"
        else:      return "background-color:#7f1d1d;color:white"
    def cv(v): return f"color:{'#00ff88' if v>=0 else '#ff4444'};font-weight:bold"
    def cr(v):
        if v>=10:  return "color:#ff4500;font-weight:900"
        elif v>=5: return "color:#ff8c00;font-weight:700"
        elif v>=2: return "color:#ffc107;font-weight:bold"
        else:      return "color:#8b949e"
    fmt_t={"Precio $":"${:.4f}","RVOL":"{:.1f}x","Vel 1m %":"{:+.2f}%",
           "Vel 2m %":"{:+.2f}%","Δ 5m %":"{:+.2f}%","Acel":"{:+.3f}",
           "ST $":"${:.4f}","Δ Día %":"{:+.2f}%","RSI":"{:.1f}",
           "Soporte $":"${:.4f}","Resist $":"${:.4f}",
           "SL $":"${:.4f}","TP $":"${:.4f}","R:R":"{:.2f}"}
    try:
        styled=(df_sh.style
                .map(cs,subset=["Score 🐂","Score 🐻"])
                .map(cv,subset=["Vel 1m %","Vel 2m %","Δ 5m %","Δ Día %"])
                .map(cr,subset=["RVOL"]).format(fmt_t))
    except Exception:
        try:
            styled=(df_sh.style
                    .applymap(cs,subset=["Score 🐂","Score 🐻"])
                    .applymap(cv,subset=["Vel 1m %","Vel 2m %","Δ 5m %","Δ Día %"])
                    .applymap(cr,subset=["RVOL"]).format(fmt_t))
        except Exception:
            styled=df_sh.style.format(fmt_t)
    st.dataframe(styled,use_container_width=True,hide_index=True,height=430)

    # Auto-trade
    if modo_auto:
        st.markdown("### 🤖 Auto-Trade")
        np_=len(get_pos())
        for _,row in df_scan[df_scan["Score 🐂"]>=auto_score].iterrows():
            if np_>=max_pos: st.warning(f"Máx {max_pos} pos."); break
            ok,msg=buy(row["Ticker"],auto_qty,row["SL $"],row["TP $"])
            if ok: np_+=1
            st.write(msg)

    # Ejecución manual
    st.markdown('<hr class="n">',unsafe_allow_html=True)
    st.markdown("### 🛒 Ejecución Manual")
    ce1,ce2=st.columns([1,2])
    with ce1:
        t_op=st.selectbox("Ticker",df_scan["Ticker"].tolist())
        rsel=df_scan[df_scan["Ticker"]==t_op].iloc[0]
        qty_m=st.number_input("Cantidad",value=1,min_value=1,step=1)
        sl_m=st.number_input("SL $",value=float(rsel["SL $"]),step=0.001,format="%.4f")
        tp_m=st.number_input("TP $",value=float(rsel["TP $"]),step=0.001,format="%.4f")
        b1,b2=st.columns(2)
        with b1:
            if st.button("🟢 COMPRAR",use_container_width=True):
                ok,msg=buy(t_op,qty_m,sl_m,tp_m); st.success(msg) if ok else st.error(msg)
        with b2:
            if st.button("🔴 VENDER",use_container_width=True):
                ok,msg=sell(t_op,qty_m); st.success(msg) if ok else st.error(msg)
    with ce2:
        st.markdown(f"### 📊 {t_op}")
        stc2="#00ff88" if "ALCISTA" in str(rsel["Supertrend"]) else "#ff4444"
        st.markdown(f'<b style="color:{stc2}">{rsel["Supertrend"]}</b> — ST: <b>${rsel["ST $"]}</b>',
                    unsafe_allow_html=True)
        m1,m2_,m3,m4=st.columns(4)
        m1.metric("Precio $",f"${rsel['Precio $']:.4f}")
        m2_.metric("RVOL",f"{rsel['RVOL']:.1f}x")
        m3.metric("Vel 1min",f"{rsel['Vel 1m %']:+.2f}%")
        m4.metric("Score 🐂",f"{rsel['Score 🐂']}/10")
        m5,m6,m7,m8=st.columns(4)
        m5.metric("RSI",f"{rsel['RSI']}")
        m6.metric("SL $",f"${rsel['SL $']:.4f}")
        m7.metric("TP $",f"${rsel['TP $']:.4f}")
        m8.metric("R:R",f"{rsel['R:R']}x")
        m9,m10=st.columns(2)
        m9.metric("Δ 5min",f"{rsel['Δ 5m %']:+.2f}%")
        m10.metric("Δ Día",f"{rsel['Δ Día %']:+.2f}%")
        det=rsel.get("_det",{})
        if det:
            st.markdown("**📌 Motor de señal:**")
            for k,v in det.items():
                c=("#00ff88" if any(x in str(v) for x in ["▲","🚀","⚡","🔥","✅","🟢","🏆"])
                   else("#ff4444" if any(x in str(v) for x in ["▼","💥","❌","🔴"])
                        else "#ffc107"))
                st.markdown(f'<span style="color:{c};font-size:.79em"><b>{k}</b>: {v}</span>',
                            unsafe_allow_html=True)

elif st.session_state.last_scan is not None:
    st.warning("""
    ⚠️ Sin señales. Prueba:
    1. Completa los **Pasos 2 y 3** para tener mejores candidatos
    2. Baja **RVOL mínimo** a **1.0x**
    3. Baja **Velocidad mínima** a **0.0%**
    4. Los Yahoo Top Gainers y activos de 5min siempre pasan con filtros relajados
    """)
else:
    st.markdown("""
    ### 📋 Flujo completo para capturar despegues:

    **Paso 1 — 🌐 Cargar universo** (una vez al día)
    Carga las 5,000+ acciones de NYSE+NASDAQ+AMEX via Twelve Data

    **Paso 2 — 🏆 Yahoo Top Gainers** (cada 10-15 min)
    Trae los stocks que más suben HOY: SDOT +135%, BLZE +62%, CLRB +45%
    Los mismos que Webull Top Gainers 1 Day

    **Paso 3 — 🔥 Detector 5min** (cada 5-10 min)
    Escanea todo el universo y detecta: JLHL +16%, NXTS +16%, MRDN +13%
    Los mismos que Webull % Chg in 5Mins

    **Paso 4 — 🚀 Escaneo final 1min**
    Aplica Supertrend + RVOL + Velocidad + Aceleración sobre los candidatos
    Genera Score 1-10 y SL/TP automático para Alpaca Paper

    > **Repite pasos 2, 3 y 4 cada 5-10 minutos**
    > durante el horario de mercado para no perderte ningún despegue.
    """)

# Auto-refresh
if auto_ref:
    time.sleep(ref_seg)
    st.rerun()

st.markdown('<hr class="n">',unsafe_allow_html=True)
st.markdown("""<div style="text-align:center;color:#8b949e;font-size:.69em;
font-family:'Share Tech Mono',monospace">
⚡ THUNDER RADAR V97 — UNIVERSO COMPLETO — PAPER TRADING — Solo uso educativo<br>
Los resultados pasados no garantizan rendimientos futuros. Opera con responsabilidad.
</div>""",unsafe_allow_html=True)
