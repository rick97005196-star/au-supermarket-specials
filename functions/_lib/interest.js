/**
 * Shared by /api/track and /api/popular (anonymous product interest). See functions/api/track.js.
 */
const KEEP_WEEKS = 10;

// Brisbane date, e.g. 2026-10-08
export function brisbaneDay(ms = Date.now()) {
    return new Date(ms + 10 * 3600 * 1000).toISOString().slice(0, 10);
}

// The specials week a moment belongs to: the Wednesday it started (Brisbane), e.g. 2026-10-07
export function specialsWeek(ms = Date.now()) {
    const d = new Date(ms + 10 * 3600 * 1000);
    const back = (d.getUTCDay() - 3 + 7) % 7;            // days since Wednesday
    d.setUTCDate(d.getUTCDate() - back);
    return d.toISOString().slice(0, 10);
}

// Same rule as interest.py: trimmed, single spaces, lower case, at most 160 characters
export function productKey(title) {
    return String(title || '').trim().replace(/\s+/g, ' ').toLowerCase().slice(0, 160);
}

export async function ensureTables(db) {
    await db.batch([
        db.prepare('CREATE TABLE IF NOT EXISTS product_interest (week TEXT NOT NULL, k TEXT NOT NULL, views INTEGER NOT NULL DEFAULT 0, adds INTEGER NOT NULL DEFAULT 0, favs INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (week, k))'),
        db.prepare('CREATE TABLE IF NOT EXISTS track_seen (day TEXT NOT NULL, h TEXT NOT NULL, PRIMARY KEY (day, h))'),
        db.prepare('CREATE TABLE IF NOT EXISTS track_rate (day TEXT NOT NULL, who TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, who))')
    ]);
}

export async function cleanUp(db, now = Date.now()) {
    const today = brisbaneDay(now);
    const oldest = specialsWeek(now - KEEP_WEEKS * 7 * 86400 * 1000);
    await db.batch([
        db.prepare('DELETE FROM track_seen WHERE day < ?').bind(today),
        db.prepare('DELETE FROM track_rate WHERE day < ?').bind(today),
        db.prepare('DELETE FROM product_interest WHERE week < ?').bind(oldest)
    ]);
}

// ---- /api/popular: recent interest per product ----
const WEIGHTS = [1, 0.6, 0.35, 0.2, 0.1, 0.05];
const MAX_ITEMS = 4000;

export function weekList(now = Date.now()) {
    return WEIGHTS.map((_, i) => specialsWeek(now - i * 7 * 86400 * 1000));
}

export function scoreRows(rows, weeks) {
    const weight = Object.fromEntries(weeks.map((w, i) => [w, WEIGHTS[i]]));
    const items = {};
    let total = 0;
    for (const r of rows) {
        const w = weight[r.week];
        if (!w) continue;
        const s = w * ((r.views || 0) + 2 * (r.favs || 0) + 3 * (r.adds || 0));
        if (s <= 0) continue;
        items[r.k] = (items[r.k] || 0) + s;
        total += s;
    }
    const top = Object.entries(items).sort((a, b) => b[1] - a[1]).slice(0, MAX_ITEMS)
        .map(([k, s]) => [k, Math.round(s * 100) / 100]);
    return { total: Math.round(total * 100) / 100, items: Object.fromEntries(top) };
}
