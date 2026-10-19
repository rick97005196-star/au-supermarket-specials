"""
Woolworths regular (not on special) prices for the price compare, read once a week.

This week's Coles / ALDI products that Woolworths very likely sells but has no special for are looked up
on woolworths.com.au, and the in-store price of the same product is kept (which one is "the same" is
decided by scripts/regular_match.cjs, with the website's own rules). Output: static/data/regular.json
    {"updated_at": "<Brisbane date>", "items": [...]}

    python scrapers/woolies_regular.py [--if-stale]

--if-stale: do nothing when the prices were already read since this week's Wednesday (specials change then).
When Woolworths stops answering, last week's file is kept untouched and the run fails (exit 1), so the
backup run tries again. Requests go through scrapers/polite.py: a few seconds apart, never around a refusal.
"""
import datetime
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scrapers.polite import request as polite, summary  # noqa: E402
from scrapers.regions import _brisbane_today  # noqa: E402

SPECIALS = os.path.join(ROOT, 'static', 'data', 'specials.json')
OUT = os.path.join(ROOT, 'static', 'data', 'regular.json')
MATCH = os.path.join(ROOT, 'scripts', 'regular_match.cjs')
SEARCH = 'https://www.woolworths.com.au/apis/ui/Search/products'


def is_fresh(updated_at, today):
    """True when the saved prices were read on or after this week's Wednesday."""
    try:
        return datetime.date.fromisoformat(updated_at) >= today - datetime.timedelta(days=(today.weekday() - 2) % 7)
    except (TypeError, ValueError):
        return False


def search_term(title):
    return ' '.join(re.sub(r"[^\w\s&'.-]+", ' ', title).split())


def to_item(pr):
    """One Woolworths search result as a website item, or None unless it is a plain in-store price."""
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
        'discount_desc': 'Regular Price',
        'image_url': pr.get('LargeImageFile') or pr.get('MediumImageFile') or '',
        'product_url': f"https://www.woolworths.com.au/shop/productdetails/{code}/{slug}",
    }


def match(mode, data=None):
    r = subprocess.run(['node', MATCH, mode, SPECIALS], input=json.dumps(data) if data is not None else '',
                       capture_output=True, text=True, encoding='utf-8', check=True)
    return json.loads(r.stdout)


def main():
    today = _brisbane_today()
    try:
        with open(OUT, encoding='utf-8') as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = {}
    if '--if-stale' in sys.argv and is_fresh(old.get('updated_at'), today):
        print(f"Regular prices already read this week ({old['updated_at']}) - nothing to do")
        return 0

    targets = match('targets')
    terms = list(dict.fromkeys(filter(None, (search_term(t['title']) for t in targets))))
    print(f"{len(targets)} Coles / ALDI products to look up at Woolworths, {len(terms)} searches")

    from curl_cffi import requests as cffi
    s = cffi.Session(impersonate='chrome')
    polite('woolworths', lambda: s.get('https://www.woolworths.com.au/', timeout=20))  # session cookies first
    cands = {}
    for i, term in enumerate(terms, 1):
        r = polite('woolworths', lambda: s.get(SEARCH, params={'SearchTerm': term, 'PageSize': 12, 'PageNumber': 1},
                                                timeout=20))
        bundles = None
        if r is not None and r.status_code == 200:
            try:
                bundles = r.json().get('Products') or []
            except (ValueError, AttributeError):          # not JSON, or not the usual answer
                pass
        if bundles is None:
            # shortcut: a run cut short saves nothing (last week's prices stay); save the part read if this happens often
            print(f"::error::Woolworths stopped answering at search {i}/{len(terms)} "
                  f"({'refused' if r is None else r.status_code}) - last week's regular prices are kept")
            return 1
        for b in bundles:
            for pr in b.get('Products') or []:
                it = to_item(pr)
                if it:
                    cands.setdefault(it['id'], it)
        if i % 100 == 0:
            print(f"  {i}/{len(terms)} searches, {len(cands)} regular prices seen", flush=True)

    kept = match('keep', list(cands.values()))
    if not kept:
        print(f"::error::No regular price matched any of the {len(targets)} products - last week's file is kept")
        return 1
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'updated_at': today.isoformat(), 'items': sorted(kept, key=lambda x: x['id'])},
                  f, ensure_ascii=False, separators=(',', ':'))
    print(f"Saved {len(kept)} Woolworths regular prices (from {len(cands)} seen) - requests {summary()}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
