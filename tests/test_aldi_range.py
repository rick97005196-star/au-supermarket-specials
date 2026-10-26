"""A read that stops part-way through ALDI's range (Lower Prices = everyday low prices, the aisles = regular prices)
keeps the saved range prices it did not reach, each with its own label; a full read, or one where the deals failed
too, keeps nothing (the save guard then decides).

    python tests/test_aldi_range.py     (needs requests and beautifulsoup4: the updater imports the readers)
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import database  # noqa: E402
from scrapers.regions import EVERYDAY_DESC, REGULAR_DESC, is_everyday, is_regular  # noqa: E402
from scrapers.updater import _aldi_range_kept  # noqa: E402

bad = []
total = 0


def check(cond, msg):
    global total
    total += 1
    if not cond:
        bad.append(msg)


check(is_regular({'discount_desc': REGULAR_DESC, 'save_amount': 0}), 'is_regular')
check(not is_regular({'discount_desc': REGULAR_DESC, 'save_amount': 1.0}), 'a discount wins over the regular mark')
check(not is_regular({'discount_desc': EVERYDAY_DESC}) and not is_everyday({'discount_desc': REGULAR_DESC}),
      'everyday and regular prices never mix')

tmp = tempfile.mkdtemp()
database.DB_DIR, database.DB_PATH = tmp, os.path.join(tmp, 'specials.db')
database.init_db()
in_range = [{'title': f'Product {i} 500g', 'price': 2.0 + i, 'discount_desc': EVERYDAY_DESC if i % 3 == 0 else REGULAR_DESC}
            for i in range(30)]
label = {it['title']: it['discount_desc'] for it in in_range}
deals = [{'title': f'Deal {i}', 'price': 9.99, 'discount_desc': 'Super Savers'} for i in range(5)]
database.save_specials('ALDI', in_range + deals, period='current', date_range='Super Savers & Special Buys (10/14 - 10/20)')

check(_aldi_range_kept(in_range + deals) == [], 'a full read keeps nothing')
part = _aldi_range_kept(in_range[:10] + deals)
check(sorted(it['title'] for it in part) == sorted(it['title'] for it in in_range[10:]),
      f'a part-way read keeps the 20 it did not reach, kept {len(part)}')
check(all(it['discount_desc'] == label[it['title']] and it['price'] > 0 for it in part),
      'kept items keep their own label (everyday or regular)')
check({it['discount_desc'] for it in part} == {EVERYDAY_DESC, REGULAR_DESC}, 'both kinds are kept')
check(_aldi_range_kept(in_range[:10] + deals[:1]) == [], 'deals failed too: keeps nothing, the save guard decides')

# Other stores' regular prices are saved too (they have no discount, like everyday low prices)
database.save_specials('Coles', [{'title': 'Coles Milk 2L', 'price': 3.1, 'discount_desc': REGULAR_DESC}],
                       period='current', date_range='10/14 - 10/20')
conn = database.get_db()
n = conn.execute("SELECT COUNT(*) FROM specials WHERE store = 'Coles' AND discount_desc = ?", (REGULAR_DESC,)).fetchone()[0]
conn.close()
check(n == 1, f'a Coles regular price is saved, found {n}')

for b in bad:
    print('FAIL', b)
print(f'{total - len(bad)}/{total} ALDI range checks passed')
sys.exit(1 if bad else 0)
