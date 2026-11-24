"""Checks for the stand-alone 小黃屋 site: scrapers/chemist_all.py (product list) and scripts/build_chemist.py."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from scrapers.chemist_all import parse_products, name_from_slug  # noqa: E402
from build_chemist import department, product_id  # noqa: E402

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
    'Dog Flea Treatment Large': 'other',
}
for title, want in cases.items():
    assert department(title) == want, (title, department(title), want)
assert department('Something New', fallback='vitamins') == 'vitamins'
print('chemist site: ok')
