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
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
.stApp { background:#0f1c26; color:#eef1ee; }
.block-container { max-width:1040px; padding:2rem 2rem 4rem; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif; }
.caption-mono,.metric-label,.small-mono { font-family:'IBM Plex Mono',monospace; }
.caption-mono { color:#5b9bc4; letter-spacing:.15em; text-transform:uppercase; font-size:.72rem; }
.subtitle,.muted { color:#8da2b0; }
.panel { background:#152634; border:1px solid rgba(199,211,218,.15); border-radius:6px; padding:1.15rem; margin:.8rem 0; }
.metric-card { background:#152634; border:1px solid rgba(199,211,218,.15); border-radius:5px; padding:1rem; min-height:112px; }
.metric-label { color:#8da2b0; font-size:.68rem; letter-spacing:.11em; text-transform:uppercase; }
.metric-value { color:#eef1ee; font:600 1.8rem 'Space Grotesk',sans-serif; margin-top:.45rem; }
.metric-help { color:#8da2b0; font-size:.78rem; margin-top:.2rem; }
.river-pill { display:inline-block; border:1px solid #e8a33d; color:#e8a33d; border-radius:20px; padding:.35rem .75rem; font:600 .75rem 'IBM Plex Mono',monospace; }
.enso-stat { border-bottom:1px solid rgba(199,211,218,.12); padding:.6rem 0; }
.enso-stat:last-child { border-bottom:0; }
.enso-label { color:#8da2b0; display:block; font: .68rem 'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:.1em; }
.enso-value { color:#eef1ee; display:block; margin-top:.25rem; }
.region-high,.region-low { border-radius:4px; padding:.8rem; font-size:.88rem; }
.region-high { background:rgba(224,71,92,.12); border-left:3px solid #e0475c; }
.region-low { background:rgba(91,155,196,.12); border-left:3px solid #5b9bc4; }
footer { color:#7c93a3; font-size:.8rem; border-top:1px solid rgba(199,211,218,.15); margin-top:1.5rem; padding-top:1rem; }
a { color:#e8a33d !important; }
</style>
""", unsafe_allow_html=True)

WMO = {
    0: "Céu limpo", 1: "Predomínio de sol", 2: "Parcialmente nublado", 3: "Encoberto",
    45: "Nevoeiro", 48: "Nevoeiro com geada", 51: "Garoa fraca", 53: "Garoa", 55: "Garoa forte",
    56: "Garoa gelada", 57: "Garoa gelada forte", 61: "Chuva fraca", 63: "Chuva", 65: "Chuva forte",
    66: "Chuva gelada", 67: "Chuva gelada forte", 71: "Neve fraca", 73: "Neve", 75: "Neve forte",
    77: "Grãos de neve", 80: "Pancadas fracas", 81: "Pancadas de chuva", 82: "Pancadas fortes",
    85: "Pancadas de neve", 86: "Pancadas de neve fortes", 95: "Trovoadas", 96: "Trovoada com granizo", 99: "Trovoada forte com granizo",
}

@st.cache_data(ttl=900, show_spinner=False)
def get_weather(name: str):
    lat, lon = STATIONS[name]
    params = {
        "latitude": lat, "longitude": lon, "timezone": "America/Sao_Paulo", "forecast_days": 15,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,pressure_msl,cloud_cover",
        "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code,relative_humidity_2m,pressure_msl,cloud_cover,wind_speed_10m,wind_gusts_10m,wind_direction_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max",
    }
    response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    if not data.get("current") or not data.get("hourly") or not data.get("daily"):
        raise ValueError("A resposta da previsão veio incompleta.")
    return data

@st.cache_data(ttl=900, show_spinner=False)
def get_river_feed():
    response = requests.get("https://nivelguaiba.com.br/feed", timeout=10)
    response.raise_for_status()
    return response.json()

def cache_path(name):
    return CACHE_DIR / ("weather_" + str(abs(hash(name))) + ".json")

def load_cached(name):
    try:
        path = cache_path(name)
        return json.loads(path.read_text()) if path.exists() else None
    except Exception:
        return None

def save_cached(name, data):
    try:
        cache_path(name).write_text(json.dumps(data))
    except Exception:
        pass

def card(label, value, help_text=""):
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-help">{help_text}</div></div>', unsafe_allow_html=True)

def format_wind(deg):
    directions = ["N", "NE", "L", "SE", "S", "SO", "O", "NO"]
    return directions[round(deg / 45) % 8]

def compute_alerts(data):
    alerts = []
    daily = data["daily"]
    for i, code in enumerate(daily["weather_code"][:15]):
        rain = daily["precipitation_sum"][i]
        gust = daily["wind_gusts_10m_max"][i]
        day = "hoje" if i == 0 else pd.to_datetime(daily["time"][i]).strftime("%d/%m")
        if code in (96, 99): alerts.append(("Granizo", f"{day}: trovoada com granizo"))
        elif code == 95: alerts.append(("Tempestade", f"{day}: trovoadas previstas"))
        if rain >= 100: alerts.append(("Chuva muito forte", f"{day}: {rain:.0f} mm acumulados"))
        elif rain >= 50: alerts.append(("Chuva forte", f"{day}: {rain:.0f} mm acumulados"))
        elif rain >= 20: alerts.append(("Chuva moderada", f"{day}: {rain:.0f} mm acumulados"))
        if gust >= 100: alerts.append(("Vendaval severo", f"{day}: rajadas de {gust:.0f} km/h"))
        elif gust >= 60: alerts.append(("Vento forte", f"{day}: rajadas de {gust:.0f} km/h"))
    return list(dict.fromkeys(alerts))

def render_river(data):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Rio dos Sinos — monitoramento")
    rain3 = sum(data["daily"]["precipitation_sum"][:3])
    if rain3 < 20: risk, color = "Normal", "#5b9bc4"
    elif rain3 < 60: risk, color = "Atenção", "#e8c33d"
    elif rain3 < 120: risk, color = "Alerta", "#e0812f"
    else: risk, color = "Risco elevado de cheia", "#e0475c"
    st.markdown(f'<span class="river-pill" style="border-color:{color};color:{color}">● {risk}</span>', unsafe_allow_html=True)
    st.caption(f"Estimativa complementar com base na chuva prevista para os próximos 3 dias: **{rain3:.0f} mm**. Isto não substitui a leitura da régua do rio.")

    try:
        feed = get_river_feed()
        items = feed.get("items", [])
        stations = []
        for tag, label in (("taquara", "Taquara (a montante)"), ("saoleopoldo", "São Leopoldo (a jusante)")):
            item = next((x for x in items if tag in x.get("tags", [])), None)
            if item:
                title = item.get("title", "—")
                published = item.get("date_published")
                stations.append({"Estação": label, "Leitura": title, "Atualizado": pd.to_datetime(published).strftime("%d/%m %H:%M") if published else "—"})
            else:
                stations.append({"Estação": label, "Leitura": "sem leitura recente no feed", "Atualizado": "—"})
        st.dataframe(pd.DataFrame(stations), use_container_width=True, hide_index=True)
    except Exception:
        st.info("Não foi possível carregar as leituras ao vivo agora. Consulte [Nível Guaíba — São Leopoldo](https://nivelguaiba.com.br/saoleopoldo).")

    thresholds = pd.DataFrame([
        ["Novo Hamburgo", "6,60 m", "~6,80–7,00 m"], ["Campo Bom", "—", "7,20 m"],
        ["São Leopoldo (ANA 87382000)", "—", "4,50 m"], ["Sapiranga", "—", "sem cota oficial divulgada"],
    ], columns=["Município", "Cota de atenção", "Cota de inundação"])
    st.dataframe(thresholds, use_container_width=True, hide_index=True)
    st.caption("As cotas são referências divulgadas em boletins anteriores e podem ser revistas pela Defesa Civil. As leituras disponíveis são de Taquara e São Leopoldo; Novo Hamburgo não tem, neste painel, sensor público automatizado.")
    st.markdown("[Gráfico completo — Nível Guaíba](https://nivelguaiba.com.br/saoleopoldo) · [Níveis dos rios — ClimaRS](https://clima.rs.gov.br/) · [SACE — SGB/CPRM](https://www.sgb.gov.br/sace/) · [Defesa Civil NH](https://www.novohamburgo.rs.gov.br/)")
    st.markdown('</div>', unsafe_allow_html=True)

def render_enso():
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    left, right = st.columns([1.4, 1])
    with left:
        st.subheader("El Niño — Monitor ENOS 2026/2027")
        st.write("Formação confirmada pela NOAA em 11 de junho de 2026 — águas do Pacífico Equatorial com anomalias acima de 2°C perto da costa da América do Sul, padrão clássico do fenómeno.")
        st.markdown('<span class="river-pill">El Niño ativo</span>', unsafe_allow_html=True)
        st.markdown("### 63% · SUPER EL NIÑO")
    with right:
        st.markdown('<div class="enso-stat"><span class="enso-label">Persistência</span><span class="enso-value">&gt;90% de chance ativo até início de 2027</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="enso-stat"><span class="enso-label">Anomalia TSM (Pacífico)</span><span class="enso-value">+1,8°C a +2,5°C</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="enso-stat"><span class="enso-label">Boletim oficial</span><span class="enso-value">INMET · INPE · ANA · CEMADEN · SGB — 29/jun/2026</span></div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    with a: st.markdown('<div class="region-high"><b>Sul do Brasil (RS · SC · PR)</b> — chuvas acima da média e risco elevado de temporais, cheias e deslizamentos, mais intenso na primavera e verão.</div>', unsafe_allow_html=True)
    with b: st.markdown('<div class="region-low"><b>Norte / Nordeste</b> — tendência de estiagem e chuva abaixo da média.</div>', unsafe_allow_html=True)
    st.write("Anos de El Niño historicamente elevam o risco de cheias no Rio Grande do Sul. Por isso, vale acompanhar de perto o indicador do Rio dos Sinos ao longo da primavera e do verão.")
    st.markdown("[Mapa por estado — Monitor El Niño Brasil](https://monitorelninobrasi.com.br/) · [NOAA/NCEI — ENSO](https://www.ncei.noaa.gov/access/monitoring/enso/) · [INMET](https://portal.inmet.gov.br/)")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="caption-mono">ESTAÇÃO DO VALE · BOLETIM LOCAL</div>', unsafe_allow_html=True)
st.title("Clima — Novo Hamburgo & Lomba Grande")
st.write("Previsão de 15 dias, alertas de tempestade e granizo, monitoramento do Rio dos Sinos e rastreio do El Niño — via Open-Meteo e fontes públicas.")

station = st.selectbox("Localização", list(STATIONS.keys()))
if st.button("↻ Atualizar agora"):
    get_weather.clear(); get_river_feed.clear()

try:
    data = get_weather(station)
    save_cached(station, data)
    source_note = "Dados em tempo real"
except Exception as error:
    data = load_cached(station)
    if not data:
        st.error(f"Não foi possível carregar os dados meteorológicos: {error}")
        st.stop()
    source_note = "Últimos dados guardados localmente"
    st.warning("A API não respondeu agora; a mostrar a última previsão guardada.")

st.success(f"{source_note} · atualizado {datetime.now().strftime('%d/%m/%Y %H:%M')}")
current, daily, hourly = data["current"], data["daily"], data["hourly"]
condition = WMO.get(current.get("weather_code", 0), "Condição desconhecida")

st.subheader(f"Agora em {station}")
cols = st.columns(5)
with cols[0]: card("Temperatura", f"{current['temperature_2m']:.1f} °C", condition)
with cols[1]: card("Sensação", f"{current['apparent_temperature']:.1f} °C", "temperatura aparente")
with cols[2]: card("Humidade", f"{current['relative_humidity_2m']:.0f}%", "humidade relativa")
with cols[3]: card("Vento", f"{current['wind_speed_10m']:.0f} km/h", f"{format_wind(current['wind_direction_10m'])} · rajadas {current['wind_gusts_10m']:.0f} km/h")
with cols[4]: card("Pressão", f"{current['pressure_msl']:.0f} hPa", f"nuvens {current['cloud_cover']:.0f}%")

st.subheader("Alertas")
alerts = compute_alerts(data)
if alerts:
    for title, detail in alerts[:8]: st.warning(f"**{title}** — {detail}")
else: st.info("Nenhum alerta automático identificado para os próximos dias.")

st.subheader("Chuva acumulada e vento")
a, b = st.columns(2)
with a:
    rain_today = daily["precipitation_sum"][0]
    prob3 = max(hourly.get("precipitation_probability", [0])[:3])
    card("Chuva hoje", f"{rain_today:.1f} mm", f"probabilidade nas próximas 3h: {prob3}%")
with b:
    card("Rajada máxima prevista", f"{max(daily['wind_gusts_10m_max']):.0f} km/h", "nos próximos 15 dias")

st.subheader("Próximas 24 horas")
now = pd.Timestamp.now(tz="America/Sao_Paulo").tz_localize(None)
hour_df = pd.DataFrame({"Hora": pd.to_datetime(hourly["time"]), "Temperatura": hourly["temperature_2m"], "Chuva (mm)": hourly["precipitation"], "Prob. chuva (%)": hourly["precipitation_probability"], "Condição": [WMO.get(c, "—") for c in hourly["weather_code"]]})
hour_df = hour_df[hour_df["Hora"] >= now].head(24).copy()
hour_df["Hora"] = hour_df["Hora"].dt.strftime("%H:%M")
st.dataframe(hour_df, use_container_width=True, hide_index=True)

st.subheader("Previsão de 15 dias")
days = pd.DataFrame({"Data": pd.to_datetime(daily["time"]).strftime("%d/%m"), "Condição": [WMO.get(c, "—") for c in daily["weather_code"]], "Máxima (°C)": [round(x, 1) for x in daily["temperature_2m_max"]], "Mínima (°C)": [round(x, 1) for x in daily["temperature_2m_min"]], "Chuva (mm)": [round(x, 1) for x in daily["precipitation_sum"]], "Prob. chuva (%)": daily["precipitation_probability_max"]})
st.dataframe(days, use_container_width=True, hide_index=True)
st.bar_chart(days.set_index("Data")[["Chuva (mm)"]], color="#5b9bc4")

render_river(data)
render_enso()

st.markdown('<footer>Sobre a precisão: este boletim usa o modelo aberto Open-Meteo. Para eventos de chuva forte, vento ou frente fria, confira também os boletins oficiais da Defesa Civil, INMET, ClimaRS e MetSul.</footer>', unsafe_allow_html=True)
