import sqlite3
import datetime
import json
import os

from scrapers.regions import EVERYDAY_DESC, SPECIAL_DESC, REGULAR_DESC, is_everyday, is_regular

os.makedirs('static/data', exist_ok=True)

conn = sqlite3.connect('data/specials.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# the supermarket's own aisle (older databases do not have it yet)
_cols = {r[1] for r in c.execute("PRAGMA table_info(specials)").fetchall()}
_aisle_col = "store_category" if 'store_category' in _cols else "'' AS store_category"
c.execute(f"""
    SELECT id, store, period, date_range, category, title, price, price_display,
           unit_price, was_price, save_amount, discount_desc, image_url, product_url,
           regions, region_prices, sale_from, {_aisle_col}
    FROM specials
    WHERE price > 0 AND ((save_amount > 0 OR was_price > price) OR store = 'ALDI' OR discount_desc LIKE ? OR discount_desc IN (?, ?))
    ORDER BY id ASC
""", (EVERYDAY_DESC + '%', SPECIAL_DESC, REGULAR_DESC))
rows = c.fetchall()
items = [dict(r) for r in rows]

# State availability (compact keys, only when needed): rg = states where it is on special,
# rp = {state: prices} where that state's price differs. No rg = every state.
for it in items:
    sf = it.pop('sale_from', '') or ''
    if sf:
        it['sf'] = sf          # ALDI: on sale from this date (YYYY-MM-DD)
    rg = it.pop('regions', '') or ''
    rp = it.pop('region_prices', '') or ''
    if rg:
        it['rg'] = rg.split(',')
    if rp:
        try:
            it['rp'] = json.loads(rp)
        except Exception:
            pass

# ---- One offer = one card ----
# 1) the same product written slightly differently (footnote marks, Nando's / Nando’s)
from scrapers.regions import clean_title
import re as _re2
_seen = {}
_dedup = []
for it in items:
    it['title'] = clean_title(it['title'])
    k = (it['store'], it['period'], it['title'].lower(), round(it['price'] or 0, 2))
    if k in _seen:
        if it.get('store_category') and not _seen[k].get('store_category'):
            _seen[k]['store_category'] = it['store_category']     # keep the aisle from either copy
        continue
    _seen[k] = it
    _dedup.append(it)
# 2) Woolworths / Coles: the catalogue lists a whole range ("Pringles Potato Chips 134g") while the website
#    lists each flavour at the same price -> keep the website's individual products, drop the range line
_STOP = {'from', 'the', 'dept', 'deli', 'fridge', 'freezer', 'bakery', 'aisle', 'health', 'food', 'varieties',
         'variety', 'range', 'or', 'and', 'pk', 'pack', 'each', 'selected', 'bottle', 'bottles', 'cans', 'can', 'x',
         'litre', 'litres', 'l', 'ml', 'g', 'kg', 'with'}
def _toks(t):
    t = _re2.sub(r'\s[–-]\s*from the .*$', '', t.lower())
    words = _re2.findall(r"[a-z0-9']+", t)
    return {w for w in words if w not in _STOP and not _re2.fullmatch(r'\d+(?:\.\d+)?(?:g|kg|ml|l|litre|pk)?', w)}
def _nums(t):
    return set(_re2.findall(r'\d+(?:\.\d+)?', t.lower()))
_WEB = {'Woolworths': 'woolworths.com.au', 'Coles': 'coles.com.au'}
_web = {}
for it in _dedup:
    if it['store'] in _WEB and _WEB[it['store']] in (it.get('product_url') or ''):
        _web.setdefault((it['store'], it['period'], round(it['price'] or 0, 2)), []).append(it)
items = []
_dropped = 0
for it in _dedup:
    if it['store'] in _WEB and 'salefinder' in (it.get('product_url') or '') and 'rg' not in it:
        ta, na = _toks(it['title']), _nums(it['title'])
        dup = False
        for w in _web.get((it['store'], it['period'], round(it['price'] or 0, 2)), []):
            tb, nb = _toks(w['title']), _nums(w['title'])
            if not ta or not tb:
                continue
            first_a = it['title'].lower().split()[0]
            first_b = w['title'].lower().split()[0]
            if first_a.rstrip("'s") != first_b.rstrip("'s"):
                continue                      # different brand
            if na and nb and not (na & nb):
                continue                      # different size / pack
            if len(ta & tb) / len(ta | tb) >= 0.6 or ta <= tb:
                dup = True
                if w.get('discount_desc') == SPECIAL_DESC and (it.get('was_price') or 0) > (it['price'] or 0):
                    # the website's "SPECIAL" shows no saving; the catalogue line for the same deal does
                    w.update(was_price=it['was_price'], discount_desc=it['discount_desc'],
                             save_amount=it.get('save_amount') or round(it['was_price'] - it['price'], 2))
        if dup:
            _dropped += 1
            continue
    items.append(it)
print(f"Duplicates removed: {len(_seen) and (len(rows) - len(_dedup))} same-name, {_dropped} catalogue ranges already listed by flavour")

# Load translations if available
trans_path = 'static/data/translations.json'
translations = {}
if os.path.exists(trans_path):
    with open(trans_path, 'r', encoding='utf-8') as f:
        try:
            translations = json.load(f)
        except Exception:
            translations = {}

import categories
from categories import classify_product, is_popular_product, calculate_popularity_score
categories.HINTED.clear()
categories.GUESSED.clear()

# translations are also found for slightly renamed products (footnote marks, quote style, spaces)
_tr_norm = {}
for _k, _v in translations.items():
    _tr_norm.setdefault(_re2.sub(r'\s+', ' ', clean_title(_k)).strip().lower(), _v)

for it in items:
    t = it.get('title', '')
    # rules first; products no rule knows: the AI's answer, then the supermarket's own aisle
    it['category'] = classify_product(t, it.pop('store_category', '') or '', it.get('product_url') or '')
    it['is_popular'] = is_popular_product(t)
    it['popularity_score'] = calculate_popularity_score(it)
    tr = translations.get(t) or _tr_norm.get(_re2.sub(r'\s+', ' ', t).strip().lower())
    if tr:
        it['translations'] = {k: tr[k] for k in ('zh', 'ja', 'ko') if tr.get(k)}

# ---- What visitors really look at moves products up (anonymous counts, see interest.py) ----
from interest import apply_interest, load_interest
_interest, _interest_total = load_interest()
_moved = apply_interest(items, _interest, _interest_total)
print(f"Visitor interest: {len(_interest)} products counted (weighted total {_interest_total:.0f}), {_moved} specials moved up")

# Everyday low prices and regular prices are not specials: never "熱門暢銷", never in the best-sellers at the top
# (-1, not 0: the website recomputes a score of 0 itself)
_everyday = _regular = 0
for it in items:
    if is_everyday(it) or is_regular(it):
        it['popularity_score'] = -1
        _everyday += is_everyday(it)
        _regular += is_regular(it)
print(f"Everyday low prices: {_everyday} items, regular prices: {_regular} items")

# ---- "熱門暢銷" badge: only the top ~10% per category, max 2 per brand, so the badge stays meaningful ----
import math, re as _re
HOUSE_BRANDS = {'coles', 'woolworths', 'macro', 'essentials'}
def _brand(title):
    words = _re.sub(r"[^a-z0-9&' ]", ' ', (title or '').lower()).split()
    if not words:
        return ''
    # two-word brands like "red rock", "tip top", "dairy farmers", "tim tam"
    return ' '.join(words[:2]) if words[0] in HOUSE_BRANDS or len(words[0]) <= 3 else words[0]

groups = {}
for it in items:
    it['is_popular'] = False
    if (it.get('popularity_score') or 0) > 0:
        groups.setdefault((it.get('period'), it.get('category')), []).append(it)
for (period, cat), members in groups.items():
    size = sum(1 for x in items if x.get('period') == period and x.get('category') == cat)
    quota = max(1, min(20, math.ceil(size * 0.10)))
    per_brand = {}
    picked = 0
    for it in sorted(members, key=lambda x: -(x.get('popularity_score') or 0)):
        b = _brand(it.get('title'))
        if per_brand.get(b, 0) >= 2:
            continue
        per_brand[b] = per_brand.get(b, 0) + 1
        it['is_popular'] = True
        picked += 1
        if picked >= quota:
            break
print(f"Popular badge: {sum(1 for x in items if x['is_popular'])} of {len(items)} items")

# Two files: every visitor downloads this week's (mostly on mobile data); next week's only when it is
# looked at or starts. Compact JSON. specials-next.json is always written, also empty, so an old one never stays.
_next = [it for it in items if it.get('period') == 'next']
for _name, _part in (('specials.json', [it for it in items if it.get('period') != 'next']), ('specials-next.json', _next)):
    with open('static/data/' + _name, 'w', encoding='utf-8') as f:
        json.dump(_part, f, ensure_ascii=False, separators=(',', ':'))
    print(f"Exported {len(_part)} specials to static/data/{_name} (with translations)")

# How the products no rule recognised were placed (read by scripts/check_data.py; not published)
_report = {'ai': [], 'aisle': [], 'guessed': []}
for it in items:
    t = it.get('title', '')
    how = categories.HINTED.get(t) or ('guessed' if t in categories.GUESSED else '')
    if how:
        _report[how].append({'title': t, 'store': it.get('store'), 'period': it.get('period'), 'category': it.get('category')})
with open('data/category_report.json', 'w', encoding='utf-8') as f:
    json.dump(_report, f, ensure_ascii=False, indent=1)
print(f"Products no rule recognised: {len(_report['ai'])} placed by the AI, {len(_report['aisle'])} by the "
      f"supermarket's aisle, {len(_report['guessed'])} guessed")

# Also generate stats.json
import database
stats = database.get_stats()
# Numbers for every state (the website shows the visitor's own state)
from scrapers.regions import ALL_REGIONS, BASE_REGION
def _region_stats(region):
    out = {}
    for period in ('current', 'next'):
        total, by_store, half, everyday, everyday_by_store, regular, regular_by_store = 0, {}, 0, 0, {}, 0, {}
        for it in items:
            if it.get('period') != period or ('rg' in it and region not in it['rg']):
                continue
            p = dict(it, **(it.get('rp', {}).get(region) or {}))
            if is_everyday(p):
                everyday += 1          # listed on the site, but not a special: not in the specials numbers
                everyday_by_store[p['store']] = everyday_by_store.get(p['store'], 0) + 1
                continue
            if is_regular(p):
                regular += 1           # listed on the site, but not a special
                regular_by_store[p['store']] = regular_by_store.get(p['store'], 0) + 1
                continue
            total += 1
            by_store[p['store']] = by_store.get(p['store'], 0) + 1
            if (p['store'] == 'ALDI' or (p.get('save_amount') or 0) > 0) and database.is_half_price(
                    p.get('price'), p.get('was_price'), p.get('save_amount'), p.get('discount_desc')):
                half += 1
        out[period] = {'total': total, 'by_store': by_store, 'half_price_count': half, 'everyday_count': everyday,
                       'everyday_by_store': everyday_by_store, 'regular_count': regular, 'regular_by_store': regular_by_store}
    return out
# "Next week" must never show this week's dates (happens when only ALDI has published next week)
def _shift_week(rng, days=7):
    import re as _r
    m = _r.findall(r'(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s*(\d{4})?', rng or '')
    if len(m) < 2:
        return ''
    try:
        y = m[1][2] or str(datetime.date.today().year)
        s0 = datetime.datetime.strptime(f"{m[0][0]} {m[0][1]} {m[0][2] or y}", "%d %b %Y").date() + datetime.timedelta(days=days)
        e0 = datetime.datetime.strptime(f"{m[1][0]} {m[1][1]} {y}", "%d %b %Y").date() + datetime.timedelta(days=days)
    except ValueError:
        return ''
    f = lambda d: f"{d.strftime('%a')} {d.day} {d.strftime('%b %Y')}"
    return f"{f(s0)} - {f(e0)}"
if stats['next'].get('total') and stats['next'].get('date_range') == stats['current'].get('date_range'):
    stats['next']['date_range'] = _shift_week(stats['current']['date_range']) or stats['next']['date_range']
stats['base_region'] = BASE_REGION
stats['regions'] = {r: _region_stats(r) for r in ALL_REGIONS}
for period in ('current', 'next'):   # the default numbers are Queensland's
    stats[period].update(stats['regions'][BASE_REGION][period])
# The weeks in specials-next.json: the site knows when next week starts without downloading it
stats['next_ranges'] = sorted({it['date_range'] for it in _next if it.get('date_range')})
# When the specials were last refreshed (UTC, ISO format) - shown on the site as "updated x hours ago"
stats['data_updated_at'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
with open('static/data/stats.json', 'w', encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print("Exported stats to static/data/stats.json")
conn.close()
