"""
Chemist Warehouse (小黃屋): the list of every product the shop sells, for the stand-alone 小黃屋 site.

Source: the shop's public product sitemap, the list it publishes for outside readers
(robots.txt -> Sitemap: https://static.chemistwarehouse.com.au/AMS/sitemap/cwh_sitemap.xml).
One small download a week; nothing else on chemistwarehouse.com.au is read.

The sitemap only has each product's link (/buy/<id>/<name-in-the-link>), so only the name and the link are kept.
No price is taken from here: prices come only from the printed in-store catalogue (chemist_scraper.py);
the site sends visitors to the shop's own page for every other price.

    python scrapers/chemist_all.py          # reads the list if the saved one is older than 6 days
    python scrapers/chemist_all.py --force
"""
import datetime as _dt
import json
import os
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVED = os.path.join(ROOT, 'data', 'chemist_all.json')
INDEX = 'https://static.chemistwarehouse.com.au/AMS/sitemap/cwh_sitemap.xml'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Accept': 'application/xml,text/xml,*/*',
}
EVERY_DAYS = 6
MIN_PRODUCTS = 500          # a much shorter list means something went wrong: keep the saved one
MAX_DROP = 0.5              # never accept a list less than half the size of the saved one

_LOC = re.compile(r'<loc>\s*([^<\s]+)\s*</loc>', re.I)
_BUY = re.compile(r'^https://www\.chemistwarehouse\.com\.au/buy/(\d+)/([a-z0-9][a-z0-9\-]*)/?$', re.I)
_UNIT = re.compile(r'^\d')


def name_from_slug(slug):
    """'cerave-moisturising-cream-454g' -> 'Cerave Moisturising Cream 454g'"""
    words = [w for w in slug.split('-') if w]
    return ' '.join(w if _UNIT.match(w) else w[:1].upper() + w[1:] for w in words)


def _get(url):
    import requests
    from scrapers.polite import request
    r = request('chemistwarehouse', lambda: requests.get(url, headers=HEADERS, timeout=60))
    if r is None or r.status_code != 200:
        print(f' Chemist Warehouse list: could not read {url} ({getattr(r, "status_code", "no answer")})')
        return None
    return r.text


def parse_products(xml):
    out = {}
    for loc in _LOC.findall(xml or ''):
        m = _BUY.match(loc.strip())
        if m and m.group(1) not in out:
            out[m.group(1)] = {'pid': m.group(1), 'title': name_from_slug(m.group(2).lower()), 'url': m.group(0)}
    return list(out.values())


def load_saved():
    try:
        with open(SAVED, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def update(force=False):
    saved = load_saved()
    now = _dt.datetime.now(_dt.timezone.utc)
    if saved and not force:
        try:
            age = now - _dt.datetime.strptime(saved['read'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=_dt.timezone.utc)
            if age < _dt.timedelta(days=EVERY_DAYS):
                print(f" Chemist Warehouse list read {age.days} days ago - keeping the saved list ({len(saved['products'])})")
                return 0
        except (KeyError, ValueError):
            pass
    index = _get(INDEX)
    if not index:
        return 0                       # keep the saved list; the next run tries again
    files = [u for u in _LOC.findall(index) if 'product' in u.lower()]
    if not files:
        print(' Chemist Warehouse list: no product sitemap in the index - keeping the saved list')
        return 0
    products = {}
    for u in files:
        xml = _get(u)
        if xml is None:
            print(' Chemist Warehouse list: a part could not be read - keeping the saved list')
            return 0
        for p in parse_products(xml):
            products.setdefault(p['pid'], p)
    items = sorted(products.values(), key=lambda p: p['title'].lower())
    old = len(saved['products']) if saved else 0
    if len(items) < MIN_PRODUCTS or (old and len(items) < old * MAX_DROP):
        print(f' Chemist Warehouse list: only {len(items)} products (saved {old}) - keeping the saved list')
        return 0
    with open(SAVED, 'w', encoding='utf-8') as f:
        json.dump({'read': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'source': INDEX, 'products': items},
                  f, ensure_ascii=False, separators=(',', ':'))
    print(f' Chemist Warehouse list: {len(items)} products saved (was {old})')
    return 0


if __name__ == '__main__':
    sys.exit(update(force='--force' in sys.argv))
