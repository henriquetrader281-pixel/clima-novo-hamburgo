import { json, method, redis } from '../_lib/core.js';
const KEY = 'clima:push:subscriptions';
function valid(subscription) {
  return subscription && typeof subscription.endpoint === 'string' && subscription.endpoint.startsWith('https://') && subscription.keys && typeof subscription.keys.p256dh === 'string' && typeof subscription.keys.auth === 'string';
}
export default async function handler(req, res) {
  if (!method(req, res, ['POST', 'DELETE'])) return;
  try {
    if (req.method === 'POST') {
      if (!valid(req.body)) return json(res, 400, { error: 'invalid_push_subscription' });
      await redis('SADD', KEY, JSON.stringify(req.body));
      return json(res, 201, { ok: true });
    }
    if (!valid(req.body)) return json(res, 400, { error: 'invalid_push_subscription' });
    await redis('SREM', KEY, JSON.stringify(req.body));
    return json(res, 200, { ok: true });
  } catch (error) { console.error(error); return json(res, 503, { error: 'subscription_store_unavailable' }); }
}
