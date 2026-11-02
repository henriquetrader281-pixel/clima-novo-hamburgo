import { fetchWeatherKit, normalizeWeather } from './_lib/weatherkit.js';
import { json, method } from './_lib/core.js';

export default async function handler(req, res) {
  if (!method(req, res, ['GET'])) return;
  const lat = Number(req.query.lat), lon = Number(req.query.lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) return json(res, 400, { error: 'invalid_coordinates' });
  try { return json(res, 200, normalizeWeather(await fetchWeatherKit(lat, lon))); }
  catch (error) { console.error(error); return json(res, 503, { error: 'weatherkit_unavailable' }); }
}
