/**
 * Cloudflare Pages Function: /api/hit  - anonymous visitor statistics (binding: FEEDBACK_DB)
 *
 *   POST /api/hit   the website counts one page view          (called once per page load)
 *   GET  /api/hit   owner reads the statistics                 (Authorization: Bearer <password>)
 *
 * What is stored: the day, a random visitor id that the browser made up itself (no name, email,
 * IP or cookie from anyone else), phone/computer, language and chosen state. Robots are ignored.
 */
import { checkOwner, authError } from '../_lib/auth.js';
const SITE = 'au-supermarket-specials.pages.dev';
const BOT = /bot|crawl|spider|slurp|preview|headless|lighthouse|facebookexternalhit|whatsapp|telegram|discord|curl|wget|python|node-fetch|axios|monitor|uptime/i;

const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
    status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
});

async function sha256(text) {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
}

async function ensureTables(db) {
    await db.batch([
        db.prepare('CREATE TABLE IF NOT EXISTS visit_unique (day TEXT NOT NULL, vid TEXT NOT NULL, device TEXT, lang TEXT, region TEXT, PRIMARY KEY (day, vid))'),
        db.prepare('CREATE TABLE IF NOT EXISTS visit_count (day TEXT PRIMARY KEY, views INTEGER NOT NULL DEFAULT 0)'),
        db.prepare('CREATE TABLE IF NOT EXISTS hit_rate (day TEXT NOT NULL, who TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, who))')
    ]);
}

// Brisbane date (the owner's time zone), e.g. 2026-10-01
function brisbaneDay(offsetDays = 0) {
    const d = new Date(Date.now() + 10 * 3600 * 1000 - offsetDays * 86400 * 1000);
    return d.toISOString().slice(0, 10);
}

export async function onRequestPost({ request, env }) {
    const origin = request.headers.get('Origin') || request.headers.get('Referer') || '';
    let host = '';
    try { host = new URL(origin).hostname; } catch (e) {}
    if (!(host === SITE || host.endsWith('.' + SITE) || host === 'localhost' || host === '127.0.0.1')) return json({ ok: false }, 403);
    if (BOT.test(request.headers.get('User-Agent') || '')) return json({ ok: true, bot: true });
    if (!env.FEEDBACK_DB) return json({ ok: false, error: 'no_db' });
    let d = {};
    try { d = JSON.parse((await request.text()).slice(0, 500)); } catch (e) { return json({ ok: false }, 400); }
    if (!d || typeof d !== 'object' || Array.isArray(d)) return json({ ok: false }, 400);
    const vid = String(d.vid || '');
    if (!/^[a-f0-9]{16,32}$/.test(vid)) return json({ ok: false }, 400);
    const short = (v, ok) => (ok.includes(v) ? v : 'other');
    const device = short(d.device, ['mobile', 'desktop']);
    const lang = short(d.lang, ['zh', 'en', 'ja', 'ko']);
    const region = short(d.region, ['QLD', 'NSW', 'ACT', 'VIC', 'SA', 'WA', 'TAS', 'NT']);
    const day = brisbaneDay();
    const db = env.FEEDBACK_DB;
    await ensureTables(db);
    // anti-flood: one network counts at most 300 page views a day (a script cannot inflate the numbers
    // or use up the free database allowance). Only a one-way daily hash of the IP is kept.
    const who = (await sha256((request.headers.get('CF-Connecting-IP') || 'x') + '|' + day + '|hit')).slice(0, 16);
    const lim = await db.prepare('INSERT INTO hit_rate (day, who, n) VALUES (?, ?, 1) ON CONFLICT(day, who) DO UPDATE SET n = n + 1 RETURNING n').bind(day, who).first();
    if (lim && lim.n > 300) return json({ ok: true, limited: true });
    await db.batch([
        db.prepare('INSERT OR IGNORE INTO visit_unique (day, vid, device, lang, region) VALUES (?, ?, ?, ?, ?)').bind(day, vid, device, lang, region),
        db.prepare('INSERT INTO visit_count (day, views) VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET views = views + 1').bind(day)
    ]);
    return json({ ok: true });
}

export async function onRequestGet({ request, env }) {
    const auth = await checkOwner(request, env);
    if (auth !== 'ok') return authError(auth);
    if (!env.FEEDBACK_DB) return json({ ok: false, error: 'no_db' });
    const db = env.FEEDBACK_DB;
    await ensureTables(db);
    await db.prepare('DELETE FROM hit_rate WHERE day < ?').bind(brisbaneDay(1)).run();
    const from30 = brisbaneDay(29), from7 = brisbaneDay(6), today = brisbaneDay();
    const [visitors, views, totals, device, lang, region] = await db.batch([
        db.prepare('SELECT day, COUNT(*) AS n FROM visit_unique WHERE day >= ? GROUP BY day').bind(from30),
        db.prepare('SELECT day, views AS n FROM visit_count WHERE day >= ?').bind(from30),
        db.prepare(`SELECT
            (SELECT COUNT(DISTINCT vid) FROM visit_unique WHERE day = ?) AS today_visitors,
            (SELECT COALESCE(SUM(views), 0) FROM visit_count WHERE day = ?) AS today_views,
            (SELECT COUNT(DISTINCT vid) FROM visit_unique WHERE day >= ?) AS week_visitors,
            (SELECT COUNT(DISTINCT vid) FROM visit_unique WHERE day >= ?) AS month_visitors,
            (SELECT COALESCE(SUM(views), 0) FROM visit_count WHERE day >= ?) AS month_views,
            (SELECT COUNT(DISTINCT vid) FROM visit_unique) AS all_visitors,
            (SELECT COALESCE(SUM(views), 0) FROM visit_count) AS all_views,
            (SELECT MIN(day) FROM visit_count) AS since`).bind(today, today, from7, from30, from30),
        db.prepare('SELECT device AS k, COUNT(DISTINCT vid) AS n FROM visit_unique WHERE day >= ? GROUP BY device ORDER BY n DESC').bind(from30),
        db.prepare('SELECT lang AS k, COUNT(DISTINCT vid) AS n FROM visit_unique WHERE day >= ? GROUP BY lang ORDER BY n DESC').bind(from30),
        db.prepare('SELECT region AS k, COUNT(DISTINCT vid) AS n FROM visit_unique WHERE day >= ? GROUP BY region ORDER BY n DESC').bind(from30)
    ]);
    const vMap = Object.fromEntries((visitors.results || []).map(r => [r.day, r.n]));
    const pMap = Object.fromEntries((views.results || []).map(r => [r.day, r.n]));
    const days = [];
    for (let i = 29; i >= 0; i--) {
        const day = brisbaneDay(i);
        days.push({ day, visitors: vMap[day] || 0, views: pMap[day] || 0 });
    }
    return json({
        ok: true, days, totals: (totals.results || [])[0] || {},
        device: device.results || [], lang: lang.results || [], region: region.results || []
    });
}
