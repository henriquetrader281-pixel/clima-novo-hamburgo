import { SignJWT, importPKCS8 } from 'jose';
import { json, method } from './_lib/core.js';
const conditionToWmo = {
  Clear: 0, MostlyClear: 1, PartlyCloudy: 2, MostlyCloudy: 3, Cloudy: 3,
  Foggy: 45, Haze: 45, Breezy: 2, Windy: 3,
  Drizzle: 51, Rain: 61, HeavyRain: 65, Showers: 80, ScatteredShowers: 80,
  Thunderstorms: 95, IsolatedThunderstorms: 95, StrongStorms: 99,
  Flurries: 71, Snow: 73, HeavySnow: 75, Sleet: 68, FreezingRain: 66
};
const value = (field, fallback = 0) => field?.value ?? field ?? fallback;
const kmh = field => value(field) * 3.6;
function normalizeWeather(raw) {
  const current = raw.currentWeather || {};
  const hourly = raw.forecastHourly?.hours || [];
  const daily = raw.forecastDaily?.days || [];
  return {
    source: 'Apple WeatherKit',
    current: {
      temperature_2m: value(current.temperature), apparent_temperature: value(current.apparentTemperature),
      relative_humidity_2m: value(current.humidity) * 100, pressure_msl: value(current.pressure),
      cloud_cover: value(current.cloudCover) * 100, wind_speed_10m: kmh(current.windSpeed),
      wind_gusts_10m: kmh(current.windGust), wind_direction_10m: value(current.windDirection),
      precipitation: value(current.precipitationAmount), weather_code: conditionToWmo[current.conditionCode] ?? 3
    },
    hourly: {
      time: hourly.map(h => h.forecastStart),
      temperature_2m: hourly.map(h => value(h.temperature)), relative_humidity_2m: hourly.map(h => value(h.humidity) * 100),
      pressure_msl: hourly.map(h => value(h.pressure)), cloud_cover: hourly.map(h => value(h.cloudCover) * 100),
      wind_speed_10m: hourly.map(h => kmh(h.windSpeed)), wind_gusts_10m: hourly.map(h => kmh(h.windGust)),
      wind_direction_10m: hourly.map(h => value(h.windDirection)), precipitation: hourly.map(h => value(h.precipitationAmount)),
      precipitation_probability: hourly.map(h => Math.round(value(h.precipitationChance) * 100)),
      weather_code: hourly.map(h => conditionToWmo[h.conditionCode] ?? 3)
    },
    daily: {
      time: daily.map(d => d.forecastStart?.slice(0, 10)), weather_code: daily.map(d => conditionToWmo[d.conditionCode] ?? 3),
      temperature_2m_max: daily.map(d => value(d.temperatureMax ?? d.highTemperature)), temperature_2m_min: daily.map(d => value(d.temperatureMin ?? d.lowTemperature)),
      apparent_temperature_max: daily.map(d => value(d.apparentTemperatureMax ?? d.highTemperature)), apparent_temperature_min: daily.map(d => value(d.apparentTemperatureMin ?? d.lowTemperature)),
      precipitation_sum: daily.map(d => value(d.precipitationAmount)), precipitation_probability_max: daily.map(d => Math.round(value(d.precipitationChance) * 100)),
      wind_speed_10m_max: daily.map(d => kmh(d.maxWindSpeed ?? d.windSpeed)), wind_gusts_10m_max: daily.map(d => kmh(d.maxWindGust ?? d.windGust))
    }
  };
}
async function appleToken() {
  const key = process.env.WEATHERKIT_PRIVATE_KEY?.replace(/\\n/g, '\n');
  if (!key || !process.env.WEATHERKIT_TEAM_ID || !process.env.WEATHERKIT_KEY_ID || !process.env.WEATHERKIT_SERVICE_ID) throw new Error('WeatherKit não configurado');
  const privateKey = await importPKCS8(key, 'ES256');
  return new SignJWT({ sub: process.env.WEATHERKIT_SERVICE_ID })
    .setProtectedHeader({ alg: 'ES256', kid: process.env.WEATHERKIT_KEY_ID, id: `${process.env.WEATHERKIT_TEAM_ID}.${process.env.WEATHERKIT_SERVICE_ID}` })
    .setIssuer(process.env.WEATHERKIT_TEAM_ID).setIssuedAt().setExpirationTime('5m').sign(privateKey);
}
export default async function handler(req, res) {
  if (!method(req, res, ['GET'])) return;
  const lat = Number(req.query.lat), lon = Number(req.query.lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) return json(res, 400, { error: 'invalid_coordinates' });
  try {
    const token = await appleToken();
    const url = `https://weatherkit.apple.com/api/v1/weather/pt-BR/${lat}/${lon}?dataSets=currentWeather,forecastDaily,forecastHourly&countryCode=BR&timezone=America%2FSao_Paulo`;
    const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) return json(res, response.status === 401 ? 502 : response.status, { error: 'weatherkit_unavailable' });
    return json(res, 200, normalizeWeather(await response.json()));
  } catch (error) { console.error(error); return json(res, 503, { error: 'weatherkit_not_configured' }); }
}
