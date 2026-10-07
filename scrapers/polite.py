"""
Polite downloading, shared by every scraper.

  * One request at a time per website, with a few seconds (plus a random part) between requests,
    like a person reading page after page.
  * "Too many requests" / "server busy" answers are respected: we wait as long as the site asks
    (Retry-After), within reason.
  * When a site refuses us (403, or a bot-check page), we STOP asking that site for the rest of this
    update. We never switch to a different browser identity or start a new "visitor" to get around
    the refusal - the next scheduled update simply tries again later, and the data already saved is
    used in the meantime.
"""
import random
import threading
import time

# seconds between two requests to the same site: (minimum, extra random part)
PACE = {
    'salefinder': (2.0, 1.5),     # catalogue site (Coles & Woolworths printed catalogues)
    'woolworths': (2.0, 1.5),     # Woolworths half-price list
    'coles': (6.0, 3.0),          # coles.com.au half-price list (strict bot protection)
    'aldi': (1.5, 1.0),
}
MAX_WAIT = 120                    # never wait longer than this for one Retry-After

_lock = threading.Lock()
_host_locks = {}
_next_time = {}
_blocked = {}                     # site -> reason, for this update only
_count = {}                       # site -> requests made in this update
_fails = {}                       # site -> network failures in a row
MAX_FAILS = 3                     # this many failures in a row = the site is down: stop asking it


def _host_lock(site):
    with _lock:
        return _host_locks.setdefault(site, threading.Lock())


def is_blocked(site):
    return site in _blocked


def mark_blocked(site, reason):
    if site not in _blocked:
        _blocked[site] = reason
        print(f"::notice::{site}: the website refused us ({reason}) - no more requests to it in this update; "
              f"saved data is used and the next scheduled update tries again")


def summary():
    """Requests made to each site in this update (printed at the end of the scrape)."""
    return dict(_count), dict(_blocked)


def request(site, send, *, retries=2):
    """Calls send() (which performs ONE HTTP request and returns the response) politely.
    Returns the response, or None when the site is blocked / unreachable.
    A 403 or a bot-check page marks the site blocked for the rest of this update."""
    if is_blocked(site):
        return None
    base, extra = PACE.get(site, (2.0, 1.0))
    last_exc = None
    for attempt in range(retries + 1):
        with _host_lock(site):
            wait = _next_time.get(site, 0) - time.time()
            if wait > 0:
                time.sleep(wait)
            try:
                r = send()
                last_exc = None
            except Exception as e:                      # network hiccup
                r, last_exc = None, e
            _count[site] = _count.get(site, 0) + 1
            _next_time[site] = time.time() + base + random.random() * extra
        if r is None:
            time.sleep(10 * (attempt + 1))
            continue
        _fails[site] = 0
        code = getattr(r, 'status_code', 0)
        if code in (429, 503):
            ra = (getattr(r, 'headers', {}) or {}).get('Retry-After')
            try:
                pause = min(MAX_WAIT, max(5, int(ra)))
            except Exception:
                pause = 30 * (attempt + 1)
            if attempt < retries:
                print(f"{site}: server asked us to slow down ({code}) - waiting {pause}s")
                with _host_lock(site):
                    _next_time[site] = time.time() + pause
                continue
            mark_blocked(site, f'HTTP {code}')
            return r
        if code == 403:
            mark_blocked(site, 'HTTP 403')
            return r
        if code >= 500 and attempt < retries:
            time.sleep(10 * (attempt + 1))
            continue
        return r
    if last_exc is not None:
        print(f"{site}: unreachable ({repr(last_exc)[:100]})")
        _fails[site] = _fails.get(site, 0) + 1
        if _fails[site] >= MAX_FAILS:
            mark_blocked(site, 'unreachable')
    return None
