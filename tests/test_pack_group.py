"""Checks for pack_group.py (同款不同包裝: the same drink in any pack, at any store) and the group history.

    python tests/test_pack_group.py
"""
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pack_group as pg  # noqa: E402
import price_history as ph  # noqa: E402

bad = []


def check(cond, msg):
    if not cond:
        bad.append(msg)


def it(title, price, disp=None, store='Coles', cat='drinks', pid='1001'):
    url = {'Coles': f'https://www.coles.com.au/product/x-{pid}',
           'Woolworths': f'https://www.woolworths.com.au/shop/productdetails/{pid}/x'}[store]
    return {'title': title, 'price': price, 'price_display': disp or f'${price:.2f}', 'store': store,
            'category': cat, 'period': 'current', 'product_url': url}


single = it('Monster Energy Ultra Can 500mL', 3.25)
four = it('Monster Energy Ultra Cans 500mL x 4 pack', 8.75, store='Woolworths', pid='2002')
coles4 = it('Monster Energy Drink Ultra 4x500ml 2L', 23.0, '2 for $23.00', pid='3003')
check(pg.group_key(single) == pg.group_key(four) == pg.group_key(coles4) == 'monster|ultra|500|can|',
      f'single, 4-pack and 2-for-$23 4-packs are one group: {pg.group_key(single)} {pg.group_key(four)} {pg.group_key(coles4)}')
check(abs(pg.drink_unit(coles4)[1] - 2.875) < 1e-9, 'Coles 2 for $23 4-packs = $2.875 a can')
check(pg.group_key(it('Monster Energy Ultra Zero Can 500mL', 3)) != pg.group_key(single), 'Ultra Zero is another drink')
check(pg.group_key(it('Monster Energy Ultra Cans 250ml x 6', 10)) != pg.group_key(single), '250 mL cans are another group')
check(pg.group_key(it('Wild Turkey & Cola 101 Can 375ml 4 Pack', 32, cat='liquor'))
      != pg.group_key(it('Wild Turkey & Cola Cans 10x375mL', 52, cat='liquor')), 'Cola 101 is not Cola')
check(pg.group_key(it('Pepsi, Solo or Sunkist Soft Drink 10x375mL', 10)) == '', 'several products in one name: no group')

# --- group history: this week's best per can against the best seen before this week, any pack, any store ---
D = datetime.date
h = {'v': 1, 'items': {}}
d = D(2026, 11, 4)
while d <= D(2026, 11, 10):
    ph.record(h, [dict(coles4, price=17.5, price_display='2 for $17.50')], d)     # $2.1875 a can
    d += datetime.timedelta(days=1)
items = [single, four, coles4]
ph.apply_history(items, hist=h, day=D(2026, 11, 25), save_file=False)
g = four.get('pgh')
check(g and g[1] == 2.19 and g[2] == 2.19 and g[3] == 'Coles' and g[4] == 4 and g[6] == 0,
      f'this week $2.19 (Woolworths 4-pack) = the earlier $2.19 (Coles 4-pack): {g}')
check(single.get('pgh') == g and single.get('pg') == four.get('pg'), 'every card of the group gets the same line')
items = [dict(single), dict(coles4)]
ph.apply_history(items, hist=h, day=D(2026, 11, 25), save_file=False)
g = items[0].get('pgh')
check(g and g[1] == 2.88 and g[2] == 2.19 and g[6] == 1, f'without the Woolworths pack: dearer than before: {g}')

if bad:
    print('FAILED:\n- ' + '\n- '.join(bad))
    sys.exit(1)
print('pack_group: all checks passed')
