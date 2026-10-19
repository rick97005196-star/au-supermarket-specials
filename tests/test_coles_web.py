"""Checks for reading the Coles website lists (Half Price and All specials): each kind of price is
understood, a half price product is never counted twice, and an interrupted read continues from the
page it stopped at. No request is sent to coles.com.au.

    python tests/test_coles_web.py
"""
import contextlib
import io
import json
import os
import runpy
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scrapers import coles_web  # noqa: E402
from scrapers.coles_web import product_to_item, special_to_item  # noqa: E402
from scrapers.regions import SPECIAL_DESC  # noqa: E402
from scrapers.updater import _is_lasting  # noqa: E402
import database  # noqa: E402

bad = []
total = 0


def check(cond, msg):
    global total
    total += 1
    if not cond:
        bad.append(msg)


def product(pid, now, was=0, **pricing):
    """A product in the shape coles.com.au gives it (fields copied from the website's answer)."""
    return {'_type': 'PRODUCT', 'id': pid, 'brand': 'Coles', 'name': f'Test Product {pid}', 'size': '500g',
            'availability': True, 'imageUris': [{'uri': f'/{pid}.jpg'}],
            'merchandiseHeir': {'category': 'BISCUITS', 'subCategory': 'SWEET'},
            'pricing': dict({'now': now, 'was': was, 'promotionType': 'SPECIAL', 'onlineSpecial': False,
                             'comparable': '$1.00/ 100g'}, **pricing)}


# --- half price: only in the Half Price list ---
half = product(9628571, 3, 6, specialType='PERCENT_OFF', priceDescription='1/2 Price', saveAmount=3)
it = product_to_item(half)
check(it and it['discount_desc'] == '1/2 PRICE' and it['save_amount'] == 3, 'half price is read by the Half Price list')
check(special_to_item(half) is None, 'half price is never repeated by the All specials list')

# --- multi-buys: priced as the deal, like Woolworths ---
pick = product(1497888, 6, specialType='MULTI_SAVE', offerDescription='Pick any 2 for $9',
               multiBuyPromotion={'type': 'MultibuyMultiSku', 'minQuantity': 2, 'reward': 4.5})
it = special_to_item(pick)
check(it and (it['price'], it['was_price'], it['save_amount'], it['discount_desc'], it['price_display'])
      == (9.0, 12.0, 3.0, '2 for $9.00', '2 for $9.00'), f'"Pick any 2 for $9" is read: {it}')
check(it and not database.is_half_price(it['price'], it['was_price'], it['save_amount'], it['discount_desc']),
      'a multi-buy is not half price')
check(product_to_item(pick) is None, 'a multi-buy is not in the Half Price list')

buy = special_to_item(product(5191256, 4, specialType='MULTI_SAVE', offerDescription='Buy 2 for $7'))
check(buy and (buy['price'], buy['was_price']) == (7.0, 8.0), f'"Buy 2 for $7" is read: {buy}')

bogo = special_to_item(product(1998726, 30, specialType='MULTI_SAVE', offerDescription='Pick any 2 for $30'))
check(bogo and bogo['save_amount'] == 30 and not database.is_half_price(
    bogo['price'], bogo['was_price'], bogo['save_amount'], bogo['discount_desc']),
    'buy one get one free is kept, and is not half price')

check(special_to_item(product(1, 5, specialType='MULTI_SAVE', offerDescription='Pick any 2 for $10')) is None,
      'a "multi-buy" that saves nothing is skipped')

# --- price cuts ---
cut = special_to_item(product(2710131, 75, 86, saveAmount=11, saveStatement='save $11.00'))
check(cut and (cut['price'], cut['was_price'], cut['save_amount'], cut['discount_desc']) == (75.0, 86.0, 11.0, 'Save $11.00'),
      f'a price cut is read: {cut}')
off = special_to_item(product(1831040, 6, 10, specialType='PERCENT_OFF', priceDescription='40% Off'))
check(off and off['discount_desc'] == 'Save $4.00' and not database.is_half_price(
    off['price'], off['was_price'], off['save_amount'], off['discount_desc']), '40% off is a price cut, not half price')

# --- "SPECIAL" with no "was" price (mostly Coles fresh produce): kept at its price, no saving ---
plain = special_to_item(product(5111654, 0.98))
check(plain and (plain['price'], plain['was_price'], plain['save_amount'], plain['discount_desc'])
      == (0.98, 0, 0, SPECIAL_DESC), f'a "SPECIAL" with no "was" price is kept, marked Special: {plain}')
check(plain and not database.is_half_price(plain['price'], plain['was_price'], plain['save_amount'], plain['discount_desc']),
      'a "SPECIAL" with no "was" price is not half price')
check(plain and not _is_lasting(plain), 'a "SPECIAL" is this week only: not copied to next week')
check(special_to_item(product(6, 5, specialType='MULTI_SAVE', offerDescription='Buy 3 save 10%')) is None,
      'a multi-buy whose deal cannot be read is skipped, not shown as a plain special')
check(special_to_item(dict(product(7, 2), availability=False)) is None, 'an unavailable "SPECIAL" is skipped')

# --- not specials here ---
check(special_to_item(product(2, 6, 10, onlineSpecial=True)) is None, 'online-only special is skipped')
check(special_to_item(dict(product(3, 6, 10), availability=False)) is None, 'unavailable product is skipped')
check(special_to_item({'_type': 'SINGLE_TILE', 'id': 4}) is None, 'an advert tile is skipped')

# --- an interrupted read continues from the same page; a complete read starts over ---
pages = {1: [product(10, 6, 10), product(11, 3, 6)], 2: [product(12, 2, 4, onlineSpecial=True), pick]}
answers = []
coles_web._get = lambda url: answers.pop(0) if answers else None
sr = lambda n: {'noOfResults': 60, 'pageSize': 48, 'results': pages[n]}

mem = {'cursor': 1, 'pages': 0, 'items': {}}
answers[:] = [sr(1)]                                     # page 2 is refused (bot check)
read, added, start = coles_web._read_pages(mem, '{page}', special_to_item, 60)
check((read, added, start, mem['cursor'], mem['pages'], mem.get('last_full')) == (1, 1, 1, 2, 2, None),
      f'refused at page 2: remembered page 1, next update starts at page 2: {read, added, start, mem}')
answers[:] = [sr(2)]
read, added, start = coles_web._read_pages(mem, '{page}', special_to_item, 60)
check((read, added, start, mem['cursor'], mem['pages_done']) == (1, 1, 2, 1, 0) and mem.get('last_full'),
      f'every page read: list complete, next read starts at page 1: {mem}')
check(sorted(mem['items']) == ['10', '1497888'], f'only the price cut and the multi-buy are kept: {sorted(mem["items"])}')

# --- the database keeps a "SPECIAL" (like an everyday price) but still drops a product with no deal at all ---
work = tempfile.mkdtemp()
database.DB_DIR = os.path.join(work, 'data')             # where export_static_data.py reads it from
os.makedirs(database.DB_DIR)
database.DB_PATH = os.path.join(database.DB_DIR, 'specials.db')
database.init_db()
database.save_specials('Coles', [plain, dict(plain, id='8', title='Coles No Deal 1kg', discount_desc='')],
                       period='current', date_range='Wed 14 Oct 2026 - Tue 20 Oct 2026')
got = database.get_specials(period='current', store='Coles')
titles = [it['title'] for it in got.get('items', got.get('specials', []))]
check(titles == [plain['title']], f'the database keeps the "SPECIAL" and drops the product with no deal: {titles}')

# --- the catalogue line for the same deal lends its saving to the website "SPECIAL"s that replace it ---
salads = [dict(plain, id=f'9{n}', title=f'Coles Kitchen Classic {n} Salad 400g', price=5.0, price_display='$5.00',
               product_url=f'https://www.coles.com.au/product/{n}') for n in ('Coleslaw', 'Pasta')]
catalogue = dict(plain, id='99', title='Coles Kitchen Classic Coleslaw or Pasta Salad 400g', price=5.0,
                 price_display='$5.00', was_price=5.8, save_amount=0.8, discount_desc='Save $0.80',
                 product_url='https://www.salefinder.com.au/1/coles-kitchen-classic-salad/2/')
database.save_specials('Coles', salads + [catalogue], period='current', date_range='Wed 14 Oct 2026 - Tue 20 Oct 2026')
os.chdir(work)
with contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(os.path.join(ROOT, 'export_static_data.py'), run_name='__main__')
os.chdir(ROOT)
out = {it['title']: it for it in json.load(open(os.path.join(work, 'static', 'data', 'specials.json'), encoding='utf-8'))}
check(catalogue['title'] not in out and all((out.get(s_['title']) or {}).get('save_amount') == 0.8 for s_ in salads),
      f'the website "SPECIAL"s take the catalogue saving and the range line is not listed twice: '
      f'{[(t, i.get("save_amount")) for t, i in out.items()]}')

# --- what the All specials list hands over never repeats the Half Price list ---
coles_web.MEMORY_FILE = os.path.join(tempfile.mkdtemp(), 'coles_web.json')
coles_web._switching = lambda: False
twice = special_to_item(product(20, 6, 10))
coles_web._save_memory({'week': coles_web.coles_week_start(), 'cursor': 1, 'pages': 1, 'last_full': time.time(),
                        'items': {'20': dict(twice, discount_desc='1/2 PRICE')},   # in both lists (price changed)
                        'more': {'cursor': 1, 'pages': 1, 'last_full': time.time(),
                                 'items': {'20': twice, '10': mem['items']['10']}}})
got = [it['id'] for it in coles_web.scrape_coles_web_more()]
check(got == ['10'], f'a product in the Half Price list is not handed over again: {got}')

if bad:
    for b in bad:
        print('FAIL', b)
print(f"{total - len(bad)}/{total} Coles website checks passed")
sys.exit(1 if bad else 0)
