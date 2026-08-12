import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Estação do Vale — Novo Hamburgo", page_icon="🌦️", layout="wide")

STATIONS = {
    "Novo Hamburgo — Centro": (-29.6783, -51.1308),
    "Lomba Grande": (-29.7605, -50.9929),
}
CACHE_DIR = Path(".weather_cache")
CACHE_DIR.mkdir(exist_ok=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
:root { --navy:#0f1c26; --panel:#152634; --line:rgba(199,211,218,.15); --paper:#eef1ee; --muted:#8da2b0; --blue:#5b9bc4; --gold:#e8a33d; }
.stApp { background:var(--navy); color:var(--paper); }
.block-container { max-width:1100px; padding-top:2.5rem; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif; }
.metric-card { background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:1.1rem; min-height:120px; }
.metric-label { color:var(--muted); font:11px 'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:.1em; }
.metric-value { color:var(--paper); font:600 30px 'Space Grotesk',sans-serif; margin-top:.5rem; }
.metric-help { color:var(--muted); font-size:.82rem; margin-top:.25rem; }
section[data-testid="stSidebar"] { background:var(--panel); }
</style>
""", unsafe_allow_html=True)

WMO = {
    0: "Céu limpo", 1: "Predomínio de sol", 2: "Parcialmente nublado", 3: "Encoberto",
    45: "Nevoeiro", 48: "Nevoeiro com geada", 51: "Garoa fraca", 53: "Garoa", 55: "Garoa forte",
    61: "Chuva fraca", 63: "Chuva", 65: "Chuva forte", 71: "Neve fraca", 73: "Neve", 80: "Pancadas fracas",
    81: "Pancadas de chuva", 82: "Pancadas fortes", 95: "Trovoadas", 96: "Trovoada com granizo", 99: "Trovoada forte com granizo",
}

@st.cache_data(ttl=900, show_spinner=False)
def get_weather(name: str):
    lat, lon = STATIONS[name]
    params = {
        "latitude": lat, "longitude": lon, "timezone": "America/Sao_Paulo", "forecast_days": 15,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,pressure_msl,cloud_cover",
        "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_gusts_10m_max",
    }
    response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    if not data.get("current") or not data.get("daily"):
        raise ValueError("A resposta da previsão veio incompleta.")
    return data

def card(label, value, help_text=""):
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-help">{help_text}</div></div>', unsafe_allow_html=True)

def load_cached(name):
    path = CACHE_DIR / ("weather_" + str(abs(hash(name))) + ".json")
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None

def save_cached(name, data):
    path = CACHE_DIR / ("weather_" + str(abs(hash(name))) + ".json")
    path.write_text(json.dumps(data))

st.caption("ESTAÇÃO DO VALE · BOLETIM LOCAL")
st.title("Clima — Novo Hamburgo & Lomba Grande")
st.write("Previsão de 15 dias, alertas de tempestade e indicador meteorológico local, com dados abertos da Open-Meteo.")

station = st.selectbox("Localização", list(STATIONS.keys()))
col_refresh, col_time = st.columns([1, 3])
with col_refresh:
    refresh = st.button("↻ Atualizar agora", use_container_width=True)
with col_time:
    st.caption(f"Atualização automática da API a cada 15 minutos · {datetime.now().strftime('%d/%m/%Y %H:%M')}")

if refresh:
    get_weather.clear()

try:
    data = get_weather(station)
    save_cached(station, data)
    source_note = "Dados em tempo real"
except Exception as error:
    data = load_cached(station)
    if data:
        source_note = "Últimos dados guardados localmente"
        st.warning(f"A API não respondeu agora. A mostrar a última previsão disponível. ({error})")
    else:
        st.error(f"Não foi possível carregar a previsão: {error}")
        st.info("Verifica a ligação à internet e usa o botão Atualizar agora.")
        st.stop()

current = data["current"]
daily = data["daily"]
code = current.get("weather_code", 0)
condition = WMO.get(code, "Condição meteorológica desconhecida")

st.success(source_note)
st.subheader(f"Agora em {station}")
cols = st.columns(5)
with cols[0]: card("Temperatura", f"{current['temperature_2m']:.1f} °C", condition)
with cols[1]: card("Sensação", f"{current['apparent_temperature']:.1f} °C", "temperatura aparente")
with cols[2]: card("Humidade", f"{current['relative_humidity_2m']:.0f}%", "humidade relativa")
with cols[3]: card("Vento", f"{current['wind_speed_10m']:.0f} km/h", f"rajada {current['wind_gusts_10m']:.0f} km/h")
with cols[4]: card("Chuva agora", f"{current['precipitation']:.1f} mm", f"pressão {current['pressure_msl']:.0f} hPa")

st.subheader("Alertas calculados")
alerts = []
for i, rain in enumerate(daily["precipitation_sum"][:15]):
    gust = daily.get("wind_gusts_10m_max", [0] * 15)[i]
    weather_code = daily["weather_code"][i]
    if weather_code in (95, 96, 99): alerts.append("Trovoada ou granizo previsto")
    if rain >= 50: alerts.append(f"Chuva forte prevista: {rain:.0f} mm")
    if gust >= 60: alerts.append(f"Vento forte previsto: rajada até {gust:.0f} km/h")
if alerts:
    for alert in dict.fromkeys(alerts): st.warning(alert)
else:
    st.info("Nenhum alerta automático identificado para os próximos dias.")

st.subheader("Previsão de 15 dias")
days = pd.DataFrame({
    "Data": pd.to_datetime(daily["time"]).strftime("%d/%m"),
    "Condição": [WMO.get(c, "—") for c in daily["weather_code"]],
    "Máxima (°C)": [round(x, 1) for x in daily["temperature_2m_max"]],
    "Mínima (°C)": [round(x, 1) for x in daily["temperature_2m_min"]],
    "Chuva (mm)": [round(x, 1) for x in daily["precipitation_sum"]],
    "Prob. chuva (%)": daily["precipitation_probability_max"],
})
st.dataframe(days, use_container_width=True, hide_index=True)

st.subheader("Chuva prevista")
chart = days.set_index("Data")[["Chuva (mm)"]]
st.bar_chart(chart, color="#5b9bc4")

st.caption("Fonte: Open-Meteo · Este painel é informativo e não substitui alertas oficiais da Defesa Civil, INMET ou autoridades locais.")
