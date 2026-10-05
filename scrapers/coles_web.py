"""
Coles website Half Price specials (in-store only).

The printed Coles catalogue (salefinder) only shows ~300 highlighted specials, while coles.com.au
lists ~1,200+ Half Price products every week. This reads the website's own Half Price list and keeps
only real in-store half-price deals:
  * pricing.onlineSpecial == True  -> online-only deal, skipped
  * price must be <= 55% of the normal price (same strict rule as the Woolworths half-price list)

coles.com.au only allows a few pages per visitor before showing a "Pardon Our Interruption" page,
so each update reads as many pages as it can (a few minutes at most) and remembers them in
data/coles_web.json. The website is checked every hour on Wednesday (the day Coles specials change),
so the full list is collected within a few hours of the new week starting. The memory is cleared
automatically when a new Coles week starts (Wednesday, Sydney time).
"""
import datetime
import json
import os
import re
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_FILE = os.path.join(ROOT, 'data', 'coles_web.json')
LIST_URL = 'https://www.coles.com.au/on-special?filter_Special=halfprice&page={page}'
IMG_BASE = 'https://productimages.coles.com.au/productimages'
IMPERSONATIONS = ['chrome', 'safari', 'chrome124', 'safari17_0', 'chrome120', 'safari15_5', 'chrome116', 'edge101']
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def coles_week_start(now=None):
    """The Wednesday the current Coles specials week started (Sydney time)."""
    try:
        from zoneinfo import ZoneInfo
        today = (now or datetime.datetime.now(ZoneInfo('Australia/Sydney'))).date()
    except Exception:
        today = ((now or datetime.datetime.utcnow()) + datetime.timedelta(hours=10)).date()
    return (today - datetime.timedelta(days=(today.weekday() - 2) % 7)).isoformat()


def _load_memory(week):
    try:
        with open(MEMORY_FILE, encoding='utf-8') as f:
            mem = json.load(f)
        if mem.get('week') == week:
            return mem
    except Exception:
        pass
    return {'week': week, 'cursor': 1, 'pages': 0, 'items': {}}


def _save_memory(mem):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(mem, f, ensure_ascii=False, indent=0, sort_keys=True)


def _title(p):
    brand, name, size = (p.get('brand') or '').strip(), (p.get('name') or '').strip(), (p.get('size') or '').strip()
    t = name if not brand or name.lower().startswith(brand.lower()) else f'{brand} {name}'
    if size and size.lower() not in t.lower():
        t = f'{t} {size}'
    return re.sub(r'\s+', ' ', t).strip()


def product_to_item(p):
    """One product from the Coles website -> one special, or None when it is not an in-store half price deal."""
    if p.get('_type') != 'PRODUCT':
        return None
    pr = p.get('pricing') or {}
    if pr.get('onlineSpecial'):
        return None                                   # online-only special
    if p.get('availability') is False:
        return None
    now, was = float(pr.get('now') or 0), float(pr.get('was') or 0)
    if not (was > 0 and 0 < now <= was * 0.55):
        return None                                   # strictly half price
    pid = p.get('id')
    title = _title(p)
    if not pid or not title:
        return None
    slug = re.sub(r'[^a-z0-9]+', '-', f"{p.get('brand') or ''} {p.get('name') or ''} {p.get('size') or ''}".lower()).strip('-')
    img = ((p.get('imageUris') or [{}])[0] or {}).get('uri') or ''
    heir = p.get('merchandiseHeir') or {}
    return {
        'id': str(pid),
        'store': 'Coles',
        'title': title,
        'price': now,
        'price_display': f'${now:.2f}',
        'unit_price': pr.get('comparable') or '',
        'was_price': was,
        'save_amount': round(was - now, 2),
        'discount_desc': '1/2 PRICE',
        'image_url': f'{IMG_BASE}{img}' if img.startswith('/') else img,
        'category': ' '.join(x for x in (heir.get('category'), heir.get('subCategory')) if x).title(),
        'product_url': f'https://www.coles.com.au/product/{slug}-{pid}',
    }


def scrape_coles_web_half_price(time_budget=300, max_blocked=4):
    """Returns this week's in-store Half Price specials from coles.com.au (remembered across updates)."""
    week = coles_week_start()
    mem = _load_memory(week)
    try:
        from curl_cffi import requests as cffi
    except Exception:
        print('Coles website: curl_cffi not installed, using remembered items only')
        return list(mem['items'].values())

    state = {'i': -1, 's': None}

    def fresh():
        state['i'] += 1
        state['s'] = cffi.Session(impersonate=IMPERSONATIONS[state['i'] % len(IMPERSONATIONS)])

    def get(page):
        try:
            r = state['s'].get(LIST_URL.format(page=page), timeout=20)
        except Exception:
            return None
        m = NEXT_DATA.search(r.text or '')
        if not m:
            return None
        try:
            return json.loads(m.group(1))['props']['pageProps'].get('searchResults')
        except Exception:
            return None

    fresh()
    t0, blocked, read, added = time.time(), 0, 0, 0
    page = int(mem.get('cursor') or 1)
    while time.time() - t0 < time_budget:
        sr = get(page)
        if not sr:
            blocked += 1
            if blocked >= max_blocked:
                break
            fresh()
            time.sleep(15 * blocked)
            continue
        blocked = 0
        read += 1
        mem['pages'] = -(-int(sr.get('noOfResults') or 0) // int(sr.get('pageSize') or 48)) or mem.get('pages') or 1
        for p in sr.get('results') or []:
            it = product_to_item(p)
            if it:
                if it['id'] not in mem['items']:
                    added += 1
                mem['items'][it['id']] = it
        page = page + 1 if page < mem['pages'] else 1
        mem['cursor'] = page
        if read >= mem['pages']:
            break                                     # read every page once this run
        time.sleep(3)
        if read % 4 == 0:
            fresh()                                   # a new visitor every few pages
            time.sleep(5)
    _save_memory(mem)
    print(f"Coles website half price: read {read} pages this run (+{added} new), "
          f"{len(mem['items'])} in-store half-price specials remembered for week of {week} "
          f"(website lists {mem['pages']} pages)")
    return list(mem['items'].values())


if __name__ == '__main__':
    items = scrape_coles_web_half_price(time_budget=60)
    print(len(items), items[:2])
