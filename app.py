import streamlit as st
import yfinance as yf

st.set_page_config(layout="wide")

st.title("🚀 BOT SCALPING PRO")

symbols_input = st.text_input("Acciones", "AAPL,TSLA,AMD")

def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()

if st.button("🔍 Escanear"):

    symbols = [s.strip() for s in symbols_input.split(",")]

    for sym in symbols:
        try:
            with st.spinner(f"Analizando {sym}..."):

                df = yf.download(
                    sym,
                    period="1d",
                    interval="5m",
                    progress=False
                )

                if df is None or df.empty:
                    st.warning(f"{sym} sin datos")
                    continue

                # 🔴 LIMPIAR COLUMNAS (CLAVE)
                if isinstance(df.columns, tuple) or hasattr(df.columns, "levels"):
                    df.columns = df.columns.get_level_values(0)

                # 🔴 ASEGURAR NUMÉRICOS
                df["Close"] = df["Close"].astype(float)

                # INDICADORES
                df["EMA9"] = ema(df["Close"], 9)
                df["EMA20"] = ema(df["Close"], 20)

                # 🔴 EXTRAER VALORES SEGUROS
                ema9 = df["EMA9"].iloc[-1].item()
                ema20 = df["EMA20"].iloc[-1].item()
                precio = df["Close"].iloc[-1].item()

                tendencia = "🟢 ALCISTA" if ema9 > ema20 else "🔴 BAJISTA"

                st.success(
                    f"{sym} | Precio: {round(precio,2)} | EMA9: {round(ema9,2)} | {tendencia}"
                )

        except Exception as e:
            st.error(f"{sym} error: {str(e)}")
