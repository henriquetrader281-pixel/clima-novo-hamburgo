import json
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup
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
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
:root{--bg:#071521;--surface:#0d2130;--surface2:#142d40;--text:#f2f7f7;--muted:#98afbd;--blue:#69b8e2;--gold:#f2b84b;--line:rgba(178,207,222,.15)}
html,body,[class*="css"]{font-family:'Inter',sans-serif}
.stApp{background:radial-gradient(ellipse 760px 520px at 8% -8%,rgba(47,129,174,.22),transparent 65%),radial-gradient(ellipse 650px 420px at 98% 10%,rgba(242,184,75,.09),transparent 62%),linear-gradient(145deg,#071521 0%,#0a1c2a 48%,#091927 100%);color:var(--text)}
[data-testid="stAppViewContainer"]{background:transparent}
.block-container{max-width:1380px;padding:1.7rem clamp(1rem,3vw,2.8rem) 4rem}
h1,h2,h3,h4{font-family:'Space Grotesk',sans-serif!important;letter-spacing:-.035em;color:var(--text)}
h1{font-size:clamp(2rem,4vw,3rem)!important;line-height:1.08!important}
h2{font-size:1.55rem!important}
h3{font-size:1.2rem!important}
p,li,label{color:#cfdae0}
.caption-mono,.metric-label,.small-mono{font-family:'IBM Plex Mono',monospace}
.caption-mono{color:#8bc9e8;letter-spacing:.18em;text-transform:uppercase;font-size:.68rem;margin-bottom:.4rem}
.subtitle,.muted,[data-testid="stCaptionContainer"]{color:var(--muted)!important}
.hero-clock{background:linear-gradient(145deg,rgba(19,47,66,.94),rgba(10,29,43,.8));border:1px solid var(--line);border-radius:18px;padding:13px 18px;text-align:center;box-shadow:0 14px 34px rgba(0,0,0,.17)}
.hero-clock .time{font:600 2rem 'Space Grotesk',sans-serif;color:#fff;letter-spacing:-.05em}
.hero-clock .date{font: .65rem 'IBM Plex Mono',monospace;color:var(--muted);text-transform:capitalize}
.header-status{display:inline-flex;align-items:center;gap:8px;border:1px solid rgba(105,184,226,.22);background:rgba(40,105,140,.13);border-radius:999px;padding:6px 11px;color:#b8d8e8;font: .62rem 'IBM Plex Mono',monospace;letter-spacing:.1em;text-transform:uppercase}
.header-status:before{content:"";width:7px;height:7px;border-radius:50%;background:#65d6a3;box-shadow:0 0 0 4px rgba(101,214,163,.12)}
.metric-card{background:linear-gradient(145deg,rgba(19,47,66,.98),rgba(10,29,43,.97));border:1px solid var(--line);border-radius:18px;padding:1.05rem 1.1rem;min-height:125px;box-shadow:0 14px 30px rgba(0,0,0,.14)}
.metric-label{color:#8eaaba;font-size:.65rem;letter-spacing:.12em;text-transform:uppercase}
.metric-value{color:#f4f8f7;font:700 clamp(1.35rem,2.5vw,2rem) 'Space Grotesk',sans-serif;margin-top:.55rem;letter-spacing:-.05em}
.metric-help{color:#9bb1bd;font-size:.72rem;margin-top:.2rem;line-height:1.45}
.panel{background:linear-gradient(145deg,rgba(16,41,59,.96),rgba(10,29,43,.96));border:1px solid var(--line);border-radius:20px;padding:1.25rem;margin:.7rem 0;box-shadow:0 14px 34px rgba(0,0,0,.12)}
[data-testid="stVerticalBlockBorderWrapper"]{background:rgba(13,33,48,.58);border:1px solid var(--line);border-radius:18px}
[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:6px;background:rgba(7,21,33,.68);padding:7px;border:1px solid var(--line);border-radius:999px}
[data-testid="stTabs"] button[data-baseweb="tab"]{height:42px;border-radius:999px;padding:0 16px;color:#a8bfcb;font: .68rem 'IBM Plex Mono',monospace}
[data-testid="stTabs"] button[aria-selected="true"]{background:linear-gradient(135deg,#244c65,#16364d);color:#fff;border:1px solid rgba(242,184,75,.4)}
[data-testid="stTabs"] [data-baseweb="tab-highlight"]{background:var(--gold)}
[data-testid="stSelectbox"]>div>div{background:#0d2130;border:1px solid var(--line);border-radius:12px}
.stButton>button,[data-testid="stBaseButton-secondary"]{background:rgba(105,184,226,.10);border:1px solid rgba(105,184,226,.28);color:#d8edf6;border-radius:999px;padding:.55rem 1rem;font: .68rem 'IBM Plex Mono',monospace;transition:.2s}
.stButton>button:hover,[data-testid="stBaseButton-secondary"]:hover{background:rgba(105,184,226,.18);border-color:var(--blue);color:#fff}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:12px;overflow:hidden}
[data-testid="stAlert"]{border-radius:14px}
.stSuccess,.stInfo,.stWarning,.stError{border-radius:14px}
.river-pill{display:inline-block;border:1px solid var(--gold);color:var(--gold);border-radius:999px;padding:.4rem .8rem;font:600 .68rem 'IBM Plex Mono',monospace;background:rgba(242,184,75,.07)}
.enso-stat{border-bottom:1px solid var(--line);padding:.65rem 0}
.enso-stat:last-child{border-bottom:0}
.enso-label{color:var(--muted);display:block;font:.64rem 'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:.1em}
.enso-value{color:var(--text);display:block;margin-top:.25rem;font-weight:600}
.region-high,.region-low{border-radius:13px;padding:.9rem;font-size:.84rem;line-height:1.5;min-height:100%}
.region-high{background:rgba(224,71,92,.12);border:1px solid rgba(224,71,92,.18);border-left:3px solid #e0475c}
.region-low{background:rgba(91,155,196,.12);border:1px solid rgba(91,155,196,.18);border-left:3px solid #5b9bc4}
.monitor-card{background:linear-gradient(145deg,rgba(15,40,58,.98),rgba(8,27,41,.98));border:1px solid var(--line);border-radius:18px;padding:1rem 1.1rem;margin:.3rem 0 .8rem}
.monitor-kicker{color:#8bc9e8;font: .62rem 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase}
.monitor-state{display:inline-block;border-radius:999px;padding:.3rem .65rem;font:600 .6rem 'IBM Plex Mono',monospace;letter-spacing:.05em;margin:.55rem 0}
.state-clear{color:#9ce0bd;border:1px solid rgba(101,214,163,.28);background:rgba(101,214,163,.08)}
.state-alert{color:#ffb9c2;border:1px solid rgba(224,71,92,.35);background:rgba(224,71,92,.1)}
.state-warn{color:#ffd58a;border:1px solid rgba(242,184,75,.3);background:rgba(242,184,75,.09)}
.state-offline{color:#ffb6a9;border:1px solid rgba(224,129,47,.3);background:rgba(224,129,47,.08)}
.monitor-entry{background:rgba(7,21,33,.4);border:1px solid rgba(178,207,222,.13);border-radius:12px;padding:.75rem .85rem;margin:.55rem 0}
.monitor-entry strong{color:#edf5f6;font-size:.82rem}
.monitor-meta{color:#92adbb;font:.62rem 'IBM Plex Mono',monospace;margin-top:.35rem}
.monitor-entry a{color:#9acde4!important;font-size:.72rem}
.source-note{color:#829baa;font-size:.7rem;line-height:1.55}
footer{color:#829baa;font-size:.76rem;border-top:1px solid var(--line);margin-top:1.5rem;padding-top:1rem}
a{color:#9acde4!important}
hr{border-color:var(--line)}
@media(max-width:700px){
 .block-container{padding:1rem .8rem 3rem}
 [data-testid="stTabs"] [data-baseweb="tab-list"]{overflow-x:auto;border-radius:14px}
 [data-testid="stTabs"] button[data-baseweb="tab"]{padding:0 10px;font-size:.6rem}
 .metric-card{min-height:105px;padding:.8rem}
 .metric-value{font-size:1.35rem}
}
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
        if gust >= 100: alerts.append(("Rajadas severas previstas", f"{day}: rajadas de {gust:.0f} km/h — não é confirmação de tornado"))
        elif gust >= 60: alerts.append(("Vento forte previsto", f"{day}: rajadas de {gust:.0f} km/h"))
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
        for tag, label in (("taquara", "Taquara (a montante)"), ("campobom", "Campo Bom (intermediária)"), ("saoleopoldo", "São Leopoldo (a jusante)")):
            item = next((x for x in items if tag in x.get("tags", [])), None)
            if item:
                title = item.get("title", "—")
                if tag == "saoleopoldo":
                    match = re.search(r"([\d,]+)m", title)
                    if match:
                        level = float(match.group(1).replace(",", "."))
                        if level >= 4.50:
                            title += " — Inundação"
                        elif level >= 3.50:
                            title += " — Atenção de inundação"
                        if level >= 4.50:
                            st.error(f"ALERTA: São Leopoldo atingiu {level:.2f} m — cota de inundação: 4,50 m. Consulte a Defesa Civil.")
                        elif level >= 3.50:
                            st.warning(f"Atenção: São Leopoldo está em {level:.2f} m — cota de atenção: 3,50 m.")
                published = item.get("date_published")
                stations.append({"Estação": label, "Leitura": title, "Atualizado": pd.to_datetime(published).strftime("%d/%m %H:%M") if published else "—"})
            else:
                stations.append({"Estação": label, "Leitura": "sem leitura recente no feed", "Atualizado": "—"})
        st.dataframe(pd.DataFrame(stations), use_container_width=True, hide_index=True)
    except Exception:
        st.info("Não foi possível carregar as leituras ao vivo agora. Consulte [Nível Guaíba — São Leopoldo](https://nivelguaiba.com.br/saoleopoldo).")

    thresholds = pd.DataFrame([
        ["Novo Hamburgo", "6,60 m", "~6,80–7,00 m"], ["Campo Bom", "—", "7,20 m"],
        ["São Leopoldo (ANA 87382000)", "3,50 m", "4,50 m"], ["Sapiranga", "—", "sem cota oficial divulgada"],
    ], columns=["Município", "Cota de atenção", "Cota de inundação"])
    st.dataframe(thresholds, use_container_width=True, hide_index=True)
    st.caption("As cotas são referências divulgadas em boletins oficiais e podem ser revistas pela Defesa Civil. O painel acompanha Taquara, Campo Bom e São Leopoldo; Novo Hamburgo não tem, neste painel, sensor público automatizado.")
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

@st.cache_data(ttl=21600, show_spinner=False)
def get_enso_probabilities():
    url = "https://cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/probabilities/"
    response = requests.get(url, timeout=15, headers={"User-Agent": "Estacao-do-Vale/1.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", id="probabilities-table") or soup.find("table", class_=re.compile("probabilities"))
    if not table:
        raise ValueError("A tabela de probabilidades da NOAA não foi encontrada.")
    rows = []
    for row in table.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if len(cells) == 4 and cells[0] != "Season":
            rows.append({"Trimestre": cells[0], "La Niña (%)": int(cells[1]), "Neutral (%)": int(cells[2]), "El Niño (%)": int(cells[3])})
    if not rows:
        raise ValueError("A tabela da NOAA não contém linhas de probabilidade válidas.")
    text = soup.get_text(" ", strip=True)
    issued_match = re.search(r"Issued\\s+([A-Za-z]+\\s+\\d{4})", text)
    issued = issued_match.group(1) if issued_match else "data não informada"
    return pd.DataFrame(rows), issued


# ---------------- MONITORAMENTO OFICIAL DE EVENTOS EXTREMOS ----------------
INMET_RSS_URL = "https://apiprevmet3.inmet.gov.br/avisos/rss"
CHM_WARNINGS_URL = "https://www.marinha.mil.br/chm/dados-do-smm-avisos-de-mau-tempo/avisos-de-mau-tempo"
CHM_CYCLONE_ARCHIVE_URL = "https://www.marinha.mil.br/chm/dados-do-smm-monitoramento-de-ciclones"
CHM_MONTHS = {"JAN": 1, "FEV": 2, "FEB": 2, "MAR": 3, "ABR": 4, "APR": 4, "MAI": 5, "MAY": 5,
              "JUN": 6, "JUL": 7, "AGO": 8, "AUG": 8, "SET": 9, "SEP": 9, "OUT": 10, "OCT": 10,
              "NOV": 11, "DEZ": 12, "DEC": 12}
INMET_HEADERS = {"User-Agent": "Estacao-do-Vale/2.0 (weather dashboard)", "Accept": "application/rss+xml, application/xml, text/xml"}

def _xml_child_text(node, wanted):
    for child in node.iter():
        if child.tag.split("}")[-1].lower() == wanted.lower():
            return (child.text or "").strip()
    return ""

def _point_in_polygon(lat, lon, polygon):
    """Ray-casting test. Polygon points use CAP's 'latitude,longitude' notation."""
    points = []
    for pair in polygon.split():
        try:
            p_lat, p_lon = [float(v) for v in pair.split(",")[:2]]
            points.append((p_lon, p_lat))
        except (ValueError, TypeError):
            continue
    if len(points) < 3:
        return False
    inside = False
    x, y = lon, lat
    j = len(points) - 1
    for i in range(len(points)):
        xi, yi = points[i]
        xj, yj = points[j]
        intersects = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi)
        if intersects:
            inside = not inside
        j = i
    return inside

def _parse_cap_details(url):
    """Fetch one CAP alert to obtain its geographic area and validity window."""
    if not url or not url.startswith("https://apiprevmet3.inmet.gov.br/"):
        return {}
    try:
        response = requests.get(url, headers=INMET_HEADERS, timeout=5)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        info_nodes = [node for node in root.iter() if node.tag.split("}")[-1].lower() == "info"]
        details = {"areas": [], "polygons": [], "expires": None, "description": ""}
        for info in info_nodes[:4]:
            description = _xml_child_text(info, "description")
            if description:
                details["description"] = (details["description"] + " " + description).strip()
            for node in info.iter():
                tag = node.tag.split("}")[-1].lower()
                if tag == "expires" and node.text:
                    details["expires"] = node.text.strip()
                if tag == "areadesc" and node.text:
                    details["areas"].append(node.text.strip())
                if tag == "polygon" and node.text:
                    details["polygons"].append(node.text.strip())
        return details
    except Exception:
        return {}

@st.cache_data(ttl=300, show_spinner=False)
def get_inmet_alerts():
    response = requests.get(INMET_RSS_URL, headers=INMET_HEADERS, timeout=12)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = [node for node in root.iter() if node.tag.split("}")[-1].lower() == "item"]
    alerts = []
    lat, lon = STATIONS["Novo Hamburgo — Centro"]
    for item in items[:30]:
        title = _xml_child_text(item, "title")
        description = BeautifulSoup(_xml_child_text(item, "description"), "html.parser").get_text(" ", strip=True)
        link = _xml_child_text(item, "link")
        published = _xml_child_text(item, "pubdate")
        full_text = f"{title} {description}".lower()
        if re.search(r"tornado|tromba.?d.?agua|tromba.?d.?água|funil de vento", full_text):
            kind = "tornado"
        elif re.search(r"ciclone|ciclonico|ciclônico|subtropical", full_text):
            kind = "ciclone"
        elif "granizo" in full_text:
            kind = "granizo"
        elif re.search(r"tempestade|trovoada|raios", full_text):
            kind = "tempestade"
        elif re.search(r"vendaval|vento forte|ventos fortes|rajada", full_text):
            kind = "vento"
        elif re.search(r"chuva intensa|chuvas intensas|chuva forte", full_text):
            kind = "chuva"
        else:
            continue

        cap = _parse_cap_details(link)
        area_text = " | ".join(cap.get("areas", []))
        detail_text = f"{description} {cap.get('description', '')} {area_text}".lower()
        polygons = cap.get("polygons", [])
        if polygons:
            is_local = any(_point_in_polygon(lat, lon, polygon) for polygon in polygons)
            location_basis = "polígono oficial CAP"
        else:
            is_local = bool(re.search(
                r"\b(rio grande do sul|rs|novo hamburgo|lomba grande|são leopoldo|sao leopoldo|campo bom|sapiranga|vale do sinos|metropolitana de porto alegre)\b",
                detail_text, re.I
            ))
            location_basis = "descrição textual; posição aproximada" if is_local else "localização não confirmada"
        expires = cap.get("expires")
        valid = True
        if expires:
            try:
                expiry = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                valid = expiry >= datetime.now(timezone.utc)
            except ValueError:
                pass
        if valid:
            alerts.append({
                "title": title or "Aviso INMET",
                "description": description or cap.get("description", ""),
                "type": kind,
                "link": link,
                "published": published,
                "areas": area_text,
                "local": is_local,
                "location_basis": location_basis,
                "expires": expires,
            })
    return alerts

def _chm_utc_datetime(day, hhmm, month, year, issue_day):
    year = int(year)
    if int(day) < int(issue_day):
        if month == 12:
            month, year = 1, year + 1
        else:
            month += 1
    return datetime(year, month, int(day), int(hhmm[:2]), int(hhmm[2:]), tzinfo=ZoneInfo("UTC"))

@st.cache_data(ttl=300, show_spinner=False)
def get_chm_notices():
    response = requests.get(CHM_WARNINGS_URL, headers={"User-Agent": "Mozilla/5.0 Estacao-do-Vale/2.0"}, timeout=12)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = re.sub(r"[ \t]+", " ", soup.get_text("\n", strip=True))
    # The first half of the page is Portuguese; English translations repeat the same notices.
    if "ALPHA AREA" in text:
        text = text.split("ALPHA AREA", 1)[0]
    blocks = re.split(r"(?=AVISO\s+NR\.?\s+[A-Z0-9-]+/\d{4})", text, flags=re.I)
    notices = []
    now_utc = datetime.now(timezone.utc)
    for block in blocks:
        header = re.search(r"AVISO\s+NR\.?\s+([A-Z0-9-]+/\d{4})", block, flags=re.I)
        if not header:
            continue
        title_match = re.search(r"AVISO\s+(?:ESPECIAL\s+)?(?:DE\s+)?[A-ZÁÉÍÓÚÇ ]{4,80}", block, flags=re.I)
        issue_match = re.search(
            r"EMITIDO\s+ÀS\s+(\d{4})Z\s*-\s*[\wÁÉÍÓÚÇ-]+\s*-\s*(\d{2})/([A-Z]{3})/(\d{4})",
            block, flags=re.I
        )
        validity = re.search(r"VÁLIDO\s+ATÉ\s+(\d{2})(\d{4})Z", block, flags=re.I)
        start_at = re.search(r"A\s+PARTIR\s+DE\s+(\d{2})(\d{4})Z", block, flags=re.I)
        issued = None
        starts = None
        expires = None
        if issue_match:
            issue_hhmm, issue_day, issue_month_text, issue_year = issue_match.groups()
            month = CHM_MONTHS.get(issue_month_text.upper())
            if month:
                issued = _chm_utc_datetime(issue_day, issue_hhmm, month, issue_year, issue_day)
                if validity:
                    expires = _chm_utc_datetime(validity.group(1), validity.group(2), month, issue_year, issue_day)
                if start_at:
                    starts = _chm_utc_datetime(start_at.group(1), start_at.group(2), month, issue_year, issue_day)
        active = bool(expires is not None and expires >= now_utc and (starts is None or starts <= now_utc))
        expired = bool(expires is not None and expires < now_utc)
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        notices.append({
            "number": header.group(1),
            "title": title_match.group(0).strip() if title_match else (lines[1] if len(lines) > 1 else "Aviso de mau tempo"),
            "text": re.sub(r"\s+", " ", block).strip(),
            "issued": issued,
            "starts": starts,
            "expires": expires,
            "active": active,
            "expired": expired,
            # Without a parsed expiry time, validity cannot be confirmed safely.
            "unconfirmed": expires is None,
            "area": next((line for line in lines if re.search(r"^ÁREA\s+(?:COSTEIRA|OCEÂNICA|ENTRE|AO|DO|DA|DE)", line, re.I)), ""),
        })
    return notices

def _render_monitor_item(item, source):
    title = item.get("title", "Aviso meteorológico")
    meta = []
    if item.get("areas"):
        meta.append(item["areas"])
    if item.get("published"):
        meta.append(item["published"])
    elif item.get("expires"):
        meta.append("Válido até " + str(item["expires"]))
    area_line = " · ".join(meta)
    st.markdown(
        '<div class="monitor-entry"><strong>' + title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") +
        '</strong><div class="monitor-meta">' + area_line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") +
        '</div></div>', unsafe_allow_html=True
    )
    if item.get("link"):
        target = item["link"] if item["link"].startswith("https://apiprevmet3.inmet.gov.br/") else "https://avisos.inmet.gov.br/"
        st.markdown(f"[Abrir aviso oficial — {source} ↗]({target})")

def render_extreme_event_monitors():
    st.markdown("### Tornados e ciclones")
    st.caption("Avisos oficiais vigentes. Rajadas previstas e temporais não são, por si só, confirmação de tornado ou ciclone.")
    left, right = st.columns(2, gap="large")

    # Tornado monitor — INMET alert feed plus geographic check using each CAP polygon.
    with left:
        st.markdown('<div class="monitor-card"><div class="monitor-kicker">INMET · Alertas CAP/RSS</div><h3>🌪️ Monitor de tornados</h3></div>', unsafe_allow_html=True)
        try:
            inmet = get_inmet_alerts()
            regional = [a for a in inmet if a["local"]]
            tornadoes = [a for a in regional if a["type"] == "tornado"]
            other = [a for a in regional if a["type"] != "tornado"]
            if tornadoes:
                st.markdown('<span class="monitor-state state-alert">AVISO ESPECÍFICO IDENTIFICADO</span>', unsafe_allow_html=True)
                st.error("O texto de um aviso oficial menciona tornado ou fenômeno relacionado e sua área atinge Novo Hamburgo, conforme CAP ou descrição geográfica.")
                for item in tornadoes[:4]:
                    _render_monitor_item(item, "INMET")
            elif other:
                st.markdown('<span class="monitor-state state-warn">TEMPO SEVERO · SEM AVISO ESPECÍFICO DE TORNADO</span>', unsafe_allow_html=True)
                st.warning("Há avisos oficiais de tempo severo que atingem a região, mas nenhum deles menciona tornado explicitamente.")
                for item in other[:4]:
                    _render_monitor_item(item, "INMET")
            else:
                st.markdown('<span class="monitor-state state-clear">SEM AVISO ESPECÍFICO DE TORNADO</span>', unsafe_allow_html=True)
                st.success("Nenhum aviso vigente do INMET mencionando tornado foi encontrado para o ponto de Novo Hamburgo nesta consulta.")
                st.caption("Isso não significa risco zero nem substitui radar, Defesa Civil ou observação meteorológica.")
            st.caption(f"Fonte consultada: INMET · {len(inmet)} aviso(s) de fenômenos relevantes no feed; {len(regional)} com área local confirmada. Atualização em cache de 5 minutos.")
        except Exception as error:
            st.markdown('<span class="monitor-state state-offline">FONTE INDISPONÍVEL</span>', unsafe_allow_html=True)
            st.error(f"Não foi possível consultar o INMET. O painel não presume ausência de risco. Detalhe: {error}")
        st.markdown("[Abrir avisos oficiais do INMET ↗](https://avisos.inmet.gov.br/)")

    # Cyclone monitor — active CHM notices, cross-checked with INMET local CAP alerts.
    with right:
        st.markdown('<div class="monitor-card"><div class="monitor-kicker">Marinha / CHM + INMET</div><h3>🌀 Monitor de ciclones</h3></div>', unsafe_allow_html=True)
        chm_error = None
        inmet_error = None
        try:
            chm = get_chm_notices()
        except Exception as error:
            chm = []
            chm_error = str(error)
        try:
            inmet = get_inmet_alerts()
        except Exception as error:
            inmet = []
            inmet_error = str(error)

        chm_cyclone_notices = [
            a for a in chm
            if not a.get("expired", False)
            and re.search(r"ciclone|ciclon|subtropical|tropical", a.get("text", ""), re.I)
        ]
        chm_active_cyclones = [a for a in chm_cyclone_notices if a.get("active", False)]
        chm_unconfirmed_cyclones = [a for a in chm_cyclone_notices if a.get("unconfirmed", a.get("expires") is None)]
        inmet_cyclones = [a for a in inmet if a["local"] and a["type"] == "ciclone"]

        if chm_active_cyclones or inmet_cyclones:
            st.markdown('<span class="monitor-state state-alert">AVISO DE CICLONE IDENTIFICADO</span>', unsafe_allow_html=True)
            for item in chm_active_cyclones[:4]:
                expires_at = item.get("expires")
                expiry = expires_at.astimezone(LOCAL_TZ).strftime("%d/%m %H:%M") if expires_at else "vigência não identificada"
                st.warning(f"**{item.get('title', 'Aviso de mau tempo')}** · CHM aviso {item.get('number', 'sem número')} · válido até {expiry} (horário de Brasília)")
                if item.get("area"):
                    st.caption(item["area"])
                st.markdown("[Abrir aviso vigente da Marinha ↗](" + CHM_WARNINGS_URL + ")")
            for item in inmet_cyclones[:4]:
                _render_monitor_item(item, "INMET")
        elif chm_error and inmet_error:
            st.markdown('<span class="monitor-state state-offline">FONTES INDISPONÍVEIS</span>', unsafe_allow_html=True)
            st.error("Não foi possível consultar Marinha nem INMET. O painel não presume ausência de ciclone.")
            st.caption(f"CHM: {chm_error} · INMET: {inmet_error}")
        elif chm_unconfirmed_cyclones:
            st.markdown('<span class="monitor-state state-warn">AVISO LOCALIZADO · VIGÊNCIA NÃO CONFIRMADA</span>', unsafe_allow_html=True)
            st.warning("A página do CHM contém texto relacionado a ciclone, mas não foi possível validar automaticamente o horário de expiração. Confira o aviso original antes de tratá-lo como vigente.")
            for item in chm_unconfirmed_cyclones[:3]:
                st.caption(f"CHM aviso {item.get('number', 'sem número')} · {item.get('title', 'Aviso de mau tempo')}")
                st.markdown("[Conferir aviso oficial ↗](" + CHM_WARNINGS_URL + ")")
        elif chm_error or inmet_error:
            st.markdown('<span class="monitor-state state-warn">CONSULTA PARCIAL</span>', unsafe_allow_html=True)
            st.warning("Uma das fontes oficiais não respondeu. Consulte os avisos originais antes de concluir que não há risco.")
            if chm_error:
                st.caption("CHM indisponível nesta consulta.")
            if inmet_error:
                st.caption("INMET indisponível nesta consulta.")
        else:
            st.markdown('<span class="monitor-state state-clear">SEM AVISO ESPECIAL ATIVO IDENTIFICADO</span>', unsafe_allow_html=True)
            st.success("Não foi encontrado aviso vigente mencionando ciclone tropical ou subtropical na METAREA V, nem aviso local do INMET classificado como ciclone.")
            st.caption("O CHM publica avisos especiais para ciclones tropicais/subtropicais. Ciclones extratropicais podem aparecer em avisos gerais de vento e tempo severo.")
            # Display any active coastal warning for context without relabelling it as a cyclone.
            coast = [a for a in chm if a["active"] and re.search(r"RS|SANTA CATARINA|PARANÁ|CHUÍ|TRAMANDAÍ|RIO GRANDE", a["text"], re.I)]
            if coast:
                st.caption("Outros avisos marítimos ativos na costa sul (não classificados como ciclone):")
                for item in coast[:3]:
                    expiry = item["expires"].astimezone(LOCAL_TZ).strftime("%d/%m %H:%M") if item["expires"] else "vigência não identificada"
                    st.info(f"**{item['title']}** · {item['area']} · até {expiry}")
        st.markdown(f"[Avisos vigentes do CHM ↗]({CHM_WARNINGS_URL})")
        st.markdown(f"[Arquivo histórico de ciclones tropicais/subtropicais ↗]({CHM_CYCLONE_ARCHIVE_URL})")
        st.caption("O arquivo de ciclones do CHM é histórico; não é um rastreador ao vivo.")

    st.markdown("---")
    st.caption("Segurança: a ausência de aviso específico não significa ausência de risco. Em situação crítica, siga os canais da Defesa Civil, INMET e Marinha.")

def render_enso():
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    try:
        enso_df, issued = get_enso_probabilities()
        current_row = enso_df.iloc[0]
        current_prob = int(current_row["El Niño (%)"])
        st.subheader("El Niño — Monitor ENOS atualizado pela NOAA")
        st.write("As probabilidades abaixo são consultadas diretamente no outlook oficial do Climate Prediction Center (NOAA/CPC) e atualizadas automaticamente a cada seis horas.")
        left, right = st.columns([1.4, 1])
        with left:
            st.markdown('<span class="river-pill">El Niño ativo</span>', unsafe_allow_html=True)
            st.markdown(f"### {current_prob}% · probabilidade NOAA")
            st.caption(f"Trimestre mais próximo: **{current_row['Trimestre']}** · boletim emitido em **{issued}**.")
        with right:
            st.markdown('<div class="enso-stat"><span class="enso-label">Próximo trimestre</span><span class="enso-value">'+str(current_row["Trimestre"])+'</span></div>', unsafe_allow_html=True)
            st.markdown('<div class="enso-stat"><span class="enso-label">El Niño</span><span class="enso-value">'+str(current_prob)+'%</span></div>', unsafe_allow_html=True)
            st.markdown('<div class="enso-stat"><span class="enso-label">Neutral</span><span class="enso-value">'+str(int(current_row["Neutral (%)"]))+'%</span></div>', unsafe_allow_html=True)
        st.markdown("#### Probabilidades por trimestre")
        chart_df = enso_df.set_index("Trimestre")[["La Niña (%)", "Neutral (%)", "El Niño (%)"]]
        st.bar_chart(chart_df, color=["#4f86b5", "#8da2b0", "#e0475c"])
        st.dataframe(enso_df, use_container_width=True, hide_index=True)
        st.caption("A probabilidade é do fenômeno ENSO por trimestre e não representa, sozinha, a probabilidade de chuva ou de cheia no Rio Grande do Sul.")
    except Exception as error:
        st.warning(f"A NOAA não respondeu agora; o indicador dinâmico não pôde ser atualizado: {error}")
        st.info("Consulte o boletim oficial da NOAA/CPC diretamente até a próxima atualização.")
    a, b = st.columns(2)
    with a: st.markdown('<div class="region-high"><b>Sul do Brasil (RS · SC · PR)</b> — o El Niño pode alterar os padrões de chuva e aumentar riscos de temporais e cheias, mas os impactos locais dependem da previsão e dos alertas atuais.</div>', unsafe_allow_html=True)
    with b: st.markdown('<div class="region-low"><b>Interpretação</b> — este indicador climático não substitui os avisos da Defesa Civil, INMET ou ClimaRS.</div>', unsafe_allow_html=True)
    st.markdown("[Probabilidades oficiais NOAA/CPC](https://cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/probabilities/) · [Boletim ENSO](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml) · [NOAA/NCEI — ENSO](https://www.ncei.noaa.gov/access/monitoring/enso/) · [INMET](https://portal.inmet.gov.br/)")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- INTERFACE PRINCIPAL ----------------
now_local = datetime.now(LOCAL_TZ)
weekday_pt = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"][now_local.weekday()]
hero_left, hero_right = st.columns([5, 1.15])
with hero_left:
    st.markdown('<div class="caption-mono">ESTAÇÃO DO VALE · CENTRAL METEOROLÓGICA LOCAL</div>', unsafe_allow_html=True)
    st.title("Clima — Novo Hamburgo & Lomba Grande")
    st.caption("Previsão do tempo, alertas oficiais, monitoramento do Rio dos Sinos e acompanhamento de eventos extremos.")
    st.markdown('<span class="header-status">Dados meteorológicos e fontes oficiais</span>', unsafe_allow_html=True)
with hero_right:
    st.markdown(
        '<div class="hero-clock"><div class="time">' + now_local.strftime("%H:%M") +
        '</div><div class="date">' + weekday_pt + " · " + now_local.strftime("%d/%m/%Y") + '</div></div>',
        unsafe_allow_html=True
    )

control_left, control_right = st.columns([3, 1])
with control_left:
    station = st.selectbox("Localização", list(STATIONS.keys()), label_visibility="visible")
with control_right:
    if st.button("↻ Atualizar dados", use_container_width=True):
        get_weather.clear()
        get_river_feed.clear()
        get_river_history.clear()
        get_inmet_alerts.clear()
        get_chm_notices.clear()
        st.rerun()

try:
    data = get_weather(station)
    save_cached(station, data)
    source_note = "Dados atualizados pela Open-Meteo"
except Exception as error:
    data = load_cached(station)
    if not data:
        st.error(f"Não foi possível carregar os dados meteorológicos: {error}")
        st.stop()
    source_note = "Últimos dados guardados localmente"
    st.warning("A API não respondeu agora; exibindo a última previsão guardada.")

current, daily, hourly = data["current"], data["daily"], data["hourly"]
condition = WMO.get(current.get("weather_code", 0), "Condição desconhecida")
st.caption(f"{source_note} · consulta em {now_local.strftime('%d/%m/%Y %H:%M')} · horário de Brasília")

tab_now, tab_forecast, tab_events, tab_river, tab_enso = st.tabs([
    "☀️  Agora", "📅  Previsão", "🌪️  Eventos extremos", "🌊  Rio e bacia", "🌎  ENOS"
])

with tab_now:
    st.subheader(f"Condições atuais — {station}")
    metric_cols = st.columns(5, gap="medium")
    with metric_cols[0]:
        card("Temperatura", f"{current['temperature_2m']:.1f} °C", condition)
    with metric_cols[1]:
        card("Sensação térmica", f"{current['apparent_temperature']:.1f} °C", "temperatura aparente")
    with metric_cols[2]:
        card("Umidade", f"{current['relative_humidity_2m']:.0f}%", "umidade relativa")
    with metric_cols[3]:
        card("Vento", f"{current['wind_speed_10m']:.0f} km/h", f"{format_wind(current['wind_direction_10m'])} · rajadas {current['wind_gusts_10m']:.0f} km/h")
    with metric_cols[4]:
        card("Pressão", f"{current['pressure_msl']:.0f} hPa", f"nuvens {current['cloud_cover']:.0f}%")

    st.divider()
    st.subheader("Resumo de riscos previstos")
    alerts = compute_alerts(data)
    if alerts:
        for title, detail in alerts[:8]:
            if "severas" in title.lower() or "muito forte" in title.lower() or "granizo" in title.lower():
                st.warning(f"**{title}** — {detail}")
            else:
                st.info(f"**{title}** — {detail}")
    else:
        st.success("Nenhum risco automático de chuva intensa, granizo ou rajadas fortes identificado nos próximos dias.")
    a, b = st.columns(2, gap="large")
    with a:
        rain_today = daily["precipitation_sum"][0]
        prob3 = max(hourly.get("precipitation_probability", [0])[:3])
        card("Chuva prevista hoje", f"{rain_today:.1f} mm", f"probabilidade nas próximas 3h: {prob3}%")
    with b:
        card("Maior rajada prevista", f"{max(daily['wind_gusts_10m_max']):.0f} km/h", "máximo do horizonte de 15 dias; não é medição atual")

with tab_forecast:
    st.subheader("Próximas 24 horas")
    st.caption("Horários apresentados em America/Sao_Paulo (UTC−03:00).")
    now = pd.Timestamp.now(tz=LOCAL_TZ).tz_localize(None)
    hour_df = pd.DataFrame({
        "Hora": pd.to_datetime(hourly["time"]),
        "Temperatura (°C)": hourly["temperature_2m"],
        "Chuva (mm)": hourly["precipitation"],
        "Prob. chuva (%)": hourly["precipitation_probability"],
        "Condição": [WMO.get(c, "—") for c in hourly["weather_code"]],
    })
    hour_df = hour_df[hour_df["Hora"] >= now].head(24).copy()
    hour_df["Hora"] = hour_df["Hora"].dt.strftime("%H:%M")
    st.dataframe(hour_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Previsão de 15 dias")
    days = pd.DataFrame({
        "Data": pd.to_datetime(daily["time"]).strftime("%d/%m"),
        "Condição": [WMO.get(c, "—") for c in daily["weather_code"]],
        "Máxima (°C)": [round(x, 1) for x in daily["temperature_2m_max"]],
        "Mínima (°C)": [round(x, 1) for x in daily["temperature_2m_min"]],
        "Chuva (mm)": [round(x, 1) for x in daily["precipitation_sum"]],
        "Prob. chuva (%)": daily["precipitation_probability_max"],
    })
    chart_left, chart_right = st.columns([1.2, 1], gap="large")
    with chart_left:
        st.markdown("#### Chuva prevista por dia")
        st.bar_chart(days.set_index("Data")[["Chuva (mm)"]], color="#69b8e2")
    with chart_right:
        st.markdown("#### Temperaturas")
        temp_df = pd.DataFrame({
            "Máxima": daily["temperature_2m_max"],
            "Mínima": daily["temperature_2m_min"],
        }, index=days["Data"])
        st.line_chart(temp_df, color=["#f2b84b", "#69b8e2"])
    st.dataframe(days, use_container_width=True, hide_index=True)

with tab_events:
    render_extreme_event_monitors()
    st.divider()
    st.subheader("Risco previsto na estação selecionada")
    st.caption("Estes são indicadores de previsão do modelo meteorológico, não avisos oficiais de tornado ou ciclone.")
    risk_data = []
    for i, day in enumerate(daily["time"][:15]):
        rain = float(daily["precipitation_sum"][i])
        gust = float(daily["wind_gusts_10m_max"][i])
        code = int(daily["weather_code"][i])
        risk_data.append({
            "Data": pd.to_datetime(day).strftime("%d/%m"),
            "Condição": WMO.get(code, "—"),
            "Chuva (mm)": round(rain, 1),
            "Rajada (km/h)": round(gust, 1),
            "Granizo/raios": "Sim" if code in (95, 96, 99) else "Não indicado",
        })
    st.dataframe(pd.DataFrame(risk_data), use_container_width=True, hide_index=True)

with tab_river:
    render_river(data)
    render_basin_analysis(data)
    render_regional_impact()
    render_official_sources()

with tab_enso:
    render_enso()

st.markdown(
    '<footer>Estação do Vale · Novo Hamburgo e Lomba Grande · Open-Meteo, INMET, Marinha/CHM, Nível Guaíba e NOAA/CPC. '
    'Em situações de risco, siga as orientações oficiais da Defesa Civil e dos órgãos meteorológicos.</footer>',
    unsafe_allow_html=True
)
