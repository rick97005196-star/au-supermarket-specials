"""Checks for the stand-alone 小黃屋 site: scrapers/chemist_all.py (product list) and scripts/build_chemist.py."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from scrapers.chemist_all import parse_products, name_from_slug  # noqa: E402
from build_chemist import department, product_id, ended  # noqa: E402
import datetime  # noqa: E402

xml = '''<urlset>
<url><loc>https://www.chemistwarehouse.com.au/buy/91329/cerave-moisturising-cream-454g</loc></url>
<url><loc> https://www.chemistwarehouse.com.au/buy/69707/bioglan-red-krill-oil-1000mg-60-capsules </loc></url>
<url><loc>https://www.chemistwarehouse.com.au/buy/91329/cerave-moisturising-cream-454g</loc></url>
<url><loc>https://www.chemistwarehouse.com.au/shop-online/256/vitamins</loc></url>
<url><loc>https://example.com/buy/1/not-the-shop</loc></url>
</urlset>'''
got = parse_products(xml)
assert [p['pid'] for p in got] == ['91329', '69707'], got          # once each, only product pages of the shop
assert got[0]['title'] == 'Cerave Moisturising Cream 454g'
assert name_from_slug('bioglan-red-krill-oil-1000mg-60-capsules') == 'Bioglan Red Krill Oil 1000mg 60 Capsules'

assert product_id('https://www.chemistwarehouse.com.au/buy/156722/swisse-x') == '156722'
assert product_id('') == ''

cases = {
    'Burberry Goddess 100ml EDP': 'fragrance',
    'Elevit Pre-conception & Pregnancy 100 Tablets': 'baby',
    'Telfast 180mg 30 Tablets': 'medicine',
    'Panadol Rapid 20 Caplets': 'medicine',
    'Hask Keratin Protein 5-in-1 Leave In Spray 175ml': 'hair',
    'Swisse Nutra Cellular Hair Growth Mens 60 Tablets': 'vitamins',   # a supplement, not hair care
    'INC. 100 WPI Vanilla Flavour 2kg': 'sports',
    'Colgate Toothpaste Total Active Prevention Deep Clean 200g': 'oral',
    'Braun Series 5 Beard Trimmer + 8 Tools BT5560': 'appliance',
    'Rimmel Cosmetics Range': 'makeup',
    'Cetaphil Sun SPF 50 Ultra Light Lotion 100ml': 'skin',
    'Blackmores Omega Super Strength Fish Oil 150 Capsules': 'vitamins',
    'Dog Flea Treatment Large': 'pet',
    'Archline Orthotic Foam Thongs Arch Support Flip Flops Euro Size 36': 'health',
    'Neat Feat Gel Heel Cups': 'health',
    'Ocean Road Black Home Soy Candle 380g': 'other',
}
for title, want in cases.items():
    assert department(title) == want, (title, department(title), want)
assert department('Something New', fallback='vitamins') == 'vitamins'
r = 'Thu 12 Nov 2026 - Wed 25 Nov 2026'
assert not ended(r, datetime.date(2026, 11, 25))      # the last day still counts
assert ended(r, datetime.date(2026, 11, 26))
assert not ended('', datetime.date(2026, 11, 26))      # no dates: never dropped by this rule
print('chemist site: ok')

# between two catalogues: the last catalogue is kept (save_last) and shown only once ended, marked 'ended'
import json, tempfile  # noqa: E401,E402
import build_chemist as bc  # noqa: E402
_tmp = tempfile.mkdtemp()
_src, _last = bc.SRC, bc.LAST
bc.SRC, bc.LAST = os.path.join(_tmp, 'specials.json'), os.path.join(_tmp, 'last.json')
_it = {'store': 'Chemist Warehouse', 'period': 'current', 'title': 'Blackmores Fish Oil 400 Capsules', 'price': 20,
       'product_url': 'https://www.chemistwarehouse.com.au/buy/1/x', 'date_range': 'Thu 12 Nov 2026 - Wed 25 Nov 2026'}
_far = {**_it, 'title': 'Swisse Ultiboost 60 Tablets', 'date_range': 'Thu 12 Nov 2099 - Wed 25 Nov 2099'}
with open(bc.SRC, 'w') as f:
    json.dump([_far, {**_far, 'store': 'Coles'}], f)
bc.save_last()
saved = json.load(open(bc.LAST))['items']
assert [x['title'] for x in saved] == ['Swisse Ultiboost 60 Tablets'], saved     # only 小黃屋, the catalogue on now
assert bc.last_catalogue() == [], 'a catalogue still on is never shown as the ended one'
with open(bc.SRC, 'w') as f:
    json.dump([], f)
bc.save_last()                                                                   # nothing on: the saved copy stays
assert json.load(open(bc.LAST))['items'] == saved
with open(bc.LAST, 'w') as f:
    json.dump({'items': [bc._special(_it)]}, f)
old = bc.last_catalogue()
assert len(old) == 1 and old[0]['period'] == 'ended' and old[0]['dept'] == 'vitamins', old
bc.SRC, bc.LAST = _src, _last
print('last catalogue between two catalogues: OK')
