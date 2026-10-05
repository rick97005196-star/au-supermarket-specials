// Owner password check shared by the feedback box and the visitor statistics.
// Only a slow salted hash (PBKDF2-SHA256, 100,000 rounds) is stored - never the password itself -
// and it is kept in the private Cloudflare D1 database, NOT in this public code.
// A network that types a wrong password 10 times in an hour is locked out for that hour.
const ITERATIONS = 100000;           // the most Cloudflare Workers allow

const hex = (buf) => [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
const unhex = (s) => new Uint8Array(s.match(/../g).map(x => parseInt(x, 16)));

async function pbkdf2(password, saltHex) {
    const enc = new TextEncoder();
    const key = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveBits']);
    const bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt: unhex(saltHex), iterations: ITERATIONS }, key, 256);
    return hex(bits);
}

// constant-time compare, so the answer time does not leak how much of the hash matched
function sameHex(a, b) {
    if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
    let d = 0;
    for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
    return d === 0;
}

async function ipHash(request) {
    const ip = request.headers.get('CF-Connecting-IP') || 'x';
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(ip + '|auth|owner'));
    return hex(buf).slice(0, 16);
}

async function ensureTables(db) {
    await db.batch([
        db.prepare('CREATE TABLE IF NOT EXISTS auth_fail (who TEXT NOT NULL, at INTEGER NOT NULL)'),
        db.prepare('CREATE TABLE IF NOT EXISTS owner_secret (k TEXT PRIMARY KEY, salt TEXT NOT NULL, hash TEXT NOT NULL, updated_at TEXT)'),
    ]);
}

async function storedSecret(db) {
    return db.prepare("SELECT salt, hash FROM owner_secret WHERE k = 'pw'").first();
}

/** 'ok' | 'wrong' | 'locked' */
export async function checkOwner(request, env) {
    const key = (request.headers.get('Authorization') || '').replace(/^Bearer\s+/i, '').trim();
    const db = env && env.FEEDBACK_DB;
    if (!db) return 'wrong';                       // no private database -> nobody gets in
    await ensureTables(db);
    const who = await ipHash(request);
    const since = Date.now() - 3600 * 1000;
    const row = await db.prepare('SELECT COUNT(*) AS n FROM auth_fail WHERE who = ? AND at > ?').bind(who, since).first();
    if (row && row.n >= 10) return 'locked';
    const sec = await storedSecret(db);      // set with PUT /api/owner-password
    if (sec && key && key.length <= 200 && sameHex(await pbkdf2(key, sec.salt), sec.hash)) return 'ok';
    if (key) await db.prepare('INSERT INTO auth_fail (who, at) VALUES (?, ?)').bind(who, Date.now()).run();
    return 'wrong';
}

/** Store a new owner password (hash only). Caller must already have passed checkOwner. */
export async function setOwnerPassword(env, password) {
    const db = env.FEEDBACK_DB;
    await ensureTables(db);
    const salt = hex(crypto.getRandomValues(new Uint8Array(16)));
    const hash = await pbkdf2(password, salt);
    await db.prepare("INSERT INTO owner_secret (k, salt, hash, updated_at) VALUES ('pw', ?, ?, ?) ON CONFLICT(k) DO UPDATE SET salt = excluded.salt, hash = excluded.hash, updated_at = excluded.updated_at")
        .bind(salt, hash, new Date().toISOString()).run();
}

export function authError(result) {
    return new Response(JSON.stringify({ ok: false, error: result === 'locked' ? 'locked' : 'unauthorized' }), {
        status: result === 'locked' ? 429 : 401,
        headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
    });
}
