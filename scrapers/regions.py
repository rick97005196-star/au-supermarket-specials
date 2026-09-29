# -*- coding: utf-8 -*-
"""
Regional (state) catalogues for Coles & Woolworths.

Coles and Woolworths print a slightly different catalogue for every state: ~90% of the specials
are the same, but some prices differ and some local items (fruit & veg, drinks) only exist in
one state. The website shows Queensland by default and lets visitors pick their own state.

How the data is stored (keeps the files small):
  * every special is stored ONCE
  * `regions`       = the states where it is on special (missing/empty = every state)
  * `region_prices` = {state: {price, was_price, ...}} only for states where the price differs
"""
import json
import os
import random
import re
import threading
from concurrent.futures import ThreadPoolExecutor

# salefinder decides the state from the "postcodeId" cookie (ids of each capital city)
REGIONS = [
    ('QLD', 8328),   # Brisbane City 4000
    ('NSW', 349),    # Haymarket (Sydney) 2000
    ('ACT', 3608),   # Canberra 2600
    ('VIC', 5188),   # Melbourne 3000
    ('SA', 11707),   # Adelaide 5000
    ('WA', 13646),   # Perth 6000
    ('TAS', 15374),  # Hobart 7000
    ('NT', 1),       # Darwin 0800
]
BASE_REGION = 'QLD'
ALL_REGIONS = [r for r, _ in REGIONS]
# Canberra stores use the NSW catalogue
SLUG_TOKENS = {'ACT': ('act', 'nsw')}


def region_request(url, postcode_id):
    """URL + kwargs for a page shown for one state. The landing pages are cached by URL,
    so a random query string is needed, otherwise another state's page may come back."""
    sep = '&' if '?' in url else '?'
    return f"{url}{sep}cb={random.randint(10**6, 10**9)}", {'cookies': {'postcodeId': str(postcode_id)}}


def _has_region_links(text, region):
    toks = SLUG_TOKENS.get(region, (region.lower(),))
    for m in re.finditer(r'-catalogue/([a-z0-9-]+)/\d+/catalogue2', text or ''):
        if any(t in m.group(1).lower().split('-') for t in toks):
            return True
    return False


_IMPERSONATE = ('chrome', 'safari', 'chrome124', 'edge', 'chrome120', 'safari17_0')


def fetch_region_page(url, postcode_id, region, attempts=6):
    """The catalogue landing page as shown to someone living in `region`.
    The catalogue site sometimes refuses cloud servers (HTTP 403) for uncached pages, so this
    retries with fresh browser-like sessions, and only accepts a page listing that state's
    own catalogues. Returns the page text or None."""
    import time
    last = None
    for i in range(attempts):
        full, kw = region_request(url, postcode_id)
        try:
            try:
                from curl_cffi import requests as cr
                sess = cr.Session(impersonate=_IMPERSONATE[i % len(_IMPERSONATE)])
            except Exception:
                import requests as rq
                sess = rq.Session()
                sess.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            r = sess.get(full, timeout=25, **kw)
            last = r.status_code
            if r.status_code == 200 and _has_region_links(r.text, region):
                return r.text
            if r.status_code == 200:
                last = '200 but another state'
        except Exception as e:
            last = repr(e)[:120]
        time.sleep(4 + 4 * i + random.random() * 3)
    print(f"{region}: landing page not available ({last})")
    return None


def filter_region_links(slugs_ids, region, exact_prefix=None):
    """Keep only catalogue links that belong to `region` (e.g. 'weekly-catalogue-qld',
    'coles-catalogue-qld-metro'); prefer the metro / exact version over regional-town ones."""
    toks = SLUG_TOKENS.get(region, (region.lower(),))
    for tok in toks:  # first token = the state itself, then the fallback (ACT -> NSW)
        if exact_prefix:
            hit = [(s, i) for s, i in slugs_ids if s.lower() == f"{exact_prefix}-{tok}"]
        else:
            hit = [(s, i) for s, i in slugs_ids if tok in s.lower().split('-')]
            metro = [(s, i) for s, i in hit if 'metro' in s.lower()]
            hit = metro or hit
        if hit:
            return hit
    return []


# ---------------------------------------------------------------- merging

def _norm_desc(item):
    return re.sub(r'[\d.$]+', '#', (item.get('discount_desc') or '').lower()).strip()


def _key_map(items):
    """(title, n) -> item. Items with the same name (e.g. one multi-buy + one 1/2 price) are told
    apart by the kind of offer, so they are matched to the same offer in other states."""
    groups = {}
    for it in items:
        groups.setdefault((it.get('title') or '').strip().lower(), []).append(it)
    out = {}
    for title, members in groups.items():
        members = sorted(members, key=lambda x: (_norm_desc(x), x.get('price') or 0))
        for n, it in enumerate(members):
            out[(title, n)] = it
    return out


PRICE_FIELDS = ('price', 'price_display', 'was_price', 'save_amount', 'discount_desc', 'unit_price')


def _same_price(a, b):
    return all(abs(float(a.get(f) or 0) - float(b.get(f) or 0)) < 0.005 for f in ('price', 'was_price', 'save_amount'))


def merge_regions(per_region):
    """per_region: {region: [items]} for ONE period. Regions that could not be read are treated
    as identical to the base region (better than hiding their specials)."""
    base = per_region.get(BASE_REGION)
    if base is None:
        return []
    known = [r for r in ALL_REGIONS if per_region.get(r) is not None]
    mirror = [r for r in ALL_REGIONS if r not in known]  # unreadable -> same as base
    maps = {r: _key_map(per_region[r]) for r in known}

    order = list(maps[BASE_REGION].keys())
    seen = set(order)
    for r in known:
        for k in maps[r]:
            if k not in seen:
                seen.add(k)
                order.append(k)

    merged = []
    for k in order:
        present = [r for r in known if k in maps[r]]
        if k in maps[BASE_REGION]:
            present += mirror
        main_region = BASE_REGION if k in maps[BASE_REGION] else present[0]
        item = dict(maps[main_region][k])
        rp = {}
        for r in present:
            if r in maps and r != main_region:
                other = maps[r][k]
                if not _same_price(item, other):
                    rp[r] = {f: other.get(f) for f in PRICE_FIELDS if other.get(f) not in (None, '')}
        item['regions'] = None if set(present) == set(ALL_REGIONS) else [r for r in ALL_REGIONS if r in present]
        item['region_prices'] = rp or None
        merged.append(item)
    return merged


# ---------------------------------------------------------------- orchestration

MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'catalogues.json')


def _load_memory():
    try:
        with open(MEMORY_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_memory(memory):
    try:
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=1, sort_keys=True)
    except Exception as e:
        print(f"Could not save catalogue memory: {e}")


def scrape_all_regions(store, discover_fn, scrape_items_fn, pick_fn, max_pages=50, workers=4):
    """Read every state's catalogues (the same catalogue is only downloaded once) and merge them.
    Returns {'current': {'items', 'date_range'}, 'next': {...}} like the single-state scrapers."""
    chosen = {}      # region -> {'current': cat, 'next': cat}
    catalogues = {}  # id -> cat
    memory = _load_memory()
    for region, pid in REGIONS:
        try:
            cats = discover_fn(pid, region)
        except Exception as e:
            print(f"{store} {region}: catalogue discovery failed: {e}")
            cats = []
        if cats:
            memory.setdefault(store, {})[region] = [
                {'id': c['id'], 'url': c['url'], 'date_range': c.get('date_range', '')} for c in cats]
        else:
            # The catalogue site sometimes refuses our server. Use the catalogues seen on an earlier
            # run instead: yesterday's "next week" catalogue is today's "this week", so the Wednesday
            # switch-over still happens.
            cats = [dict(c, soup=None) for c in memory.get(store, {}).get(region, [])]
            if cats:
                print(f"::notice::{store} {region}: site busy - using the catalogues remembered from an earlier run")
            else:
                print(f"::warning::{store} {region}: no catalogue found - this state will show the {BASE_REGION} specials")
                continue
        cur, nxt = pick_fn(cats)
        chosen[region] = {'current': cur, 'next': nxt}
        for c in (cur, nxt):
            if c is not None:
                catalogues.setdefault(c['id'], c)
        print(f"{store} {region}: current {cur and cur['id']} ({cur and cur['date_range']}), next {nxt and nxt['id']}")

    _save_memory(memory)
    items_by_id = {}
    lock = threading.Lock()

    def work(cat):
        items = scrape_items_fn(cat['url'], cat.get('soup'), max_pages=max_pages)
        with lock:
            items_by_id[cat['id']] = items
        print(f"{store} catalogue {cat['id']}: {len(items)} specials")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, catalogues.values()))

    res = {'current': {'items': [], 'date_range': ''}, 'next': {'items': [], 'date_range': ''}}
    base = chosen.get(BASE_REGION)
    if not base:
        print(f"::warning::{store}: the {BASE_REGION} catalogue could not be read - existing data will be kept")
        return res
    for period in ('current', 'next'):
        base_cat = base.get(period)
        if base_cat is None:
            continue
        base_start = (base_cat.get('date_range') or '').split('-')[0].strip()
        per_region = {}
        for region, sel in chosen.items():
            cat = sel.get(period)
            # a state whose catalogue is for another week (rare) is treated like the base state
            if cat is None or (cat.get('date_range') or '').split('-')[0].strip() != base_start:
                continue
            if cat['id'] in items_by_id:
                per_region[region] = items_by_id[cat['id']]
        if not per_region.get(BASE_REGION):
            continue
        res[period]['date_range'] = base_cat['date_range']
        res[period]['items'] = merge_regions(per_region)
        n_local = sum(1 for x in res[period]['items'] if x.get('regions'))
        n_price = sum(1 for x in res[period]['items'] if x.get('region_prices'))
        print(f"{store} {period}: {len(res[period]['items'])} specials in total, "
              f"{n_local} only in some states, {n_price} with state-specific prices")
    return res
