import { json, method } from './_lib/core.js';

const SOURCE_URL = 'https://www.marinha.mil.br/chm/dados-do-smm-avisos-de-mau-tempo/avisos-de-mau-tempo';
const HISTORICAL_URL = 'https://www.marinha.mil.br/chm/dados-do-smm-monitoramento-de-ciclones';
const MONTHS = { JAN: 0, FEV: 1, FEB: 1, MAR: 2, ABR: 3, APR: 3, MAI: 4, MAY: 4, JUN: 5, JUL: 6, AGO: 7, AUG: 7, SET: 8, SEP: 8, OUT: 9, OCT: 9, NOV: 10, DEZ: 11, DEC: 11 };

function decode(value = '') {
  return value
    .replace(/&nbsp;/gi, ' ').replace(/&amp;/gi, '&')
    .replace(/&quot;/gi, '"').replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, '<').replace(/&gt;/gi, '>')
    .replace(/&#(\\d+);/g, (_, n) => String.fromCharCode(Number(n)));
}

function htmlToText(html) {
  return decode(html
    .replace(/<script[\\s\\S]*?<\\/script>/gi, ' ')
    .replace(/<style[\\s\\S]*?<\\/style>/gi, ' ')
    .replace(/<\\/(p|div|tr|h[1-6]|li|td|th)>/gi, '\\n')
    .replace(/<br\\s*\\/?>/gi, '\\n')
    .replace(/<[^>]+>/g, ' '))
    .replace(/[ \\t]+/g, ' ')
    .replace(/\\n[ \\t]+/g, '\\n')
    .replace(/\\n{2,}/g, '\\n')
    .trim();
}

function makeUtcDate(day, hhmm, month, year, referenceDay) {
  if (!day || !hhmm || month === undefined || !year) return null;
  let m = month;
  if (Number(day) < Number(referenceDay)) m += 1;
  const date = new Date(Date.UTC(Number(year), m, Number(day), Number(hhmm.slice(0, 2)), Number(hhmm.slice(2, 4))));
  return date.toISOString();
}

function parseIssueDate(block) {
  const match = block.match(/EMITIDO\\s+ÀS\\s+(\\d{4})Z[\\s\\S]{0,100}?(\\d{2})\\/([A-Z]{3})\\/(\\d{4})/i);
  if (!match) return null;
  const month = MONTHS[match[3].toUpperCase()];
  if (month === undefined) return null;
  return { day: Number(match[2]), month, year: Number(match[4]) };
}

function parseNotices(text) {
  const headers = [...text.matchAll(/AVISO\\s+NR\\.?\\s*([A-Z0-9-]+\\/\\d{4})/gi)];
  const results = [];

  for (let i = 0; i < headers.length; i++) {
    const start = headers[i].index;
    const end = i + 1 < headers.length ? headers[i + 1].index : text.length;
    const block = text.slice(start, end).trim();
    if (!/ciclone|ciclon|subtropical|tropical/i.test(block)) continue;

    const issue = parseIssueDate(block);
    const validity = block.match(/VÁLIDO\\s+ATÉ\\s+(\\d{2})(\\d{4})Z/i);
    const startAt = block.match(/A\\s+PARTIR\\s+DE\\s+(\\d{2})(\\d{4})Z/i);
    const validUntil = issue && validity
      ? makeUtcDate(validity[1], validity[2], issue.month, issue.year, issue.day)
      : null;
    const startsAt = issue && startAt
      ? makeUtcDate(startAt[1], startAt[2], issue.month, issue.year, issue.day)
      : null;
    const now = Date.now();
    const expired = validUntil ? new Date(validUntil).getTime() < now : false;
    const scheduled = startsAt ? new Date(startsAt).getTime() > now : false;
    const status = expired ? 'expired' : scheduled ? 'scheduled' : validUntil ? 'active' : 'unconfirmed';

    const cleanBlock = block.replace(/\\s+/g, ' ').trim();
    results.push({
      number: headers[i][1],
      title: (block.match(/AVISO\\s+(?:DE|ESPECIAL)[^\\n]*/i)?.[0] || 'Aviso especial relacionado a ciclone').slice(0, 180),
      summary: cleanBlock.slice(0, 520),
      startsAt,
      validUntil,
      status,
      area: (block.match(/ÁREA[^.]{0,260}\\./i)?.[0] || '').slice(0, 260)
    });
  }
  return results.filter(item => item.status !== 'expired');
}

export default async function handler(req, res) {
  if (!method(req, res, ['GET'])) return;
  try {
    const response = await fetch(SOURCE_URL, {
      signal: AbortSignal.timeout(12000),
      headers: { Accept: 'text/html', 'User-Agent': 'Estacao-do-Vale/2.0' }
    });
    if (!response.ok) return json(res, 502, { error: 'chm_unavailable', source: SOURCE_URL });

    const html = await response.text();
    const text = htmlToText(html);
    const alerts = parseNotices(text);

    return json(res, 200, {
      source: 'Marinha do Brasil — Centro de Hidrografia da Marinha (CHM)',
      sourceUrl: SOURCE_URL,
      historicalUrl: HISTORICAL_URL,
      fetchedAt: new Date().toISOString(),
      status: alerts.some(item => item.status === 'active') ? 'active' : alerts.length ? 'attention' : 'clear',
      alerts,
      note: 'A página do CHM reúne avisos marítimos vigentes. O arquivo de monitoramento de ciclones é histórico; não representa, sozinho, uma posição de ciclone em tempo real.'
    });
  } catch (error) {
    console.error('CHM cyclone monitor:', error);
    return json(res, 502, { error: 'chm_cyclone_failed', source: SOURCE_URL });
  }
}
