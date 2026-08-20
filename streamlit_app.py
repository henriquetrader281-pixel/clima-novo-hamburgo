import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Estação do Vale — Novo Hamburgo", page_icon="🌦️", layout="wide")

STATIONS = {
    "Novo Hamburgo — Centro": (-29.6783, -51.1308),
    "Lomba Grande": (-29.7605, -50.9929),
}
CACHE_DIR = Path(".weather_cache")
CACHE_DIR.mkdir(exist_ok=True)
LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
LOCAL_TZ_LABEL = "Horário de Brasília"

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
def get_river_history(days=2):
    response = requests.get("https://nivelguaiba.com.br/saoleopoldo.json", params={"_": int(datetime.now(LOCAL_TZ).timestamp())}, timeout=10)
    response.raise_for_status()
    raw = response.json()
    frame = pd.DataFrame({"Data/hora": pd.to_datetime(list(raw.keys())), "Nível (m)": list(raw.values())})
    cutoff = pd.Timestamp.now(tz=LOCAL_TZ).tz_localize(None) - pd.Timedelta(days=days)
    return frame[frame["Data/hora"] >= cutoff].sort_values("Data/hora")

@st.cache_data(ttl=900, show_spinner=False)
def get_basin_forecast():
    points = {
        "Taquara": (-29.6500, -50.7800),
        "Campo Bom": (-29.6800, -51.0500),
        "São Leopoldo": (-29.7600, -51.1500),
        "Novo Hamburgo": (-29.6783, -51.1308),
    }
    rows = []
    for place, (lat, lon) in points.items():
        params = {
            "latitude": lat, "longitude": lon, "timezone": "America/Sao_Paulo", "forecast_days": 7,
            "daily": "precipitation_sum,precipitation_probability_max,weather_code,wind_gusts_10m_max",
        }
        response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()["daily"]
        for i, day in enumerate(payload["time"]):
            rows.append({
                "Data": pd.to_datetime(day), "Ponto": place,
                "Chuva prevista (mm)": payload["precipitation_sum"][i],
                "Prob. chuva (%)": payload["precipitation_probability_max"][i],
                "Código": payload["weather_code"][i],
                "Rajada máxima (km/h)": payload["wind_gusts_10m_max"][i],
            })
    return pd.DataFrame(rows)

@st.cache_data(ttl=900, show_spinner=False)
def get_regional_impact():
    places = {
        "Novo Hamburgo": (-29.6783, -51.1308, "Rio dos Sinos", 3.50, 4.50, 30, 60, 60),
        "Porto Alegre": (-30.0346, -51.2177, "Guaíba", 2.10, 3.00, 40, 80, 70),
    }
    rows = []
    for city, (lat, lon, river, river_attention, river_flood, rain_attention, rain_alert, wind_alert) in places.items():
        params = {
            "latitude": lat, "longitude": lon, "timezone": "America/Sao_Paulo", "forecast_days": 2,
            "current": "precipitation,weather_code,wind_gusts_10m",
            "daily": "precipitation_sum,precipitation_probability_max,weather_code,wind_gusts_10m_max",
        }
        response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        current = payload.get("current", {})
        daily = payload.get("daily", {})
        rain24 = float(sum((daily.get("precipitation_sum") or [0])[:1]))
        max_rain = float(max(daily.get("precipitation_sum") or [0]))
        max_wind = float(max(daily.get("wind_gusts_10m_max") or [0]))
        code = int(current.get("weather_code", 0))
        if max_wind >= wind_alert or max_rain >= rain_alert:
            risk = "Alerta"
        elif max_wind >= wind_alert * 0.8 or max_rain >= rain_attention:
            risk = "Atenção"
        else:
            risk = "Normal"
        rows.append({"Município": city, "Risco meteorológico": risk, "Chuva 24h (mm)": round(rain24, 1), "Maior chuva diária (mm)": round(max_rain, 1), "Rajada máxima (km/h)": round(max_wind, 1), "Rio monitorado": river, "Nível do rio": "Consultar fonte oficial", "Latitude": lat, "Longitude": lon, "Código": code})
    return pd.DataFrame(rows)

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

def render_basin_analysis(data):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Histórico recente e previsão da bacia")
    st.caption("O histórico abaixo usa a série pública da estação Ponte 25 de Julho, em São Leopoldo. A previsão da bacia é uma agregação meteorológica de quatro pontos representativos; ela não é uma previsão hidrológica do nível futuro do rio.")
    try:
        history = get_river_history(2)
        if history.empty:
            st.info("Ainda não há histórico recente disponível para o gráfico.")
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=history["Data/hora"], y=history["Nível (m)"], mode="lines+markers", name="São Leopoldo", line={"color":"#5b9bc4", "width":3}, marker={"size":4}))
            fig.add_hline(y=4.50, line_dash="dash", line_color="#e0475c", annotation_text="Cota de inundação: 4,50 m")
            fig.add_hline(y=3.50, line_dash="dot", line_color="#e8c33d", annotation_text="Atenção: 3,50 m")
            fig.update_layout(height=360, margin={"l":10,"r":10,"t":20,"b":10}, paper_bgcolor="#152634", plot_bgcolor="#152634", font={"color":"#eef1ee"}, xaxis_title="Data/hora", yaxis_title="Nível (m)")
            st.plotly_chart(fig, use_container_width=True, theme=None)
            latest = history.iloc[-1]
            st.caption(f"Última leitura pública: **{latest['Nível (m)']:.2f} m** em {latest['Data/hora'].strftime('%d/%m/%Y %H:%M')}. Fonte: [Nível Guaíba / São Leopoldo](https://nivelguaiba.com.br/saoleopoldo).")
    except Exception as error:
        st.warning(f"Não foi possível carregar o histórico público agora: {error}")

    try:
        basin = get_basin_forecast()
        daily = basin.groupby("Data", as_index=False).agg({"Chuva prevista (mm)":"mean", "Prob. chuva (%)":"max", "Rajada máxima (km/h)":"max"})
        daily["Chuva prevista (mm)"] = daily["Chuva prevista (mm)"].round(1)
        st.markdown("#### Previsão meteorológica da bacia — próximos 7 dias")
        forecast_fig = go.Figure()
        forecast_fig.add_trace(go.Bar(x=daily["Data"], y=daily["Chuva prevista (mm)"], name="Chuva média nos pontos", marker_color="#5b9bc4"))
        forecast_fig.add_trace(go.Scatter(x=daily["Data"], y=daily["Prob. chuva (%)"], name="Maior probabilidade (%)", mode="lines+markers", yaxis="y2", line={"color":"#e8a33d", "width":2}))
        forecast_fig.update_layout(height=360, margin={"l":10,"r":10,"t":20,"b":10}, paper_bgcolor="#152634", plot_bgcolor="#152634", font={"color":"#eef1ee"}, xaxis_title="Data", yaxis={"title":"Chuva média (mm)"}, yaxis2={"title":"Probabilidade (%)", "overlaying":"y", "side":"right", "range":[0,100]})
        st.plotly_chart(forecast_fig, use_container_width=True, theme=None)
        st.dataframe(daily.rename(columns={"Chuva prevista (mm)":"Chuva média (mm)", "Prob. chuva (%)":"Maior prob. chuva (%)"}), use_container_width=True, hide_index=True)
        total = float(daily["Chuva prevista (mm)"].sum())
        st.info(f"A média dos quatro pontos indica aproximadamente **{total:.1f} mm** de chuva na bacia nos próximos sete dias. Use este indicador junto com o nível observado e os alertas oficiais; chuva prevista não equivale automaticamente a cheia.")
    except Exception as error:
        st.warning(f"Não foi possível carregar a previsão agregada da bacia agora: {error}")
    st.markdown('</div>', unsafe_allow_html=True)

def render_regional_impact():
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Mapa regional de impacto — Novo Hamburgo e Porto Alegre")
    st.caption("Indicador automático de apoio baseado na previsão meteorológica. Não substitui os alertas e mapas oficiais da Defesa Civil RS.")
    try:
        regional = get_regional_impact()
        colors = {"Normal": "#5b9bc4", "Atenção": "#e8c33d", "Alerta": "#e0475c"}
        fig = go.Figure()
        for _, row in regional.iterrows():
            fig.add_trace(go.Scattermap(lat=[row["Latitude"]], lon=[row["Longitude"]], mode="markers+text", text=[row["Município"]], textposition="top center", marker={"size":22, "color":colors.get(row["Risco meteorológico"], "#8da2b0")}, name=row["Município"], hovertemplate=f"<b>{row['Município']}</b><br>Risco: {row['Risco meteorológico']}<br>Chuva diária máxima: {row['Maior chuva diária (mm)']} mm<br>Rajada máxima: {row['Rajada máxima (km/h)']} km/h<extra></extra>"))
        fig.update_layout(map={"style":"open-street-map", "center":{"lat":-29.86,"lon":-51.18}, "zoom":8.2}, height=420, margin={"l":0,"r":0,"t":10,"b":0}, paper_bgcolor="#152634", font={"color":"#eef1ee"}, legend={"orientation":"h"})
        st.plotly_chart(fig, use_container_width=True, theme=None)
        st.dataframe(regional[["Município", "Risco meteorológico", "Chuva 24h (mm)", "Maior chuva diária (mm)", "Rajada máxima (km/h)", "Rio monitorado", "Nível do rio"]], use_container_width=True, hide_index=True)
        st.info("Para risco hidrológico, o painel cruza este indicador com as estações oficiais do Rio dos Sinos e do Guaíba quando a leitura pública está disponível. Quando o nível não é obtido automaticamente, o município permanece dependente da consulta oficial.")
    except Exception as error:
        st.warning(f"Não foi possível calcular o mapa regional agora: {error}")
    st.markdown('</div>', unsafe_allow_html=True)

def render_official_sources():
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Fontes oficiais de monitoramento")
    st.caption("As leituras abaixo devem ser conferidas diretamente nas plataformas oficiais durante eventos críticos. O painel reúne os acessos públicos para reduzir a dependência de uma única fonte.")
    sources = pd.DataFrame([
        ["Defesa Civil RS", "Rede Hidrometeorológica", "Estações hidrológicas e meteorológicas do Estado; atualização de missão crítica", "https://redehidrometeorologica.defesacivil.rs.gov.br/"],
        ["ClimaRS", "Rio dos Sinos — São Leopoldo", "Nível, tendência e estado da estação no painel estadual", "https://clima.rs.gov.br/"],
        ["ANA", "Hidroweb / Hidro-Telemetria", "Dados nacionais de níveis, vazões e chuva das estações da RHN", "https://www.snirh.gov.br/hidrotelemetria/Estacoes.aspx"],
        ["SGB/CPRM", "SACE — bacias monitoradas", "Sistemas de alertas hidrológicos e referências de bacias", "https://www.sgb.gov.br/sace/"],
        ["Defesa Civil NH", "Alertas municipais", "Orientações locais, alertas e canais da Defesa Civil de Novo Hamburgo", "https://www.novohamburgo.rs.gov.br/"]
    ], columns=["Órgão", "Fonte", "O que consultar", "Link"])
    st.dataframe(sources, use_container_width=True, hide_index=True, column_config={"Link": st.column_config.LinkColumn("Abrir fonte")})
    st.info("A Rede Hidrometeorológica da Defesa Civil RS é a fonte estadual prioritária para estações novas. Se uma leitura não aparecer aqui, use os links oficiais acima; isso pode indicar manutenção, atraso de transmissão ou diferença entre estações.")
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

now_local = datetime.now(LOCAL_TZ)
st.success(f"{source_note} · atualizado {now_local.strftime('%d/%m/%Y %H:%M')} ({LOCAL_TZ_LABEL})")
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
st.caption(f"Horários apresentados em {LOCAL_TZ_LABEL} (UTC−03:00).")
now = pd.Timestamp.now(tz=LOCAL_TZ).tz_localize(None)
hour_df = pd.DataFrame({"Hora": pd.to_datetime(hourly["time"]), "Temperatura": hourly["temperature_2m"], "Chuva (mm)": hourly["precipitation"], "Prob. chuva (%)": hourly["precipitation_probability"], "Condição": [WMO.get(c, "—") for c in hourly["weather_code"]]})
hour_df = hour_df[hour_df["Hora"] >= now].head(24).copy()
hour_df["Hora"] = hour_df["Hora"].dt.strftime("%H:%M")
st.dataframe(hour_df, use_container_width=True, hide_index=True)

st.subheader("Previsão de 15 dias")
st.caption(f"Datas e horários da previsão em {LOCAL_TZ_LABEL} (UTC−03:00).")
days = pd.DataFrame({"Data": pd.to_datetime(daily["time"]).strftime("%d/%m"), "Condição": [WMO.get(c, "—") for c in daily["weather_code"]], "Máxima (°C)": [round(x, 1) for x in daily["temperature_2m_max"]], "Mínima (°C)": [round(x, 1) for x in daily["temperature_2m_min"]], "Chuva (mm)": [round(x, 1) for x in daily["precipitation_sum"]], "Prob. chuva (%)": daily["precipitation_probability_max"]})
st.dataframe(days, use_container_width=True, hide_index=True)
st.bar_chart(days.set_index("Data")[["Chuva (mm)"]], color="#5b9bc4")

render_river(data)
render_basin_analysis(data)
render_regional_impact()
render_official_sources()
render_enso()

st.markdown('<footer>Sobre a precisão: este boletim usa o modelo aberto Open-Meteo. Para eventos de chuva forte, vento ou frente fria, confira também os boletins oficiais da Defesa Civil, INMET, ClimaRS e MetSul.</footer>', unsafe_allow_html=True)
