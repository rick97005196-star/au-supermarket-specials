"""Checks for the weekly Woolworths regular prices (scrapers/woolies_regular.py + scripts/regular_match.cjs):
which Woolworths products count as plain in-store prices, which of them the price compare keeps, and how a week's
department pages are read in parts.
No network: the Woolworths answers are made up here.

    python tests/test_regular.py
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
import scrapers.woolies_regular as wr  # noqa: E402

bad = []
total = 0


def check(cond, msg):
    global total
    total += 1
    if not cond:
        bad.append(msg)


# --- a new week starts on Wednesday (2026-10-21 is a Wednesday) ---
d = datetime.date
check(wr.is_fresh('2026-10-21', d(2026, 10, 21)), 'read this Wednesday: fresh')
check(wr.is_fresh('2026-10-21', d(2026, 10, 27)), 'still fresh on the next Tuesday')
check(not wr.is_fresh('2026-10-20', d(2026, 10, 21)), 'read on Tuesday: stale from Wednesday')
check(not wr.is_fresh('2026-10-21', d(2026, 10, 28)), 'stale a week later')
check(not wr.is_fresh(None, d(2026, 10, 21)) and not wr.is_fresh('soon', d(2026, 10, 21)), 'no date: stale')

# --- which products are plain in-store prices ---
base = {'Stockcode': 123, 'Name': "Arnott's Shapes Pizza", 'PackageSize': '190g', 'InstorePrice': 3.5,
        'InstoreWasPrice': 3.5, 'CupPrice': 1.84, 'CupMeasure': '100G', 'MediumImageFile': 'https://x/m.jpg'}
it = wr.to_item(base)
check(it and it['id'] == 'w123' and it['title'] == "Arnott's Shapes Pizza 190g" and it['price'] == 3.5, f'item: {it}')
check(it and it['price_display'] == '$3.50 ea' and it['unit_price'] == '$1.84 / 100G', 'price wording')
check(it and it['save_amount'] == 0 and it['was_price'] == 0 and it['image_url'] == 'https://x/m.jpg', 'no saving')
check(it and it['product_url'] == 'https://www.woolworths.com.au/shop/productdetails/123/arnott-s-shapes-pizza', 'link')
check(wr.to_item(dict(base, Name="Arnott's Shapes Pizza 190g"))['title'] == "Arnott's Shapes Pizza 190g",
      'size not repeated when the name has it')
loose = wr.to_item(dict(base, Name='Bananas', PackageSize='per kg', InstorePrice=4.0, CupPrice=4.0, CupMeasure='1KG'))
check(loose and loose['price_display'] == '$4.00 kg', 'sold by the kilo')
for why, change in [('on special', {'InstoreIsOnSpecial': True}), ('was price above price', {'InstoreWasPrice': 5}),
                    ('online only', {'IsOnlineOnly': True}), ('marketplace seller', {'IsMarketProduct': True}),
                    ('third-party seller', {'ThirdPartyProductInfo': {'x': 1}}),
                    ('not in the reference store', {'InstorePrice': None}), ('no price', {'InstorePrice': 0}),
                    ('no stock code', {'Stockcode': None})]:
    check(wr.to_item(dict(base, **change)) is None, f'skipped: {why}')

# --- which regular prices the price compare keeps (the website's own rules) ---
def item(i, store, title, price, **kw):
    return dict({'id': i, 'store': store, 'title': title, 'price': price, 'price_display': f'${price:.2f} ea',
                 'save_amount': 0.5, 'was_price': price + 0.5, 'period': 'current'}, **kw)


week = [
    item('w1', 'Woolworths', 'Arnotts Tim Tam Original 200g', 3.5),   # Woolworths sells Arnott's
    item('c1', 'Coles', 'Arnotts Shapes Pizza 190g', 3.0),             # to look up
    item('a1', 'ALDI', 'ARNOTTS Shapes Pizza 190g', 2.9),              # to look up
    item('c2', 'Coles', 'Arnotts Tim Tam Original 200g', 3.6),         # Woolworths special already there
    item('c3', 'Coles', 'Pringles Original 134g', 3.0),                # no Woolworths special of this brand
    item('a2', 'ALDI', 'ARNOTTS FARM Cookies 200g', 2.0),              # an ALDI brand, not Arnott's
    item('c4', 'Coles', 'Arnotts Jatz Original 225g', 2.5, period='next'),   # next week
]
tmp = tempfile.mkdtemp()
wr.SPECIALS = os.path.join(tmp, 'specials.json')
with open(wr.SPECIALS, 'w', encoding='utf-8') as f:
    json.dump(week, f)
targets = wr.match('targets')
check(sorted(t['id'] for t in targets) == ['a1', 'c1'], f'looked up: {targets}')

cands = [wr.to_item(base),                                                   # same product: kept
         wr.to_item(dict(base, Stockcode=124, PackageSize='380g', InstorePrice=6.0)),   # other size
         wr.to_item(dict(base, Stockcode=125, Name="Arnott's Tim Tam Original", PackageSize='200g', InstorePrice=6.0)),
         wr.to_item(dict(base, Stockcode=126, Name="Arnott's Shapes Pizza Party Pack", InstorePrice=3.6))]
kept = wr.match('keep', cands)
check([k['id'] for k in kept] == ['w123'], f'kept: {[k["id"] for k in kept]}')

# --- one week read in parts: each run goes on where the last one stopped; the lists are written only when every
# department is read, and a run that read nothing changes no file ---
class Found:
    status_code = 200

    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class Broken:                                            # a block page instead of JSON
    status_code = 200

    def json(self):
        raise ValueError('not JSON')


def page(total, *products):
    return Found({'Bundles': [{'Products': list(products)}], 'TotalRecordCount': total})


def answers(*seq):
    seq = list(seq)
    return lambda site, send: seq.pop(0) if seq else None


def saved(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def raw(path):
    with open(path, 'rb') as f:
        return f.read()


def files():
    return [raw(p) if os.path.exists(p) else None for p in (wr.LIST, wr.OUT, wr.PROGRESS)]


sys.modules['curl_cffi'] = types.SimpleNamespace(requests=types.SimpleNamespace(Session=lambda **k: None))
wr.OUT = os.path.join(tmp, 'regular.json')
wr.LIST = os.path.join(tmp, 'regular-woolworths.json')
wr.PROGRESS = os.path.join(tmp, 'regular_progress.json')
wr.FOOD = ['Fruit & Veg', 'Bakery']
wr.MIN_ROWS = 1
with open(wr.OUT, 'w', encoding='utf-8') as f:
    json.dump({'updated_at': '2026-10-14', 'items': [{'id': 'w9'}]}, f)
last_week = raw(wr.OUT)
today = wr._brisbane_today().isoformat()
DEPS = Found({'Categories': [{'NodeId': '1', 'UrlFriendlyName': 'fruit-veg', 'Description': 'Fruit & Veg'},
                             {'NodeId': '2', 'UrlFriendlyName': 'bakery', 'Description': 'Bakery'},
                             {'NodeId': '3', 'UrlFriendlyName': 'specials', 'Description': 'Specials'}]})
bread = dict(base, Stockcode=200, Name='Wonder White Bread', PackageSize='700g', InstorePrice=3.8)
special = dict(base, Stockcode=201, InstoreIsOnSpecial=True)
# polite() answers in order: the home page, the department list, then one answer per page

wr.polite = answers(Found({}), DEPS, page(40, base, special), None)     # page 1 of 2, then a refusal
check(wr.main() == 1, 'a refused run fails')
prog = saved(wr.PROGRESS)
check(prog['dep'] == 'Fruit & Veg' and prog['page'] == 2 and [r[0] for r in prog['rows']] == ['w123']
      and prog['started'] == today and not prog['done'], f'where it stopped is remembered: {prog}')
check(not os.path.exists(wr.LIST) and raw(wr.OUT) == last_week, "a part-read week keeps last week's lists")

for why, seq in [('no department list', (Found({}), None)), ('the first page refused', (Found({}), DEPS, None)),
                 ('a block page', (Found({}), DEPS, Broken()))]:
    before = files()
    wr.polite = answers(*seq)
    check(wr.main() == 1 and files() == before, f'read nothing, changed nothing: {why}')

wr.polite = answers(Found({}), DEPS, page(40, bread), page(1, base))     # page 2, then Bakery (w123 again)
check(wr.main() == 0, 'the run that finishes the week succeeds')
lst, out = saved(wr.LIST), saved(wr.OUT)
check([r[0] for r in lst['items']] == ['w123', 'w200'] and lst['updated_at'] == today and lst['store'] == 'Woolworths',
      f'every regular price listed once: {lst}')
check(all(len(r) == len(wr.ROW) and isinstance(r[wr.ROW.index('category')], str) for r in lst['items']), 'row shape')
check([it['id'] for it in out['items']] == ['w123'] and out['updated_at'] == today,
      f'the price compare keeps only matched prices, under today: {out}')
check(saved(wr.PROGRESS) == {'started': today, 'done': True}, 'the finished week is remembered without its rows')

wr.polite = answers()
check(wr.main() == 0, 'week already read: nothing to do, no request')

with open(wr.PROGRESS, 'w', encoding='utf-8') as f:     # last week's, finished
    json.dump({'started': '2026-10-14', 'done': True}, f)
wr.time = types.SimpleNamespace(monotonic=iter([0, 0, 10 ** 6]).__next__)   # time is up after one page
wr.polite = answers(Found({}), DEPS, page(40, base))
check(wr.main() == 0, 'a run that stops at its time limit succeeds')
prog = saved(wr.PROGRESS)
check(prog['started'] == today and not prog['done'] and prog['dep'] == 'Fruit & Veg' and prog['page'] == 2
      and [r[0] for r in prog['rows']] == ['w123'], f'a new week starts over: {prog}')
wr.time = time

wr.MIN_ROWS = 10
before = files()
wr.polite = answers(Found({}), DEPS, page(40, bread), page(1))
check(wr.main() == 1 and files() == before, "too few prices for a whole week: last week's lists stay")

for b in bad:
    print('FAIL', b)
print(f'{total - len(bad)}/{total} regular-price checks passed')
sys.exit(1 if bad else 0)
