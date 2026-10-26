"""
Woolworths regular (not on special) prices, read once a week in parts.

Every week the food departments of woolworths.com.au are read page by page (36 products a page, the same
category browse the website itself uses), and every product sold in the reference store at its plain in-store
price is kept. Output:
    static/data/regular-woolworths.json   {"updated_at", "store": "Woolworths", "items": [[<ROW fields>], ...]}
        every regular price; the website loads it only when someone asks for regular prices or searches
    static/data/regular.json              {"updated_at", "items": [...]}
        the few the price compare needs (which ones: scripts/regular_match.cjs, with the website's own rules)

    python scrapers/woolies_regular.py

One run reads for at most TIME_BUDGET and keeps its place in data/regular_progress.json, so the next run goes on
where it stopped. The files above are written only when every department is read; until then last week's stay
(the website drops lists older than 15 days). The read starts over each Wednesday (specials change then). When
Woolworths stops answering, what was read is kept and the run fails (exit 1). Delete the progress file to read
the whole week again. Requests go through scrapers/polite.py: a few seconds apart, never around a refusal.
"""
import datetime
import json
import math
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from categories import classify_product  # noqa: E402
from scrapers.polite import request as polite, summary  # noqa: E402
from scrapers.regions import _brisbane_today, REGULAR_DESC  # noqa: E402

SPECIALS = os.path.join(ROOT, 'static', 'data', 'specials.json')
OUT = os.path.join(ROOT, 'static', 'data', 'regular.json')
LIST = os.path.join(ROOT, 'static', 'data', 'regular-woolworths.json')
MATCH = os.path.join(ROOT, 'scripts', 'regular_match.cjs')
PROGRESS = os.path.join(ROOT, 'data', 'regular_progress.json')
HOME = 'https://www.woolworths.com.au/'
CATS = 'https://www.woolworths.com.au/apis/ui/PiesCategoriesWithSpecials'
BROWSE = 'https://www.woolworths.com.au/apis/ui/browse/category'
FOOD = ['Fruit & Veg', 'Poultry, Meat & Seafood', 'Deli', 'Dairy, Eggs & Fridge', 'Bakery', 'Freezer',
        'Snacks & Confectionery', 'Pantry', 'International Foods', 'Drinks', 'Beer, Wine & Spirits']
PAGE_SIZE = 36
TIME_BUDGET = 55 * 60        # seconds a run reads; the whole week is about 630 pages, 40 minutes
# one regular price in the list file (a list, not a dict: the file stays about half the size)
ROW = ('id', 'title', 'price', 'price_display', 'unit_price', 'image_url', 'product_url', 'category')
MIN_ROWS = 5000              # a full week has about 15,000; fewer means the pages changed - keep last week's


def is_fresh(updated_at, today):
    """True when the saved prices were read on or after this week's Wednesday."""
    try:
        return datetime.date.fromisoformat(updated_at) >= today - datetime.timedelta(days=(today.weekday() - 2) % 7)
    except (TypeError, ValueError):
        return False


def to_item(pr):
    """One Woolworths product as a website item, or None unless it is a plain in-store price."""
    if pr.get('IsOnlineOnly') or pr.get('IsMarketProduct') or pr.get('ThirdPartyProductInfo'):
        return None
    code, name = str(pr.get('Stockcode') or ''), (pr.get('Name') or '').strip()
    if not code or not name or 'online only' in name.lower() or 'everyday market' in name.lower():
        return None
    if pr.get('InstorePrice') is None:                    # not sold in the reference store
        return None
    price, was = float(pr['InstorePrice'] or 0), float(pr.get('InstoreWasPrice') or 0)
    if price <= 0 or pr.get('InstoreIsOnSpecial') or was > price + 0.004:
        return None                                       # on special: the specials lists carry it, with its saving
    pkg = (pr.get('PackageSize') or '').strip()
    unit_p, unit_m = pr.get('CupPrice'), pr.get('CupMeasure')
    per_kg = str(unit_m or '').upper() == '1KG' and unit_p and abs(float(unit_p) - price) < 0.01
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', name).strip('-').lower()
    return {
        'id': 'w' + code,
        'store': 'Woolworths',
        'title': f"{name} {pkg}".strip() if pkg and pkg not in name else name,
        'price': price,
        'price_display': f"${price:.2f} kg" if per_kg else f"${price:.2f} ea",
        'unit_price': f"${unit_p} / {unit_m}" if unit_p and unit_m else '',
        'was_price': 0.0,
        'save_amount': 0.0,
        'discount_desc': REGULAR_DESC,
        'image_url': pr.get('LargeImageFile') or pr.get('MediumImageFile') or '',
        'product_url': f"https://www.woolworths.com.au/shop/productdetails/{code}/{slug}",
    }


def to_row(it, aisle):
    it['category'] = classify_product(it['title'], aisle, it['product_url'])
    return [it[k] for k in ROW]


def browse(s, dep, n):
    """Page n of one department as (rows, more pages?), or None when Woolworths stops answering."""
    slug, name = dep['UrlFriendlyName'], dep['Description']
    body = {
        'categoryId': dep['NodeId'], 'pageNumber': n, 'pageSize': PAGE_SIZE, 'sortType': 'TraderRelevance',
        'url': f'/shop/browse/{slug}', 'location': f'/shop/browse/{slug}', 'formatObject': '{"name":"%s"}' % name,
        'isSpecial': False, 'isBundle': False, 'isMobile': False, 'filters': [], 'token': '', 'gpBoost': 0,
        'isHideUnavailableProducts': False, 'isRegisteredRewardCardPromotion': False, 'enableAdReRanking': False,
        'groupEdmVariants': False, 'categoryVersion': 'v2', 'flags': {'EnableProductBoostExperiment': False},
    }
    r = polite('woolworths', lambda: s.post(BROWSE, json=body, timeout=20))
    try:
        data = r.json() if r is not None and r.status_code == 200 else None
    except ValueError:                                    # not JSON: a block page
        data = None
    if not isinstance(data, dict):
        print(f"::error::Woolworths stopped answering ({'refused' if r is None else r.status_code}) at {name} page {n}")
        return None
    prods = [pr for b in data.get('Bundles') or [] for pr in b.get('Products') or []]
    rows = [to_row(it, name) for it in map(to_item, prods) if it]
    return rows, bool(prods) and n < math.ceil(int(data.get('TotalRecordCount') or 0) / PAGE_SIZE)


def read_pages(prog, names, read_page, budget):
    """Reads the departments in `names` page by page from where `prog` stopped, for at most `budget` seconds.
    read_page(name, n) gives (rows, more pages?), or None when the shop stops answering.
    Updates prog (dep, page, rows, done); returns (pages read, refused?)."""
    rows = {r[0]: r for r in prog.get('rows') or []}
    i, n = (names.index(prog['dep']), prog.get('page') or 1) if prog.get('dep') in names else (0, 1)
    start, pages, refused = time.monotonic(), 0, False
    while i < len(names):
        if time.monotonic() - start > budget:
            print(f"Time is up after {pages} pages - the rest waits for the next run")
            break
        got = read_page(names[i], n)
        if got is None:
            refused = True
            break
        page_rows, more = got
        for r in page_rows:
            rows.setdefault(r[0], r)
        pages += 1
        if pages % 50 == 0:
            print(f"  {pages} pages, {len(rows)} regular prices so far ({names[i]} page {n})", flush=True)
        i, n = (i, n + 1) if more else (i + 1, 1)
    prog.update(dep=names[i] if i < len(names) else None, page=n, rows=list(rows.values()), done=i >= len(names))
    return pages, refused


def match(mode, data=None):
    r = subprocess.run(['node', MATCH, mode, SPECIALS], input=json.dumps(data) if data is not None else '',
                       capture_output=True, text=True, encoding='utf-8', check=True)
    return json.loads(r.stdout)


def load_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))


def main():
    today = _brisbane_today()
    prog = load_json(PROGRESS)
    if not is_fresh(prog.get('started'), today):        # a new week (specials change on Wednesday): start over
        prog = {'started': today.isoformat()}
    if prog.get('done'):
        print("This week's Woolworths regular prices are already read - nothing to do")
        return 0

    from curl_cffi import requests as cffi
    s = cffi.Session(impersonate='chrome')
    polite('woolworths', lambda: s.get(HOME, timeout=20))     # session cookies first
    r = polite('woolworths', lambda: s.get(CATS, timeout=20))
    try:
        cats = r.json().get('Categories') if r is not None and r.status_code == 200 else None
    except (ValueError, AttributeError):
        cats = None
    if not cats:
        print(f"::error::No department list from Woolworths ({'refused' if r is None else r.status_code})"
              " - nothing changed")
        return 1
    deps = {c.get('Description'): c for c in cats if c.get('NodeId') and c.get('UrlFriendlyName')}
    for name in FOOD:
        if name not in deps:
            print(f"::warning::Woolworths has no department called {name!r} any more - it is skipped")
    names = [name for name in FOOD if name in deps]

    pages, refused = read_pages(prog, names, lambda name, n: browse(s, deps[name], n), TIME_BUDGET)
    if not pages:
        print("::error::Woolworths answered no page - nothing changed")
        return 1
    if not prog['done']:
        save_json(PROGRESS, prog)
        print(f"Read {pages} pages, {len(prog['rows'])} regular prices so far; next run starts at "
              f"{prog['dep']} page {prog['page']} - requests {summary()}")
        return 1 if refused else 0

    rows = sorted(prog['rows'], key=lambda row: row[0])
    if len(rows) < MIN_ROWS:
        print(f"::error::Only {len(rows)} regular prices in the whole week (a full week has about 15,000) -"
              " Woolworths may have changed its pages; last week's lists are kept")
        return 1
    items = [dict(zip(ROW, row), store='Woolworths', was_price=0.0, save_amount=0.0, discount_desc=REGULAR_DESC)
             for row in rows]
    kept = sorted(match('keep', items), key=lambda x: x['id'])
    updated = today.isoformat()
    save_json(LIST, {'updated_at': updated, 'store': 'Woolworths', 'items': rows})
    if kept:
        save_json(OUT, {'updated_at': updated, 'items': kept})
    save_json(PROGRESS, {'started': prog['started'], 'done': True})
    if not kept:
        print(f"::error::None of the {len(rows)} regular prices matched a Coles / ALDI special"
              " - the price compare keeps last week's")
        return 1
    print(f"Saved {len(rows)} Woolworths regular prices, {len(kept)} of them for the price compare"
          f" - requests {summary()}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
