"""Checks for the Coles recent regular prices (scrapers/coles_recent.py): the shelf price before a special, per item
for "2 for $6" deals; the latest special wins; products on special this week are not listed; old ones drop out.
No network.

    python tests/test_coles_recent.py
"""
import datetime
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import scrapers.coles_recent as cr  # noqa: E402

bad = []
total = 0


def check(cond, msg):
    global total
    total += 1
    if not cond:
        bad.append(msg)


def special(pid, title, price, was, desc, unit='', week='Wed 4 Nov 2026 - Tue 10 Nov 2026', **kw):
    return dict(store='Coles', title=title, price=price, was_price=was, discount_desc=desc, unit_price=unit,
                date_range=week, product_url=f'https://www.coles.com.au/product/x-{pid}', image_url=f'/{pid}.jpg',
                category='pantry', period='current', **kw)


# --- the shelf price a special tells ---
check(cr.regular_of(special(1, 'Twisties 140g', 1.9, 3.8, '1/2 PRICE', '$1.36/ 100g')) == (3.8, '$2.72/ 100g'),
      f"half price: the was price, unit price scaled: {cr.regular_of(special(1, 'Twisties 140g', 1.9, 3.8, '1/2 PRICE', '$1.36/ 100g'))}")
check(cr.regular_of(special(2, 'Red Onion 1kg', 6.0, 9.6, '2 for $6.00', '$4.80/ 1kg')) == (4.8, '$4.80/ 1kg'),
      '"2 for $6": was is for the 2, per item; its unit price is already the single item\'s')
check(cr.regular_of(special(3, 'Yoghurt', 9.0, 15.0, '3 for $9.00', '$2.00/ 100g')) == (5.0, '$2.00/ 100g'), '3 for')
check(cr.regular_of(special(4, 'Chips', 3.5, 5.0, 'Save $1.50')) == (5.0, ''), 'save: no unit price stays empty')
for why, it in [('no was price', special(5, 'A', 3.0, 0, 'Save $1')), ('was below the deal', special(6, 'B', 6.0, 5.0, '2 for $6.00')),
                ('absurd was', special(7, 'C', 1.0, 50.0, 'Save $49')), ('not Coles', dict(special(8, 'D', 1.0, 2.0, ''), store='Woolworths')),
                ('catalogue, no product number', dict(special(9, 'E', 1.0, 2.0, ''), product_url='https://www.salefinder.com.au/1/food'))]:
    check(cr.regular_of(it) is None, f'not used: {why}')
check(cr.week_of(special(1, 'A', 1, 2, ''), datetime.date(2026, 11, 19)) == '2026-11-04', 'week from the date range')
check(cr.week_of({'date_range': ''}, datetime.date(2026, 11, 19)) == '2026-11-19', 'no date range: today')

# --- remembering: the latest special wins, old ones drop out ---
today = datetime.date(2026, 11, 19)
mem = {}
cr.remember(mem, [special(10, 'Milk 2L', 3.0, 3.6, 'Save $0.60', week='Wed 4 Nov 2026 - Tue 10 Nov 2026')], today)
cr.remember(mem, [special(10, 'Milk 2L', 3.2, 3.8, 'Save $0.60', week='Wed 28 Oct 2026 - Tue 3 Nov 2026')], today)
check(mem['10'][1] == 3.6 and mem['10'][6] == '2026-11-04', f'an older special does not replace a newer one: {mem}')
cr.remember(mem, [special(10, 'Milk 2L', 3.4, 4.0, 'Save $0.60', week='Wed 11 Nov 2026 - Tue 17 Nov 2026')], today)
check(mem['10'][1] == 4.0 and mem['10'][6] == '2026-11-11', 'a newer special replaces it')
mem['99'] = ['Old', 2.0, '', '', 'https://www.coles.com.au/product/old-99', 'pantry', '2026-06-01']
cr.remember(mem, [], today)
check('99' not in mem, 'forgotten after 16 weeks')

# --- listing: not on special this week, seen in the last 12 weeks, today's rules for the department ---
mem = {'1': ['Twisties 140g', 3.8, '$2.71/ 100g', '/1.jpg', 'https://www.coles.com.au/product/t-1', 'snacks', '2026-11-04'],
       '2': ['Red Onion 1kg', 4.8, '$4.80/ 1kg', '/2.jpg', 'https://www.coles.com.au/product/r-2', 'produce', '2026-11-04'],
       '3': ['Ancient 1kg', 2.0, '', '', 'https://www.coles.com.au/product/a-3', 'pantry', '2026-08-01'],
       '4': ['Mumm Marlborough Brut Prestige 750mL', 30.0, '', '', 'https://www.coles.com.au/product/m-4', 'health_vitamins', '2026-11-04'],
       '5': ['Zqx Pink Fizz 750mL', 15.0, '', '', 'https://www.coles.com.au/product/z-5', 'liquor', '2026-11-04']}
rows = cr.recent_rows(mem, [special(2, 'Red Onion 1kg', 3.0, 4.8, 'Save $1.80')], today)
ids = [r[0] for r in rows]
check(ids == ['1', '4', '5'], f'on special this week or too old: not listed: {ids}')
check(rows[0] == ['1', 'Twisties 140g', 3.8, '$3.80', '$2.71/ 100g', '/1.jpg', 'https://www.coles.com.au/product/t-1', 'snacks', '2026-11-04'],
      f'row: {rows[0]}')
dep = {r[0]: r[7] for r in rows}
check(dep['4'] == 'liquor', f"today's rules fix an old department: {dep['4']}")
check(dep['5'] == 'liquor', f'no rule knows it: the saved department stands in for its aisle: {dep["5"]}')

# --- shelf prices the weekly reader got this week replace the remembered ones; last week's are not used ---
prog = {'started': '2026-11-19', 'rows': [['1', 'Twisties 140g', 4.2, '$4.20', '$3.00/ 100g', '/1.jpg', 'https://www.coles.com.au/product/t-1', 'snacks'],
                                          ['2', 'Red Onion 1kg', 5.0, '$5.00', '', '', 'https://www.coles.com.au/product/r-2', 'produce'],
                                          ['7', 'Bad', 0, '', '', '', '', 'pantry']]}
shelf = cr.shelf_rows(prog, today)
check(sorted(shelf) == ['1', '2'], f'shelf rows with a price: {sorted(shelf)}')
check(cr.shelf_rows(dict(prog, started='2026-11-05'), today) == {}, "last week's shelf prices are not used")
rows = cr.recent_rows(mem, [special(2, 'Red Onion 1kg', 3.0, 4.8, 'Save $1.80')], today, shelf)
got = {r[0]: (r[2], r[8]) for r in rows}
check(got.get('1') == (4.2, 'shelf') and '2' not in got and got.get('4') == (30.0, '2026-11-04'),
      f'shelf price replaces the remembered one, on special still left out: {got}')

# --- the 6-week shelf memory: this week's read is "shelf", an older one keeps its day; a newer special wins ---
row = lambda i, p: [i, f'P{i} 1kg', p, f'${p:.2f}', '', '', f'https://www.coles.com.au/product/p-{i}', 'pantry']
mem6 = {'items': {'1': row('1', 4.0) + ['2026-11-19'], '4': row('4', 28.0) + ['2026-10-29'],
                  '8': row('8', 9.0) + ['2026-10-29'], '9': row('9', 2.0) + ['2026-09-01']}}
sh = cr.shelf_rows({}, today, mem6)
check({k: v[8] for k, v in sh.items()} == {'1': 'shelf', '4': '2026-10-29', '8': '2026-10-29'},
      f'shelf memory: this week / older / too old: {sh}')
rows = cr.recent_rows(mem, [], today, sh)
got = {r[0]: (r[2], r[8]) for r in rows}
check(got.get('4') == (30.0, '2026-11-04') and got.get('8') == (9.0, '2026-10-29') and got.get('1') == (4.0, 'shelf'),
      f'a newer special wins over an older shelf price: {got}')

# --- a run: learns from specials.json, writes both files; no specials: nothing changes ---
tmp = tempfile.mkdtemp()
cr.SPECIALS, cr.MEMORY, cr.LIST, cr.PROGRESS, cr.SHELF = (os.path.join(tmp, f) for f in ('specials.json', 'mem.json', 'recent.json', 'progress.json', 'shelf.json'))
with open(cr.SPECIALS, 'w', encoding='utf-8') as f:
    json.dump([special(1, 'Twisties 140g', 1.9, 3.8, '1/2 PRICE', '$1.36/ 100g', week='Wed 18 Nov 2026 - Tue 24 Nov 2026')], f)
old = os.path.join(tmp, 'old.json')
with open(old, 'w', encoding='utf-8') as f:
    json.dump({'items': [special(2, 'Red Onion 1kg', 6.0, 9.6, '2 for $6.00', '$4.80/ 1kg')]}, f)
check(cr.main(['--seed', old], today) == 0, 'run')
with open(cr.LIST, encoding='utf-8') as f:
    out = json.load(f)
check(out['kind'] == 'recent' and out['store'] == 'Coles' and out['updated_at'] == '2026-11-19'
      and [r[0] for r in out['items']] == ['2'], f'list: {out}')
with open(cr.MEMORY, encoding='utf-8') as f:
    check(sorted(json.load(f)['items']) == ['1', '2'], 'both remembered')
os.remove(cr.SPECIALS)
before = open(cr.LIST, 'rb').read()
check(cr.main([], today) == 0 and open(cr.LIST, 'rb').read() == before, 'no specials.json: the saved list stays')

for b in bad:
    print('FAIL', b)
print(f'{total - len(bad)}/{total} Coles recent-price checks passed')
sys.exit(1 if bad else 0)
