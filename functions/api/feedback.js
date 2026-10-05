/**
 * Cloudflare Pages Function: /api/feedback
 * Anonymous feedback box - backup copy in Cloudflare D1 (binding: FEEDBACK_DB), so no message is
 * lost even when the email service (Web3Forms) is over its monthly limit.
 *
 *   POST   /api/feedback            visitor sends a message (anonymous)
 *   GET    /api/feedback            owner reads messages          (Authorization: Bearer <password>)
 *   PUT    /api/feedback?id=&read=1 owner marks read / unread     (Authorization)
 *   DELETE /api/feedback?id=        owner deletes a message       (Authorization)
 *
 * Nothing that identifies a visitor is stored: no name, email or IP address. For the anti-flood
 * limit only a one-way daily hash of the IP is kept (it cannot be turned back into the IP).
 */
import { checkOwner, authError } from '../_lib/auth.js';
const TYPES = ['suggestion', 'data_error', 'bug', 'other'];
const SITE = 'au-supermarket-specials.pages.dev';

const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
    status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
});

async function sha256(text) {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
}

async function ensureTable(db) {
    await db.prepare(`CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        type TEXT, message TEXT NOT NULL, lang TEXT, region TEXT, device TEXT,
        is_read INTEGER DEFAULT 0, ip_hash TEXT)`).run();
}


export async function onRequestPost({ request, env }) {
    const origin = request.headers.get('Origin') || request.headers.get('Referer') || '';
    let host = '';
    try { host = new URL(origin).hostname; } catch (e) {}
    if (!(host === SITE || host.endsWith('.' + SITE) || host === 'localhost' || host === '127.0.0.1')) return json({ ok: false, error: 'Forbidden' }, 403);
    if (!env.FEEDBACK_DB) return json({ ok: false, error: 'no_db' });
    const raw = await request.text();
    if (raw.length > 8000) return json({ ok: false, error: 'too_long' }, 413);
    let d;
    try { d = JSON.parse(raw); } catch (e) { return json({ ok: false, error: 'bad_json' }, 400); }
    if (!d || typeof d !== 'object' || Array.isArray(d)) return json({ ok: false, error: 'bad_json' }, 400);
    if (d.botcheck) return json({ ok: true });                       // robot: pretend success
    const message = String(d.message || '').trim().slice(0, 1000);
    if (message.length < 2) return json({ ok: false, error: 'empty' }, 400);
    const type = TYPES.includes(d.type) ? d.type : 'other';
    const short = (v) => String(v || '').slice(0, 16);

    const db = env.FEEDBACK_DB;
    await ensureTable(db);
    const day = new Date().toISOString().slice(0, 10);
    const ipHash = (await sha256((request.headers.get('CF-Connecting-IP') || 'x') + '|' + day + '|au-specials')).slice(0, 16);
    const since = new Date(Date.now() - 3600 * 1000).toISOString();
    const recent = await db.prepare('SELECT COUNT(*) AS n FROM feedback WHERE ip_hash = ? AND created_at > ?').bind(ipHash, since).first();
    if (recent && recent.n >= 5) return json({ ok: false, error: 'too_many' }, 429);

    const res = await db.prepare('INSERT INTO feedback (created_at, type, message, lang, region, device, ip_hash) VALUES (?, ?, ?, ?, ?, ?, ?)')
        .bind(new Date().toISOString(), type, message, short(d.lang), short(d.region), short(d.device), ipHash).run();
    return json({ ok: true, id: res.meta && res.meta.last_row_id });
}

export async function onRequestGet({ request, env }) {
    const auth = await checkOwner(request, env);
    if (auth !== 'ok') return authError(auth);
    if (!env.FEEDBACK_DB) return json({ ok: false, error: 'no_db' });
    const db = env.FEEDBACK_DB;
    await ensureTable(db);
    const rows = await db.prepare('SELECT id, created_at, type, message, lang, region, device, is_read FROM feedback ORDER BY id DESC LIMIT 500').all();
    const month = new Date().toISOString().slice(0, 7);
    const stats = await db.prepare("SELECT COUNT(*) AS total, SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) AS unread, SUM(CASE WHEN substr(created_at, 1, 7) = ? THEN 1 ELSE 0 END) AS this_month FROM feedback").bind(month).first();
    return json({ ok: true, items: rows.results || [], stats });
}

export async function onRequestPut({ request, env }) {
    const auth = await checkOwner(request, env);
    if (auth !== 'ok') return authError(auth);
    const url = new URL(request.url);
    const id = parseInt(url.searchParams.get('id'), 10);
    const read = url.searchParams.get('read') === '1' ? 1 : 0;
    if (!id || !env.FEEDBACK_DB) return json({ ok: false }, 400);
    await env.FEEDBACK_DB.prepare('UPDATE feedback SET is_read = ? WHERE id = ?').bind(read, id).run();
    return json({ ok: true });
}

export async function onRequestDelete({ request, env }) {
    const auth = await checkOwner(request, env);
    if (auth !== 'ok') return authError(auth);
    const id = parseInt(new URL(request.url).searchParams.get('id'), 10);
    if (!id || !env.FEEDBACK_DB) return json({ ok: false }, 400);
    await env.FEEDBACK_DB.prepare('DELETE FROM feedback WHERE id = ?').bind(id).run();
    return json({ ok: true });
}
