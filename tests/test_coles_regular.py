"""Checks for the weekly Coles regular prices (scrapers/coles_regular.py): which Coles products count as plain
shelf prices, and how a week's category pages are read in parts, Thursday to Sunday only.
No network: the Coles answers are made up here.

    python tests/test_coles_regular.py
"""
import datetime
import json
import os
import sys
import tempfile
import time
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.modules['curl_cffi'] = types.SimpleNamespace(requests=types.SimpleNamespace(Session=lambda **k: None))
import scrapers.coles_regular as cr  # noqa: E402
import scrapers.woolies_regular as wr  # noqa: E402

bad = []
total = 0


def check(cond, msg):
    global total
    total += 1
    if not cond:
        bad.append(msg)


# --- which products are plain shelf prices ---
base = {'_type': 'PRODUCT', 'id': 123, 'brand': 'Nutella', 'name': 'Hazelnut Spread', 'size': '220g',
        'availability': True, 'pricing': {'now': 5.6, 'was': 0, 'comparable': '$2.55 per 100g'},
        'imageUris': [{'uri': '/1/123.jpg'}], 'merchandiseHeir': {'category': 'PANTRY', 'subCategory': 'SPREADS'}}


def priced(**pr):
    return dict(base, pricing=dict(base['pricing'], **pr))


it = cr.to_item(base)
check(it and it['id'] == '123' and it['store'] == 'Coles' and it['title'] == 'Nutella Hazelnut Spread 220g'
      and it['price'] == 5.6, f'item: {it}')
check(it and it['price_display'] == '$5.60' and it['unit_price'] == '$2.55 per 100g', 'price wording')
check(it and it['was_price'] == 0 and it['save_amount'] == 0 and it['discount_desc'] == 'Regular Price', 'no saving')
check(it and it['product_url'].startswith('https://www.coles.com.au/product/') and it['product_url'].endswith('-123'),
      'link')
check(cr.to_item(priced(was=5.6)) is not None, 'was price equal to price: still regular')
for why, p in [('on special', priced(promotionType='SPECIAL')), ('was price above price', priced(was=7)),
               ('special type', priced(specialType='DOWN_DOWN')), ('offer wording', priced(offerDescription='2 for $9')),
               ('online-only special', priced(onlineSpecial=True)), ('no price', priced(now=0)),
               ('not in stock', dict(base, availability=False)), ('not a product', dict(base, _type='SINGLE_TILE'))]:
    check(cr.to_item(p) is None, f'skipped: {why}')

# --- one week read in parts, Thursday to Sunday: each run goes on where the last one stopped; the list is written
# only when every category is read, and a run that read nothing changes no file ---
calls = []


def answers(*seq):
    seq = list(seq)
    calls.clear()
    cr._get = lambda url: (calls.append(url), seq.pop(0) if seq else None)[1]


def page(total, *products):
    return {'results': list(products), 'noOfResults': total, 'pageSize': 48}


def saved(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def raw(path):
    with open(path, 'rb') as f:
        return f.read()


def files():
    return [raw(p) if os.path.exists(p) else None for p in (cr.LIST, cr.PROGRESS)]


def on(day):
    cr._brisbane_today = lambda: day


tmp = tempfile.mkdtemp()
cr.LIST = os.path.join(tmp, 'regular-coles.json')
cr.PROGRESS = os.path.join(tmp, 'coles_regular_progress.json')
cr.FOOD = ['bakery', 'pantry']
cr.MIN_ROWS = 1
bread = dict(base, id=200, brand='Coles', name='White Bread', size='700g', pricing={'now': 2.6})
special = priced(promotionType='SPECIAL', was=7)
browse = 'https://www.coles.com.au/browse/{}?page={}'.format

on(datetime.date(2026, 10, 26))                                         # a Monday
answers(page(1, base))
check(cr.main() == 0 and calls == [] and files() == [None, None], 'Monday to Wednesday: no request, no file')

on(datetime.date(2026, 10, 22))                                         # a Thursday
answers(page(60, base, special), None)                                  # page 1 of 2, then a refusal
check(cr.main() == 1, 'a refused run fails')
prog = saved(cr.PROGRESS)
check(calls == [browse('bakery', 1), browse('bakery', 2)], f'pages asked: {calls}')
check(prog['dep'] == 'bakery' and prog['page'] == 2 and [r[0] for r in prog['rows']] == ['123']
      and prog['started'] == '2026-10-22' and not prog['done'], f'where it stopped is remembered: {prog}')
check(not os.path.exists(cr.LIST), "a part-read week keeps last week's list")

before = files()
answers(None)
check(cr.main() == 1 and files() == before, 'read nothing, changed nothing')

answers(page(60, bread), page(1, base))                                 # page 2, then pantry (123 again)
check(cr.main() == 0, 'the run that finishes the week succeeds')
check(calls == [browse('bakery', 2), browse('pantry', 1)], f'goes on where it stopped: {calls}')
lst = saved(cr.LIST)
check([r[0] for r in lst['items']] == ['123', '200'] and lst['updated_at'] == '2026-10-22' and lst['store'] == 'Coles',
      f'every regular price listed once: {lst}')
check(all(len(r) == len(cr.ROW) and isinstance(r[cr.ROW.index('category')], str) for r in lst['items']), 'row shape')
check(saved(cr.PROGRESS) == {'started': '2026-10-22', 'done': True}, 'the finished week is remembered without its rows')

answers()
check(cr.main() == 0 and calls == [], 'week already read: nothing to do, no request')

on(datetime.date(2026, 10, 29))                                         # next Thursday: a new week
wr.time = types.SimpleNamespace(monotonic=iter([0, 0, 10 ** 6]).__next__)   # time is up after one page
answers(page(60, base))
check(cr.main() == 0, 'a run that stops at its time limit succeeds')
prog = saved(cr.PROGRESS)
check(prog['started'] == '2026-10-29' and not prog['done'] and prog['dep'] == 'bakery' and prog['page'] == 2
      and [r[0] for r in prog['rows']] == ['123'], f'a new week starts over: {prog}')
wr.time = time

cr.MIN_ROWS = 10
before = files()
answers(page(60, bread), page(1))
check(cr.main() == 1 and files() == before, "too few prices for a whole week: last week's list stays")

for b in bad:
    print('FAIL', b)
print(f'{total - len(bad)}/{total} Coles regular-price checks passed')
sys.exit(1 if bad else 0)
