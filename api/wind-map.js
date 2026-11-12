import { json, method } from './_lib/core.js';

const POINTS = [
  [-29.52, -51.34], [-29.52, -51.18], [-29.52, -51.02],
  [-29.68, -51.34], [-29.68, -51.18], [-29.68, -51.02],
  [-29.84, -51.34], [-29.84, -51.18], [-29.84, -51.02]
];
export default async function handler(req, res) {
  if (!method(req, res, ['GET'])) return;
  try {
    const url = new URL('https://api.open-meteo.com/v1/forecast');
    url.searchParams.set('latitude', POINTS.map(p => p[0]).join(','));
    url.searchParams.set('longitude', POINTS.map(p => p[1]).join(','));
    url.searchParams.set('current', 'temperature_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,weather_code');
    url.searchParams.set('wind_speed_unit', 'kmh');
    url.searchParams.set('timezone', 'America/Sao_Paulo');
    const response = await fetch(url);
    if (!response.ok) return json(res, 502, { error: 'wind_source_unavailable' });
    const rows = await response.json();
    const data = Array.isArray(rows) ? rows : [rows];
    return json(res, 200, {
      source: 'Open-Meteo',
      fetchedAt: new Date().toISOString(),
      points: data.map((row, i) => ({ lat: POINTS[i][0], lon: POINTS[i][1], ...row.current }))
    });
  } catch (error) { console.error(error); return json(res, 502, { error: 'wind_map_failed' }); }
}
