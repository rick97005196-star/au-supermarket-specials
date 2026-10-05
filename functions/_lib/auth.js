// Owner password check shared by the feedback box and the visitor statistics.
// Only a slow salted hash (PBKDF2, 100,000 rounds) is stored - never the password itself -
// and a network that types a wrong password 10 times in an hour is locked out for that hour.
const SALT = '135173e7189e04226c92687201601ac4';
const HASH = '18dc82d6907dc5134cf9f5e8f99c59afe446c5a47020addd3debe43edd2e2f54';

async function pbkdf2(password) {
    const enc = new TextEncoder();
    const key = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveBits']);
    const salt = new Uint8Array(SALT.match(/../g).map(x => parseInt(x, 16)));
    const bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt, iterations: 100000 }, key, 256);
    return [...new Uint8Array(bits)].map(b => b.toString(16).padStart(2, '0')).join('');
}

async function ipHash(request) {
    const ip = request.headers.get('CF-Connecting-IP') || 'x';
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(ip + '|auth|' + SALT));
    return [...new Uint8Array(buf)].slice(0, 8).map(b => b.toString(16).padStart(2, '0')).join('');
}

/** 'ok' | 'wrong' | 'locked' */
export async function checkOwner(request, env) {
    const key = (request.headers.get('Authorization') || '').replace(/^Bearer\s+/i, '').trim();
    const db = env && env.FEEDBACK_DB;
    let who = null;
    if (db) {
        who = await ipHash(request);
        await db.prepare('CREATE TABLE IF NOT EXISTS auth_fail (who TEXT NOT NULL, at INTEGER NOT NULL)').run();
        const since = Date.now() - 3600 * 1000;
        const row = await db.prepare('SELECT COUNT(*) AS n FROM auth_fail WHERE who = ? AND at > ?').bind(who, since).first();
        if (row && row.n >= 10) return 'locked';
    }
    if (key && key.length <= 200 && (await pbkdf2(key)) === HASH) return 'ok';
    if (db && key) await db.prepare('INSERT INTO auth_fail (who, at) VALUES (?, ?)').bind(who, Date.now()).run();
    return 'wrong';
}

export function authError(result) {
    return new Response(JSON.stringify({ ok: false, error: result === 'locked' ? 'locked' : 'unauthorized' }), {
        status: result === 'locked' ? 429 : 401,
        headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
    });
}
