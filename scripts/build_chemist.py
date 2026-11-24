"""
Build the data for the stand-alone Chemist Warehouse (小黃屋) site (chemist/).

Sources (nothing is downloaded here):
  * static/data/specials.json - made by the normal update; scrapers/chemist_scraper.py reads the printed,
    in-store catalogue. The only prices on the site come from here.
  * data/chemist_all.json - every product the shop sells (names and links only), scrapers/chemist_all.py.
Both are sorted into pharmacy departments and written to chemist/data/products.json.

    python scripts/build_chemist.py
"""
import json
import os
import re
import sys
import datetime as _dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'static', 'data', 'specials.json')
OUT_DIR = os.path.join(ROOT, 'chemist', 'data')
OUT = os.path.join(OUT_DIR, 'products.json')
ALL = os.path.join(ROOT, 'data', 'chemist_all.json')   # scrapers/chemist_all.py
STORE = 'Chemist Warehouse'

# Departments, checked in this order (the first that matches wins). Words are matched in the English name.
DEPARTMENTS = [
    ('fragrance', r'\b(?:edp|edt|parfum|perfume|cologne|aftershave|eau de)\b'),
    ('baby', r'\b(?:elevit|menevit|pregnan\w*|breastfeed\w*|pre-?conception|baby|infant|nappy|nappies|formula stage)\b'),
    ('medicine', r'\b(?:claratyne|zyrtec|zyretc|telfast|fexaren|allernex|demazin|sudafed|nicorette|nicotinell|dulcolax|laxactive|'
                 r'buscopan|gastrosyl|pantoleze|releva|dozatin|melatonin|clearx|cough|cold & flu|panadol|nurofen|ibuprofen|'
                 r'paracetamol|hayfever|antihistamine|heartburn|diarrhoea|constipation relief|ferro-?grad|rapid test|'
                 r'decongestant|pain relief|lozenges?|mg \d+ tablets? - )\b'),
    ('oral', r'\b(?:toothpaste|toothbrush|mouthwash|listerine|floss|oral-?b|colgate|sensodyne|denture)\b'),
    ('appliance', r'\b(?:braun|philips|trimmer|shaver|epilator|hair dryer|straightener|electric|oral-b io|thermometer|'
                  r'blood pressure)\b'),
    ('hair', r'\b(?:shampoo|conditioner|hair(?!\s*(?:growth|radiance|skin|&\s*nail))|haircare|keratin|scalp|batiste|hask|'
             r'redken|kristin ess|klorane|kativa|gro hair|my\. organics|ovidio)'),
    ('sports', r'\b(?:protein|whey|wpi|creatine monohydrate|creatine hcl|mass|shred|optifast|vlcd|pre-?workout|'
               r'muscle nation|vitalstrength|vital strength|bondi protein|inc\.)'),
    ('makeup', r'\b(?:mascara|lipstick|lip gloss|foundation|concealer|primer|setting (?:spray|mist)|makeup|cosmetics|'
               r'brow|lashes|nail|sally hansen|rimmel|maybelline|mcobeauty|w7|my beauty|eyeliner|blush(?! \d)|bronzer)\b'),
    ('skin', r'\b(?:spf|sunscreen|sun range|tann\w*|tan\b|moistur\w*|serum|cream|lotion|cleanser|micellar|micellaire|'
             r'retinol|niacinamide|hyaluronic acid water|skincare|skin care|face range|body wash|wash|lip balm|'
             r'qv|dermaveen|cetaphil|cerave|neutrogena|olay|l\'or[eé]al|vichy|uriage|la roche|bondi sands|'
             r'deodorant|antiperspirant|roll on|goat|barely personal|dot:dot|mist)\b'),
    ('vitamins', r'\b(?:vitamin\w*|vit|multi\w*|capsules?|caps|tablets?|tabs|softgels?|gumm\w*|chewables?|magnesium|'
                 r'calcium|zinc|iron|probiotic\w*|fish oil|omega|krill|collagen|glucosamine|turmeric|curcumin|coq10|'
                 r'ubiquinol|ashwagandha|theanine|melatonin|sleep|b12|b complex|nmn|berberine|milk thistle|ginkgo|'
                 r'selenium|supplement|powder|swisse|blackmores|bioglan|cenovis|ostelin|wagner|microgenics|'
                 r'nature\'?s way|nature\'?s own|healthy care|ethical nutrients|nutra-?life|life-?space|go healthy|'
                 r'berocca|elevit|caruso\'?s|herbs of gold|metagenics|bio-?ceuticals|thompson\'?s|fusion)\b'),
]
_RX = [(k, re.compile(p, re.I)) for k, p in DEPARTMENTS]


def department(title, fallback='other'):
    for key, rx in _RX:
        if rx.search(title or ''):
            return key
    return fallback


def product_id(url):
    m = re.search(r'/buy/(\d+)', url or '')
    return m.group(1) if m else ''


def _special(it):
    tr = it.get('translations') or {}
    return {
        'id': it.get('id'),
        'pid': product_id(it.get('product_url')),
        'period': it.get('period') or 'current',
        'title': it.get('title') or '',
        'zh': tr.get('zh') or '',
        'price': it.get('price') or 0,
        'price_display': it.get('price_display') or '',
        'was_price': it.get('was_price') or 0,
        'save_amount': it.get('save_amount') or 0,
        'discount_desc': it.get('discount_desc') or '',
        'date_range': it.get('date_range') or '',
        'image_url': it.get('image_url') or '',
        'url': it.get('product_url') or '',
        'pop': it.get('popularity_score') or 0,
    }


def build():
    with open(SRC, encoding='utf-8') as f:
        items = json.load(f)
    specials = [_special(it) for it in items if it.get('store') == STORE]
    if not specials:
        # never publish a site without the catalogue: keep what is online
        print('build_chemist: no Chemist Warehouse catalogue items found - nothing written')
        return 1
    for sp in specials:
        # a catalogue item that is not in the vitamins rules is still a health item in a pharmacy catalogue
        sp['dept'] = department(sp['title'], fallback='vitamins')

    # every product the shop sells (scrapers/chemist_all.py); catalogue specials are matched by product number
    listed = []
    try:
        with open(ALL, encoding='utf-8') as f:
            all_data = json.load(f)
    except (OSError, ValueError):
        all_data = {'products': [], 'read': ''}
    on_special = {sp['pid'] for sp in specials if sp['pid']}
    for p in all_data.get('products', []):
        if p.get('pid') in on_special:
            continue                    # shown once, as its catalogue special
        listed.append({'pid': p['pid'], 'title': p['title'], 'url': p['url'], 'dept': department(p['title'])})

    os.makedirs(OUT_DIR, exist_ok=True)
    data = {
        'updated': _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'list_read': all_data.get('read', ''),
        'date_ranges': sorted({sp['date_range'] for sp in specials if sp['date_range']}),
        'specials': specials,
        'products': listed,
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    counts = {}
    for x in specials + listed:
        counts[x['dept']] = counts.get(x['dept'], 0) + 1
    print(f'build_chemist: {len(specials)} specials + {len(listed)} other products -> {OUT}  {counts}')
    return 0


if __name__ == '__main__':
    sys.exit(build())
