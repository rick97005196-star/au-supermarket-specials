/**
 * Cloudflare Pages Function: /api/sites  - browsing statistics of all 6 sites, for the owner page
 *
 *   GET /api/sites   owner reads the statistics   (Authorization: Bearer <password>)
 *
 * The numbers come from Cloudflare Web Analytics (already on for every site) through the GraphQL API,
 * so the other sites need no code change and nothing new is collected or stored here.
 * Needs the Pages secret CF_ANALYTICS_TOKEN (permission: Account Analytics: Read). CF_ACCOUNT_ID is
 * optional; without it the account is looked up with the token. Neither is ever sent to the browser.
 */
import { checkOwner, authError } from '../_lib/auth.js';
const SITES = [
    { code: 'hub', name: '主網站', host: 'au-working-holiday.pages.dev' },
    { code: 'supermarket', name: '超市特價', host: 'au-supermarket-specials.pages.dev' },
    { code: 'qld', name: '集簽職缺', host: 'workingholiday-qld.pages.dev' },
    { code: 'deals', name: '活動優惠', host: 'au-deals-map.pages.dev' },
    { code: 'road', name: '交通法規', host: 'au-road-guide.pages.dev' },
    { code: 'birthday', name: '生日優惠', host: 'au-birthday-deals.pages.dev' }
];
const ALL = { code: 'all', name: '全部網站', host: '' };
const API = 'https://api.cloudflare.com/client/v4';

const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
    status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
});

// Brisbane date (the owner's time zone, no daylight saving), e.g. 2026-10-01
function brisbaneDay(offsetDays = 0) {
    const d = new Date(Date.now() + 10 * 3600 * 1000 - offsetDays * 86400 * 1000);
    return d.toISOString().slice(0, 10);
}
const dayOf = (iso) => new Date(Date.parse(iso) + 10 * 3600 * 1000).toISOString().slice(0, 10);
const noMs = (d) => d.toISOString().replace(/\.\d{3}Z$/, 'Z');

// exact host match, so preview copies like abc123.au-deals-map.pages.dev are not counted
const FILTER = `{ AND: [{ datetime_geq: $start, datetime_leq: $end }, { bot: 0 }, { requestHost_in: ${JSON.stringify(SITES.map(s => s.host))} }] }`;
const QUERY = `query ($tag: string!, $start: Time!, $end: Time!) {
  viewer { accounts(filter: { accountTag: $tag }) {
    hours: rumPageloadEventsAdaptiveGroups(filter: ${FILTER}, limit: 5000) { count sum { visits } dimensions { datetimeHour requestHost } }
    device: rumPageloadEventsAdaptiveGroups(filter: ${FILTER}, limit: 100) { count sum { visits } dimensions { requestHost deviceType } }
    country: rumPageloadEventsAdaptiveGroups(filter: ${FILTER}, limit: 2000, orderBy: [sum_visits_DESC]) { count sum { visits } dimensions { requestHost countryName } }
    pages: rumPageloadEventsAdaptiveGroups(filter: ${FILTER}, limit: 2000, orderBy: [count_DESC]) { count sum { visits } dimensions { requestHost requestPath } }
  } }
}`;

// [{k, n}] biggest first; everything after the first n rows becomes one 'other' row
function top(map, n) {
    const rows = Object.entries(map).map(([k, v]) => ({ k, n: v })).sort((a, b) => b.n - a.n);
    if (rows.length <= n + 1) return rows;
    return [...rows.slice(0, n), { k: 'other', n: rows.slice(n).reduce((s, r) => s + r.n, 0) }];
}
const deviceOf = (t) => (['desktop', 'mobile', 'tablet'].includes(String(t).toLowerCase()) ? String(t).toLowerCase() : 'other');

export async function onRequestGet({ request, env }) {
    const auth = await checkOwner(request, env);
    if (auth !== 'ok') return authError(auth);
    if (!env.CF_ANALYTICS_TOKEN) return json({ ok: false, error: 'no_token' });
    const cf = (path, body) => fetch(API + path, {
        method: body ? 'POST' : 'GET',
        headers: { Authorization: 'Bearer ' + env.CF_ANALYTICS_TOKEN, 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined
    }).then(r => r.json());
    try {
        let tag = /^[0-9a-f]{32}$/.test(env.CF_ACCOUNT_ID || '') ? env.CF_ACCOUNT_ID : '';
        if (!tag) {
            const a = await cf('/accounts?per_page=5');
            if (!a.success) return json({ ok: false, error: 'api', message: (a.errors && a.errors[0] && a.errors[0].message) || 'accounts lookup failed' });
            tag = String((a.result && a.result[0] && a.result[0].id) || '');
        }
        if (!/^[0-9a-f]{32}$/.test(tag)) return json({ ok: false, error: 'no_account' });

        const start = new Date(brisbaneDay(29) + 'T00:00:00+10:00');
        const d = await cf('/graphql', { query: QUERY, variables: { tag, start: noMs(start), end: noMs(new Date()) } });
        if (d.errors && d.errors.length) return json({ ok: false, error: 'api', message: String(d.errors[0].message || 'graphql error').slice(0, 300) });
        const acc = d.data && d.data.viewer && d.data.viewer.accounts && d.data.viewer.accounts[0];
        if (!acc) return json({ ok: false, error: 'api', message: 'no data for this account' });

        const byHost = Object.fromEntries(SITES.map(s => [s.host, s]));
        const stats = Object.fromEntries([ALL, ...SITES].map(s => [s.code, { visits: {}, views: {}, device: {}, country: {}, pages: {} }]));
        const add = (obj, k, n) => { obj[k] = (obj[k] || 0) + (Number(n) || 0); };
        const each = (rows, fn) => {
            for (const r of rows || []) {
                const site = byHost[r.dimensions && r.dimensions.requestHost];
                if (!site) continue;
                fn(stats[site.code], r, '');
                fn(stats.all, r, site.name + ' ');
            }
        };
        const visitsOf = (r) => (r.sum && r.sum.visits) || 0;
        each(acc.hours, (t, r) => { const day = dayOf(r.dimensions.datetimeHour); add(t.visits, day, visitsOf(r)); add(t.views, day, r.count); });
        each(acc.device, (t, r) => add(t.device, deviceOf(r.dimensions.deviceType), visitsOf(r)));
        each(acc.country, (t, r) => add(t.country, r.dimensions.countryName || 'unknown', visitsOf(r)));
        each(acc.pages, (t, r, prefix) => add(t.pages, prefix + (r.dimensions.requestPath || '/'), r.count));

        const days30 = [];
        for (let i = 29; i >= 0; i--) days30.push(brisbaneDay(i));
        const sum = (rows, k) => rows.reduce((s, x) => s + x[k], 0);
        const sites = [ALL, ...SITES].map(s => {
            const t = stats[s.code];
            const days = days30.map(day => ({ day, visits: t.visits[day] || 0, views: t.views[day] || 0 }));
            return {
                ...s, days,
                totals: { today: days[29].visits, todayViews: days[29].views, week: sum(days.slice(23), 'visits'), month: sum(days, 'visits'), monthViews: sum(days, 'views') },
                device: top(t.device, 4), country: top(t.country, 8), pages: top(t.pages, 10)
            };
        });
        return json({ ok: true, sites });
    } catch (e) {
        return json({ ok: false, error: 'api', message: String((e && e.message) || e).slice(0, 300) });
    }
}
