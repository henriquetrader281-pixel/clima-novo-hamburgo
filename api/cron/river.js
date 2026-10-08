import webpush from 'web-push';
import { alertTransitions, fetchRiver, json, method, readJson, redis, requireCron, writeJson } from '../../_lib/core.js';
const SUBSCRIPTIONS_KEY = 'clima:push:subscriptions';
const STATE_KEY = 'clima:river:last-state';
export default async function handler(req, res) {
  if (!method(req, res, ['GET'])) return;
  if (!requireCron(req, res)) return;
  if (!process.env.VAPID_PRIVATE_KEY || !process.env.VAPID_PUBLIC_KEY || !process.env.VAPID_SUBJECT) return json(res, 503, { error: 'push_not_configured' });
  try {
    const current = await fetchRiver();
    const previous = await readJson(STATE_KEY, null);
    await writeJson(STATE_KEY, current);
    const alerts = alertTransitions(previous, current);
    let sent = 0, removed = 0;
    if (alerts.length) {
      webpush.setVapidDetails(process.env.VAPID_SUBJECT, process.env.VAPID_PUBLIC_KEY, process.env.VAPID_PRIVATE_KEY);
      const subscriptions = await redis('SMEMBERS', SUBSCRIPTIONS_KEY) || [];
      for (const raw of subscriptions) {
        let subscription;
        try { subscription = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch { continue; }
        for (const station of alerts) {
          const isFlood = station.status === 'inundação';
          const body = `${station.label}: ${station.level?.toFixed(2)} m — ${isFlood ? 'cota de inundação atingida.' : 'nível de atenção atingido.'}`;
          try { await webpush.sendNotification(subscription, JSON.stringify({ title: `Alerta do Rio dos Sinos — ${station.label}`, body, tag: `rio-${station.key}-${station.status}`, url: '/', requireInteraction: isFlood })); sent++; }
          catch (error) { if (error.statusCode === 404 || error.statusCode === 410) { await redis('SREM', SUBSCRIPTIONS_KEY, JSON.stringify(subscription)); removed++; } else console.error('push', error.statusCode || error.message); }
        }
      }
    }
    return json(res, 200, { ok: true, fetchedAt: current.fetchedAt, alerts, sent, removed });
  } catch (error) { console.error(error); return json(res, 502, { error: 'river_cron_failed' }); }
}
