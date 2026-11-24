"""
Chemist Warehouse (小黃屋): the printed catalogue (in store, about two weeks).

chemistwarehouse.com.au/catalogue shows its catalogue with the Red Pepper / Nexus viewer. The viewer reads
public JSON files; we read the same ones (2 requests per catalogue):
  1. node.nexuspublications.com.au/client/3476/catalogues/json   -> the catalogues on show, with start / finish
  2. node.nexuspublications.com.au/catalogue/<id>/page/1/regions/json -> every product on every page
     (name, catalogue price, "$X OFF RRP" / "$X OFF EDLP", picture, link to the product on chemistwarehouse.com.au)

Strict rules (in-store specials only, exact numbers only):
  * only products with a saving printed in the catalogue as an exact amount: "$X OFF RRP", "$X OFF EDLP"
    (Chemist Warehouse's own everyday low price) or "1/2 PRICE OFF RRP" (RRP = twice the price)
  * "UP TO ...", "N% OFF" without an amount, cashback and products with no printed saving are left out
    (no exact "was" price to show)
  * anything that says online only / web only is left out
  * a whole range at one price ("Assorted Range", "Selected ...") is left out; two named products at one
    printed price and saving ("A or B 100ml EDT") are kept
"""
import json
import os
import re
import sys
import datetime as _dt
from typing import Any, Dict, List, Optional, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

STORE = 'Chemist Warehouse'
CLIENT_ID = '3476'
API = 'https://node.nexuspublications.com.au'
CATALOGUE_PAGE = 'https://www.chemistwarehouse.com.au/catalogue'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://app.nexuspublications.com.au/',
    'Origin': 'https://app.nexuspublications.com.au',
}
MAX_PRICE = 1000.0

_ONLINE = re.compile(r'\bonline\b|\bweb\s*only\b|\bapp\s*only\b|\bapp\s*exclusive\b', re.I)
_MONEY = r'\$\s*(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)'


def _get_json(url):
    import requests
    from scrapers.polite import request
    r = request('chemistwarehouse', lambda: requests.get(url, headers=HEADERS, timeout=40))
    if r is None or r.status_code != 200:
        print(f" Chemist Warehouse: could not read {url} ({getattr(r, 'status_code', 'no answer')})")
        return None
    try:
        return r.json()
    except ValueError:
        print(f" Chemist Warehouse: not JSON from {url}")
        return None


def _today():
    try:
        from zoneinfo import ZoneInfo
        return _dt.datetime.now(ZoneInfo('Australia/Sydney')).date()
    except Exception:
        return (_dt.datetime.utcnow() + _dt.timedelta(hours=10)).date()


def _date(s) -> Optional[_dt.date]:
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s or '')
    if not m:
        return None
    try:
        return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def date_range_text(start: _dt.date, end: _dt.date) -> str:
    """'Thu 12 Nov 2026 - Wed 25 Nov 2026' (the same form as the Coles / Woolworths weeks)."""
    f = lambda d: f"{d.strftime('%a')} {d.day} {d.strftime('%b %Y')}"
    return f"{f(start)} - {f(end)}"


def pick_catalogues(catalogues, today=None) -> Tuple[Optional[dict], Optional[dict]]:
    """(the catalogue on now, the next one already published). By the catalogue's own dates."""
    today = today or _today()
    dated = []
    for c in catalogues or []:
        s, e = _date(c.get('start')), _date(c.get('finish'))
        if s and e and s <= e and c.get('nid_1'):
            dated.append((s, e, c))
    now = [x for x in dated if x[0] <= today <= x[1]]
    later = sorted([x for x in dated if x[0] > today], key=lambda x: x[0])
    cur = max(now, key=lambda x: x[0]) if now else None
    nxt = later[0] if later else None
    return cur, nxt


def _money(s) -> float:
    return float(s.replace(',', ''))


def saving_of(price: float, desc: str) -> Tuple[float, str]:
    """(saving, description) from the catalogue's saving text, or (0, '') when there is no exact saving.
    The description says what the saving is measured against (RRP or Chemist Warehouse's everyday price)."""
    text = ' '.join((desc or '').split())
    up = text.upper()
    if not text or 'CASHBACK' in up:
        return 0.0, ''
    m = re.search(_MONEY + r'\s*OFF\s*(RRP|EDLP|EVERYDAY\s+LOW\s+PRICE)', text, re.I)
    if m and not re.search(r'UP\s*TO\s*' + _MONEY + r'\s*OFF', text, re.I):
        save = round(_money(m.group(1)), 2)
        basis = 'RRP' if m.group(2).upper() == 'RRP' else 'EDLP'
    elif re.search(r'(?<!UP TO )(?<!BETTER THAN )\b1/2\s*PRICE\s*OFF\s*RRP', up) and 'UP TO' not in up:
        save, basis = round(price, 2), 'RRP'
    else:
        return 0.0, ''
    if save <= 0 or save > MAX_PRICE:
        return 0.0, ''
    label = f"Save ${save:.2f} off RRP" if basis == 'RRP' else f"Save ${save:.2f} off everyday price"
    if round(price + save, 2) > 0 and save / (price + save) >= 0.495:
        label += ' (1/2 price)'
    return save, label


def _first_uri(v) -> str:
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except ValueError:
            return ''
    if isinstance(v, list) and v and isinstance(v[0], dict):
        return v[0].get('uri') or ''
    return ''


def items_from_regions(regions) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Catalogue products -> site items. Also returns how many were left out and why."""
    out, skipped, seen = [], {}, set()
    skip = lambda why: skipped.__setitem__(why, skipped.get(why, 0) + 1)
    for r in regions or []:
        if not isinstance(r, dict) or r.get('field_region_type') != 'product':
            continue
        title = ' '.join((r.get('field_product_title') or '').split())
        desc = r.get('field_product_description') or ''
        try:
            price = round(float(str(r.get('field_product_price') or '').replace(',', '').replace('$', '')), 2)
        except ValueError:
            price = 0.0
        if not title or not (0 < price <= MAX_PRICE):
            skip('no name or price'); continue
        if _ONLINE.search(title) or _ONLINE.search(desc):
            skip('online only'); continue
        save, label = saving_of(price, desc)
        if save <= 0:
            skip('no exact saving printed'); continue
        url = _first_uri(r.get('field_product_buynow'))
        if re.search(r'\b(?:assorted|selected|range)\b', title, re.I):
            skip('a whole range, not one product'); continue    # one price for many products: not exact
        # "A or B" (e.g. "Calvin Klein Eternity or Obsession 100ml EDP"): two named products, the same printed
        # price and the same printed saving -> exact. The catalogue links these to a search, not one product page.
        if not re.match(r'^https://(?:www\.)?chemistwarehouse\.com\.au/(?:buy/\d+/|search\?|shop-online/)', url):
            skip('no link to Chemist Warehouse'); continue
        img = _first_uri(r.get('field_product_image')) or _first_uri(r.get('field_product_image_url'))
        if not img.startswith('https://'):
            img = ''
        key = title.lower()
        if key in seen:
            skip('same product twice'); continue
        seen.add(key)
        out.append({
            'title': title,
            'price': price,
            'price_display': f"${price:.2f}",
            'was_price': round(price + save, 2),
            'save_amount': save,
            'discount_desc': label,
            'unit_price': '',
            'image_url': img,
            'category': '',
            'product_url': url,
            'store_category': '',
        })
    return out, skipped


def read_catalogue(cat: dict) -> Tuple[List[Dict[str, Any]], str]:
    s, e = _date(cat.get('start')), _date(cat.get('finish'))
    regions = _get_json(f"{API}/catalogue/{cat['nid_1']}/page/1/regions/json?_format=json")
    if regions is None:
        return [], ''
    items, skipped = items_from_regions(regions)
    rng = date_range_text(s, e)
    why = '、'.join(f"{k} {v}" for k, v in skipped.items()) or 'none'
    print(f" Chemist Warehouse '{cat.get('title')}' ({rng}): {len(items)} specials kept; left out: {why}")
    return items, rng


def scrape_chemist_warehouse() -> Dict[str, Dict[str, Any]]:
    """{'listed': the official catalogue list was read, 'current' / 'next': {'items', 'date_range', 'read_failed'}}"""
    out = {'listed': False, 'current': {'items': [], 'date_range': ''}, 'next': {'items': [], 'date_range': ''}}
    cats = _get_json(f"{API}/client/{CLIENT_ID}/catalogues/json?_format=json")
    if not isinstance(cats, list):
        return out
    out['listed'] = True
    cur, nxt = pick_catalogues(cats)
    for period, picked in (('current', cur), ('next', nxt)):
        if not picked:
            print(f" Chemist Warehouse: no {period} catalogue listed")
            continue
        items, rng = read_catalogue(picked[2])
        out[period] = {'items': items, 'date_range': rng, 'read_failed': not items}
    return out


if __name__ == '__main__':
    r = scrape_chemist_warehouse()
    for k, v in r.items():
        print(k, v['date_range'], len(v['items']))
        for it in v['items'][:10]:
            print('  ', it['price'], it['was_price'], it['discount_desc'], '|', it['title'])
