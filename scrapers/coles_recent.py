"""
Coles recent regular prices (最近原價): the shelf price a Coles product had just before its latest special, for
products not on special this week.

The weekly Coles regular-price reader (scrapers/coles_regular.py) cannot finish a week on GitHub's servers: Coles shows
its bot check after 5 pages. But every Coles special read from the Coles website carries the price it was before
("was"), so each week's specials tell the shelf price of thousands of products. This keeps the latest one per product
and lists those not on special this week, so the website shows Coles regular prices without reading more Coles pages.
Checked against 100 shelf prices read by coles_regular.py: 91 the same, the rest 20c to $1 lower (prices rose since).
The website labels them 最近原價 with the week, and uses a real Coles regular list instead whenever one is fresh.

    data/coles_was_prices.json               {"updated_at", "items": {"<Coles id>": [title, price, unit price,
                                              image, link, category, week], ...}}  remembered for 16 weeks
    static/data/regular-coles-recent.json    {"updated_at", "store": "Coles", "kind": "recent",
                                              "items": [[id, title, price, price display, unit price, image, link,
                                              category, week], ...]}  products seen on special in the last 6 weeks,
                                              plus the shelf prices the weekly reader got this week (week = "shelf")

    python scrapers/coles_recent.py                    after each specials export (auto_update.yml)
    python scrapers/coles_recent.py --seed a.json ...  also learn from older specials.json copies, oldest first

"2 for $6" deals: Coles gives the price of the 2 as "was", so it is split per item; their unit price is already the
single item's. Other specials show the special's unit price, so it is scaled to the "was" price.
"""
import datetime
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import categories  # noqa: E402
SPECIALS = os.path.join(ROOT, 'static', 'data', 'specials.json')
MEMORY = os.path.join(ROOT, 'data', 'coles_was_prices.json')
LIST = os.path.join(ROOT, 'static', 'data', 'regular-coles-recent.json')
KEEP_DAYS = 16 * 7           # remembered this long after the product's last special
LIST_DAYS = 6 * 7            # listed this long (older shelf prices too often changed since: Nov 2026 check)
PROGRESS = os.path.join(ROOT, 'data', 'coles_regular_progress.json')
COLES_ID = re.compile(r'coles\.com\.au/product/[^?#]*-(\d+)(?:[?#]|$)', re.I)
MULTIBUY = re.compile(r'^\s*(\d+)\s*for\s*\$', re.I)
WEEK = re.compile(r'(\d{1,2})\s+([A-Za-z]{3})\w*\s+(\d{4})')
MONTHS = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}


def coles_id(it):
    m = COLES_ID.search(str(it.get('product_url') or ''))
    return m.group(1) if m else None


def week_of(it, today):
    """The first day of the special ("Wed 18 Nov 2026 - Tue 24 Nov 2026"), or today."""
    m = WEEK.search(str(it.get('date_range') or ''))
    try:
        return datetime.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))).isoformat()
    except (AttributeError, KeyError, ValueError):
        return today.isoformat()


def regular_of(it):
    """(shelf price, unit price) before this special, or None when the special does not tell it."""
    try:
        price, was = float(it.get('price') or 0), float(it.get('was_price') or 0)
    except (TypeError, ValueError):
        return None
    if it.get('store') != 'Coles' or price <= 0 or was <= 0 or not coles_id(it):
        return None
    m = MULTIBUY.match(str(it.get('discount_desc') or ''))
    n = int(m.group(1)) if m else 1
    n = n if 1 <= n <= 10 else 1
    regular, deal = round(was / n, 2), price / n
    if not deal + 0.004 < regular <= deal * 10:
        return None
    unit = str(it.get('unit_price') or '').strip()
    if n == 1 and unit:                    # the special's unit price: scaled to the shelf price
        unit = re.sub(r'\$(\d+(?:\.\d+)?)', lambda u: f'${float(u.group(1)) * was / price:.2f}', unit, count=1)
    return regular, unit


def remember(mem, items, today):
    """Learn the shelf price of every Coles special in `items`; a later special of a product replaces its earlier one."""
    learned = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        got = regular_of(it)
        if not got:
            continue
        week = week_of(it, today)
        key = coles_id(it)
        if key in mem and mem[key][6] > week:
            continue
        mem[key] = [str(it.get('title') or ''), got[0], got[1], str(it.get('image_url') or ''),
                    str(it.get('product_url') or ''), str(it.get('category') or ''), week]
        learned += 1
    for key in [k for k, v in mem.items() if v[6] < (today - datetime.timedelta(days=KEEP_DAYS)).isoformat()]:
        del mem[key]
    return learned


# our departments as supermarket aisle names, so the department a special was given (with its real aisle) can stand
# in for that aisle: today's rules still come first (they may have been fixed since), the saved department only
# where no rule knows the product - as a real aisle would. Not "pet": an old pet department may be a rule since fixed.
AS_AISLE = {'produce': 'Fruit & Veg', 'meat': 'Meat', 'seafood': 'Seafood', 'dairy_eggs': 'Dairy, Eggs & Fridge',
            'bakery': 'Bakery', 'frozen': 'Freezer', 'pantry': 'Pantry', 'snacks': 'Snacks & Confectionery',
            'drinks': 'Drinks', 'liquor': 'Beer, Wine & Spirits', 'health_vitamins': 'Health & Beauty',
            'household': 'Household'}


def department(title, link, saved):
    return categories.classify_product(title, AS_AISLE.get(saved, ''), link)


def shelf_rows(progress, today):
    """Real Coles shelf prices read this week by scrapers/coles_regular.py: Coles stops it after a few pages, so its
    list is never finished and written, but what it did read is today's price - better than one from a past special."""
    from scrapers.woolies_regular import is_fresh
    if not isinstance(progress, dict) or not is_fresh(progress.get('started'), today):
        return {}
    out = {}
    for row in progress.get('rows') or []:
        if isinstance(row, list) and len(row) >= 8 and row[0] and row[1]:
            try:
                if float(row[2]) > 0:
                    out[str(row[0])] = row[:8]
            except (TypeError, ValueError):
                pass
    return out


def recent_rows(mem, specials, today, shelf=None):
    """The remembered shelf prices of products not on special this week, seen on special in the last LIST_DAYS;
    a shelf price read this week (`shelf`, week "shelf") replaces the remembered one."""
    on_special = {coles_id(it) for it in specials if isinstance(it, dict) and it.get('store') == 'Coles'
                  and it.get('period', 'current') == 'current'} - {None}
    since = (today - datetime.timedelta(days=LIST_DAYS)).isoformat()
    shelf = shelf or {}
    rows = []
    for key, (title, price, unit, image, link, category, week) in sorted(mem.items()):
        if key in on_special or key in shelf or week < since or not title:
            continue
        rows.append([key, title, price, f'${price:.2f}', unit, image, link, department(title, link, category), week])
    for key, row in sorted(shelf.items()):
        if key not in on_special:
            rows.append(list(row) + ['shelf'])
    return rows


def load(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def items_of(data):
    return data if isinstance(data, list) else (data or {}).get('items') or []


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, path)


def main(argv, today=None):
    today = today or datetime.date.today()
    mem = (load(MEMORY) or {}).get('items') or {}
    if '--seed' in argv:
        for path in argv[argv.index('--seed') + 1:]:
            print(f'{path}: learned {remember(mem, items_of(load(path)), today)} shelf prices')
    specials = items_of(load(SPECIALS))
    if not specials:
        print('::warning::No specials.json to learn from - the saved Coles recent prices stay')
        return 0
    learned = remember(mem, specials, today)
    rows = recent_rows(mem, specials, today, shelf_rows(load(PROGRESS), today))
    save(MEMORY, {'updated_at': today.isoformat(), 'items': mem})
    save(LIST, {'updated_at': today.isoformat(), 'store': 'Coles', 'kind': 'recent', 'items': rows})
    print(f'Coles recent regular prices: {learned} learned this time, {len(mem)} remembered, '
          f'{len(rows)} listed (not on special this week)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
