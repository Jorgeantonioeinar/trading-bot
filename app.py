"""
╔══════════════════════════════════════════════════════════════════════╗
║       THUNDER RADAR V99 — WEBSOCKET REAL-TIME DEFINITIVO            ║
║                                                                      ║
║  ARQUITECTURA:                                                       ║
║  ┌─────────────────────────────────────────────────────────────┐    ║
║  │  HILO WEBSOCKET (background)    │  STREAMLIT UI (main)      │    ║
║  │  ─────────────────────────────  │  ───────────────────────  │    ║
║  │  StockDataStream (Alpaca)        │  Lee st.session_state    │    ║
║  │  → on_bar() cada vela 1min      │  Muestra alertas         │    ║
║  │  → on_trade() tick-by-tick      │  Sliders dinámicos       │    ║
║  │  → deque rolling 5min           │  Force Meter 1-100       │    ║
║  │  → Detecta spikes inmediatos    │  Auto-refresh 10 seg     │    ║
║  │  → Escribe en shared_state      │  Ejecuta órdenes Alpaca  │    ║
║  └─────────────────────────────────────────────────────────────┘    ║
║                                                                      ║
║  FUENTES:                                                            ║
║  • Alpaca WebSocket (IEX free) → tick-by-tick en tiempo real        ║
║  • Yahoo Finance Screener       → top gainers del día               ║
║  • Twelve Data                  → universo NYSE/NASDAQ/AMEX         ║
║  • Alpaca REST                  → ejecución de órdenes              ║
╚══════════════════════════════════════════════════════════════════════╝
"""

# ─────────────────────────────────────────────────────────────────────
#  IMPORTS
# ─────────────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import numpy as np
import requests
import threading
import asyncio
import time
import json
import warnings
from datetime import datetime, timedelta
from collections import deque
from zoneinfo import ZoneInfo
warnings.filterwarnings("ignore")

# Alpaca Trading
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (LimitOrderRequest, MarketOrderRequest,
                                      TakeProfitRequest, StopLossRequest)
from alpaca.trading.enums import OrderSide, TimeInForce

# Alpaca Data (REST + WebSocket)
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests  import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.live      import StockDataStream

# ─────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚡ THUNDER RADAR V99 — WEBSOCKET",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
html,body,[class*="css"]{background:#020709!important;color:#c9d1d9!important;
    font-family:'Share Tech Mono',monospace;}
h1,h2,h3{font-family:'Orbitron',sans-serif!important;}
.stButton>button{width:100%;border-radius:4px;font-weight:bold;
    font-family:'Orbitron',sans-serif;letter-spacing:1px;
    border:1px solid #30363d;transition:all .2s;}
.stButton>button:hover{transform:translateY(-1px);box-shadow:0 0 16px #ff450066;}
div[data-testid="metric-container"]{background:linear-gradient(135deg,#080d14,#0d1520);
    border:1px solid #1a2535;border-radius:8px;padding:12px;}

/* ALERTA ROJA — WebSocket Spike */
.alerta-roja{background:linear-gradient(135deg,#1a0400,#0d0205);
    border:2px solid #ff0000;border-radius:10px;padding:14px 18px;margin:5px 0;
    animation:alarm .8s infinite;}
@keyframes alarm{
    0%,100%{box-shadow:0 0 10px #ff000044,inset 0 0 10px #ff000011;}
    50%    {box-shadow:0 0 35px #ff000099,inset 0 0 20px #ff000033;}}

/* TARJETAS */
.card-spike{background:linear-gradient(135deg,#1a0800,#0a0f1a);
    border:2px solid #ff4500;border-radius:10px;padding:13px 17px;margin:5px 0;
    box-shadow:0 0 20px #ff450055;}
.card-launch{background:linear-gradient(135deg,#061510,#080d14);
    border:2px solid #00ff88;border-radius:10px;padding:13px 17px;margin:5px 0;
    box-shadow:0 0 16px #00ff8844;}
.card-watch{background:#07090d;border:1px solid #ffc10733;
    border-radius:8px;padding:9px 13px;margin:3px 0;}

/* FORCE METER */
.force-bg{background:#1a1a2e;border-radius:20px;height:24px;
    width:100%;position:relative;overflow:hidden;border:1px solid #333;}
.force-fill{height:100%;border-radius:20px;display:flex;
    align-items:center;justify-content:center;
    font-weight:900;font-size:.82em;color:#000;font-family:'Orbitron',sans-serif;}

/* WEBSOCKET STATUS */
.ws-live{color:#00ff88;font-weight:bold;animation:blink2 1s infinite;}
.ws-off {color:#ff4444;font-weight:bold;}
.ws-conn{color:#ffc107;font-weight:bold;}
@keyframes blink2{0%,100%{opacity:1}50%{opacity:.3}}

/* SCORES */
.s10{color:#00ff88;font-size:1.9em;font-weight:900;font-family:'Orbitron',sans-serif;}
.s8 {color:#39ff14;font-size:1.5em;font-weight:800;}
.s6 {color:#ffc107;font-size:1.3em;font-weight:700;}
.tkr{font-family:'Orbitron',sans-serif;font-size:1.25em;font-weight:900;color:#fff;}
.lbl{color:#8b949e;font-size:.73em;}
.hdr{text-align:center;font-family:'Orbitron',sans-serif;font-size:2.1em;font-weight:900;
    background:linear-gradient(90deg,#ff0000,#ff4500,#ffc107,#00ff88,#00d4ff);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:3px;}
.sub{text-align:center;color:#8b949e;font-size:.75em;letter-spacing:3px;}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:.73em;font-weight:bold;}
.b-reg{background:#15803d;color:#fff;}.b-pre{background:#7c3aed;color:#fff;}
.b-aft{background:#0369a1;color:#fff;}.b-cls{background:#374151;color:#fff;}
.dot{display:inline-block;width:9px;height:9px;background:#ff4500;border-radius:50%;
    margin-right:5px;animation:blink .7s infinite;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.1}}
hr.n{border:none;border-top:1px solid #ff450022;margin:12px 0;}
.ibox{background:#080d14;border:1px solid #1a2535;border-radius:8px;
    padding:10px 14px;margin:6px 0;font-size:.79em;line-height:1.6em;}
.ibox-ok{background:#080d14;border:1px solid #00ff8833;border-radius:8px;
    padding:10px 14px;margin:6px 0;font-size:.79em;}
.despegue-badge{display:inline-block;background:#ff4500;color:#fff;
    padding:2px 8px;border-radius:4px;font-size:.70em;font-weight:bold;margin:1px;}
.ticker-row{padding:6px 10px;margin:2px 0;border-radius:6px;
    background:#0a0c10;border:1px solid #1e2739;}
</style>

<!-- AUDIO ALERT — suena cuando hay spike -->
<audio id="spike-audio" preload="auto">
  <source src="data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAA..." type="audio/wav">
</audio>
<script>
function playSpike() {
  // Beep sintético usando AudioContext (funciona sin archivo externo)
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.setValueAtTime(1100, ctx.currentTime + 0.1);
    osc.frequency.setValueAtTime(880, ctx.currentTime + 0.2);
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
    osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.5);
  } catch(e) {}
}
// Chequea cada 2 segundos si hay nueva alerta
setInterval(function() {
  const el = document.getElementById('spike-trigger');
  if (el && el.dataset.trigger === '1') {
    playSpike();
    el.dataset.trigger = '0';
  }
}, 2000);
</script>
<div id="spike-trigger" data-trigger="0" style="display:none"></div>
""", unsafe_allow_html=True)

ET = ZoneInfo("America/New_York")

# ─────────────────────────────────────────────────────────────────────
#  API KEYS (st.secrets con fallback)
# ─────────────────────────────────────────────────────────────────────
def get_keys():
    try:
        ak = st.secrets["alpaca"]["key"]
        as_ = st.secrets["alpaca"]["secret"]
    except Exception:
        ak  = "PKOKUMRZBCA2YJKVZIATSPGV5J"
        as_ = "2UBriZpW7NooR1EvtowC63GcarFt7rEQFD9ofti9Ah6N"
    try:
        td = st.secrets["twelve"]["key"]
    except Exception:
        td = ""
    return ak, as_, td

ALPACA_KEY, ALPACA_SECRET, TWELVE_KEY = get_keys()

# ─────────────────────────────────────────────────────────────────────
#  CLIENTES ALPACA
# ─────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_trading():
    return TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)

@st.cache_resource
def get_data_client():
    return StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)

trading = get_trading()
data_cl = get_data_client()

# ─────────────────────────────────────────────────────────────────────
#  SESIÓN DE MERCADO
# ─────────────────────────────────────────────────────────────────────
def get_session():
    h = datetime.now(ET).hour + datetime.now(ET).minute / 60.0
    if   4.0  <= h < 9.5:  return "PRE-MARKET"
    elif 9.5  <= h < 16.0: return "REGULAR"
    elif 16.0 <= h < 20.0: return "AFTER-HOURS"
    else:                   return "CERRADO"

SESSION = get_session()

# ─────────────────────────────────────────────────────────────────────
#  ESTADO COMPARTIDO (thread-safe)
#  Comunicación entre hilo WebSocket y Streamlit UI
# ─────────────────────────────────────────────────────────────────────
# shared_state es un dict global en memoria, accedido por ambos hilos.
# El hilo WebSocket escribe → Streamlit UI lee
# _lock evita condiciones de carrera

_lock = threading.Lock()
shared_state = {
    # Precios tick-by-tick: {ticker: float}
    "prices": {},
    # Volumen acumulado de la vela actual: {ticker: float}
    "vol_current": {},
    # Rolling window 5min: {ticker: deque(maxlen=300)} con (timestamp, price, volume)
    "rolling": {},
    # Precios al inicio de la vela de 1min actual: {ticker: float}
    "open_1min": {},
    # Velas históricas almacenadas: {ticker: list de dicts}
    "bars": {},
    # ALERTAS activas: list de dicts
    "alertas": [],
    # Estado del WebSocket
    "ws_status": "DESCONECTADO",
    "ws_tickers": [],
    "ws_trades": 0,       # contador de trades recibidos
    "ws_last_tick": None, # último timestamp
    # Nueva alerta (para trigger de audio)
    "nueva_alerta": False,
    # Config dinámica (leída del sidebar, escrita por Streamlit)
    "cfg": {
        "min_spike_pct": 2.0,
        "min_rvol": 2.5,
        "min_force": 60,
        "precio_min": 0.01,
        "precio_max": 600.0,
    }
}

# ─────────────────────────────────────────────────────────────────────
#  HILO WEBSOCKET — ALPACA StockDataStream
#  Corre en background, nunca bloquea Streamlit
# ─────────────────────────────────────────────────────────────────────

def calcular_rvol(ticker: str) -> float:
    """
    Calcula RVOL usando la rolling window de 5min.
    Compara volumen de la vela actual vs promedio de velas anteriores.
    """
    with _lock:
        rolls = shared_state["rolling"].get(ticker)
        vol_curr = shared_state["vol_current"].get(ticker, 0)

    if not rolls or len(rolls) < 10:
        return 1.0

    # Agrupar por minuto y calcular volumen por vela
    now_ts  = datetime.now(ET)
    min_now = now_ts.replace(second=0, microsecond=0)

    vols_prev = []
    vol_min   = {}
    for ts, price, vol in rolls:
        m = ts.replace(second=0, microsecond=0)
        if m < min_now:
            vol_min[m] = vol_min.get(m, 0) + vol

    if not vol_min:
        return 1.0

    avg_vol = sum(vol_min.values()) / len(vol_min)
    return vol_curr / max(avg_vol, 1)


def calcular_vel_1m_5m(ticker: str) -> tuple:
    """
    Calcula velocidad en los últimos 1min y 5min usando rolling window.
    Retorna (vel_1m_pct, vel_5m_pct).
    CRÍTICO: Esta es la métrica principal para detectar PHOE y similares.
    """
    with _lock:
        precio_actual = shared_state["prices"].get(ticker, 0)
        rolls = list(shared_state["rolling"].get(ticker, deque()))

    if not rolls or precio_actual <= 0:
        return 0.0, 0.0

    now = datetime.now(ET)

    # Precio hace 1 minuto
    precio_1m_ago = None
    for ts, price, vol in reversed(rolls):
        if (now - ts).total_seconds() >= 60:
            precio_1m_ago = price
            break

    # Precio hace 5 minutos
    precio_5m_ago = None
    for ts, price, vol in reversed(rolls):
        if (now - ts).total_seconds() >= 300:
            precio_5m_ago = price
            break

    vel_1m = (precio_actual - precio_1m_ago) / max(precio_1m_ago, 1e-9) * 100 \
             if precio_1m_ago else 0.0
    vel_5m = (precio_actual - precio_5m_ago) / max(precio_5m_ago, 1e-9) * 100 \
             if precio_5m_ago else 0.0

    return vel_1m, vel_5m


def calcular_ticks_por_segundo(ticker: str, ventana_seg: int = 10) -> float:
    """
    Calcula la densidad de transacciones por segundo (tape speed).
    Un pico masivo de ticks/seg = señal de aceleración anormal.
    """
    with _lock:
        rolls = list(shared_state["rolling"].get(ticker, deque()))
    if not rolls:
        return 0.0
    now = datetime.now(ET)
    recientes = [1 for ts, _, _ in rolls if (now-ts).total_seconds() <= ventana_seg]
    return len(recientes) / ventana_seg


def evaluar_despegue(ticker: str) -> dict:
    """
    Motor de evaluación de despegue inmediato.
    Lee config dinámica de shared_state["cfg"] para respetar sliders.
    Retorna dict con force (0-100), spike info y señales.
    """
    cfg          = shared_state["cfg"]
    min_spike    = cfg["min_spike_pct"]
    min_rvol     = cfg["min_rvol"]
    precio_min   = cfg["precio_min"]
    precio_max   = cfg["precio_max"]

    with _lock:
        precio    = shared_state["prices"].get(ticker, 0)
        open_1m   = shared_state["open_1min"].get(ticker, precio)
        bars      = shared_state["bars"].get(ticker, [])

    if precio <= 0 or not (precio_min <= precio <= precio_max):
        return {"force": 0, "despegue": False}

    # Spike actual vs apertura de vela de 1min
    spike_1m_actual = (precio - open_1m) / max(open_1m, 1e-9) * 100 if open_1m > 0 else 0

    # Velocidad rolling window
    vel_1m, vel_5m = calcular_vel_1m_5m(ticker)

    # RVOL
    rvol = calcular_rvol(ticker)

    # Tape speed
    tps = calcular_ticks_por_segundo(ticker, 10)

    force = 0
    det   = {}

    # ── FACTOR 1: SPIKE ACTUAL (peso 35%) ────────────────────
    # Esta es la métrica CRÍTICA — detecta PHOE en el segundo exacto
    if spike_1m_actual >= 10:
        force += 35; det["🚨 Spike 1m"] = f"+{spike_1m_actual:.2f}% — COHETE AHORA"
    elif spike_1m_actual >= 5:
        force += 28; det["🚨 Spike 1m"] = f"+{spike_1m_actual:.2f}% — FUERTE"
    elif spike_1m_actual >= min_spike:
        force += 20; det["🚨 Spike 1m"] = f"+{spike_1m_actual:.2f}% — DESPEGUE ✅"
    elif spike_1m_actual >= min_spike * 0.5:
        force += 8;  det["🚨 Spike 1m"] = f"+{spike_1m_actual:.2f}% — Leve"
    else:
        det["🚨 Spike 1m"] = f"{spike_1m_actual:+.2f}% — Sin spike"

    # ── FACTOR 2: VELOCIDAD 1min rolling (peso 25%) ──────────
    # ACELERACIÓN ANORMAL: >2% en los últimos 60 segundos
    if vel_1m >= 5:
        force += 25; det["⚡ Vel 1min"] = f"+{vel_1m:.2f}% (último 1min) — EXPLOSIÓN"
    elif vel_1m >= 2:
        force += 18; det["⚡ Vel 1min"] = f"+{vel_1m:.2f}% (último 1min) ✅"
    elif vel_1m >= 0.5:
        force += 8;  det["⚡ Vel 1min"] = f"+{vel_1m:.2f}% (último 1min)"
    elif vel_1m < 0:
        force -= 5;  det["⚡ Vel 1min"] = f"{vel_1m:.2f}% — Bajando"
    else:
        det["⚡ Vel 1min"] = f"{vel_1m:+.2f}% — Plano"

    # ── FACTOR 3: VELOCIDAD 5min rolling (peso 15%) ──────────
    if vel_5m >= 5:
        force += 15; det["📈 Vel 5min"] = f"+{vel_5m:.2f}% (último 5min) — MOMENTUM"
    elif vel_5m >= 2:
        force += 10; det["📈 Vel 5min"] = f"+{vel_5m:.2f}% (último 5min)"
    elif vel_5m >= 0.5:
        force += 4;  det["📈 Vel 5min"] = f"+{vel_5m:.2f}%"
    else:
        det["📈 Vel 5min"] = f"{vel_5m:+.2f}%"

    # ── FACTOR 4: RVOL — EXPLOSIÓN DE VOLUMEN (peso 20%) ─────
    if rvol >= 5:
        force += 20; det["💥 RVOL"] = f"{rvol:.1f}x — EXPLOSIÓN ✅"
    elif rvol >= min_rvol:
        force += 14; det["💥 RVOL"] = f"{rvol:.1f}x — Alto ✅"
    elif rvol >= 1.5:
        force += 5;  det["💥 RVOL"] = f"{rvol:.1f}x — Sobre promedio"
    else:
        det["💥 RVOL"] = f"{rvol:.1f}x — Normal"

    # ── FACTOR 5: TAPE SPEED (transacciones/seg) ─────────────
    if tps >= 3:
        force += 5; det["🎯 Tape"] = f"{tps:.1f} ticks/seg — MASIVO"
    elif tps >= 1:
        force += 2; det["🎯 Tape"] = f"{tps:.1f} ticks/seg — Alto"
    else:
        det["🎯 Tape"] = f"{tps:.1f} ticks/seg"

    # Calcular con barras históricas si disponibles
    if bars and len(bars) >= 5:
        closes = [b["close"] for b in bars[-5:]]
        vols   = [b["volume"] for b in bars[-5:]]
        # RSI simplificado
        diffs  = [closes[i]-closes[i-1] for i in range(1,len(closes))]
        gains  = [d for d in diffs if d>0]
        losses = [-d for d in diffs if d<0]
        rsi    = 50
        if gains or losses:
            avg_g = sum(gains)/max(len(gains),1)
            avg_l = sum(losses)/max(len(losses),1)
            rsi   = 100 - 100/(1 + avg_g/max(avg_l,1e-9)) if avg_l > 0 else 70
        if 55 < rsi < 80: force += 3; det["RSI"] = f"{rsi:.0f} ▲"
        elif rsi >= 80:   force -= 3; det["RSI"] = f"{rsi:.0f} ⚠️ SB"
        elif rsi < 40:    force -= 3; det["RSI"] = f"{rsi:.0f} ▼"
        else:              det["RSI"] = f"{rsi:.0f} →"

    force = max(0, min(100, force))

    # DESPEGUE INMINENTE si Force alto + spike + rvol
    despegue = (force >= 60 and
                spike_1m_actual >= min_spike * 0.8 and
                rvol >= min_rvol * 0.7)

    return {
        "force"     : force,
        "despegue"  : despegue,
        "spike_1m"  : spike_1m_actual,
        "vel_1m"    : vel_1m,
        "vel_5m"    : vel_5m,
        "rvol"      : rvol,
        "tps"       : tps,
        "precio"    : precio,
        "detalles"  : det,
    }


# ── CALLBACKS DEL WEBSOCKET ──────────────────────────────────────────

async def on_bar(bar):
    """
    Recibe cada vela de 1min desde Alpaca WebSocket.
    Almacena la vela y actualiza el precio de apertura de la nueva vela.
    """
    sym   = bar.symbol
    close = float(bar.close)
    vol   = float(bar.volume)
    ts    = bar.timestamp

    with _lock:
        # Guardar barra histórica (últimas 50 velas)
        if sym not in shared_state["bars"]:
            shared_state["bars"][sym] = []
        shared_state["bars"][sym].append({
            "ts": ts, "open": float(bar.open), "high": float(bar.high),
            "low": float(bar.low), "close": close, "volume": vol
        })
        if len(shared_state["bars"][sym]) > 50:
            shared_state["bars"][sym].pop(0)

        # Resetear vol_current y open_1min al inicio de nueva vela
        shared_state["open_1min"][sym]   = float(bar.open)
        shared_state["vol_current"][sym] = 0
        shared_state["ws_trades"]       += 1
        shared_state["ws_last_tick"]     = datetime.now(ET)


async def on_trade(trade):
    """
    Recibe cada transacción (tick) en tiempo real desde Alpaca WebSocket.
    CRÍTICO: Aquí es donde se detecta el despegue en el segundo exacto.
    Actualiza rolling window y evalúa si hay despegue inmediato.
    """
    sym    = trade.symbol
    precio = float(trade.price)
    vol    = float(trade.size)
    ts     = datetime.now(ET)

    cfg = shared_state["cfg"]

    with _lock:
        # Actualizar precio actual
        shared_state["prices"][sym] = precio

        # Actualizar volumen acumulado de vela actual
        shared_state["vol_current"][sym] = \
            shared_state["vol_current"].get(sym, 0) + vol

        # Rolling window 5 minutos (deque con maxlen=300 = 300 ticks)
        if sym not in shared_state["rolling"]:
            shared_state["rolling"][sym] = deque(maxlen=300)
        shared_state["rolling"][sym].append((ts, precio, vol))

        shared_state["ws_trades"] += 1
        shared_state["ws_last_tick"] = ts

    # Evaluar despegue (sin lock para no bloquear)
    ev = evaluar_despegue(sym)
    force    = ev["force"]
    despegue = ev["despegue"]

    if despegue and force >= cfg.get("min_force", 60):
        alerta = {
            "ticker"    : sym,
            "ts"        : ts.strftime("%H:%M:%S ET"),
            "force"     : force,
            "precio"    : precio,
            "spike_1m"  : ev["spike_1m"],
            "vel_1m"    : ev["vel_1m"],
            "vel_5m"    : ev["vel_5m"],
            "rvol"      : ev["rvol"],
            "tps"       : ev["tps"],
            "detalles"  : ev["detalles"],
        }
        with _lock:
            # Evitar alertas duplicadas del mismo ticker en 60 seg
            ts_limite = ts - timedelta(seconds=60)
            alertas   = shared_state["alertas"]
            ya_alerto = any(
                a["ticker"] == sym and
                datetime.strptime(a["ts"][:8], "%H:%M:%S").replace(
                    tzinfo=ET, year=ts.year, month=ts.month, day=ts.day
                ) > ts_limite
                for a in alertas
                if len(a.get("ts","")) >= 8
            )
            if not ya_alerto:
                shared_state["alertas"].insert(0, alerta)
                # Mantener max 20 alertas
                shared_state["alertas"] = shared_state["alertas"][:20]
                shared_state["nueva_alerta"] = True


async def on_error(error):
    with _lock:
        shared_state["ws_status"] = f"ERROR: {str(error)[:60]}"


# ── HILO WEBSOCKET ───────────────────────────────────────────────────

class WebSocketManager:
    """
    Gestor del WebSocket de Alpaca en hilo separado.
    Permite suscribir/desuscribir tickers dinámicamente.
    """
    def __init__(self):
        self._thread  = None
        self._loop    = None
        self._stream  = None
        self._running = False

    def start(self, tickers: list):
        """Inicia el WebSocket en hilo de background."""
        if self._running and self._thread and self._thread.is_alive():
            # Ya corriendo — actualizar suscripciones
            self._update_subscriptions(tickers)
            return

        with _lock:
            shared_state["ws_status"]  = "CONECTANDO..."
            shared_state["ws_tickers"] = tickers[:]

        self._running = True
        self._thread  = threading.Thread(
            target=self._run_loop,
            args=(tickers,),
            daemon=True,   # daemon=True: el hilo muere cuando Streamlit para
            name="thunder-ws"
        )
        self._thread.start()

    def _run_loop(self, tickers: list):
        """
        Crea un event loop asyncio en el hilo de background.
        Streamlit corre en el hilo principal — este hilo es independiente.
        """
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._connect(tickers))
        except Exception as e:
            with _lock:
                shared_state["ws_status"] = f"ERROR HILO: {str(e)[:80]}"
            self._running = False

    async def _connect(self, tickers: list):
        """Conecta el StockDataStream y suscribe tickers."""
        try:
            self._stream = StockDataStream(
                ALPACA_KEY,
                ALPACA_SECRET,
                feed="iex"      # IEX = gratis, sin suscripción premium
            )

            # Suscribir a barras de 1min (on_bar)
            self._stream.subscribe_bars(on_bar, *tickers)

            # Suscribir a trades (tick-by-tick) (on_trade)
            # CRÍTICO: esto alimenta el detector de spikes en tiempo real
            self._stream.subscribe_trades(on_trade, *tickers)

            with _lock:
                shared_state["ws_status"]  = "🟢 EN VIVO"
                shared_state["ws_tickers"] = tickers[:]

            # Correr indefinidamente
            await self._stream._run_forever()

        except Exception as e:
            with _lock:
                shared_state["ws_status"] = f"DESCONECTADO: {str(e)[:60]}"
            self._running = False

    def _update_subscriptions(self, new_tickers: list):
        """
        Actualiza la lista de tickers suscritos dinámicamente.
        Se llama cuando el usuario cambia la lista desde Streamlit.
        """
        with _lock:
            current   = set(shared_state["ws_tickers"])
            nuevo_set = set(new_tickers)
            to_add    = list(nuevo_set - current)
            to_remove = list(current - nuevo_set)

        if self._stream and self._loop and self._loop.is_running():
            if to_add:
                asyncio.run_coroutine_threadsafe(
                    self._subscribe_more(to_add), self._loop)
            shared_state["ws_tickers"] = new_tickers[:]

    async def _subscribe_more(self, tickers: list):
        try:
            if self._stream:
                self._stream.subscribe_bars(on_bar, *tickers)
                self._stream.subscribe_trades(on_trade, *tickers)
        except Exception:
            pass

    def stop(self):
        self._running = False
        if self._loop:
            try:
                self._loop.stop()
            except Exception:
                pass


# Instancia global del WebSocket Manager
# @st.cache_resource asegura una sola instancia compartida entre reruns
@st.cache_resource
def get_ws_manager() -> WebSocketManager:
    return WebSocketManager()

ws_manager = get_ws_manager()


# ─────────────────────────────────────────────────────────────────────
#  SCANNER: YAHOO + TWELVE DATA (sin WebSocket — solo para lista)
# ─────────────────────────────────────────────────────────────────────
YH = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "Accept": "application/json"}

def obtener_top_gainers(precio_min: float, precio_max: float,
                         n: int = 80) -> pd.DataFrame:
    """Obtiene top gainers de Yahoo Finance (mismos que Webull Top Gainers)."""
    resultados = []
    for sid in ["day_gainers", "most_actives", "small_cap_gainers"]:
        for base in ["https://query1.finance.yahoo.com",
                     "https://query2.finance.yahoo.com"]:
            try:
                r = requests.get(
                    f"{base}/v1/finance/screener/predefined/saved",
                    headers=YH,
                    params={"scrIds": sid, "count": 50, "formatted": "false"},
                    timeout=10
                )
                if r.status_code == 200:
                    quotes = (r.json().get("finance",{})
                               .get("result",[{}])[0].get("quotes",[]))
                    for q in quotes:
                        sym = q.get("symbol","").strip().upper()
                        if not sym or not sym.isalpha() or not (1<len(sym)<=5):
                            continue
                        precio = float(q.get("regularMarketPrice", 0))
                        if not (precio_min <= precio <= precio_max):
                            continue
                        chg = float(q.get("regularMarketChangePercent", 0))
                        vol = float(q.get("regularMarketVolume", 0))
                        if chg > 0:
                            resultados.append({
                                "Ticker"  : sym,
                                "Precio $": round(precio, 4),
                                "Δ Día %" : round(chg, 2),
                                "Vol"     : int(vol),
                            })
                    break
            except Exception:
                continue
        if resultados:
            break

    # Twelve Data como complemento
    if TWELVE_KEY:
        try:
            for exc in ["NYSE","NASDAQ","AMEX"]:
                r2 = requests.get(
                    "https://api.twelvedata.com/stocks/market/movers",
                    params={"exchange":exc,"direction":"gainers",
                            "outputsize":25,"country":"US","apikey":TWELVE_KEY},
                    timeout=10)
                if r2.status_code == 200 and "values" in r2.json():
                    for item in r2.json()["values"]:
                        sym = item.get("symbol","").strip().upper()
                        if not sym or not sym.isalpha() or not (1<len(sym)<=5):
                            continue
                        precio = float(item.get("price",0))
                        if not (precio_min <= precio <= precio_max):
                            continue
                        chg = float(item.get("percent_change",0))
                        if chg > 0 and not any(r["Ticker"]==sym for r in resultados):
                            resultados.append({
                                "Ticker"  :sym,
                                "Precio $":round(precio,4),
                                "Δ Día %" :round(chg,2),
                                "Vol"     :int(float(item.get("volume",0))),
                            })
        except Exception:
            pass

    if not resultados:
        return pd.DataFrame()

    df = (pd.DataFrame(resultados)
            .drop_duplicates(subset=["Ticker"])
            .sort_values("Δ Día %", ascending=False)
            .reset_index(drop=True)
            .head(n))
    return df


# ─────────────────────────────────────────────────────────────────────
#  SL / TP DINÁMICO
# ─────────────────────────────────────────────────────────────────────
def calcular_sltp(precio: float, ask: float,
                   bars: list, atr_mult: float = 2.0,
                   min_rr: float = 2.0) -> dict:
    """Calcula SL/TP basado en ATR de las barras históricas."""
    try:
        if bars and len(bars) >= 5:
            trues = []
            for i in range(1, len(bars)):
                hl  = bars[i]["high"] - bars[i]["low"]
                hc  = abs(bars[i]["high"] - bars[i-1]["close"])
                lc  = abs(bars[i]["low"]  - bars[i-1]["close"])
                trues.append(max(hl, hc, lc))
            atr = sum(trues[-14:]) / min(len(trues[-14:]), 14)
            sup = min(b["low"] for b in bars[-10:])
        else:
            atr = precio * 0.015
            sup = precio * 0.97

        entrada = round(ask * 1.005 if ask > 0 else precio * 1.005, 4)
        sl      = round(max(precio - atr*atr_mult, sup*0.998), 4)
        sl      = max(sl, precio * 0.92)   # máx 8% pérdida
        riesgo  = precio - sl
        tp      = round(precio + riesgo*min_rr, 4)
        rr      = round((tp-precio)/max(riesgo,1e-9), 2)

        return {"entrada":entrada,"sl":sl,"tp":tp,"rr":rr,"atr":round(atr,4)}
    except Exception:
        sl = round(precio*0.97, 4)
        return {"entrada":round(precio*1.005,4),"sl":sl,
                "tp":round(precio*1.06,4),"rr":2.0,"atr":round(precio*0.015,4)}


# ─────────────────────────────────────────────────────────────────────
#  EJECUCIÓN DE ÓRDENES — LIMIT ORDER
# ─────────────────────────────────────────────────────────────────────
def execute_limit_buy(sym: str, qty: int,
                       limit_price: float, sl: float, tp: float) -> tuple:
    try:
        req = LimitOrderRequest(
            symbol=sym, qty=qty, side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            limit_price=round(float(limit_price),2),
            take_profit=TakeProfitRequest(limit_price=round(float(tp),2)),
            stop_loss=StopLossRequest(stop_price=round(float(sl),2))
        )
        trading.submit_order(req)
        return True, f"✅ LIMIT BUY {qty}x {sym} @ ${limit_price:.4f} | SL=${sl:.4f} TP=${tp:.4f}"
    except Exception as e:
        return False, f"❌ {e}"


def execute_market_sell(sym: str, qty: int) -> tuple:
    try:
        trading.submit_order(MarketOrderRequest(
            symbol=sym, qty=qty, side=OrderSide.SELL,
            time_in_force=TimeInForce.GTC))
        return True, f"✅ SELL MARKET {qty}x {sym}"
    except Exception as e:
        return False, f"❌ {e}"


def get_account():
    try:    return trading.get_account()
    except: return None

def get_positions():
    try:    return trading.get_all_positions()
    except: return []


# ─────────────────────────────────────────────────────────────────────
#  UI HELPERS
# ─────────────────────────────────────────────────────────────────────
def force_bar(force: int, despegue: bool) -> str:
    pct   = force
    color = ("#ff0000" if despegue else
             "#ff4500" if force>=80 else
             "#ff8c00" if force>=60 else
             "#ffc107" if force>=40 else "#374151")
    label = f"{'🔥'*(force//25)} {force}/100"
    return (f'<div class="force-bg">'
            f'<div class="force-fill" style="width:{pct}%;background:{color}">{label}</div>'
            f'</div>')


# ─────────────────────────────────────────────────────────────────────
#  ═══════════════════ INTERFAZ PRINCIPAL ═══════════════════
# ─────────────────────────────────────────────────────────────────────
st.markdown('<h1 class="hdr">⚡ THUNDER RADAR V99</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub">WEBSOCKET TICK-BY-TICK · ROLLING 5MIN · SPIKE DETECTOR · ALPACA PAPER</p>',
            unsafe_allow_html=True)

bm = {"REGULAR":"b-reg","PRE-MARKET":"b-pre","AFTER-HOURS":"b-aft","CERRADO":"b-cls"}
hora_et = datetime.now(ET).strftime("%H:%M:%S ET")
cuenta  = get_account()

hc1,hc2,hc3 = st.columns(3)
with hc1:
    st.markdown(f'<span class="badge {bm.get(SESSION,"b-cls")}">● {SESSION}</span>'
                f' &nbsp;<span class="dot"></span>'
                f'<span style="color:#8b949e;font-size:.73em">EN VIVO</span>',
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

# ─────────────────────────────────────────────────────────────────────
#  BARRA LATERAL
# ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ CONFIGURACIÓN V99")

    st.markdown("**💰 Filtros de Precio**")
    precio_min_f = st.number_input("Precio Mín $", value=0.01, step=0.01, min_value=0.01)
    precio_max_f = st.number_input("Precio Máx $", value=600.0, step=10.0, max_value=600.0)

    st.markdown("**🚨 Detector de Despegue (WebSocket)**")
    min_spike = st.slider("Spike mínimo %/vela", 0.5, 15.0, 2.0, 0.5,
                           help="% subida mínima en 1 vela de 1min para trigger")
    min_rvol  = st.slider("RVOL mínimo", 1.0, 10.0, 2.5, 0.5,
                           help="Volumen relativo mínimo (2.5 = 2.5x el promedio)")
    min_force = st.slider("Force mínimo para alerta", 40, 95, 65, 5,
                           help="Force Meter mínimo para generar ALERTA ROJA")

    st.markdown("**📊 SuperTrend**")
    st_per  = st.slider("Período", 5, 20, 10, 1)
    st_mult = st.slider("Multiplicador ATR", 1.0, 5.0, 3.0, 0.5)

    st.markdown("**🔒 Gestión de Riesgo**")
    atr_mult = st.slider("ATR × Stop Loss", 0.5, 4.0, 2.0, 0.5)
    min_rr   = st.slider("R:R mínimo", 1.5, 4.0, 2.0, 0.5)

    st.markdown("**📋 Resultados**")
    n_gainers = st.slider("Top Gainers a monitorear", 10, 100, 50, 5)
    top_n_f   = st.slider("Resultados finales", 10, 60, 30, 5)

    st.markdown("---")
    extras_txt = st.text_area("Tickers extra",
                               "PHOE,SDOT,BLZE,CLRB,STRL,BIYA,JLHL,NXTS", height=50)

    st.markdown("---")
    auto_compra = st.toggle("🤖 Auto-Compra (Force ≥ umbral)", value=False)
    if auto_compra:
        auto_force = st.slider("Force mínimo auto-compra", 70, 100, 80)
        auto_qty   = st.number_input("Acciones/orden", value=1, min_value=1)
        max_pos    = st.number_input("Máx posiciones", value=3, min_value=1)
        st.warning("⚠️ Ejecuta órdenes LIMIT en Paper.")

    auto_ref = st.toggle("🔁 Auto-refresh UI (10 seg)", value=True)

# Actualizar config dinámica en shared_state
# Los sliders de Streamlit alimentan el WebSocket en tiempo real
with _lock:
    shared_state["cfg"] = {
        "min_spike_pct": min_spike,
        "min_rvol"     : min_rvol,
        "min_force"    : min_force,
        "precio_min"   : precio_min_f,
        "precio_max"   : precio_max_f,
    }

# ─────────────────────────────────────────────────────────────────────
#  ESTADO DE LA SESIÓN
# ─────────────────────────────────────────────────────────────────────
for k,v in [("gainers_df", pd.DataFrame()),
             ("ws_started", False),
             ("last_refresh", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

extras = [x.strip().upper() for x in extras_txt.split(",") if x.strip()]

# ─────────────────────────────────────────────────────────────────────
#  PASO 1: OBTENER TOP GAINERS + INICIAR WEBSOCKET
# ─────────────────────────────────────────────────────────────────────
st.subheader("📡 Paso 1 — Obtener Top Movers + Iniciar WebSocket")

st.markdown("""<div class="ibox">
<b style="color:#ff4500">Cómo funciona:</b>
Obtiene los top gainers del día (Yahoo Finance) → suscribe SOLO esos ~50 tickers
al WebSocket de Alpaca → recibe datos tick-by-tick en background →
detecta spikes en el segundo exacto (PHOE y similares).
</div>""", unsafe_allow_html=True)

c1a, c1b, c1c = st.columns([2, 1, 1])
with c1a:
    if st.button("🚀 OBTENER TOP GAINERS + ACTIVAR WEBSOCKET",
                 use_container_width=True):
        with st.spinner("📡 Obteniendo top gainers..."):
            df_g = obtener_top_gainers(precio_min_f, precio_max_f, n_gainers)
            # Añadir extras manuales
            if extras:
                ex_df = pd.DataFrame([{
                    "Ticker":t,"Precio $":0,"Δ Día %":0,"Vol":0
                } for t in extras if not df_g.empty and t not in df_g["Ticker"].tolist()])
                if not ex_df.empty:
                    df_g = pd.concat([df_g, ex_df], ignore_index=True)
            st.session_state.gainers_df = df_g

        if not df_g.empty:
            tickers_ws = df_g["Ticker"].tolist()[:60]  # máx 60 por IEX free

            # Iniciar WebSocket en hilo de background
            ws_manager.start(tickers_ws)
            st.session_state.ws_started = True

            st.success(
                f"✅ {len(df_g)} stocks obtenidos | "
                f"WebSocket suscrito a {len(tickers_ws)} tickers | "
                f"Escuchando tick-by-tick..."
            )
            # Toast de confirmación
            st.toast("🟢 WebSocket Alpaca ACTIVO — Escaneando tickers",
                     icon="⚡")
        else:
            st.error("❌ Sin datos. Verifica conexión.")

with c1b:
    ws_st = shared_state.get("ws_status","DESCONECTADO")
    ws_css = "ws-live" if "🟢" in ws_st else ("ws-conn" if "CONECT" in ws_st else "ws-off")
    st.markdown(f'<span class="{ws_css}">● {ws_st}</span>', unsafe_allow_html=True)
    n_ws_tk = len(shared_state.get("ws_tickers",[]))
    st.markdown(f'<span style="color:#8b949e;font-size:.72em">{n_ws_tk} tickers</span>',
                unsafe_allow_html=True)

with c1c:
    trades_rx = shared_state.get("ws_trades",0)
    last_tick = shared_state.get("ws_last_tick")
    ts_tick   = last_tick.strftime("%H:%M:%S") if last_tick else "—"
    st.markdown(f'<span style="color:#ffc107">{trades_rx:,} ticks</span>', unsafe_allow_html=True)
    st.markdown(f'<span style="color:#8b949e;font-size:.72em">Último: {ts_tick}</span>',
                unsafe_allow_html=True)

# Mostrar gainers
if not st.session_state.gainers_df.empty:
    df_g_sh = st.session_state.gainers_df.head(15).copy()
    cols_g  = [c for c in ["Ticker","Precio $","Δ Día %","Vol"] if c in df_g_sh.columns]
    def cdg(v): return f"color:{'#00ff88' if v>=0 else '#ff4444'};font-weight:bold"
    try:
        sg = df_g_sh[cols_g].style.map(cdg,subset=["Δ Día %"])\
               .format({"Precio $":"${:.4f}","Δ Día %":"{:+.2f}%","Vol":"{:,.0f}"})
    except Exception:
        sg = df_g_sh[cols_g].style
    st.dataframe(sg, use_container_width=True, hide_index=True, height=220)

st.markdown('<hr class="n">', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
#  AUDIO TRIGGER — activa el pitido si hay nueva alerta
# ─────────────────────────────────────────────────────────────────────
if shared_state.get("nueva_alerta"):
    st.markdown("""
    <script>
    const el = document.getElementById('spike-trigger');
    if(el){ el.dataset.trigger='1'; }
    </script>
    """, unsafe_allow_html=True)
    with _lock:
        shared_state["nueva_alerta"] = False

# ─────────────────────────────────────────────────────────────────────
#  PASO 2: ALERTAS ROJAS — DESPEGUES EN TIEMPO REAL
# ─────────────────────────────────────────────────────────────────────
with _lock:
    alertas_now = list(shared_state["alertas"])

st.subheader(f"🚨 Alertas de Despegue en Tiempo Real ({len(alertas_now)} activas)")

if alertas_now:
    for al in alertas_now[:8]:
        force  = al["force"]
        fb     = force_bar(force, True)
        det_tx = " | ".join([f"<b>{k}</b>: {v}"
                              for k,v in list(al["detalles"].items())[:4]])
        st.markdown(f"""
        <div class="alerta-roja">
          <span class="tkr">🚨 {al['ticker']}</span>
          &nbsp;&nbsp;
          <span style="color:#ff4500;font-size:1.7em;font-weight:900;
                font-family:'Orbitron',sans-serif">{force}/100</span>
          &nbsp;&nbsp;
          <span style="color:#ffc107;font-size:.82em">{al['ts']}</span>
          <br>
          {fb}
          <br>
          <span class="lbl">Precio</span> <b style="color:#fff">${al['precio']:.4f}</b>
          &nbsp;|&nbsp;
          <span class="lbl">🚨 Spike 1m</span>
          <b style="color:#ff4500">{al['spike_1m']:+.2f}%</b>
          &nbsp;|&nbsp;
          <span class="lbl">Vel 1min</span>
          <b style="color:#ff8c00">{al['vel_1m']:+.2f}%</b>
          &nbsp;|&nbsp;
          <span class="lbl">Vel 5min</span>
          <b style="color:#ffc107">{al['vel_5m']:+.2f}%</b>
          &nbsp;|&nbsp;
          <span class="lbl">RVOL</span>
          <b style="color:#ff8c00">{al['rvol']:.1f}x</b>
          &nbsp;|&nbsp;
          <span class="lbl">Ticks/s</span> {al['tps']:.1f}
          <br>
          <span style="font-size:.75em;color:#8b949e">{det_tx}</span>
        </div>""", unsafe_allow_html=True)

    # Toast si hay alertas recientes
    if alertas_now and st.session_state.get("last_refresh"):
        ultimo = alertas_now[0]
        st.toast(
            f"🚨 {ultimo['ticker']} — Force {ultimo['force']}/100 | "
            f"Spike +{ultimo['spike_1m']:.2f}% | RVOL {ultimo['rvol']:.1f}x",
            icon="🔥"
        )
else:
    if st.session_state.ws_started:
        st.markdown("""<div class="ibox">
        <span style="color:#8b949e">
        🟡 WebSocket activo — esperando despegues...<br>
        Los spikes aparecerán aquí en el segundo exacto en que ocurran.
        Aumenta el <b>n° de tickers</b> o baja el <b>Force mínimo</b> si no hay alertas.
        </span></div>""", unsafe_allow_html=True)
    else:
        st.info("Activa el WebSocket en el Paso 1 para ver alertas en tiempo real.")

st.markdown('<hr class="n">', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
#  PASO 3: MONITOR EN TIEMPO REAL — todos los tickers
# ─────────────────────────────────────────────────────────────────────
st.subheader("📊 Paso 3 — Monitor de Velocidad en Tiempo Real (Rolling 5min)")

with _lock:
    prices_now = dict(shared_state["prices"])
    tickers_ws = list(shared_state["ws_tickers"])

if prices_now:
    monitor_rows = []
    for sym in tickers_ws:
        precio = prices_now.get(sym, 0)
        if precio <= 0:
            continue
        ev = evaluar_despegue(sym)
        if ev["force"] < 10:
            continue

        orden = calcular_sltp(
            precio,
            precio * 1.001,
            shared_state["bars"].get(sym, []),
            atr_mult, min_rr
        )

        monitor_rows.append({
            "Ticker"   : sym,
            "Precio $" : round(precio, 4),
            "Force"    : ev["force"],
            "🚨 Despegue": "🚨 SÍ" if ev["despegue"] else "—",
            "Spike 1m %": round(ev["spike_1m"], 2),
            "Vel 1min %": round(ev["vel_1m"],   2),
            "Vel 5min %": round(ev["vel_5m"],   2),
            "RVOL"      : round(ev["rvol"],      1),
            "Ticks/s"   : round(ev["tps"],       1),
            "Entrada $" : orden["entrada"],
            "SL $"      : orden["sl"],
            "TP $"      : orden["tp"],
            "R:R"       : orden["rr"],
            "_force"    : ev["force"],
            "_despegue" : ev["despegue"],
            "_det"      : ev["detalles"],
        })

    if monitor_rows:
        monitor_rows.sort(key=lambda x: -x["_force"])

        # Mostrar tarjetas de los top 5
        top5 = [r for r in monitor_rows if r["_force"] >= min_force][:5]
        if top5:
            st.markdown(f"**⚡ Top señales activas (Force ≥ {min_force}):**")
            for r in top5:
                force  = r["_force"]
                dep    = r["_despegue"]
                fb     = force_bar(force, dep)
                card   = "card-spike" if dep else "card-launch"
                vc     = "#00ff88" if r["Vel 1min %"]>=0 else "#ff4444"
                sc     = "#ff4500" if r["Spike 1m %"]>=5 else "#ff8c00"
                st.markdown(f"""
                <div class="{card}">
                  <span class="tkr">{'🚨' if dep else '⚡'} {r['Ticker']}</span>
                  &nbsp;&nbsp;
                  <span class="{'s10' if force>=80 else ('s8' if force>=60 else 's6')}">{force}/100</span>
                  {'<span class="despegue-badge">DESPEGUE INMINENTE</span>' if dep else ''}
                  <br>{fb}<br>
                  <span class="lbl">Precio</span> <b style="color:#fff">${r['Precio $']:.4f}</b>
                  &nbsp;|&nbsp;
                  <span class="lbl">Spike 1m</span> <b style="color:{sc}">{r['Spike 1m %']:+.2f}%</b>
                  &nbsp;|&nbsp;
                  <span class="lbl">Vel 1min</span> <b style="color:{vc}">{r['Vel 1min %']:+.2f}%</b>
                  &nbsp;|&nbsp;
                  <span class="lbl">Vel 5min</span> <b style="color:{vc}">{r['Vel 5min %']:+.2f}%</b>
                  &nbsp;|&nbsp;
                  <span class="lbl">RVOL</span> {r['RVOL']}x
                  &nbsp;|&nbsp;
                  <span class="lbl">Ticks/s</span> {r['Ticks/s']}
                  <br>
                  <span class="lbl">SL</span> <b style="color:#ff6b6b">${r['SL $']}</b>
                  &nbsp;|&nbsp;
                  <span class="lbl">TP</span> <b style="color:#00ff88">${r['TP $']}</b>
                  &nbsp;|&nbsp;
                  <span class="lbl">R:R</span> 1:{r['R:R']}
                </div>""", unsafe_allow_html=True)

                # Auto-compra si está activada
                if auto_compra and dep and force >= auto_force:
                    n_pos = len(get_positions())
                    if n_pos < max_pos:
                        ok, msg = execute_limit_buy(
                            r["Ticker"], auto_qty,
                            r["Entrada $"], r["SL $"], r["TP $"])
                        st.write(msg)

        # Tabla completa
        cols_t = ["Ticker","Precio $","Force","🚨 Despegue",
                  "Spike 1m %","Vel 1min %","Vel 5min %",
                  "RVOL","Ticks/s","Entrada $","SL $","TP $","R:R"]
        df_mon = pd.DataFrame([{k:r[k] for k in cols_t} for r in monitor_rows])

        def cf(v):
            if v>=80: return "background-color:#7f1d1d;color:#ff4500;font-weight:900"
            elif v>=60: return "background-color:#92400e;color:#ffc107"
            elif v>=40: return "background-color:#1a2535;color:#c9d1d9"
            else: return "color:#8b949e"
        def cvt(v): return f"color:{'#00ff88' if v>=0 else '#ff4444'};font-weight:bold"
        def csp(v):
            if v>=5:  return "color:#ff4500;font-weight:900"
            elif v>=2:return "color:#ff8c00;font-weight:700"
            elif v>=0.5:return"color:#ffc107"
            else: return "color:#8b949e"
        fmt_m = {"Precio $":"${:.4f}","Spike 1m %":"{:+.2f}%","Vel 1min %":"{:+.2f}%",
                  "Vel 5min %":"{:+.2f}%","RVOL":"{:.1f}x","Ticks/s":"{:.1f}",
                  "Entrada $":"${:.4f}","SL $":"${:.4f}","TP $":"${:.4f}","R:R":"{:.2f}"}
        try:
            styled=(df_mon.style.map(cf,subset=["Force"])
                    .map(cvt,subset=["Vel 1min %","Vel 5min %"])
                    .map(csp,subset=["Spike 1m %"]).format(fmt_m))
        except Exception:
            try:
                styled=(df_mon.style.applymap(cf,subset=["Force"])
                        .applymap(cvt,subset=["Vel 1min %","Vel 5min %"])
                        .applymap(csp,subset=["Spike 1m %"]).format(fmt_m))
            except Exception:
                styled=df_mon.style.format(fmt_m)
        st.dataframe(styled, use_container_width=True, hide_index=True, height=400)
    else:
        st.info("Los tickers suscritos aparecerán aquí cuando haya actividad de precio.")
else:
    if st.session_state.ws_started:
        st.markdown("""<div class="ibox">
        🟡 Esperando primeros datos del WebSocket...
        Los datos aparecerán en segundos cuando Alpaca empiece a enviar ticks.
        </div>""", unsafe_allow_html=True)
    else:
        st.info("Activa el WebSocket en el Paso 1 para ver el monitor en tiempo real.")

st.markdown('<hr class="n">', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
#  PORTAFOLIO ACTIVO
# ─────────────────────────────────────────────────────────────────────
st.subheader("💼 Portafolio Activo")
posiciones = get_positions()
if posiciones:
    rows = []
    for p in posiciones:
        pp = float(p.unrealized_plpc)*100
        pu = float(p.unrealized_pl)
        ico = "🟢" if pp>=0 else "🔴"
        rows.append({"Ticker":p.symbol,"Qty":p.qty,
                     "Entrada $":round(float(p.avg_entry_price),4),
                     "Actual $": round(float(p.current_price),4),
                     "P&L %":f"{ico} {pp:+.2f}%","P&L $":f"${pu:+.2f}",
                     "Valor $":f"${float(p.market_value):,.2f}"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    px1,px2,px3 = st.columns([2,1,1])
    with px1:
        tickers_pos = [r["Ticker"] for r in rows]
        tc = st.selectbox("Cerrar", tickers_pos)
    with px2:
        if st.button("🔴 Cerrar pos."):
            ok,msg = execute_market_sell(tc, int([r["Qty"] for r in rows if r["Ticker"]==tc][0]))
            st.success(msg) if ok else st.error(msg)
    with px3:
        if st.button("🔴 Cerrar TODO"):
            for pos in posiciones:
                execute_market_sell(pos.symbol, int(pos.qty))
            st.warning("Cerrando todo...")
else:
    st.info("Sin posiciones abiertas. 🎯")

st.markdown('<hr class="n">', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
#  EJECUCIÓN MANUAL
# ─────────────────────────────────────────────────────────────────────
st.subheader("🛒 Ejecución Manual — Limit Order (Ask + 0.5%)")

tickers_disponibles = (
    list(prices_now.keys()) if prices_now
    else (st.session_state.gainers_df["Ticker"].tolist()
          if not st.session_state.gainers_df.empty else [])
)

if tickers_disponibles:
    em1, em2 = st.columns([1, 2])
    with em1:
        t_op   = st.selectbox("Ticker", tickers_disponibles)
        precio_op = prices_now.get(t_op, 0)
        bars_op   = shared_state["bars"].get(t_op, [])
        orden_op  = calcular_sltp(precio_op, precio_op*1.001, bars_op, atr_mult, min_rr)

        if precio_op > 0:
            st.markdown(f'<div class="ibox">Precio actual (WebSocket): '
                        f'<b style="color:#00ff88">${precio_op:.4f}</b></div>',
                        unsafe_allow_html=True)

        qty_m   = st.number_input("Cantidad", value=1, min_value=1, step=1)
        lim_m   = st.number_input("Precio Límite $",
                                   value=float(orden_op["entrada"]),
                                   step=0.001, format="%.4f")
        sl_m    = st.number_input("Stop Loss $",
                                   value=float(orden_op["sl"]),
                                   step=0.001, format="%.4f")
        tp_m    = st.number_input("Take Profit $",
                                   value=float(orden_op["tp"]),
                                   step=0.001, format="%.4f")
        b1, b2  = st.columns(2)
        with b1:
            if st.button("🟢 LIMIT BUY", use_container_width=True):
                ok,msg = execute_limit_buy(t_op, qty_m, lim_m, sl_m, tp_m)
                st.success(msg) if ok else st.error(msg)
        with b2:
            if st.button("🔴 SELL MARKET", use_container_width=True):
                ok,msg = execute_market_sell(t_op, qty_m)
                st.success(msg) if ok else st.error(msg)

    with em2:
        st.markdown(f"### 📊 {t_op} — Análisis WebSocket")
        ev_op = evaluar_despegue(t_op)
        st.markdown(force_bar(ev_op["force"], ev_op["despegue"]), unsafe_allow_html=True)
        m1,m2_,m3,m4 = st.columns(4)
        m1.metric("Precio $",  f"${precio_op:.4f}" if precio_op>0 else "—")
        m2_.metric("Force",    f"{ev_op['force']}/100")
        m3.metric("Spike 1m",  f"{ev_op['spike_1m']:+.2f}%")
        m4.metric("RVOL",      f"{ev_op['rvol']:.1f}x")
        m5,m6,m7,m8 = st.columns(4)
        m5.metric("Vel 1min",  f"{ev_op['vel_1m']:+.2f}%")
        m6.metric("Vel 5min",  f"{ev_op['vel_5m']:+.2f}%")
        m7.metric("Ticks/s",   f"{ev_op['tps']:.1f}")
        m8.metric("R:R",       f"1:{orden_op['rr']:.2f}")
        if ev_op["detalles"]:
            st.markdown("**📌 Motor de señal (WebSocket):**")
            for k,v in ev_op["detalles"].items():
                c = ("#ff4500" if "COHETE" in str(v) or "EXPLOSIÓN" in str(v)
                     else "#ff8c00" if "FUERTE" in str(v) or "DESPEGUE" in str(v)
                     else "#00ff88" if "✅" in str(v)
                     else "#ff4444" if "▼" in str(v) or "Baj" in str(v)
                     else "#8b949e")
                st.markdown(f'<span style="color:{c};font-size:.79em">'
                            f'<b>{k}</b>: {v}</span>', unsafe_allow_html=True)
else:
    st.info("Activa el WebSocket para ver datos de precio en tiempo real.")

# ─────────────────────────────────────────────────────────────────────
#  AUTO-REFRESH
# ─────────────────────────────────────────────────────────────────────
if auto_ref:
    # Streamlit hace rerun cada 10 segundos para actualizar la UI
    # El WebSocket sigue corriendo en background independientemente
    time.sleep(10)
    st.rerun()

st.markdown('<hr class="n">', unsafe_allow_html=True)
st.markdown("""<div style="text-align:center;color:#8b949e;font-size:.69em;
font-family:'Share Tech Mono',monospace">
⚡ THUNDER RADAR V99 — WEBSOCKET TICK-BY-TICK — ALPACA PAPER — Solo uso educativo<br>
WebSocket: Alpaca IEX Feed (gratis) · Los resultados pasados no garantizan rendimientos futuros.
</div>""", unsafe_allow_html=True)
