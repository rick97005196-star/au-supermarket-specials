"""Checks for the weekly Woolworths regular prices (scrapers/woolies_regular.py + scripts/regular_match.cjs):
which Coles / ALDI products are looked up, which Woolworths prices are kept, and which search results are skipped.
No network: the Woolworths answers are made up here.

    python tests/test_regular.py
"""
import datetime
import json
import os
import sys
import tempfile
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

check(wr.search_term("Arnott's Shapes | Pizza (190g)") == "Arnott's Shapes Pizza 190g", 'search words')

# --- which search results are plain in-store prices ---
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

# --- which products are looked up, and which regular prices are kept (the website's own rules) ---
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

# --- Woolworths refusing: last week's file stays as it was and the run fails; --if-stale skips a fresh file ---
sys.modules['curl_cffi'] = types.SimpleNamespace(requests=types.SimpleNamespace(Session=lambda **k: None))
wr.polite = lambda site, send: None
wr.OUT = os.path.join(tmp, 'regular.json')
old = json.dumps({'updated_at': '2026-10-14', 'items': [{'id': 'w9'}]})
with open(wr.OUT, 'w', encoding='utf-8') as f:
    f.write(old)
sys.argv = ['woolies_regular.py']
check(wr.main() == 1, 'a refused run fails')
with open(wr.OUT, encoding='utf-8') as f:
    check(f.read() == old, "a refused run keeps last week's file")
with open(wr.OUT, 'w', encoding='utf-8') as f:
    json.dump({'updated_at': wr._brisbane_today().isoformat(), 'items': []}, f)
sys.argv = ['woolies_regular.py', '--if-stale']
check(wr.main() == 0, '--if-stale: nothing to do when already read this week')

for b in bad:
    print('FAIL', b)
print(f'{total - len(bad)}/{total} regular-price checks passed')
sys.exit(1 if bad else 0)
