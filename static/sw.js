/* AU Supermarket Specials — offline support (Service Worker)
 *
 * - Page & specials data: network first (always fresh when online),
 *   fall back to the last saved copy when offline (e.g. in a supermarket basement).
 * - Styles, scripts, icons, fonts: served from the saved copy (fast), refreshed in the background.
 * - Product photos from the supermarkets' servers are not stored (they can't be cached safely);
 *   the page shows a placeholder for them while offline.
 */
const VERSION = 'v1';
const SHELL_CACHE = `shell-${VERSION}`;
const DATA_CACHE = `data-${VERSION}`;
const ASSET_CACHE = `assets-${VERSION}`;

const SHELL = [
    '/',
    '/index.html',
    '/manifest.json',
    '/logo.jpg',
    '/icon-192.png',
    '/woolworths_half_price_badge.png',
    '/coles_half_price_badge.png',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(SHELL_CACHE)
            .then((cache) => cache.addAll(SHELL))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    const keep = [SHELL_CACHE, DATA_CACHE, ASSET_CACHE];
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(keys.filter((k) => !keep.includes(k)).map((k) => caches.delete(k))))
            .then(() => self.clients.claim())
    );
});

function withTimeout(promise, ms) {
    return new Promise((resolve, reject) => {
        const t = setTimeout(() => reject(new Error('timeout')), ms);
        promise.then((r) => { clearTimeout(t); resolve(r); }, (e) => { clearTimeout(t); reject(e); });
    });
}

// Network first; on failure (offline / very slow) use the saved copy
async function networkFirst(request, cacheName, timeoutMs) {
    const cache = await caches.open(cacheName);
    try {
        const response = await withTimeout(fetch(request), timeoutMs);
        if (response && response.ok) cache.put(stripSearch(request), response.clone());
        return response;
    } catch (e) {
        const cached = await cache.match(stripSearch(request));
        if (cached) return cached;
        if (request.mode === 'navigate') {
            const shell = await caches.match('/index.html');
            if (shell) return shell;
        }
        throw e;
    }
}

// Saved copy first (fast); refresh it in the background
async function staleWhileRevalidate(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);
    const refresh = fetch(request).then((response) => {
        if (response && (response.ok || response.type === 'cors')) cache.put(request, response.clone());
        return response;
    }).catch(() => cached);
    return cached || refresh;
}

// Data files are saved without "?cache-busting" query strings so the offline copy is always found
function stripSearch(request) {
    const url = new URL(request.url);
    if (url.pathname.startsWith('/data/')) return new Request(url.origin + url.pathname);
    return request;
}

async function trimCache(cacheName, maxEntries) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    for (let i = 0; i < keys.length - maxEntries; i++) await cache.delete(keys[i]);
}

self.addEventListener('fetch', (event) => {
    const request = event.request;
    if (request.method !== 'GET') return;
    const url = new URL(request.url);

    // Never touch API calls or browser-extension requests
    if (url.pathname.startsWith('/api/') || !url.protocol.startsWith('http')) return;

    // 1) The page itself
    if (request.mode === 'navigate') {
        event.respondWith(networkFirst(request, SHELL_CACHE, 4000));
        return;
    }

    // 2) Specials data (prices change every week -> always try fresh first)
    if (url.origin === location.origin && url.pathname.startsWith('/data/')) {
        event.respondWith(networkFirst(request, DATA_CACHE, 6000));
        return;
    }

    // 3) Our own styles/scripts/images and the icon/font CDNs
    const sameOriginAsset = url.origin === location.origin;
    const cdnAsset = /(^|\.)cdnjs\.cloudflare\.com$|(^|\.)fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
    if (sameOriginAsset || cdnAsset) {
        event.respondWith(
            staleWhileRevalidate(request, ASSET_CACHE).finally(() => trimCache(ASSET_CACHE, 80))
        );
    }
    // 4) Everything else (supermarket product photos) -> normal network
});
