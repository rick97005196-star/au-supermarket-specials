"""同款不同包裝 (the same drink in any pack, at any store) - the Python twin of static/compare.js sensibleUnitOf
(drinks part), brandKeyOf, variantKeyOf and static/app.js packGroupKey, so the export can give every can / bottle
of drink a group key ('pg') and compare its price per can with the group's history (price_history.py).

The website uses the 'pg' key from the data, so both sides always agree. tests/test_pack_group.py checks that this
file gives exactly the same keys as the JavaScript for every product on the site.
"""
import re

_DRINK_CATS = {'drinks', 'liquor'}
_NOT_DRINK = re.compile(r'\b(powder|concentrate|syrup|tea bags?|capsules|pods|beans|ground|instant|sachets?|jelly|ice blocks?|'
                        r'icy poles?|tablets?|batter|fries|chips|nuts|cask|vinegar|sauce|oil|marinade|dressing|stock|broth)\b')
_CAN_SIZES = {250, 275, 300, 330, 355, 375, 440, 473, 500}
_TWO_WORD_BRANDS = {'red bull', 'red rock', 'dairy farmers', 'sunny queen', 'old el', 'san remo', 'john west',
                    'uncle tobys', 'golden circle', 'king island', 'black swan', 'mount franklin', 'pure harvest',
                    'blue dragon', 'la espanola', 'the natural', 'v energy', 'mr muscle', 'head shoulders', 'oral b',
                    'cold power', 'morning fresh'}
_BRAND_PREFIX = set('the mr mrs dr st la le el old sour sweet big little king uncle aunt grandma nanna country'.split())
_VARIANT_FILLER = set(('energy drink drinks soft can cans bottle bottles pack packs pk multipack multi single x each ea '
                       'flavour flavoured flavor mini value case of the and with in a an per approx edition range selected '
                       'varieties').split())
_SEVERAL = re.compile(r'\bor\b|,|\bassorted\b|\bvarieties\b|\bselected\b|\bmixed\b|\brange\b', re.I)


def per_item_price(it):
    m = re.search(r'(\d+)\s*for\s*\$\s*([\d,]+(?:\.\d+)?)', str(it.get('price_display') or ''), re.I)
    if m:
        n, total = int(m.group(1)), float(m.group(2).replace(',', ''))
        if n > 0 and total > 0:
            return total / n
    try:
        return float(it.get('price') or 0)
    except (TypeError, ValueError):
        return 0.0


def _js_round(x):
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def drink_pack(t):
    """compare.js _drinkPack: {n, ml} for a pack of n containers of ml each, or None."""
    U = r'(ml|l|litres?|liters?)'
    to_ml = lambda q, u: q if u == 'ml' else q * 1000
    m = re.search(r'(\d+)\s*[x×]\s*(\d+(?:\.\d+)?)\s*' + U + r'\b', t)
    if m:
        return int(m.group(1)), to_ml(float(m.group(2)), m.group(3))
    m = re.search(r'(\d+(?:\.\d+)?)\s*' + U + r'\s*[x×]\s*(\d+)\b', t)
    if m:
        return int(m.group(3)), to_ml(float(m.group(1)), m.group(2))
    if re.search(r'\bor\b|\bassorted\b|\bvarieties\b|\d\s*(ml|l)?\s*[-–/]\s*\d', t):
        return None
    sizes = [to_ml(float(x.group(1)), x.group(2)) for x in re.finditer(r'(\d+(?:\.\d+)?)\s*' + U + r'\b', t)]
    if not sizes:
        return None
    ml = min(sizes)
    packs = [int(x.group(1) or x.group(2)) for x in
             re.finditer(r'\b(\d+)\s*(?:pk|packs?|cans|bottles)\b|\b(?:pk|pack of|case of)\s*(\d+)\b', t)]
    if packs and not all(n == packs[0] for n in packs):
        return None
    n = packs[0] if packs else 1
    if any(s != ml and abs(s - ml * n) > 1 for s in sizes):
        return None
    return n, ml


def drink_unit(it):
    """(basis 'can'|'btl', price per container, ml, containers in the pack) or None (compare.js sensibleUnitOf)."""
    per = per_item_price(it)
    t = re.sub(r'(\d),(\d{3})\b', r'\1\2', str(it.get('title') or '').lower())
    if not (per > 0 and (it.get('category') in _DRINK_CATS or re.search(r'\b(cans?|bottles?)\b', t))
            and not _NOT_DRINK.search(t) and not re.search(r'\d\s*(kg|g)\b', t)):
        return None
    p = drink_pack(t)
    if not p:
        return None
    n, ml = p
    if not (1 <= n <= 60 and 100 <= ml <= 1250):
        return None
    no_btl = not re.search(r'\bbottles?\b', t)
    can = (bool(re.search(r'\bcans?\b', t))
           or (no_btl and it.get('category') != 'liquor' and _js_round(ml) in _CAN_SIZES and n > 1)
           or (no_btl and re.search(r'\b(energy|soft drink|red bull|monster|v energy|mother|beer|lager|ale|cider|seltzer)\b', t)
               and _js_round(ml) in _CAN_SIZES))
    value = per / n
    if not (0.01 <= value <= 3000):
        return None
    return ('can' if can else 'btl'), value, ml, n


def brand_of(title):
    raw = str(title or '').replace('’', '').replace("'", '').replace('&', ' ')
    words = [w for w in re.sub(r'[^a-z0-9\s-]', ' ', raw.lower()).split() if w]
    brand = words[0] if words else ''
    two = ' '.join(words[:2])
    if brand in _BRAND_PREFIX or two in _TWO_WORD_BRANDS:
        brand = two
    return brand


def variant_of(title):
    brand_n = len(brand_of(title).split(' '))
    t = str(title or '').lower().replace('’', '').replace("'", '').replace('&', ' ')
    t = re.sub(r'(\d),(\d{3})\b', r'\1\2', t)
    words = [w for w in re.sub(r'[^a-z0-9.\s-]', ' ', t).split() if w][brand_n:]
    left = [w.replace('-', '') for w in words if not re.search(r'\d', w) and w not in _VARIANT_FILLER
            and not re.fullmatch(r'ml|l|g|kg|litres?|liters?', w) and len(w) > 1]
    return ' '.join(sorted(set(left)))


def _pack_nums(title):
    t = str(title or '').lower()
    t = re.sub(r'\d+(?:\.\d+)?\s*(?:ml|l|litres?|liters?)\b', ' ', t)
    t = re.sub(r'\d+\s*[x×]|[x×]\s*\d+', ' ', t)
    t = re.sub(r'\b\d+\s*(?:pk|packs?|cans|bottles|each|ea)\b|\b(?:pk|pack of|case of)\s*\d+\b', ' ', t)
    return re.findall(r'\d+(?:\.\d+)?', t)


def group_key(it):
    """'' or brand|flavour words|ml|can-or-btl|other numbers - the same as app.js packGroupKey."""
    u = drink_unit(it)
    if not u:
        return ''
    if _SEVERAL.search(str(it.get('title') or '')):
        return ''
    basis, _, ml, _ = u
    return '|'.join([brand_of(it.get('title')), variant_of(it.get('title')), str(_js_round(ml)), basis,
                     ','.join(sorted(_pack_nums(it.get('title'))))])
