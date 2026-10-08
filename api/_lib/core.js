const FEED_URL = 'https://nivelguaiba.com.br/feed';
const SUBSCRIPTIONS_KEY = 'clima:push:subscriptions';
const STATE_KEY = 'clima:river:last-state';
const STATIONS = {
  saoleopoldo: { label: 'São Leopoldo', attention: 3.5, flood: 4.5 },
  campobom: { label: 'Campo Bom', flood: 7.2 },
  taquara: { label: 'Taquara' }
};

export function cors(res, methods = 'GET,POST,DELETE,OPTIONS') {
  res.setHeader('Access-Control-Allow-Origin', process.env.FRONTEND_ORIGIN || '*');
  res.setHeader('Access-Control-Allow-Methods', methods);
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Max-Age', '86400');
}
export function json(res, status, body) { cors(res); res.status(status).json(body); }
export function method(req, res, allowed) {
  cors(res, allowed.join(','));
  if (req.method === 'OPTIONS') { res.status(204).end(); return false; }
  if (!allowed.includes(req.method)) { res.setHeader('Allow', allowed.join(',')); res.status(405).json({ error: 'method_not_allowed' }); return false; }
  return true;
}
export function requireCron(req, res) {
  const secret = process.env.CRON_SECRET;
  const auth = req.headers.authorization || '';
  if (!secret || auth !== `Bearer ${secret}`) { json(res, 401, { error: 'unauthorized' }); return false; }
  return true;
}
function redisConfig() {
  if (!process.env.KV_REST_API_URL || !process.env.KV_REST_API_TOKEN) throw new Error('KV_REST_API_URL/KV_REST_API_TOKEN não configurados');
  return { url: process.env.KV_REST_API_URL.replace(/\/$/, ''), token: process.env.KV_REST_API_TOKEN };
}
export async function redis(command, ...args) {
  const cfg = redisConfig();
  const response = await fetch(`${cfg.url}/${command}/${args.map(v => encodeURIComponent(typeof v === 'string' ? v : JSON.stringify(v))).join('/')}`, { headers: { Authorization: `Bearer ${cfg.token}` } });
  if (!response.ok) throw new Error(`Redis HTTP ${response.status}`);
  return (await response.json()).result;
}
export async function readJson(key, fallback) { const value = await redis('GET', key); return value ? JSON.parse(value) : fallback; }
export async function writeJson(key, value) { await redis('SET', key, JSON.stringify(value)); }
export async function fetchRiver() {
  const response = await fetch(FEED_URL, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`feed HTTP ${response.status}`);
  const feed = await response.json();
  const items = feed.items || [];
  const stations = Object.fromEntries(Object.entries(STATIONS).map(([key, rule]) => {
    const item = items.find(entry => (entry.tags || []).some(tag => String(tag).toLowerCase() === key));
    const match = item?.title?.match(/([\d,.]+)\s*m/i);
    const level = match ? Number(match[1].replace(',', '.')) : null;
    const status = level == null ? 'sem leitura' : rule.flood != null && level >= rule.flood ? 'inundação' : rule.attention != null && level >= rule.attention ? 'atenção' : 'normal';
    return [key, { key, label: rule.label, level, status, observedAt: item?.date_published || null, source: FEED_URL }];
  }));
  return { stations, fetchedAt: new Date().toISOString() };
}
export function alertTransitions(previous, current) {
  const alerts = [];
  for (const [key, station] of Object.entries(current.stations)) {
    const before = previous?.stations?.[key]?.status;
    if (station.status !== 'normal' && station.status !== 'sem leitura' && station.status !== before) alerts.push(station);
  }
  return alerts;
}
