/**
 * Cloudflare Pages Function: /api/track - anonymous product interest (binding: FEEDBACK_DB)
 *
 *   POST /api/track   {"k": "<product title>", "e": "v" | "a" | "f"}
 *        v = product details opened, a = added to a shopping list, f = saved as a regular buy
 *
 * Used to learn which specials people really look at, so the default order improves by itself
 * (see /api/popular and interest.py). What is stored: per week, how many times each product was
 * opened / added / saved. Nothing about the visitor: no id, name, email or IP.
 *
 * Abuse protection (a script cannot push a product up):
 *   - each network (one-way daily hash of the IP, deleted the next day) counts each product and
 *     action at most once a day, and at most 200 actions a day in total;
 *   - robots are ignored, only this website may send, and only the three actions are accepted.
 */
import { brisbaneDay, specialsWeek, productKey, ensureTables, cleanUp } from '../_lib/interest.js';

const SITE = 'au-supermarket-specials.pages.dev';
const BOT = /bot|crawl|spider|slurp|preview|headless|lighthouse|facebookexternalhit|whatsapp|telegram|discord|curl|wget|python|node-fetch|axios|monitor|uptime/i;
const COLUMN = { v: 'views', a: 'adds', f: 'favs' };
const DAILY_LIMIT = 200;

const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
    status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
});

async function sha256(text) {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
}

export async function onRequestPost({ request, env }) {
    const origin = request.headers.get('Origin') || request.headers.get('Referer') || '';
    let host = '';
    try { host = new URL(origin).hostname; } catch (e) {}
    if (!(host === SITE || host.endsWith('.' + SITE) || host === 'localhost' || host === '127.0.0.1')) return json({ ok: false }, 403);
    if (BOT.test(request.headers.get('User-Agent') || '')) return json({ ok: true, bot: true });
    if (!env.FEEDBACK_DB) return json({ ok: false, error: 'no_db' });

    let d = {};
    try { d = JSON.parse((await request.text()).slice(0, 600)); } catch (e) { return json({ ok: false }, 400); }
    if (!d || typeof d !== 'object' || Array.isArray(d)) return json({ ok: false }, 400);
    const column = COLUMN[d.e];
    const k = productKey(d.k);
    if (!column || k.length < 3 || /[\u0000-\u001f<>]/.test(k)) return json({ ok: false }, 400);

    const db = env.FEEDBACK_DB;
    await ensureTables(db);
    const day = brisbaneDay();
    const ip = request.headers.get('CF-Connecting-IP') || 'x';
    const who = (await sha256(ip + '|' + day + '|track')).slice(0, 16);
    const lim = await db.prepare('INSERT INTO track_rate (day, who, n) VALUES (?, ?, 1) ON CONFLICT(day, who) DO UPDATE SET n = n + 1 RETURNING n').bind(day, who).first();
    if (lim && lim.n > DAILY_LIMIT) return json({ ok: true, limited: true });

    // the same network counts the same product and action once a day
    const h = (await sha256(ip + '|' + day + '|' + d.e + '|' + k)).slice(0, 20);
    const seen = await db.prepare('INSERT OR IGNORE INTO track_seen (day, h) VALUES (?, ?)').bind(day, h).run();
    if (!seen.meta || !seen.meta.changes) return json({ ok: true, counted: false });

    await db.prepare(`INSERT INTO product_interest (week, k, ${column}) VALUES (?, ?, 1)
                      ON CONFLICT(week, k) DO UPDATE SET ${column} = ${column} + 1`).bind(specialsWeek(), k).run();
    if (Math.random() < 0.02) await cleanUp(db);
    return json({ ok: true, counted: true });
}
