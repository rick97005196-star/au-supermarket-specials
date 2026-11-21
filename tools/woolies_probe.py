"""One-off check (saves nothing): read every department's price cuts with the real reader, count and time them."""
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.woolies_scraper import WOOLIES_GROUPS, scrape_woolies_specials_group  # noqa: E402

t0, n = time.time(), 0
for slug, gid, name, kind in WOOLIES_GROUPS:
    if kind != 'cut':
        continue
    got = scrape_woolies_specials_group(slug, gid, name, kind)
    n += len(got)
    for it in list(got)[:2]:
        print('   ', it['title'], it['price'], it['was_price'], it['discount_desc'], it['category'])
print(f'TOTAL price cuts: {n} in {int(time.time() - t0)} s')
