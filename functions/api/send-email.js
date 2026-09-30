/**
 * Cloudflare Pages Function: /api/send-email
 * Supports sending shopping list emails via Resend API (Free tier: 3,000 emails/month).
 * If RESEND_API_KEY environment variable is not configured, returns fallback: true
 * so the frontend seamlessly opens the visitor's mail client (mailto:).
 */
export async function onRequestPost(context) {
    try {
        const { request, env } = context;

        // ---- Anti-abuse: only this website may use it, and only for a shopping list ----
        // (otherwise anyone could use the site's email key to send any content to anyone)
        const origin = request.headers.get('Origin') || request.headers.get('Referer') || '';
        let originHost = '';
        try { originHost = new URL(origin).hostname; } catch (e) {}
        const allowed = originHost === 'au-supermarket-specials.pages.dev' || originHost.endsWith('.au-supermarket-specials.pages.dev') || originHost === 'localhost';
        if (!allowed) {
            return new Response(JSON.stringify({ ok: false, error: 'Forbidden' }), { status: 403, headers: { 'Content-Type': 'application/json' } });
        }
        const raw = await request.text();
        if (raw.length > 60000) {
            return new Response(JSON.stringify({ ok: false, fallback: true, error: 'List too long' }), { status: 413, headers: { 'Content-Type': 'application/json' } });
        }
        const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
        const now = Date.now();
        globalThis.__sendLog = (globalThis.__sendLog || []).filter(x => now - x.t < 3600000);
        if (globalThis.__sendLog.filter(x => x.ip === ip).length >= 5) {
            return new Response(JSON.stringify({ ok: false, fallback: true, error: 'Too many emails, please try later' }), { status: 429, headers: { 'Content-Type': 'application/json' } });
        }
        const data = JSON.parse(raw);
        const { email, text_content, total_cost } = data;
        // The email body is built here from plain text only: visitors cannot inject their own HTML/links
        const esc = (s) => String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
        const html_content = `<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;margin:0 auto;padding:16px">`
            + `<h2 style="margin:0 0 12px;font-size:18px">🛒 澳洲超市特價優惠 · 採買清單</h2>`
            + `<pre style="white-space:pre-wrap;font-family:inherit;font-size:14px;line-height:1.6;margin:0">${esc(text_content).slice(0, 20000)}</pre>`
            + `<p style="margin-top:20px;font-size:12px;color:#64748b">https://au-supermarket-specials.pages.dev</p></div>`;

        if (!email || !/^[^\s@,;<>]+@[^\s@,;<>]+\.[a-z]{2,}$/i.test(String(email).trim()) || String(email).length > 120) {
            return new Response(JSON.stringify({ 
                ok: false, 
                error: 'Invalid email address' 
            }), {
                status: 400,
                headers: { 'Content-Type': 'application/json' }
            });
        }

        // Check if RESEND_API_KEY is configured in Cloudflare Pages Environment Variables
        const apiKey = env && env.RESEND_API_KEY;
        if (!apiKey) {
            return new Response(JSON.stringify({ 
                ok: false, 
                fallback: true, 
                message: 'RESEND_API_KEY not configured. Falling back to mail client.' 
            }), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            });
        }

        const fromAddress = (env && env.EMAIL_FROM) || 'AU Supermarket Specials <onboarding@resend.dev>';

        const resendRes = await fetch('https://api.resend.com/emails', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                from: fromAddress,
                to: [String(email).trim()],
                subject: `🛒 澳洲三大超市本週採買清單 (預估總額 $${Number(total_cost || 0).toFixed(2)})`,
                text: String(text_content || '').slice(0, 20000),
                html: html_content
            })
        });

        if (resendRes.ok) {
            globalThis.__sendLog.push({ ip, t: now });
            return new Response(JSON.stringify({ 
                ok: true, 
                message: 'Email sent successfully via Resend' 
            }), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            });
        } else {
            const errText = await resendRes.text();
            return new Response(JSON.stringify({ 
                ok: false, 
                fallback: true, 
                error: errText 
            }), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            });
        }
    } catch (err) {
        return new Response(JSON.stringify({ 
            ok: false, 
            fallback: true, 
            error: err.message 
        }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}
