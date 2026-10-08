import { fetchRiver, json, method } from './_lib/core.js';
export default async function handler(req, res) {
  if (!method(req, res, ['GET'])) return;
  try { return json(res, 200, await fetchRiver()); }
  catch (error) { console.error(error); return json(res, 502, { error: 'river_feed_unavailable' }); }
}
