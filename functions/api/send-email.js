/**
 * Cloudflare Pages Function: /api/send-email
 * Supports sending shopping list emails via Resend API (Free tier: 3,000 emails/month).
 * If RESEND_API_KEY environment variable is not configured, returns fallback: true
 * so the frontend seamlessly opens the visitor's mail client (mailto:).
 */
export async function onRequestPost(context) {
    try {
        const { request, env } = context;
        const data = await request.json();
        const { email, text_content, html_content, total_cost, total_saved } = data;

        if (!email || !email.includes('@')) {
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
                to: [email],
                subject: `🛒 澳洲三大超市本週採買清單 (預估總額 $${Number(total_cost || 0).toFixed(2)})`,
                text: text_content,
                html: html_content
            })
        });

        if (resendRes.ok) {
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
