"""
Coles website Half Price specials (in-store only).

The printed Coles catalogue (salefinder) only shows ~300 highlighted specials, while coles.com.au
lists ~1,200+ Half Price products every week. This reads the website's own Half Price list and keeps
only real in-store half-price deals:
  * pricing.onlineSpecial == True  -> online-only deal, skipped
  * price must be <= 55% of the normal price (same strict rule as the Woolworths half-price list)

coles.com.au only allows a few pages per visitor before showing a "Pardon Our Interruption" page.
We respect that: each update reads politely until the site says stop, remembers what it read in
data/coles_web.json, and the next update continues from the same page. The website is checked every hour on Wednesday (the day Coles specials change),
so the full list is collected within a few hours of the new week starting. The memory is cleared
automatically when a new Coles week starts (Wednesday, Sydney time).

After the Half Price list, the website's All specials list adds the other in-store deals the same way:
multi-buys ("Pick any 2 for $9") and price cuts ("save $11.00", "40% Off"). Half price products are
left to the Half Price list. Specials marked only "SPECIAL" with no "was" price (mostly Coles fresh
produce) are kept at their price with no saving, marked SPECIAL_DESC and shown as "特價".
Coles' website has no everyday low price list.
"""
import datetime
import json
import os
import re
import time

from scrapers.regions import SPECIAL_DESC

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_FILE = os.path.join(ROOT, 'data', 'coles_web.json')
LIST_URL = 'https://www.coles.com.au/on-special?filter_Special=halfprice&page={page}'
MORE_URL = 'https://www.coles.com.au/on-special?page={page}'          # All specials (half price included)
IMG_BASE = 'https://productimages.coles.com.au/productimages'
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def coles_week_start(now=None):
    """The Wednesday the current Coles specials week started.
    Counted from Wednesday 1am Brisbane time (= 2am Sydney in summer): by then every state's Coles
    website has switched, so items read just before the switch are never kept as "next week's"."""
    now = now or datetime.datetime.utcnow()
    local = now + datetime.timedelta(hours=10) - datetime.timedelta(hours=1)
    today = local.date()
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


def _product(p):
    """What every Coles website special shares, or None for online-only / unavailable products."""
    if p.get('_type') != 'PRODUCT':
        return None
    pr = p.get('pricing') or {}
    if pr.get('onlineSpecial'):
        return None                                   # online-only special
    if p.get('availability') is False:
        return None
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
        'unit_price': pr.get('comparable') or '',
        'image_url': f'{IMG_BASE}{img}' if img.startswith('/') else img,
        'category': ' '.join(x for x in (heir.get('category'), heir.get('subCategory')) if x).title(),
        # Coles' own aisle (e.g. "Skin Care Facial Skincare"): used when no category rule knows the product
        'store_category': ' '.join(x for x in (heir.get('category'), heir.get('subCategory')) if x).title(),
        'product_url': f'https://www.coles.com.au/product/{slug}-{pid}',
    }


def product_to_item(p):
    """One product from the Coles website -> one special, or None when it is not an in-store half price deal."""
    base = _product(p)
    if not base:
        return None
    pr = p.get('pricing') or {}
    now, was = float(pr.get('now') or 0), float(pr.get('was') or 0)
    if not (was > 0 and 0 < now <= was * 0.55):
        return None                                   # strictly half price
    return dict(base, price=now, price_display=f'${now:.2f}', was_price=was,
                save_amount=round(was - now, 2), discount_desc='1/2 PRICE')


_MULTI = re.compile(r'\b(\d+)\s*for\s*\$\s*(\d+(?:\.\d{1,2})?)', re.I)     # "Pick any 2 for $9", "Buy 2 for $7"


def special_to_item(p):
    """One product from the All specials list -> a multi-buy, a price cut or a "SPECIAL" with no
    "was" price, or None (half price: the Half Price list has it)."""
    base = _product(p)
    if not base or product_to_item(p):
        return None
    pr = p.get('pricing') or {}
    now, was = float(pr.get('now') or 0), float(pr.get('was') or 0)
    if now <= 0:
        return None
    m = _MULTI.search(pr.get('offerDescription') or '')
    if m:
        n, deal = int(m.group(1)), float(m.group(2))
        if not (n >= 2 and 0 < deal < n * now - 0.009):
            return None
        # a multi-buy is priced as the deal, like Woolworths: "2 for $9.00", was = 2 x the single price
        desc = f'{n} for ${deal:.2f}'
        return dict(base, price=deal, price_display=desc, was_price=round(n * now, 2),
                    save_amount=round(n * now - deal, 2), discount_desc=desc)
    if not was > now:
        if was or pr.get('specialType') or pr.get('offerDescription') or pr.get('promotionType') != 'SPECIAL':
            return None                               # e.g. a multi-buy that saves nothing
        return dict(base, price=now, price_display=f'${now:.2f}', was_price=0, save_amount=0,
                    discount_desc=SPECIAL_DESC)
    return dict(base, price=now, price_display=f'${now:.2f}', was_price=was,
                save_amount=round(was - now, 2), discount_desc=f'Save ${was - now:.2f}')


REFRESH_HOURS = 6          # after a complete read, the list is only read again every few hours
MORE_REFRESH_HOURS = 12    # All specials is 4x longer and changes slowly: read at most twice a day

_session = []              # ONE browser identity for the whole update, shared by both lists


def _with_aisle(items):
    """Remembered items read before the aisle was kept separately carry it in 'category'."""
    return [dict(it, store_category=it.get('store_category') or it.get('category') or '') for it in items]


def _switching():
    # Tuesday 11pm – Wednesday 1am Brisbane: the states switch to the new week one after another.
    # Show only the catalogue for these two hours instead of mixing two weeks of website prices.
    now = datetime.datetime.utcnow()
    return now.weekday() == 1 and 13 <= now.hour < 15


def _get(url):
    """One page of a website list, or None when refused or shown the bot check."""
    from curl_cffi import requests as cffi
    from scrapers.polite import request, mark_blocked
    if not _session:
        _session.append(cffi.Session(impersonate='chrome'))
    r = request('coles', lambda: _session[0].get(url, timeout=20))
    if r is None or r.status_code != 200:
        return None
    m = NEXT_DATA.search(r.text or '')
    if not m:
        mark_blocked('coles', 'bot-check page')         # "Pardon Our Interruption": stop here
        return None
    try:
        return json.loads(m.group(1))['props']['pageProps'].get('searchResults')
    except Exception:
        return None


def _read_pages(mem, url, to_item, time_budget):
    """Reads one website list from the page the last update stopped at, until the time is up or the
    site says stop. Returns (pages read, new specials, first page read)."""
    from scrapers.polite import is_blocked
    t0, read, added = time.time(), 0, 0
    page = int(mem.get('cursor') or 1)
    start_page = page
    while time.time() - t0 < time_budget and not is_blocked('coles'):
        sr = _get(url.format(page=page))
        if not sr:
            break                                       # refused / bot check: continue next update
        read += 1
        mem['pages'] = -(-int(sr.get('noOfResults') or 0) // int(sr.get('pageSize') or 48)) or mem.get('pages') or 1
        for p in sr.get('results') or []:
            it = to_item(p)
            if it:
                if it['id'] not in mem['items']:
                    added += 1
                mem['items'][it['id']] = it
        mem['pages_done'] = int(mem.get('pages_done') or 0) + 1
        page = page + 1 if page < mem['pages'] else 1
        mem['cursor'] = page
        if mem['pages_done'] >= mem['pages']:
            mem['last_full'] = time.time()              # every page read at least once: list complete
            mem['pages_done'] = 0
            break
    return read, added, start_page


def _has_curl_cffi():
    try:
        import curl_cffi  # noqa: F401
        return True
    except Exception:
        print('Coles website: curl_cffi not installed, using remembered items only')
        return False


def scrape_coles_web_half_price(time_budget=None, max_blocked=None):
    """Returns this week's in-store Half Price specials from coles.com.au (remembered across updates).

    Polite: one browser identity per update, ~6-9 seconds between pages. coles.com.au has bot
    protection that stops a visitor after a few pages; when that happens we STOP for this update
    (no new identity, no retry) and continue from the same page on the next scheduled update."""
    if _switching():
        print('Coles website: weekly switch-over in progress, website half-price list skipped this run')
        return []
    week = coles_week_start()
    mem = _load_memory(week)
    if mem['items'] and time.time() - float(mem.get('last_full') or 0) < REFRESH_HOURS * 3600:
        print(f"Coles website half price: whole list read {int((time.time() - mem['last_full']) / 60)} min ago - "
              f"using the saved list ({len(mem['items'])} specials)")
        return _with_aisle(mem['items'].values())
    if not _has_curl_cffi():
        return _with_aisle(mem['items'].values())
    read, added, start_page = _read_pages(mem, LIST_URL, product_to_item, 600 if time_budget is None else time_budget)
    _save_memory(mem)
    print(f"Coles website half price: read {read} pages this run from page {start_page} (+{added} new), "
          f"{len(mem['items'])} in-store half-price specials remembered for week of {week} "
          f"(website lists {mem['pages']} pages)")
    return _with_aisle(mem['items'].values())


def scrape_coles_web_more(time_budget=None):
    """This week's other in-store specials from coles.com.au: multi-buys, price cuts and "SPECIAL"s (remembered
    across updates, same memory file). Read after the Half Price list, in the same polite way, and
    never a product the Half Price list already has."""
    if _switching():
        print('Coles website: weekly switch-over in progress, website All specials list skipped this run')
        return []
    week = coles_week_start()
    mem = _load_memory(week)                            # re-read: the Half Price list has just saved it
    more = mem.setdefault('more', {'cursor': 1, 'pages': 0, 'items': {}})
    if more['items'] and time.time() - float(more.get('last_full') or 0) < MORE_REFRESH_HOURS * 3600:
        print(f"Coles website All specials: whole list read {int((time.time() - more['last_full']) / 60)} min ago - "
              f"using the saved list ({len(more['items'])} specials)")
    elif _has_curl_cffi():
        read, added, start_page = _read_pages(more, MORE_URL, special_to_item, 600 if time_budget is None else time_budget)
        _save_memory(mem)
        multi = sum(' for $' in it['discount_desc'] for it in more['items'].values())
        plain = sum(it['discount_desc'] == SPECIAL_DESC for it in more['items'].values())
        print(f"Coles website All specials: read {read} pages this run from page {start_page} (+{added} new), "
              f"{len(more['items'])} more in-store specials remembered ({multi} multi-buys, "
              f"{len(more['items']) - multi - plain} price cuts, {plain} with no saving shown; "
              f"website lists {more['pages']} pages)")
    return _with_aisle(it for pid, it in more['items'].items() if pid not in mem['items'])


if __name__ == '__main__':
    items = scrape_coles_web_half_price(time_budget=60)
    print(len(items), items[:2])
    more = scrape_coles_web_more(time_budget=60)
    print(len(more), more[:2])
