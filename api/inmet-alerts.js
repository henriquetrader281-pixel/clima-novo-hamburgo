import { json, method } from './_lib/core.js';
const RSS_URL = 'https://apiprevmet3.inmet.gov.br/avisos/rss';
const LOCAL = { lat: -29.6783, lon: -51.1308 };
const STATES = { RS: [-30.1, -53.0], SC: [-27.2, -50.2], PR: [-24.7, -51.5] };
function clean(value = '') { return value.replace(/<!\[CDATA\[|\]\]>/g, '').replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim(); }
function classify(title, description) {
  const text = `${title} ${description}`.toLowerCase();
  if (/tornado/.test(text)) return 'tornado';
  if (/granizo/.test(text)) return 'granizo';
  if (/vendaval|vento forte|ventos fortes/.test(text)) return 'vento';
  if (/tempestade|raios/.test(text)) return 'tempestade';
  return null;
}
function coordinates(text) {
  const upper = text.toUpperCase();
  const state = Object.keys(STATES).find(code => new RegExp(`\\b${code}\\b`).test(upper));
  if (upper.includes('NOVO HAMBURGO') || upper.includes('SÃO LEOPOLDO') || upper.includes('CAMPO BOM')) return { lat: LOCAL.lat, lon: LOCAL.lon, precision: 'local' };
  if (state) return { lat: STATES[state][0], lon: STATES[state][1], precision: 'estado' };
  return { lat: LOCAL.lat, lon: LOCAL.lon, precision: 'aproximado' };
}
export default async function handler(req, res) {
  if (!method(req, res, ['GET'])) return;
  try {
    const response = await fetch(RSS_URL, { signal: AbortSignal.timeout(10000), headers: { Accept: 'application/rss+xml, application/xml' } });
    if (!response.ok) return json(res, 502, { error: 'inmet_unavailable' });
    const xml = await response.text();
    const alerts = [...xml.matchAll(/<item>([\s\S]*?)<\/item>/gi)].map(match => {
      const block = match[1];
      const title = clean(block.match(/<title>([\s\S]*?)<\/title>/i)?.[1]);
      const description = clean(block.match(/<description>([\s\S]*?)<\/description>/i)?.[1]);
      const type = classify(title, description);
      if (!type) return null;
      const link = clean(block.match(/<link>([\s\S]*?)<\/link>/i)?.[1]);
      const publishedAt = clean(block.match(/<pubDate>([\s\S]*?)<\/pubDate>/i)?.[1]);
      return { title, description, type, link, publishedAt, ...coordinates(`${title} ${description}`) };
    }).filter(Boolean);
    return json(res, 200, { source: 'INMET', fetchedAt: new Date().toISOString(), note: 'Quando o INMET não fornece geometria municipal, a posição é aproximada pelo município ou centroide estadual.', alerts });
  } catch (error) { console.error(error); return json(res, 502, { error: 'inmet_alerts_failed' }); }
}
