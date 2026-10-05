/**
 * Cloudflare Pages Function: /api/owner-password  - the owner changes the admin password.
 *
 *   PUT /api/owner-password   Authorization: Bearer <current password>   body: {"new_password": "..."}
 *
 * Only a salted PBKDF2 hash of the new password is stored, in the private D1 database.
 */
import { checkOwner, authError, setOwnerPassword } from '../_lib/auth.js';
const SITE = 'au-supermarket-specials.pages.dev';
const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
    status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
});

export async function onRequestPut({ request, env }) {
    const origin = request.headers.get('Origin') || '';
    let host = '';
    try { host = new URL(origin).hostname; } catch (e) {}
    if (!(host === SITE || host.endsWith('.' + SITE) || host === 'localhost' || host === '127.0.0.1')) return json({ ok: false }, 403);
    const auth = await checkOwner(request, env);
    if (auth !== 'ok') return authError(auth);
    let d;
    try { d = JSON.parse((await request.text()).slice(0, 1000)); } catch (e) { return json({ ok: false, error: 'bad_json' }, 400); }
    const pw = d && typeof d.new_password === 'string' ? d.new_password : '';
    if (pw.length < 10 || pw.length > 200) return json({ ok: false, error: 'too_short' }, 400);
    await setOwnerPassword(env, pw);
    return json({ ok: true });
}
