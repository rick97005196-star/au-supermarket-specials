/**
 * Cloudflare Pages Function: /api/popular - how much interest each product received recently
 * (binding: FEEDBACK_DB). Public: it only contains counts per product, nothing about anyone.
 *
 *   GET /api/popular  ->  {"ok": true, "weeks": [...], "total": 1234.5, "items": {"<product key>": 12.3, ...}}
 *
 * Score per product = sum over the last 6 specials weeks of
 *     weight(week) x (opened + 2 x saved + 3 x added to a shopping list)
 * with recent weeks counting most (1, 0.6, 0.35, 0.2, 0.1, 0.05), so the order follows what people
 * look at now. Read by scripts/fetch_interest.py on every update (see interest.py).
 */
import { ensureTables, cleanUp, weekList, scoreRows } from '../_lib/interest.js';

const json = (obj, status = 200, cache = 'no-store') => new Response(JSON.stringify(obj), {
    status, headers: { 'Content-Type': 'application/json', 'Cache-Control': cache }
});

export async function onRequestGet({ env }) {
    if (!env.FEEDBACK_DB) return json({ ok: false, error: 'no_db' });
    const db = env.FEEDBACK_DB;
    await ensureTables(db);
    if (Math.random() < 0.1) await cleanUp(db);
    const weeks = weekList();
    const res = await db.prepare('SELECT week, k, views, adds, favs FROM product_interest WHERE week >= ?')
        .bind(weeks[weeks.length - 1]).all();
    const { total, items } = scoreRows(res.results || [], weeks);
    return json({ ok: true, generated_at: new Date().toISOString(), weeks, total, items }, 200, 'public, max-age=300');
}
