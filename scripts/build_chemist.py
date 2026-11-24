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
NAMES = os.path.join(ROOT, 'data', 'chemist_translations.json')   # scripts/translate_chemist.py
STORE = 'Chemist Warehouse'

# Departments, checked in this order (the first that matches wins). Words are matched in the English name.
DEPARTMENTS = [
    ('fragrance', r'\b(?:edp|edt|parfum|perfume|cologne|aftershave|eau de)\b'),
    ('pet', r'\b(?:dogs?|cats?|pets?|animals?|puppy|kitten|k9|flea|wormer|bravecto|nexgard|simparica|frontline|advocate|'
            r'revolution plus|seresto|drontal|milbemax)\b'),
    ('baby', r'\b(?:elevit|menevit|pregnan\w*|breastfeed\w*|pre-?conception|baby|babies|infant|toddler|newborn|nappy|'
             r'nappies|huggies|formula stage|bubs|a2 platinum|aptamil|karicare|s-?26|bellamy\w*|ergopouch|tog|swaddle|'
             r'teats?|soother|dummy|pigeon|avent|tommee tippee|playgro|tiny twinkle|bib|sippy|bottle teat|'
             r'starting solids|months?)\b'),
    ('medicine', r'\b(?:claratyne|zyrtec|zyretc|telfast|fexaren|allernex|demazin|sudafed|nicorette|nicotinell|dulcolax|'
                 r'laxactive|buscopan|gastrosyl|pantoleze|releva|dozatin|clearx|cough|cold & flu|cold and flu|panadol|'
                 r'nurofen|ibuprofen|paracetamol|hayfever|antihistamine|heartburn|diarrhoea|constipation relief|'
                 r'ferro-?grad|decongestant|pain relief|lozenges?|ointment|eye drops?|ear drops?|nasal spray|'
                 r'antifungal|thrush|canesten|pevaryl|wart|cold sore|haemorrhoid|voltaren|codral|strepsils|'
                 r'gaviscon|mylanta|imodium|antacid|sulfate|sulphate|hydrochloride|'
                 r'oral liquid|suppositor\w*|inhaler|ventolin|injection|'
                 r'(?:tablets|capsules|caplets|patches)\s+\d+(?:\s+\d+\s*x\s*\d+)?\s+[a-z]{5,}(?:\s+[a-z]+)?$|'
                 r'\w+(?:pam|olol|pril|sartan|statin|azole|mycin|cillin|oxacin|dipine|prazole|tidine|triptan|gliptin|lukast|cycline|setron|floxacin)\b)\b'),
    ('health', r'\b(?:bandages?|band-?aids?|elastoplast|plasters?|dressings?|wound|first aid|sterile|gauze|tape|'
               r'strips|adhesive|swabs?|compression|support|brace|sleeve|orthotic|orthopedic|archline|insoles?|'
               r'thongs|slippers|heel|ankle|knee|wrist|back support|posture|pillow|mattress|heat pack|cold pack|'
               r'tens|thermometer|blood pressure|glucose|ketone|insulin|glucology|accu-?chek|test strips?|lancets?|'
               r'syringe|scales?|incontinence|tena|depend|poise|briefs|pads?|panty liners?|period|tampons?|kotex|libra|'
               r'condoms?|lubricant|pregnancy test|ovulation|thermoskin|bodyassist|scholl|corn|callus|foot|feet|'
               r'socks|mask|masks|sanitiser|sanitizer|hand wash|wheat bag|walking|crutch|mobility|pill box|'
               r'hearing|ear plugs?|nebuliser|livingstone|allcare|melior|opsite|jelonet)\b'),
    ('oral', r'\b(?:toothpaste|toothbrush\w*|mouthwash|listerine|floss\w*|oral-?b|colgate|sensodyne|denture|'
             r'interdental|piksters|whitening strips|teeth|dental)\b'),
    ('appliance', r'\b(?:braun|philips|trimmer|shaver|epilator|hair dryer|dryer|straightener|curler|curling|electric|'
                  r'oral-b io|massager|diffuser|humidifier|smart)\b'),
    ('hair', r'\b(?:shampoo|conditioner|hair(?!\s*(?:growth|radiance|skin|&\s*nail))|haircare|keratin|scalp|batiste|'
             r'hask|redken|kristin ess|klorane|kativa|gro hair|my\. organics|ovidio|schwarzkopf|colorsilk|'
             r'hair colour|hair color|blonde|brunette|mousse|styler|styling|pomade|hairspray|bobby pins|'
             r'scrunchie|hair ties?|brush|comb|toni & guy|pantene|tresemme|garnier nutrisse|nice n easy|'
             r'headgear|osis|olaplex|moroccanoil)\b'),
    ('sports', r'\b(?:protein|whey|wpi|creatine monohydrate|creatine hcl|mass|shred|optifast|vlcd|pre-?workout|'
               r'muscle nation|vitalstrength|vital strength|bondi protein|inc\.|optislim|electrolytes?|hydralyte|'
               r'sports drink|energy drink|bcaa|amino)'),
    ('makeup', r'\b(?:mascara|lipstick|lip gloss|lip oil|lip liner|lipliner|lip pencil|foundation|concealer|primer|'
               r'setting (?:spray|mist|powder)|makeup|make-up|cosmetics|brow|lashes|nails?|sally hansen|rimmel|'
               r'maybelline|mcobeauty|w7|my beauty|eyeliner|eyeshadow|shadow|blush(?! \d)|bronzer|highlighter|'
               r'revlon|nyx|colorstay|max factor|essence|covergirl|bourjois|opi|manicare|selfie nails|'
               r'nude by nature|lip|matte|tweezers?|nail polish|press on|glam)\b'),
    ('skin', r'\b(?:spf|sunscreen|sun range|tann\w*|moistur\w*|serum|cream|creme|lotion|cleanser|cleansing|'
             r'micellar|micellaire|retinol|niacinamide|hyaluronic acid water|skincare|skin care|face range|'
             r'body wash|lip balm|deodorant|antiperspirant|roll on|cetaphil|cerave|neutrogena|olay|qv|dermaveen|'
             r'la roche|vichy|uriage|bondi sands|bio oil)\b'),
    ('vitamins', r'\b(?:vitamin\w*|vit|multi\w*|capsules?|caps|tablets?|tabs|softgels?|gumm\w*|chewables?|magnesium|'
                 r'calcium|zinc|iron|probiotic\w*|fish oil|omega|krill|collagen|glucosamine|turmeric|curcumin|coq10|'
                 r'ubiquinol|ashwagandha|theanine|melatonin|sleep|b12|b complex|nmn|berberine|milk thistle|ginkgo|'
                 r'selenium|supplement|powder|swisse|blackmores|bioglan|cenovis|ostelin|wagner|microgenics|'
                 r'nature\'?s way|nature\'?s own|healthy care|ethical nutrients|nutra-?life|life-?space|go healthy|'
                 r'berocca|elevit|caruso\'?s|herbs of gold|metagenics|bio-?ceuticals|thompson\'?s|fusion|mcg|'
                 r'manuka|honey|tea|elixir|greens|superfood|fibre|metamucil|sachets|drink|nature s sunshine|'
                 r'nature s way|nature s own|caruso s)\b'),
    ('skin', r'\b(?:spf|sunscreen|sun range|tann\w*|tan\b|moistur\w*|serum|cream|creme|lotion|cleanser|cleansing|'
             r'micellar|micellaire|retinol|niacinamide|hyaluronic acid water|skincare|skin care|face range|'
             r'body wash|wash|lip balm|balm|qv|dermaveen|cetaphil|cerave|neutrogena|olay|l\s?\'?or[eé]al|vichy|'
             r'uriage|la roche|bondi sands|deodorant|antiperspirant|roll on|goat|barely personal|dot:dot|mist|'
             r'bio oil|oil|soap|bath|body|face|facial|wipes|scrub|exfoliat\w*|toner|aloe|razor|razors|blades?|'
             r'gillette|schick|venus|wax|waxing|nad\'?s|veet|shaving|skin|pimple|blemish|acne|patch)\b'),
]
_RX = [(k, re.compile(p, re.I)) for k, p in DEPARTMENTS]
DEPT_KEYS = ['vitamins', 'medicine', 'health', 'baby', 'skin', 'makeup', 'hair', 'fragrance', 'oral', 'sports',
             'appliance', 'pet', 'other']
ONLINE_ONLY = re.compile(r'(?:^|-)(?:online-only|online-exclusive|web-only|web-exclusive|online-excl)(?:-|$)', re.I)


def department(title, fallback='other'):
    for key, rx in _RX:
        if rx.search(title or ''):
            return key
    return fallback


def product_id(url):
    m = re.search(r'/buy/(\d+)', url or '')
    return m.group(1) if m else ''


def ended(date_range, today=None):
    """'Thu 12 Nov 2026 - Wed 25 Nov 2026' -> True once 25 Nov has passed in Sydney (the catalogue's last day counts)."""
    m = re.findall(r'(\d{1,2})\s+([A-Za-z]{3})\w*\s+(\d{4})', date_range or '')
    if len(m) < 2:
        return False
    try:
        end = _dt.datetime.strptime(' '.join(m[-1]), '%d %b %Y').date()
    except ValueError:
        return False
    if today is None:
        from zoneinfo import ZoneInfo
        today = _dt.datetime.now(ZoneInfo('Australia/Sydney')).date()
    return today > end


def _special(it):
    tr = it.get('translations') or {}
    return {
        'id': it.get('id'),
        'pid': product_id(it.get('product_url')),
        'period': it.get('period') or 'current',
        'title': it.get('title') or '',
        'zh': tr.get('zh') or '',
        'ja': tr.get('ja') or '',
        'ko': tr.get('ko') or '',
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
    specials = [_special(it) for it in items if it.get('store') == STORE and not ended(it.get('date_range'))]
    if not specials:
        # between two catalogues (the old one ended, the new one is not out yet): the site still shows every
        # product and says the next catalogue is not out yet - an ended catalogue must never stay on show
        print('build_chemist: no catalogue on now - the site shows all products and "next catalogue not out yet"')
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
    skipped_online = 0
    for p in all_data.get('products', []):
        if p.get('pid') in on_special:
            continue                    # shown once, as its catalogue special
        slug = (p.get('url') or '').rstrip('/').rsplit('/', 1)[-1]
        if not slug:
            continue
        if ONLINE_ONLY.search(slug):
            skipped_online += 1         # in-store only: products the shop sells online only are left out
            continue
        # compact (about 27,000 rows): the page makes the name and the link back from the number and the link text
        listed.append([p['pid'], slug, DEPT_KEYS.index(department(p['title']))])

    os.makedirs(OUT_DIR, exist_ok=True)
    data = {
        'updated': _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'list_read': all_data.get('read', ''),
        'date_ranges': sorted({sp['date_range'] for sp in specials if sp['date_range']}),
        'specials': specials,
        'depts': DEPT_KEYS,
        'products': listed,             # [product number, link text, index in depts]
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    # translated names of the other products, one small file per language (the page loads only the one it shows)
    try:
        with open(NAMES, encoding='utf-8') as f:
            names = json.load(f)
    except (OSError, ValueError):
        names = {}
    shown = {r[0] for r in listed}
    for i, lang in enumerate(('zh', 'ja', 'ko')):
        part = {pid: v[i] for pid, v in names.items() if pid in shown and len(v) > i and v[i]}
        with open(os.path.join(OUT_DIR, f'names-{lang}.json'), 'w', encoding='utf-8') as f:
            json.dump(part, f, ensure_ascii=False, separators=(',', ':'))
    counts = {}
    for d in [x['dept'] for x in specials] + [DEPT_KEYS[r[2]] for r in listed]:
        counts[d] = counts.get(d, 0) + 1
    print(f'build_chemist: {len(specials)} specials + {len(listed)} other products '
          f'({skipped_online} online-only left out) -> {OUT}  {counts}')
    return 0


if __name__ == '__main__':
    sys.exit(build())
