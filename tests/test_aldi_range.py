"""A read that stops part-way through ALDI's everyday range keeps the saved everyday prices it did not
reach; a full read, or one where the deals failed too, keeps nothing (the save guard then decides).

    python tests/test_aldi_range.py     (needs requests and beautifulsoup4: the updater imports the readers)
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import database  # noqa: E402
from scrapers.regions import EVERYDAY_DESC  # noqa: E402
from scrapers.updater import _aldi_range_kept  # noqa: E402

bad = []
total = 0


def check(cond, msg):
    global total
    total += 1
    if not cond:
        bad.append(msg)


tmp = tempfile.mkdtemp()
database.DB_DIR, database.DB_PATH = tmp, os.path.join(tmp, 'specials.db')
database.init_db()
everyday = [{'title': f'Product {i} 500g', 'price': 2.0 + i, 'discount_desc': EVERYDAY_DESC} for i in range(30)]
deals = [{'title': f'Deal {i}', 'price': 9.99, 'discount_desc': 'Super Savers'} for i in range(5)]
database.save_specials('ALDI', everyday + deals, period='current', date_range='Super Savers & Special Buys (10/14 - 10/20)')

check(_aldi_range_kept(everyday + deals) == [], 'a full read keeps nothing')
part = _aldi_range_kept(everyday[:10] + deals)
check(sorted(it['title'] for it in part) == sorted(it['title'] for it in everyday[10:]),
      f'a part-way read keeps the 20 it did not reach, kept {len(part)}')
check(all(it['discount_desc'] == EVERYDAY_DESC and it['price'] > 0 for it in part), 'kept items stay everyday prices')
check(_aldi_range_kept(everyday[:10] + deals[:1]) == [], 'deals failed too: keeps nothing, the save guard decides')

for b in bad:
    print('FAIL', b)
print(f'{total - len(bad)}/{total} ALDI everyday range checks passed')
sys.exit(1 if bad else 0)
