# -*- coding: utf-8 -*-
"""
本週熱門 (the default order): the specials Australians discuss most this week come first.

Source: OzBargain, Australia's big public deals community. Each deal posted there for Coles, Woolworths or
ALDI has up-votes, down-votes and comments. scripts/fetch_buzz.py saves the deals of the last 8 days to
data/buzz.json (in the cloud, on each update, at most every 6 hours). export_static_data.py calls
apply_buzz() to give each matched special a 'bz' score (up-votes - down-votes + comments) and 'bzd'
(the discussion: deal id, votes, comments) for the website.

Strict matching - a special gets a score only when the deal clearly is that product, else it gets nothing
(it then keeps the usual order after the discussed ones; no guessing):
  * same supermarket (the deal's store page on OzBargain, and the deal title names that store);
  * the product's brand is in the deal title and at least 75% of the product's name words are too - or the deal
    names a product line ("Gym Bod Protein Ice Cream Varieties") and every one of its words is in the product's
    name (at least 2 words besides the brand);
  * if both name a size (1L, 500g, 4 x 240ml...), at least one size is the same;
  * the deal's price ($X) is the special's price - or, for a deal without a price, the deal says
    half price and the special is half price;
  * deals that are online only / marketplace / Everyday Market, or match more than MAX_MATCHES products
    (too general to say which product people liked) are not used.
"""
import datetime
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
BUZZ_FILE = os.path.join(ROOT, 'data', 'buzz.json')
WINDOW_DAYS = 8
MAX_MATCHES = 12
MIN_COVERAGE = 0.75
HOUSE_BRANDS = {'coles', 'woolworths', 'macro', 'essentials'}
STORE_WORDS = {'Coles': {'coles'}, 'Woolworths': {'woolworths', 'woolies'}, 'ALDI': {'aldi'}}
NOT_IN_STORE = re.compile(r'online only|online exclusive|marketplace|everyday market|first order|'
                          r'\bdelivered\b|app only|via everyday', re.I)
STOP = {'pack', 'pk', 'x', 'each', 'ea', 'varieties', 'variety', 'selected', 'range', 'the', 'and', 'with',
        'of', 'for', 'in', 'per', 'a', 'an', 'or', 'to', 'at', 'from', 'new', 'only', 'price', 'half',
        'off', 'save', 'was', 'now', 'kg', 'g', 'ml', 'l', 'litre', 'litres', 'bottle', 'bottles', 'can',
        'cans', 'bag', 'box', 'jar', 'tub', 'tin', 'pouch', 'pouches', 'tray', 'prepacked', 'punnet', 'bunch',
        'special', 'specials', 'buys', 'buy', 'super', 'savers', 'in-store', 'instore', 'store', 'stores'}
_SIZE = re.compile(r'(\d+(?:\.\d+)?)\s*(ml|l|litres?|g|kg)\b')
_MULTI = re.compile(r'(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*(ml|l|g|kg)\b|(\d+(?:\.\d+)?)\s*(ml|l|g|kg)\s*x\s*(\d+)\b')
_PRICE = re.compile(r'\$\s*(\d+(?:\.\d{1,2})?)')
_HALF = re.compile(r'1/2\s*price|half\s*price|50\s*%\s*off', re.I)


def _norm(s):
    s = str(s or '').lower().replace('&amp;', '&').replace('&', ' and ').replace('’', "'")
    return re.sub(r"'s\b", 's', s).replace("'", '')


def _words(s):
    return re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', _norm(s))


def sizes(s):
    """{'240ml', '1000g'...} - every pack size named, in ml / g."""
    out = set()
    for num, unit in _SIZE.findall(_norm(s)):
        v = float(num)
        if unit in ('l', 'litre', 'litres'):
            v, unit = v * 1000, 'ml'
        elif unit == 'kg':
            v, unit = v * 1000, 'g'
        out.add(f"{v:g}{unit}")
    return out


def name_words(title):
    """The product's meaningful name words (no sizes, numbers or filler words)."""
    out = []
    for w in _words(title):
        if w in STOP or w.isdigit() or _SIZE.fullmatch(w) or re.fullmatch(r'\d+(?:\.\d+)?(ml|l|g|kg|pk|pack|x)', w):
            continue
        if len(w) < 2:
            continue
        out.append(w)
    return out


def brand_words(title):
    words = name_words(title)
    if not words:
        return []
    return words[:2] if words[0] in HOUSE_BRANDS or len(words[0]) <= 3 else words[:1]


def deal_text(title, store):
    """The deal title without the '@ Store' part (the store's name would match every house-brand product)."""
    t = re.sub(r'@\s*[^/@]+', ' ', str(title or ''))
    return t


def _price_ok(item, text):
    prices = [float(p) for p in _PRICE.findall(text)]
    price = item.get('price') or 0
    if prices:
        return any(abs(p - price) < 0.006 for p in prices)
    # no price: only "half price" deals, and only for specials that really are half price
    if _HALF.search(text):
        was, now = item.get('was_price') or 0, price
        return bool(was and now and now <= was * 0.55)
    return False


def segments(title):
    """The whole deal title, and each part of a title that lists several products
    ("Gym Bod Ice Cream 475mL $5.50 & Gym Bod Ultra Tub 475mL $6.25")."""
    t = deal_text(title, '')
    parts = [p for p in re.split(r'\s+(?:&|\+|/)\s+|,\s+|;\s+', t) if p.strip()]
    return [t] + (parts if len(parts) > 1 else [])


def _segment_matches(item, seg, words, brand):
    dwords = set(_words(seg))
    if not all(b in dwords for b in brand):
        return False
    s_item, s_deal = sizes(item.get('title')), sizes(seg)
    if s_item and s_deal and not (s_item & s_deal):
        return False
    if not _price_ok(item, seg):
        return False
    # a) the deal names (almost) the whole product name
    hit = sum(1 for w in words if w in dwords)
    if hit >= 2 and hit / len(words) >= MIN_COVERAGE:
        return True
    # b) the deal names a product line ("Gym Bod Protein Ice Cream Varieties 475mL $5.50"): every product word of
    #    the deal is in the product's name, and it says more than the brand (at least 2 more words)
    iwords = set(words)
    seg_words = [w for w in name_words(seg) if not any(w in sw for sw in STORE_WORDS.values())]
    extra = [w for w in seg_words if w not in brand]
    return len(extra) >= 2 and all(w in iwords for w in seg_words)


def matches(item, deal):
    """True when the deal clearly is this product (rules at the top of this file)."""
    words = name_words(item.get('title'))
    brand = brand_words(item.get('title'))
    if not words or not brand:
        return False
    return any(_segment_matches(item, seg, words, brand) for seg in segments(deal['title']))


def deal_score(d):
    return max(0, int(d.get('votes_pos') or 0) - int(d.get('votes_neg') or 0) + int(d.get('comments') or 0))


def load_deals(path=BUZZ_FILE, now=None):
    """The usable deals of the last WINDOW_DAYS days (empty when there is no file)."""
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"[WARN] {path} could not be read ({e}) - default order without this week's discussions")
        return []
    now = now or datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=WINDOW_DAYS)
    out = []
    for d in data.get('deals') or []:
        try:
            posted = datetime.datetime.fromisoformat(d['posted'])
        except Exception:
            continue
        if posted < cutoff or d.get('store') not in STORE_WORDS or NOT_IN_STORE.search(d.get('title') or ''):
            continue
        if not (set(_words(d.get('title'))) & STORE_WORDS[d['store']]):
            continue
        if deal_score(d) <= 0:
            continue
        out.append(d)
    return out


def apply_buzz(items, deals=None, skip=None):
    """Sets 'bz' (score) and 'bzd' (the discussion) on the specials people discuss. Returns how many items.
    skip(item) -> True for products that are not specials (regular / everyday prices): they never get a score."""
    if deals is None:
        deals = load_deals()
    by_store = {}
    for it in items:
        if (it.get('price') or 0) > 0 and not (skip and skip(it)):
            by_store.setdefault(it.get('store'), []).append(it)
    best = {}
    for d in deals:
        found = [it for it in by_store.get(d['store'], []) if matches(it, d)]
        if not found or len(found) > MAX_MATCHES:
            continue
        sc = deal_score(d)
        for it in found:
            if sc > best.get(id(it), (0, None))[0]:
                best[id(it)] = (sc, d)
    n = 0
    for it in items:
        it.pop('bz', None)
        it.pop('bzd', None)
        if id(it) in best:
            sc, d = best[id(it)]
            it['bz'] = sc
            it['bzd'] = {'id': d['id'], 'v': int(d.get('votes_pos') or 0) - int(d.get('votes_neg') or 0),
                         'c': int(d.get('comments') or 0)}
            n += 1
    return n
