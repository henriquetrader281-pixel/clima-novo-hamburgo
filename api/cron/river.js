import webpush from 'web-push';
import { fetchWeatherAlertState } from '../../_lib/weatherkit.js';
import { alertTransitions, fetchRiver, json, method, readJson, redis, requireCron, writeJson } from '../../_lib/core.js';
const SUBSCRIPTIONS_KEY = 'clima:push:subscriptions';
const STATE_KEY = 'clima:river:last-state';
const WEATHER_STATE_KEY = 'clima:weather:last-state';
const WEATHER_STATIONS = {
  novoHamburgo: { label: 'Novo Hamburgo', lat: -29.6783, lon: -51.1308 },
  lombaGrande: { label: 'Lomba Grande', lat: -29.7605, lon: -50.9929 }
};

function weatherTransitions(previous, current) {
  const alerts = [];
  for (const [key, station] of Object.entries(current)) {
    const before = previous?.[key] || { wind: 'normal', hail: 'normal' };
    if (station.wind !== 'normal' && station.wind !== before.wind) alerts.push({ type: 'wind', key, station });
    if (station.hail !== 'normal' && station.hail !== before.hail) alerts.push({ type: 'hail', key, station });
  }
  return alerts;
}

async function sendAlerts(alerts) {
  if (!alerts.length) return { sent: 0, removed: 0 };
  const subscriptions = await redis('SMEMBERS', SUBSCRIPTIONS_KEY) || [];
  let sent = 0, removed = 0;
  for (const raw of subscriptions) {
    let subscription;
    try { subscription = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch { continue; }
    for (const alert of alerts) {
      const { station } = alert;
      let title, body, tag, requireInteraction = false;
      if (alert.type === 'river') {
        const flood = station.status === 'inundação';
        title = `Alerta do Rio dos Sinos — ${station.label}`;
        body = `${station.label}: ${station.level?.toFixed(2)} m — ${flood ? 'cota de inundação atingida.' : 'nível de atenção atingido.'}`;
        tag = `rio-${station.key}-${station.status}`;
        requireInteraction = flood;
      } else if (alert.type === 'hail') {
        title = `Alerta de granizo — ${WEATHER_STATIONS[alert.key].label}`;
        body = `Possibilidade de granizo nas próximas horas. Condição WeatherKit: ${station.conditionCode || 'tempestade'}.`;
        tag = `clima-${alert.key}-granizo-${station.hail}`;
        requireInteraction = true;
      } else {
        const severe = station.wind === 'vento-severo';
        title = `Alerta de vento — ${WEATHER_STATIONS[alert.key].label}`;
        body = `Rajadas previstas de até ${station.maxGust} km/h. ${severe ? 'Risco de danos: procure abrigo.' : 'Fique atento e proteja objetos soltos.'}`;
        tag = `clima-${alert.key}-vento-${station.wind}`;
        requireInteraction = severe;
      }
      try {
        await webpush.sendNotification(subscription, JSON.stringify({ title, body, tag, url: '/', requireInteraction }));
        sent++;
      } catch (error) {
        if (error.statusCode === 404 || error.statusCode === 410) { await redis('SREM', SUBSCRIPTIONS_KEY, JSON.stringify(subscription)); removed++; }
        else console.error('push', error.statusCode || error.message);
      }
    }
  }
  return { sent, removed };
}

export default async function handler(req, res) {
  if (!method(req, res, ['GET'])) return;
  if (!requireCron(req, res)) return;
  if (!process.env.VAPID_PRIVATE_KEY || !process.env.VAPID_PUBLIC_KEY || !process.env.VAPID_SUBJECT) return json(res, 503, { error: 'push_not_configured' });
  try {
    webpush.setVapidDetails(process.env.VAPID_SUBJECT, process.env.VAPID_PUBLIC_KEY, process.env.VAPID_PRIVATE_KEY);
    const currentRiver = await fetchRiver();
    const previousRiver = await readJson(STATE_KEY, null);
    await writeJson(STATE_KEY, currentRiver);
    const riverAlerts = alertTransitions(previousRiver, currentRiver).map(station => ({ type: 'river', station }));

    const currentWeather = {};
    for (const [key, station] of Object.entries(WEATHER_STATIONS)) {
      try { currentWeather[key] = await fetchWeatherAlertState(station.lat, station.lon); }
      catch (error) { console.error(`weather ${key}`, error.message); }
    }
    const previousWeather = await readJson(WEATHER_STATE_KEY, null);
    await writeJson(WEATHER_STATE_KEY, currentWeather);
    const weatherAlerts = weatherTransitions(previousWeather, currentWeather);
    const push = await sendAlerts([...riverAlerts, ...weatherAlerts]);
    return json(res, 200, { ok: true, fetchedAt: currentRiver.fetchedAt, riverAlerts, weatherAlerts, ...push });
  } catch (error) { console.error(error); return json(res, 502, { error: 'alert_cron_failed' }); }
}
