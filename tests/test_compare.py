# -*- coding: utf-8 -*-
"""Checks for the price comparison in static/compare.js: the unit price converter (per kg / litre / item)
and the "which supermarket is cheapest" pick, on hand-checked examples from the real data (Oct 2026).

    python tests/test_compare.py          -> exit code 1 and a list of problems if anything is off
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JS = r"""
const c = require(process.argv[1]);
const q = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const calls = q.calls.map(([fn, item]) => c[fn](item));
const vc = q.vc.map(([name, i]) => {
    const r = c.valueCompare(q.lists[name][i], q.lists[name]);
    return r && { verdict: r.verdict, diff: r.diff, lowest: r.lowest, basis: r.basis, mine: r.mine.value,
                  cheapest: r.cheapest.item.title, stores: r.rows.map(x => x.item.store) };
});
// a state's own price is a copy of the product with another price: it must get its own figure
const base = { title: 'Lodge Farms Barn Eggs 12 Pack 700g', price: 5.29, store: 'ALDI' };
c.cmpTypeOf(base);
const copy = Object.assign({}, base, { price: 7 });
c.cmpTypeOf(copy);
process.stdout.write(JSON.stringify({ calls, vc, copy: copy._cmpUp.value }));
"""

bad = []
total = 0


def check(cond, msg):
    global total
    total += 1
    if not cond:
        bad.append(msg)


def near(a, b, tol=0.005):
    return a is not None and abs(a - b) <= tol


EGGS = [
    {'store': 'ALDI', 'title': 'Lodge Farms Barn Eggs 12 Pack 700g', 'price': 5.29},           # 0  $7.56/kg
    {'store': 'Woolworths', 'title': 'Woolworths Cage Free Eggs 12 Pack 700g', 'price': 5.70, 'save_amount': 0.5},  # 1  $8.14/kg
    {'store': 'Woolworths', 'title': 'Woolworths Cage Free Eggs 18 Pack 900g', 'price': 8.00},  # 2  $8.89/kg
    {'store': 'Coles', 'title': 'Barossa Fresh Free Range Eggs 700g', 'price': 8.30},           # 3  free range: other kind
    {'store': 'ALDI', 'title': 'Lodge Farms Cage Eggs 12 Pack 700g', 'price': 5.00},            # 4  cage: other kind
    {'store': 'ALDI', 'title': 'Lodge Farms Barn Eggs 18 Pack 900g', 'price': 7.39},            # 5  $8.21/kg
    {'store': 'Coles', 'title': 'Coles Barn Eggs 12 Pack 700g', 'price': 4.00, 'period': 'next'},  # 6  next week: never mixed in
    {'store': 'Coles', 'title': 'Barossa Fresh Free Range Eggs 900g', 'price': 11.90},         # 7  free range, same store as 3
]
TABS = [
    {'store': 'ALDI', 'title': 'Power Force Dishwasher Tablets 46pk', 'price': 10.99, 'unit_price': '($0.24 per 1 each)'},  # 0
    {'store': 'Woolworths', 'title': 'Shine Dishwasher Tablets 30 Pack', 'price': 4.00, 'unit_price': '$0.13 / 1EA'},     # 1
    {'store': 'Coles', 'title': 'Finish Ultimate Dishwashing Tablets 46 Pack', 'price': 24.50},                           # 2  $0.53 from the title
    {'store': 'Coles', 'title': 'Finish Dishwasher Cleaner 250ml', 'price': 6.00},                                         # 3  not tablets
]

CALLS = [
    # 500 g and 1 kg at the same rate give the same price per kg; the shop's "$1.00 / 100G" says the same
    ('unitPriceOf', {'title': 'Rice 500g', 'price': 5.0}),
    ('unitPriceOf', {'title': 'Rice 1kg', 'price': 10.0}),
    ('unitPriceOf', {'title': 'Rice 1kg', 'price': 10.0, 'unit_price': '$1.00 / 100G'}),
    # 6 x 375 mL = 2.25 L
    ('unitPriceOf', {'title': 'Coca-Cola Classic Soft Drink Cans 6 x 375mL', 'price': 9.0}),
    # "2 for $12" is $6 each
    ('unitPriceOf', {'title': 'Olive Oil 1L', 'price': 7.0, 'price_display': '2 for $12.00'}),
    # sold per item: no per-kg price
    ('unitPriceOf', {'title': 'Fairy Dishwashing Tablets 46 Pack', 'price': 24.0, 'unit_price': '$0.52 / 1EA'}),
    # price per item
    ('eachPriceOf', {'title': 'Fairy Dishwashing Tablets', 'price': 24.0, 'unit_price': '$0.49/ 1ea'}),
    ('eachPriceOf', {'title': 'ALMAT Laundry Capsules 50 Pack', 'price': 11.99, 'unit_price': '($0.24 per 1 each)'}),
    ('eachPriceOf', {'title': 'Finish Ultimate Dishwashing Tablets 46 Pack', 'price': 24.50}),
    ('eachPriceOf', {'title': 'Earth Choice Dishwasher Tablets Pk 80', 'price': 20.0}),
    ('eachPriceOf', {'title': 'Omo Laundry Capsules 28 Washes 28 Pack', 'price': 14.0}),
    ('eachPriceOf', {'title': 'Omo Laundry Liquid 2 Litre or Capsules 28 Pack', 'price': 20.0}),    # a choice: no count
    ('eachPriceOf', {'title': 'Laundry Capsules 50 Pack', 'price': 11.99, 'unit_price': '$0.80 / 1EA'}),  # disagree: nothing
    # the kind of product
    ('cmpTypeOf', EGGS[0]),
    ('cmpTypeOf', EGGS[3]),
    ('cmpTypeOf', EGGS[4]),
    ('cmpTypeOf', {'title': 'Praise Whole Egg Mayonnaise with Eggs 400g', 'price': 4.0}),
    ('cmpTypeOf', {'title': 'Cadbury Mini Eggs 200g', 'price': 6.0}),
    ('cmpTypeOf', TABS[3]),
]

res = subprocess.run(['node', '-e', JS, os.path.join(ROOT, 'static', 'compare.js')],
                     input=json.dumps({'calls': CALLS, 'lists': {'eggs': EGGS, 'tabs': TABS},
                                       'vc': [['eggs', 0], ['eggs', 1], ['eggs', 3], ['eggs', 6],
                                              ['tabs', 0], ['tabs', 1], ['tabs', 3]]}),
                     capture_output=True, text=True, encoding='utf-8')
if res.returncode != 0:
    print(res.stderr)
    sys.exit(1)
out = json.loads(res.stdout)
r = [x and x.get('value') if isinstance(x, dict) else x for x in out['calls']]

check(near(r[0], 10.0) and near(r[1], 10.0) and near(r[2], 10.0), f'500 g vs 1 kg per kg: {r[0:3]}')
check(near(r[3], 4.0) and out['calls'][3]['basis'] == 'L', f'6 x 375 mL -> $4.00/L: {out["calls"][3]}')
check(near(r[4], 6.0), f'2 for $12 -> $6/L: {r[4]}')
check(r[5] is None, f'per-item product has no per-kg price: {r[5]}')
check(near(r[6], 0.49) and out['calls'][6]['basis'] == 'ea', f'"$0.49/ 1ea": {out["calls"][6]}')
check(near(r[7], 0.24), f'"($0.24 per 1 each)": {r[7]}')
check(near(r[8], 24.50 / 46), f'"46 Pack" from the title: {r[8]}')
check(near(r[9], 0.25), f'"Pk 80": {r[9]}')
check(near(r[10], 0.5), f'"28 Washes 28 Pack" is one count: {r[10]}')
check(r[11] is None, f'"Liquid ... or Capsules 28 Pack" has no single count: {r[11]}')
check(r[12] is None, f'shop figure and pack count disagree -> nothing: {r[12]}')
check(out['calls'][13] == 'eggs||B', f'barn eggs: {out["calls"][13]}')
check(out['calls'][14] == 'eggs|R|', f'free range eggs: {out["calls"][14]}')
check(out['calls'][15] == 'eggs||C', f'cage eggs: {out["calls"][15]}')
check(out['calls'][16] is None, f'mayonnaise is not eggs: {out["calls"][16]}')
check(out['calls'][17] is None, f'chocolate eggs are not eggs: {out["calls"][17]}')
check(out['calls'][18] is None, f'dishwasher cleaner is not tablets: {out["calls"][18]}')
check(near(out['copy'], 10.0), f"a state's own price gets its own figure: {out['copy']}")

aldi_barn, wool_cf, fr, nxt, aldi_tabs, wool_tabs, cleaner = out['vc']
# ALDI barn 700g $7.56/kg vs Woolworths cage free 700g $8.14/kg (Coles free range is another kind)
check(aldi_barn and aldi_barn['verdict'] == 'cheaper' and near(aldi_barn['diff'], 0.59) and aldi_barn['lowest']
      and aldi_barn['stores'] == ['Woolworths'] and '700g' in aldi_barn['cheapest'], f'ALDI barn eggs: {aldi_barn}')
check(wool_cf and wool_cf['verdict'] == 'dearer' and not wool_cf['lowest'] and wool_cf['stores'] == ['ALDI']
      and wool_cf['cheapest'] == EGGS[0]['title'], f'Woolworths cage free eggs: {wool_cf}')
check(fr is None, f'free range eggs: only Coles has them -> nothing to compare: {fr}')
check(nxt is None, f'next week is never compared with this week: {nxt}')
# dishwasher tablets per item: Woolworths $0.13 < ALDI $0.24 < Coles $0.53
check(aldi_tabs and aldi_tabs['verdict'] == 'dearer' and aldi_tabs['stores'] == ['Woolworths', 'Coles']
      and near(aldi_tabs['diff'], 0.11) and aldi_tabs['basis'] == 'ea' and not aldi_tabs['lowest'], f'ALDI tablets: {aldi_tabs}')
check(wool_tabs and wool_tabs['verdict'] == 'cheaper' and wool_tabs['lowest'], f'Woolworths tablets: {wool_tabs}')
check(cleaner is None, f'dishwasher cleaner: {cleaner}')

for b in bad:
    print('FAIL', b)
print(f'{total - len(bad)}/{total} price comparison checks passed')
sys.exit(1 if bad else 0)
