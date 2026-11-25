"""Checks for price_history.py (60 天最低價: the lowest price of the last 60 days).

    python tests/test_price_history.py
"""
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import price_history as ph  # noqa: E402

bad = []


def check(cond, msg):
    if not cond:
        bad.append(msg)


D = datetime.date
ph.STORE_SINCE = {'Coles': '2026-09-01', 'ALDI': '2026-09-01', 'Woolworths': '2026-11-22'}


def coles(price, disp=None, pid='1234', period='current', title='Coles Test Biscuits 200g'):
    return {'store': 'Coles', 'title': title, 'price': price, 'price_display': disp or f'${price:.2f}',
            'period': period, 'product_url': f'https://www.coles.com.au/product/test-biscuits-200g-{pid}'}


def days(start, end):
    d = start
    while d <= end:
        yield d
        d += datetime.timedelta(days=1)


# --- keys and per-item prices ---
check(ph.product_key(coles(1)) == 'Coles|c1234', 'Coles product number is the key')
check(ph.product_key({'store': 'Woolworths', 'title': 'x', 'product_url': 'https://www.woolworths.com.au/shop/productdetails/55/x'}) == 'Woolworths|w55', 'Woolworths number')
check(ph.product_key({'store': 'Coles', 'title': 'Tim Tam’s  Original 200g', 'product_url': 'https://www.salefinder.com.au/1/x/2/'}) == "Coles|t:tim tam s original 200g", 'catalogue link: the name')
check(ph.each_price(coles(9, '3 for $9.00')) == (3.0, '', True), '3 for $9 = $3 each')
check(ph.each_price(coles(12, '$12.00 kg')) == (12.0, 'kg', False), 'per kg')

# --- cheaper before: lowest and the last day at that price ---
h = {'v': 1, 'items': {}}
for d in days(D(2026, 10, 7), D(2026, 10, 13)):
    ph.record(h, [coles(3, '2 for $6.00')], d)              # $3 each
for d in days(D(2026, 11, 4), D(2026, 11, 10)):
    ph.record(h, [coles(4.5)], d)
today = D(2026, 11, 25)
items = [coles(4.0)]
ph.apply_history(items, hist=h, day=today, save_file=False)
check(items[0].get('ph') == [60, 3.0, '2026-10-13', 1, 1], f'was $3 each (2 for $6) on 13 Oct: {items[0].get("ph")}')

# --- this week is the lowest ---
items = [coles(2.5)]
ph.apply_history(items, hist=h, day=today, save_file=False)
check(items[0].get('ph') == [60, 2.5, '', 0], f'this week is the lowest: {items[0].get("ph")}')

# --- the same price every day: an everyday price ---
h2 = {'v': 1, 'items': {}}
for d in days(D(2026, 9, 26), D(2026, 11, 24)):
    if d.weekday() != 1:                                     # a Tuesday missing now and then is fine
        ph.record(h2, [coles(5.0)], d)
items = [coles(5.0)]
ph.apply_history(items, hist=h2, day=today, save_file=False)
check(items[0].get('ph') == [60, 5.0, '', 2], f'same price all along: {items[0].get("ph")}')

# --- never seen before this week: nothing ---
items = [coles(5.0, pid='9999')]
ph.apply_history(items, hist={'v': 1, 'items': {}}, day=today, save_file=False)
check('ph' not in items[0], 'a new product says nothing')

# --- a store whose list is complete only for a few days: nothing yet; then "近 N 天" ---
w = {'store': 'Woolworths', 'title': 'W', 'price': 2.0, 'price_display': '$2.00', 'period': 'current',
     'product_url': 'https://www.woolworths.com.au/shop/productdetails/7/w'}
hw = {'v': 1, 'items': {}}
for d in days(D(2026, 11, 1), D(2026, 11, 24)):
    ph.record(hw, [dict(w, price=1.0, price_display='$1.00')], d)
items = [dict(w)]
ph.apply_history(items, hist=hw, day=today, save_file=False)
check('ph' not in items[0], 'Woolworths complete only since 22 Nov: too short on 25 Nov')
items = [dict(w)]
ph.apply_history(items, hist=hw, day=D(2026, 12, 10), save_file=False)
check(items[0].get('ph', [0])[0] == 19, f'近 19 天 on 10 Dec: {items[0].get("ph")}')

# --- next week never counts; a different unit is not compared ---
h3 = {'v': 1, 'items': {}}
for d in days(D(2026, 11, 1), D(2026, 11, 10)):
    ph.record(h3, [coles(1.0, period='next'), coles(1.0, '$1.00 kg', pid='5555')], d)
check('Coles|c1234' not in h3['items'], 'next week is not recorded')
items = [coles(9.0, '$9.00 each', pid='5555')]
ph.apply_history(items, hist=h3, day=today, save_file=False)
check('ph' not in items[0], 'per kg is not compared with each')

# --- a second update the same day replaces that day's price; old runs are dropped ---
h4 = {'v': 1, 'items': {}}
ph.record(h4, [coles(2.0)], D(2026, 11, 20))
ph.record(h4, [coles(2.0)], D(2026, 11, 21))
ph.record(h4, [coles(9.9)], D(2026, 11, 21))
check(h4['items']['Coles|c1234'] == [['2026-11-20', '2026-11-20', 2.0, ''], ['2026-11-21', '2026-11-21', 9.9, '']],
      f'same-day correction: {h4["items"]}')
ph.record(h4, [coles(2.0, pid='7777')], D(2027, 2, 5))
check('Coles|c1234' not in h4['items'], 'older than 70 days is forgotten')

if bad:
    print('FAILED:\n- ' + '\n- '.join(bad))
    sys.exit(1)
print('price_history: all checks passed')
