"""One-off check (saves nothing): each department specials list's size, and 3 pages read with the real reader."""
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.woolies_scraper import WOOLIES_GROUPS, scrape_woolies_specials_group  # noqa: E402
import scrapers.polite as polite  # noqa: E402

t0 = time.time()
for slug, gid, name, kind in WOOLIES_GROUPS:
    if kind != 'cut':
        continue
    t = time.time()
    got = scrape_woolies_specials_group(slug, gid, name, kind, max_pages=3)
    print(f'{slug}: {len(got)} cuts in 3 pages, {time.time() - t:.0f}s, requests so far {polite._count}', flush=True)
print(f'done in {int(time.time() - t0)} s', flush=True)
