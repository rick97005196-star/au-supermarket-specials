"""60 天最低價 (lowest price in the last 60 days) for each product on the website.

Every update records the price of each product on the site this week (in-store specials, everyday and regular
prices - exactly what specials.json shows) in data/price_history.json, then gives each product a compact field

    ph = [days, lowest, "YYYY-MM-DD", state, multi(, earlier_lower_price, "YYYY-MM-DD")]
    state 0 = this week equals the lowest, 1 = it was cheaper before (lowest + the last day at that price),
          2 = the same price all along (an everyday price, not a deal),
          3 = a new low: cheaper than every earlier price (lowest = the earlier lowest, to say by how much)
    earlier_lower_price: a lower price seen within 60 days but before the store's list was complete

so the card can say 「近 60 天最低價」 or 「60 天最低 $3.50（11/4）」.

Strict rules (nothing is guessed):
  * only prices this site really listed are used (period "current"; next week's catalogue never counts);
  * a store only counts from the day its list became complete (STORE_SINCE): before that, specials could be
    missing, so "this week is the lowest" could be wrong. The window is shorter until 60 days have passed and the
    site then says so (「近 35 天」);
  * the product must have been seen before this sale week, otherwise nothing is shown (a new product or its
    first special says nothing about cheap or dear);
  * prices are compared per item ("3 for $9" = $3.00 each) and only in the same unit (each / per kg);
  * per-state prices (rp) are not recorded: the website hides the line when the visitor's state has its own price.

The file keeps runs [first_day, last_day, price, unit] per product, so it stays small; runs older than
KEEP_DAYS are dropped.
"""
import datetime
import json
import os
import re

HISTORY_PATH = os.path.join('data', 'price_history.json')     # relative, like export_static_data.py's other files
WINDOW_DAYS = 60
KEEP_DAYS = 70
MIN_DAYS = 3           # the site says how many days it compares (「近 4 天」); fewer than this says nothing
# the first day each store's list on this site was complete (see CHANGELOG / git history):
#   ALDI: everyday range aisles read from 19 Oct; Coles: the website's full specials list from 21 Oct;
#   Woolworths: the department price cuts (Save $X) only from 22 Nov (before that they were missing).
STORE_SINCE = {'ALDI': '2026-10-19', 'Coles': '2026-10-21', 'Woolworths': '2026-11-22'}

_MULTI = re.compile(r'(\d+)\s*for\s*\$\s*([\d,]+(?:\.\d+)?)', re.I)
_KILO = re.compile(r'^\$?\s*\d[\d,]*(\.\d+)?\s*(/\s*|per\s+)?kg$', re.I)
_ID = (
    (re.compile(r'woolworths\.com\.au/shop/productdetails/(\d+)', re.I), 'w'),
    (re.compile(r'coles\.com\.au/product/[^?#]*?-(\d{4,})(?:[/?#]|$)', re.I), 'c'),
    (re.compile(r'aldi\.com\.au/product/[^?#]*?-(\d{6,})(?:[/?#]|$)', re.I), 'a'),
)


def brisbane_today():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=10)).date()


def product_key(it):
    """The supermarket's own product number when the link has one, else the name (lower case, letters and digits)."""
    url = it.get('product_url') or ''
    for rx, tag in _ID:
        m = rx.search(url)
        if m:
            return f"{it.get('store')}|{tag}{m.group(1)}"
    name = re.sub(r'[^a-z0-9]+', ' ', (it.get('title') or '').lower().replace('’', "'")).strip()
    return f"{it.get('store')}|t:{name}" if name else ''


def each_price(it):
    """(price per item, unit, multi-buy?) - unit 'kg' when sold by the kilo, else ''."""
    disp = str(it.get('price_display') or '').strip()
    try:
        price = float(it.get('price') or 0)
    except (TypeError, ValueError):
        price = 0.0
    m = _MULTI.search(disp)
    multi = False
    if m:
        n, total = int(m.group(1)), float(m.group(2).replace(',', ''))
        if n > 0 and total > 0:
            price, multi = total / n, n > 1
    unit = 'kg' if _KILO.match(disp.lower()) else ''
    return (round(price, 2) if price > 0 else 0.0), unit, multi


def load(path=HISTORY_PATH):
    try:
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get('items'), dict):
            return d
    except (OSError, ValueError):
        pass
    return {'v': 1, 'items': {}}


def save(hist, path=HISTORY_PATH):
    """One product per line, so each update's git change stays small."""
    items = hist.get('items', {})
    head = {k: v for k, v in hist.items() if k != 'items'}
    with open(path, 'w', encoding='utf-8') as f:
        f.write('{' + ','.join(f'{json.dumps(k)}:{json.dumps(v)}' for k, v in sorted(head.items())) + ',"items":{\n')
        f.write(',\n'.join(f'{json.dumps(k, ensure_ascii=False)}:{json.dumps(v, separators=(",", ":"))}'
                            for k, v in sorted(items.items())))
        f.write('\n}}\n')


def record(hist, items, day):
    """Add this update's prices (one observation per product per day; the lowest if listed twice)."""
    day = day.isoformat() if hasattr(day, 'isoformat') else str(day)
    seen = {}
    for it in items:
        if it.get('period', 'current') != 'current' or it.get('store') not in STORE_SINCE:
            continue
        key = product_key(it)
        price, unit, multi = each_price(it)
        if not key or price <= 0:
            continue
        prev = seen.get(key)
        if prev is None or price < prev[0]:
            seen[key] = (price, unit, multi)
    runs_all = hist.setdefault('items', {})
    for key, (price, unit, multi) in seen.items():
        runs = runs_all.setdefault(key, [])
        # drop what an earlier update today wrote (prices can be corrected during the day)
        while runs and runs[-1][0] == day and runs[-1][1] == day:
            runs.pop()
        if runs and runs[-1][1] == day:
            runs[-1][1] = (datetime.date.fromisoformat(day) - datetime.timedelta(days=1)).isoformat()
        flag = unit + ('m' if multi else '')
        if runs and runs[-1][2] == price and runs[-1][3] == flag and runs[-1][1] >= _minus(day, 1):
            runs[-1][1] = day                                      # same price as yesterday: extend
        else:
            runs.append([day, day, price, flag])
    # forget what is older than KEEP_DAYS
    cut = _minus(day, KEEP_DAYS)
    for key in list(runs_all):
        runs = [r for r in runs_all[key] if r[1] >= cut]
        if runs:
            runs_all[key] = runs
        else:
            del runs_all[key]
    hist['updated'] = day
    return len(seen)


def _minus(day, n):
    return (datetime.date.fromisoformat(day) - datetime.timedelta(days=n)).isoformat()


def week_start(day):
    """The Wednesday the current sale week started (Coles, Woolworths and ALDI all change on Wednesday)."""
    d = datetime.date.fromisoformat(day) if isinstance(day, str) else day
    return d - datetime.timedelta(days=(d.weekday() - 2) % 7)


def summary(runs, store, price, unit, day):
    """ph for one product, or None when nothing honest can be said."""
    day = day.isoformat() if hasattr(day, 'isoformat') else str(day)
    since = STORE_SINCE.get(store)
    if not since or price <= 0:
        return None
    start = max(_minus(day, WINDOW_DAYS - 1), since)
    days = (datetime.date.fromisoformat(day) - datetime.date.fromisoformat(start)).days + 1
    if days < MIN_DAYS:
        return None
    wk = week_start(day).isoformat()
    obs = [r for r in runs if r[1] >= start and r[0] <= day and r[3].replace('m', '') == unit]
    before = [r for r in obs if r[0] < wk]
    if not before:
        return None                                   # never seen before this week: no comparison
    prev_lo = min(r[2] for r in before)
    lo = min(min(r[2] for r in obs), price)
    early = _earlier(runs, store, unit, day, start, min(lo, price))
    if price < prev_lo - 0.005:
        # 新低: cheaper than every earlier price in the window; lo = the earlier lowest, to say by how much
        at = max(r[1] for r in before if abs(r[2] - prev_lo) < 0.005)
        multi = any(r[3].endswith('m') for r in before if abs(r[2] - prev_lo) < 0.005)
        return [days, round(prev_lo, 2), at, 3, 1 if multi else 0] + early
    if price <= lo + 0.005:
        if _unchanged(obs, price, start, day):
            return [days, round(price, 2), '', 2, 0] + early          # the same price every day of the window
        return [days, round(price, 2), '', 0, 0] + early
    at = max(r[1] for r in obs if abs(r[2] - lo) < 0.005)
    multi = any(r[3].endswith('m') for r in obs if abs(r[2] - lo) < 0.005)
    return [days, round(lo, 2), at, 1, 1 if multi else 0] + early


def _earlier(runs, store, unit, day, start, below):
    """A lower price seen in the 60 days but before the store's list was complete (so it cannot be called "the
    lowest"): still a true fact, shown as 「更早 11/9 曾賣 $2.19」. [] when there is none."""
    first = _minus(day, WINDOW_DAYS - 1)
    old = [r for r in runs if r[0] < start and r[1] >= first and r[3].replace('m', '') == unit
           and r[2] < below - 0.005]
    if not old:
        return []
    elo = min(r[2] for r in old)
    eat = max(min(r[1], _minus(start, 1)) for r in old if abs(r[2] - elo) < 0.005)
    return [round(elo, 2), eat]


def _unchanged(obs, price, start, day, gap=3):
    """Seen at this one price on (nearly) every day from the window's start until today: an everyday price,
    not a deal. Short gaps (an update day when a store's list was still loading) do not count."""
    if any(abs(r[2] - price) >= 0.005 for r in obs):
        return False
    obs = sorted(obs)
    d = datetime.date.fromisoformat
    if (d(obs[0][0]) - d(start)).days > gap or (d(day) - d(obs[-1][1])).days > 0:
        return False
    return all((d(b[0]) - d(a[1])).days <= gap for a, b in zip(obs, obs[1:]))


def apply_history(items, hist=None, day=None, path=HISTORY_PATH, save_file=True):
    """Record today's prices, then give every current product its ph. Returns (recorded, with_ph)."""
    day = day or brisbane_today()
    hist = hist if hist is not None else load(path)
    n = record(hist, items, day)
    runs_all = hist['items']
    shown = 0
    for it in items:
        it.pop('ph', None)
        if it.get('period', 'current') != 'current':
            continue
        key = product_key(it)
        price, unit, _ = each_price(it)
        ph = summary(runs_all.get(key, []), it.get('store'), price, unit, day) if key else None
        if ph:
            it['ph'] = ph
            shown += 1
    if save_file:
        save(hist, path)
    return n, shown
