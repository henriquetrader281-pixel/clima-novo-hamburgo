import { json, method } from './_lib/core.js';
const PAGE = 'https://clima.cptec.inpe.br/enos';
export default async function handler(req, res) {
  if (!method(req, res, ['GET'])) return;
  try {
    const response = await fetch(PAGE, { signal: AbortSignal.timeout(10000) });
    if (!response.ok) return json(res, 502, { error: 'enso_source_unavailable' });
    const html = await response.text();
    const urls = [...html.matchAll(/https?:\/\/[^"'\s<>]+\.(?:png|jpg|jpeg|gif)/gi)].map(m => m[0]);
    const unique = [...new Set(urls)];
    const sst = unique.find(url => /obs_sst_anom/i.test(url));
    const wind = unique.find(url => /obs_wnd850_anom/i.test(url));
    const oni = unique.find(url => /ONI_evol_ts\.png/i.test(url));
    return json(res, 200, { source: 'CPTEC/INPE', fetchedAt: new Date().toISOString(), page: PAGE, images: { sstAnomaly: sst || null, windAnomaly850: wind || null, oni: oni || null } });
  } catch (error) { console.error(error); return json(res, 502, { error: 'enso_failed' }); }
}
