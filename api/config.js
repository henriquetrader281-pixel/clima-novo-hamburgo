import { json, method } from './_lib/core.js';
export default function handler(req, res) {
  if (!method(req, res, ['GET'])) return;
  if (!process.env.VAPID_PUBLIC_KEY) return json(res, 503, { error: 'push_not_configured' });
  return json(res, 200, { vapidPublicKey: process.env.VAPID_PUBLIC_KEY, subscribeEndpoint: '/push/subscribe', unsubscribeEndpoint: '/push/subscribe' });
}
