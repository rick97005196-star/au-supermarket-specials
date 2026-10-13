"""Checks for reading the extra Woolworths specials lists (seasonal, lower shelf price, multi-buys):
the offer text printed on a product is understood, and a multi-buy is never taken for half price.

    python tests/test_woolies_groups.py      (needs requests and beautifulsoup4, like the scrapers)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scrapers.woolies_scraper import _woolies_tag_text, _WAS_TAG, _MULTI_TAG  # noqa: E402
import database  # noqa: E402

bad = []
total = 0


def check(cond, msg):
    global total
    total += 1
    if not cond:
        bad.append(msg)


# --- the offer text, as the Woolworths list gives it (copied from the website's answer) ---
lower = {'CentreTag': {'TagContent': '<span>Was $3.30 - 25/08/2026</span>'},
         'HeaderTag': {'Content': '<span class="u-semibold">Lower shelf price</span>'}}
m = _WAS_TAG.search(_woolies_tag_text(lower))
check(m and m.group(1) == '3.30', 'lower shelf price: "Was $3.30" is read')

rng = {'CentreTag': {'TagContent': '<span>Range was $3.20 - 25/08/2026</span>'}}
m = _WAS_TAG.search(_woolies_tag_text(rng))
check(m and m.group(1) == '3.20', '"Range was $3.20" is read')

multi = {'CentreTag': {'TagContent': '<a title="2 for $20.00" href="/Shop/OfferGroup/24132625"><span>2 for $20</span></a>'}}
m = _MULTI_TAG.search(_woolies_tag_text(multi))
check(m and (m.group(1), m.group(2)) == ('2', '20.00'), 'multi-buy: "2 for $20.00" is read from the link title')

check(_WAS_TAG.search(_woolies_tag_text({'CentreTag': None, 'HeaderTag': None})) is None, 'no tag: nothing is read')
check(_MULTI_TAG.search(_woolies_tag_text(lower)) is None, 'a "was" price is not a multi-buy')

# --- a multi-buy (buy one, get one free) is only cheaper when buying two: never "half price" ---
check(not database.is_half_price(32.0, 64.0, 32.0, '2 for $32.00'), 'buy-one-get-one-free is not half price')
check(database.is_half_price(2.75, 5.5, 2.75, '1/2 PRICE'), 'a real half price still is')
check(database.is_half_price(5.0, 10.0, 5.0, 'Seasonal Price'), 'a 50% seasonal cut still is')

# --- before Wednesday: lasting prices are added to next week's preview, only once it exists ---
from scrapers.updater import with_lasting_prices  # noqa: E402
cur = [{'title': 'Bread 650g', 'discount_desc': 'Everyday Low Price'},
       {'title': 'Sour Cream 300mL', 'discount_desc': 'Lower Shelf Price'},
       {'title': 'Chips 170g', 'discount_desc': '1/2 PRICE'},
       {'title': 'Milk 2L', 'discount_desc': 'Everyday Low Price'}]
nxt = [{'title': 'Milk 2L', 'discount_desc': 'Save $1.00'}]
got = {it['title']: it['discount_desc'] for it in with_lasting_prices(nxt, cur)}
check(got == {'Milk 2L': 'Save $1.00', 'Bread 650g': 'Everyday Low Price', 'Sour Cream 300mL': 'Lower Shelf Price'},
      f'lasting prices join the preview, the weekly half price does not, the preview entry wins: {got}')
check(with_lasting_prices([], cur) == [], 'no preview published yet: nothing is added')

for b in bad:
    print('FAIL', b)
print(f'{total - len(bad)}/{total} Woolworths list checks passed')
sys.exit(1 if bad else 0)
