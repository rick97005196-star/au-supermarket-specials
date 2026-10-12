"""Checks for the everyday low prices (Coles "Every Day", Woolworths "Everyday Low Price"):
they are kept next to the specials, other non-discounted catalogue items are not.

    python tests/test_everyday.py
"""
import os
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scrapers.regions import is_everyday_price, everyday_desc, is_everyday, EVERYDAY_DESC  # noqa: E402
import database  # noqa: E402

bad = []
total = 0


def check(cond, msg):
    global total
    total += 1
    if not cond:
        bad.append(msg)


# --- the price wording on the catalogue pages (copied from SaleFinder) ---
check(is_everyday_price('Every Day $3.30 each $0.49 per 100g More Info'), 'Coles "Every Day"')
check(is_everyday_price('Everyday Low Price $4.50 pk 56 per ea More Info'), 'Woolworths "Everyday Low Price"')
check(not is_everyday_price('Was $4.50, Save $0.50 $4.00 each'), 'a real special is not everyday')
check(not is_everyday_price('$3.90 kg* More Info'), 'a plain price is not everyday')
check(not is_everyday_price('Everyday Market $5.00'), 'Everyday Market (online sellers) is not everyday')
check(everyday_desc('Selected stores only. Every Day $3.30 each') == EVERYDAY_DESC + ' (selected stores only)',
      'the "selected stores" note is kept')
check(everyday_desc('Every Day $2.20 each') == EVERYDAY_DESC, 'one description for every everyday item')
check(is_everyday({'discount_desc': EVERYDAY_DESC, 'save_amount': 0}), 'is_everyday')
check(not is_everyday({'discount_desc': EVERYDAY_DESC, 'save_amount': 1.0}), 'a discount wins over the everyday mark')

# --- saving: everyday items stay, other non-discounted items are still left out ---
tmp = tempfile.mkdtemp()
database.DB_DIR, database.DB_PATH = tmp, os.path.join(tmp, 'specials.db')
database.init_db()
items = [
    {'title': 'Coles Bakery Loaf 680g', 'price': 3.3, 'discount_desc': everyday_desc('Selected stores only.')},
    {'title': 'Coles Naan Bread 3 Pack 250g', 'price': 3.2, 'discount_desc': EVERYDAY_DESC},
    {'title': 'Spooky Plush', 'price': 9.0, 'discount_desc': ''},
    {'title': 'Helga\'s White Wraps 8 Pack 508g', 'price': 2.75, 'was_price': 5.5, 'discount_desc': '1/2 PRICE'},
]
database.save_specials('Coles', items, period='current', date_range='Wed 7 Oct 2026 - Tue 13 Oct 2026')
conn = sqlite3.connect(database.DB_PATH)
rows = {r[0]: r for r in conn.execute('SELECT title, popularity_score, is_popular FROM specials')}
conn.close()
check(set(rows) == {'Coles Bakery Loaf 680g', 'Coles Naan Bread 3 Pack 250g', "Helga's White Wraps 8 Pack 508g"},
      f'saved: {sorted(rows)}')
check(all(rows[t][1] == 0 and rows[t][2] == 0 for t in rows if 'Wraps' not in t), 'everyday items are never popular')

for b in bad:
    print('FAIL', b)
print(f'{total - len(bad)}/{total} everyday-price checks passed')
sys.exit(1 if bad else 0)
