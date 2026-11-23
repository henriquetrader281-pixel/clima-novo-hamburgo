import { json, method } from './_lib/core.js';

const RSS_URL = 'https://apiprevmet3.inmet.gov.br/avisos/rss';
const LOCAL = { lat: -29.6783, lon: -51.1308 };
const STATES = { RS: [-30.1, -53.0], SC: [-27.2, -50.2], PR: [-24.7, -51.5] };

function clean(value = '') {
  return value
    .replace(/<!\[CDATA\[|\]\]>/g, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ')
    .trim();
}

function classify(title, description) {
  const text = `${title} ${description}`.toLowerCase();

  // Tornado é identificado apenas quando o aviso menciona o fenômeno.
  if (/tornado|tromba.?d.?agua|tromba.?d.?água|funil de vento/.test(text)) return 'tornado';
  if (/ciclone|ciclonico|ciclônico|subtropical|tropical cyclone/.test(text)) return 'ciclone';
  if (/granizo/.test(text)) return 'granizo';
  if (/vendaval|vento forte|ventos fortes|rajadas intensas/.test(text)) return 'vento';
  if (/tempestade|trovoada|raios/.test(text)) return 'tempestade';
  if (/chuva intensa|chuvas intensas|chuva forte/.test(text)) return 'chuva';
  return null;
}

function severity(title, description) {
  const text = `${title} ${description}`;
  const match = text.match(/(Grande\s+Perigo|Perigo\s+Potencial|Perigo)/i);
  if (!match) return 'Não informada';
  const value = match[1].toLowerCase();
  return value === 'grande perigo' ? 'Grande Perigo'
    : value === 'perigo potencial' ? 'Perigo Potencial' : 'Perigo';
}

function coordinates(text) {
  const upper = text.toUpperCase();
  const state = Object.keys(STATES).find(code => new RegExp(`\\b${code}\\b`).test(upper));
  if (/NOVO HAMBURGO|LOMBA GRANDE|SÃO LEOPOLDO|SAO LEOPOLDO|CAMPO BOM|SAPIRANGA|ESTÂNCIA VELHA|IVOTI/.test(upper)) {
    return { lat: LOCAL.lat, lon: LOCAL.lon, precision: 'local' };
  }
  if (state) return { lat: STATES[state][0], lon: STATES[state][1], precision: 'estado', state };
  return { lat: LOCAL.lat, lon: LOCAL.lon, precision: 'aproximado' };
}

export default async function handler(req, res) {
  if (!method(req, res, ['GET'])) return;
  try {
    const response = await fetch(RSS_URL, {
      signal: AbortSignal.timeout(12000),
      headers: { Accept: 'application/rss+xml, application/xml', 'User-Agent': 'Estacao-do-Vale/2.0' }
    });
    if (!response.ok) return json(res, 502, { error: 'inmet_unavailable', source: RSS_URL });

    const xml = await response.text();
    const alerts = [...xml.matchAll(/<item>([\s\S]*?)<\/item>/gi)].map(match => {
      const block = match[1];
      const title = clean(block.match(/<title>([\s\S]*?)<\/title>/i)?.[1]);
      const description = clean(block.match(/<description>([\s\S]*?)<\/description>/i)?.[1]);
      const type = classify(title, description);
      if (!type) return null;

      const link = clean(block.match(/<link>([\s\S]*?)<\/link>/i)?.[1]);
      const publishedAt = clean(block.match(/<pubDate>([\s\S]*?)<\/pubDate>/i)?.[1]);
      const location = coordinates(`${title} ${description}`);
      return {
        title, description, type, link, publishedAt,
        severity: severity(title, description),
        ...location
      };
    }).filter(Boolean);

    return json(res, 200, {
      source: 'INMET',
      sourceUrl: RSS_URL,
      fetchedAt: new Date().toISOString(),
      total: alerts.length,
      note: 'Pinos sem geometria oficial usam coordenadas aproximadas. Rajadas previstas não são confirmação de tornado.',
      alerts
    });
  } catch (error) {
    console.error('INMET alerts:', error);
    return json(res, 502, { error: 'inmet_alerts_failed', source: RSS_URL });
  }
}
