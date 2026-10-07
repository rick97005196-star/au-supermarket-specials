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
import datetime
import gzip
import json
import os
import random
import re
import threading
import time
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


_REGION_SESSION = {}


def _region_session():
    s = _REGION_SESSION.get('s')
    if s is None:
        try:
            from curl_cffi import requests as cr
            s = cr.Session(impersonate='chrome')
        except Exception:
            import requests as rq
            s = rq.Session()
            s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        _REGION_SESSION['s'] = s
    return s


def fetch_region_page(url, postcode_id, region, attempts=2):
    """The catalogue landing page as shown to someone living in `region`, or None.
    Polite: one browser identity, paced requests; when the site refuses us we stop (the
    catalogues remembered from an earlier update are used instead)."""
    from scrapers.polite import request
    last = None
    for _ in range(attempts):
        full, kw = region_request(url, postcode_id)     # a fresh cache-buster, same identity
        r = request('salefinder', lambda: _region_session().get(full, timeout=25, **kw))
        if r is None:
            last = 'refused or unreachable'
            break
        last = r.status_code
        if r.status_code == 200 and _has_region_links(r.text, region):
            return r.text
        if r.status_code != 200:
            break
        last = '200 but another state'
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


def clean_title(title):
    """Catalogue names carry footnote marks that differ per state ("Prawns§", "Tablets Pk 100~")
    and mixed quote styles (Nando's / Nando’s). Remove them so one product = one entry."""
    t = (title or '').replace('\u2019', "'").replace('\u2018', "'").replace('\u00a0', ' ')
    t = re.sub(r'[\s§~*#^†‡¹²³]+$', '', t)
    return re.sub(r'\s{2,}', ' ', t).strip()


def _key_map(items):
    """(title, n) -> item. Items with the same name (e.g. one multi-buy + one 1/2 price) are told
    apart by the kind of offer, so they are matched to the same offer in other states."""
    groups = {}
    for it in items:
        it['title'] = clean_title(it.get('title'))
        groups.setdefault(it['title'].lower(), []).append(it)
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


class ItemList(list):
    """The specials of one catalogue + whether the WHOLE catalogue was read (complete=True).
    An interrupted download is never stored as complete."""
    complete = False


# Every catalogue is downloaded completely ONCE and kept here (compressed). Later updates reuse it,
# so the hourly checks only look for new catalogues, and the Wednesday switch-over uses the
# "next week" catalogue that was already downloaded on Monday/Tuesday.
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'catalogue_items.json.gz')
VERIFY_HOURS = 24          # a stored catalogue is read again once a day, to catch late changes
FULL_DISCOVERY_HOURS = 6   # every state's catalogue list is checked at least this often


def _load_cache():
    try:
        with gzip.open(CACHE_FILE, 'rt', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache):
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        data = json.dumps(cache, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        # mtime=0: the file only changes when the catalogues change (no needless commits)
        with open(CACHE_FILE, 'wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as f:
            f.write(data.encode('utf-8'))
    except Exception as e:
        print(f"Could not save catalogue cache: {e}")


def _brisbane_today():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=10)).date()


def _range_dates(rng):
    m = re.findall(r'(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s*(\d{4})?', rng or '')
    if len(m) < 2:
        return None
    today = _brisbane_today()
    try:
        ye = int(m[1][2]) if m[1][2] else today.year
        ys = int(m[0][2]) if m[0][2] else ye
        s = datetime.datetime.strptime(f"{m[0][0]} {m[0][1]} {ys}", "%d %b %Y").date()
        e = datetime.datetime.strptime(f"{m[1][0]} {m[1][1]} {ye}", "%d %b %Y").date()
        return (s.replace(year=s.year - 1) if s > e else s), e
    except ValueError:
        return None


def _needs_download(entry, cat, now):
    """Download (again) only when: never read completely, read more than a day ago, or the
    catalogue starts today/has started since it was read (the Wednesday "anything missing?" check)."""
    if not entry or not entry.get('complete'):
        return True
    if now - float(entry.get('fetched_at') or 0) > VERIFY_HOURS * 3600:
        return True
    d = _range_dates(cat.get('date_range') or entry.get('date_range'))
    fetched_day = (datetime.datetime.utcfromtimestamp(float(entry.get('fetched_at') or 0)) + datetime.timedelta(hours=10)).date()
    if d and d[0] <= _brisbane_today() and fetched_day < d[0]:
        return True
    return False


def scrape_all_regions(store, discover_fn, scrape_items_fn, pick_fn, max_pages=50, workers=1):
    """Read every state's catalogues (each catalogue downloaded completely once, then reused) and
    merge them. Returns {'current': {'items', 'date_range'}, 'next': {...}}."""
    chosen = {}      # region -> {'current': cat, 'next': cat}
    catalogues = {}  # id -> cat
    memory = _load_memory()
    cache = _load_cache()
    sc = cache.setdefault(store, {})
    meta = memory.setdefault('_meta', {}).setdefault(store, {})
    now = time.time()
    known_dates = {cid: e.get('date_range') for cid, e in sc.items() if e.get('date_range')}
    for reg_cats in (memory.get(store) or {}).values():
        for c in reg_cats:
            if c.get('date_range'):
                known_dates.setdefault(str(c['id']), c['date_range'])

    # The base state (Queensland) is checked on every update. The other states only when Queensland
    # shows a catalogue we have not seen yet, when a state was never read, or every few hours.
    full = now - float(meta.get('full_discovery') or 0) > FULL_DISCOVERY_HOURS * 3600
    region_order = sorted(REGIONS, key=lambda rp: rp[0] != BASE_REGION)
    for region, pid in region_order:
        remembered = (memory.get(store) or {}).get(region) or []
        check = full or region == BASE_REGION or not remembered
        cats = []
        if check:
            try:
                cats = discover_fn(pid, region, known_dates=known_dates)
            except Exception as e:
                print(f"{store} {region}: catalogue discovery failed: {e}")
                cats = []
        if cats:
            # merge with what was remembered (a check cut short by the site must not forget a
            # catalogue); catalogues that ended more than a week ago are dropped
            ids = {c['id'] for c in cats}
            for old in remembered:
                d = _range_dates(old.get('date_range'))
                if old['id'] not in ids and d and (_brisbane_today() - d[1]).days <= 7:
                    cats.append(dict(old, soup=None))
            memory.setdefault(store, {})[region] = [
                {'id': c['id'], 'url': c['url'], 'date_range': c.get('date_range', '')} for c in cats]
            for c in cats:
                if c.get('date_range'):
                    known_dates.setdefault(str(c['id']), c['date_range'])
            if region == BASE_REGION and not full and any(str(c['id']) not in sc for c in cats):
                full = True          # a new catalogue appeared: check every state in this update
                print(f"{store}: new catalogue found - checking every state")
        else:
            # Not checked this time (nothing new expected), or the site refused us: use the catalogues
            # seen on an earlier update. Yesterday's "next week" catalogue is today's "this week",
            # so the Wednesday switch-over still happens.
            cats = [dict(c, soup=None) for c in remembered]
            if cats:
                if check:
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
    if full:
        meta['full_discovery'] = now
    _save_memory(memory)

    items_by_id = {}
    lock = threading.Lock()
    stats = {'reused': 0, 'downloaded': 0, 'kept_old': 0}

    def work(cat):
        cid = str(cat['id'])
        entry = sc.get(cid)
        if not _needs_download(entry, cat, now):
            with lock:
                items_by_id[cat['id']] = [dict(x) for x in entry['items']]
                stats['reused'] += 1
            return
        items = scrape_items_fn(cat['url'], cat.get('soup'), max_pages=max_pages)
        complete = bool(getattr(items, 'complete', False)) and len(items) > 0
        with lock:
            if complete:
                if entry and entry.get('complete'):
                    old = {x.get('title') for x in entry['items']}
                    new = {x.get('title') for x in items}
                    if old != new:
                        print(f"{store} catalogue {cid}: re-check found changes (+{len(new - old)} / -{len(old - new)})")
                sc[cid] = {'date_range': cat.get('date_range', ''), 'items': list(items), 'complete': True, 'fetched_at': now}
                items_by_id[cat['id']] = list(items)
                stats['downloaded'] += 1
                print(f"{store} catalogue {cid}: {len(items)} specials (read completely and saved)")
            elif entry and entry.get('items') and (entry.get('complete') or len(entry['items']) >= len(items)):
                items_by_id[cat['id']] = [dict(x) for x in entry['items']]   # keep the saved copy
                stats['kept_old'] += 1
                print(f"{store} catalogue {cid}: download interrupted - using the saved copy ({len(entry['items'])} specials), retried next update")
            else:
                items_by_id[cat['id']] = list(items)
                if items:
                    sc[cid] = {'date_range': cat.get('date_range', ''), 'items': list(items), 'complete': False, 'fetched_at': now}
                print(f"{store} catalogue {cid}: {len(items)} specials (incomplete, retried next update)")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, catalogues.values()))

    # forget catalogues that ended more than a week ago
    today = _brisbane_today()
    for cid in list(sc):
        d = _range_dates(sc[cid].get('date_range'))
        if (d and (today - d[1]).days > 7) or (not d and now - float(sc[cid].get('fetched_at') or 0) > 21 * 86400):
            del sc[cid]
    _save_cache(cache)
    print(f"::notice::{store} 型錄：沿用已存的 {stats['reused']} 份、下載 {stats['downloaded']} 份"
          + (f"、下載中斷改用舊存檔 {stats['kept_old']} 份" if stats['kept_old'] else ''))

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
