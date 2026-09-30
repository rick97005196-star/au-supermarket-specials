import sqlite3
import datetime
import json
import os

os.makedirs('static/data', exist_ok=True)

conn = sqlite3.connect('data/specials.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("""
    SELECT id, store, period, date_range, category, title, price, price_display,
           unit_price, was_price, save_amount, discount_desc, image_url, product_url,
           regions, region_prices
    FROM specials
    WHERE price > 0 AND ((save_amount > 0 OR was_price > price) OR store = 'ALDI')
    ORDER BY id ASC
""")
rows = c.fetchall()
items = [dict(r) for r in rows]

# State availability (compact keys, only when needed): rg = states where it is on special,
# rp = {state: prices} where that state's price differs. No rg = every state.
for it in items:
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
        continue
    _seen[k] = it
    _dedup.append(it)
# 2) Woolworths: the catalogue lists a whole range ("Pringles Potato Chips 134g") while the website
#    lists each flavour at the same price -> keep the website's individual products, drop the range line
_STOP = {'from', 'the', 'dept', 'deli', 'fridge', 'freezer', 'bakery', 'aisle', 'health', 'food', 'varieties',
         'variety', 'range', 'or', 'and', 'pk', 'pack', 'each', 'selected', 'bottle', 'bottles', 'cans', 'can', 'x'}
def _toks(t):
    t = _re2.sub(r'\s[–-]\s*from the .*$', '', t.lower())
    words = _re2.findall(r"[a-z0-9']+", t)
    return {w for w in words if w not in _STOP and not _re2.fullmatch(r'\d+(?:\.\d+)?(?:g|kg|ml|l|litre|pk)?', w)}
def _nums(t):
    return set(_re2.findall(r'\d+(?:\.\d+)?', t.lower()))
_web = {}
for it in _dedup:
    if it['store'] == 'Woolworths' and 'woolworths.com.au' in (it.get('product_url') or ''):
        _web.setdefault((it['period'], round(it['price'] or 0, 2)), []).append(it)
items = []
_dropped = 0
for it in _dedup:
    if it['store'] == 'Woolworths' and 'salefinder' in (it.get('product_url') or '') and 'rg' not in it:
        ta, na = _toks(it['title']), _nums(it['title'])
        dup = False
        for w in _web.get((it['period'], round(it['price'] or 0, 2)), []):
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
                break
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

from categories import classify_product, is_popular_product, calculate_popularity_score

for it in items:
    t = it.get('title', '')
    it['category'] = classify_product(t, it.get('category') or '')
    it['is_popular'] = is_popular_product(t)
    it['popularity_score'] = calculate_popularity_score(it)
    if t in translations:
        tr = translations[t]
        it['translations'] = {k: tr[k] for k in ('zh', 'ja', 'ko') if tr.get(k)}

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

with open('static/data/specials.json', 'w', encoding='utf-8') as f:
    # compact JSON: this file is downloaded by every visitor (mostly on mobile data)
    json.dump(items, f, ensure_ascii=False, separators=(',', ':'))

print(f"Exported {len(items)} specials to static/data/specials.json (with translations)")

# Also generate stats.json
import database
stats = database.get_stats()
# Numbers for every state (the website shows the visitor's own state)
from scrapers.regions import ALL_REGIONS, BASE_REGION
def _region_stats(region):
    out = {}
    for period in ('current', 'next'):
        total, by_store, half = 0, {}, 0
        for it in items:
            if it.get('period') != period or ('rg' in it and region not in it['rg']):
                continue
            p = dict(it, **(it.get('rp', {}).get(region) or {}))
            total += 1
            by_store[p['store']] = by_store.get(p['store'], 0) + 1
            if (p['store'] == 'ALDI' or (p.get('save_amount') or 0) > 0) and database.is_half_price(
                    p.get('price'), p.get('was_price'), p.get('save_amount'), p.get('discount_desc')):
                half += 1
        out[period] = {'total': total, 'by_store': by_store, 'half_price_count': half}
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
# When the specials were last refreshed (UTC, ISO format) - shown on the site as "updated x hours ago"
stats['data_updated_at'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
with open('static/data/stats.json', 'w', encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print("Exported stats to static/data/stats.json")
conn.close()
