"""Checks for scrapers/chemist_scraper.py: Chemist Warehouse (小黃屋) catalogue -> only exact, in-store savings."""
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from scrapers.chemist_scraper import saving_of, items_from_regions, pick_catalogues, date_range_text  # noqa: E402
from item_rules import problems  # noqa: E402
from check_data import range_end  # noqa: E402
from categories import classify_for_store  # noqa: E402

# the catalogue's saving text -> (saving, description)
assert saving_of(55.99, '$32.00 OFF RRP') == (32.0, 'Save $32.00 off RRP')
assert saving_of(34.99, '$38.00 OFF RRP\n\nBETTER THAN 1/2 PRICE OFF RRP') == (38.0, 'Save $38.00 off RRP (1/2 price)')
assert saving_of(57.99, '$5.00 OFF EDLP') == (5.0, 'Save $5.00 off everyday price')
assert saving_of(14.74, '1/2 PRICE OFF RRP') == (14.74, 'Save $14.74 off RRP (1/2 price)')
assert saving_of(29.99, '') == (0.0, '')                                   # no saving printed
assert saving_of(13.99, '40% OFF RRP') == (0.0, '')                        # no exact amount
assert saving_of(18.99, 'UP TO 1/2 PRICE OFF RRP') == (0.0, '')            # "up to": not this product's saving
assert saving_of(27.99, 'UP TO $64.00 OFF RRP\n\nBETTER THAN 1/2 PRICE OFF RRP') == (0.0, '')
assert saving_of(36.99, 'AFTER $7 CASHBACK $29.99 ea') == (0.0, '')        # cashback is not the shop price

regions = json.load(open(os.path.join(ROOT, 'tests', 'fixtures', 'cw_regions.json')))
items, skipped = items_from_regions(regions)
titles = {it['title'] for it in items}
assert any(t.startswith('Blackmores Glucosamine') for t in titles)
assert not any('Assorted' in t for t in titles)                            # a whole range at one price
assert 'Bioglan Sleep 200 Tablets' not in titles                           # no saving printed
assert skipped.get('no exact saving printed') and skipped.get('a whole range, not one product')

# every product passes the site's own per-product rules (逐筆防呆)
rng = date_range_text(datetime.date(2026, 11, 12), datetime.date(2026, 11, 25))
assert rng == 'Thu 12 Nov 2026 - Wed 25 Nov 2026'
for it in items:
    full = dict(it, store='Chemist Warehouse', period='current', date_range=rng)
    assert problems(full, datetime.date(2026, 11, 24), range_end) == [], (it['title'], problems(full, datetime.date(2026, 11, 24), range_end))
    assert it['product_url'].startswith('https://www.chemistwarehouse.com.au/buy/')
# ...and an ended catalogue is caught
old = dict(items[0], store='Chemist Warehouse', period='current', date_range=rng)
assert problems(old, datetime.date(2026, 11, 28), range_end)

# which catalogue is on now / next, by its own dates
cats = [{'start': '2026-11-12T00:00', 'finish': '2026-11-25T23:59', 'nid_1': '1'},
        {'start': '2026-11-26T00:00', 'finish': '2026-12-09T23:59', 'nid_1': '2'}]
cur, nxt = pick_catalogues(cats, datetime.date(2026, 11, 24))
assert cur[2]['nid_1'] == '1' and nxt[2]['nid_1'] == '2'
cur, nxt = pick_catalogues(cats, datetime.date(2026, 11, 26))
assert cur[2]['nid_1'] == '2' and nxt is None
cur, nxt = pick_catalogues(cats[:1], datetime.date(2026, 11, 27))
assert cur is None and nxt is None

# a pharmacy: everything is 美妝保健 (the supermarket rules read "Grape" chewables as fruit)
assert classify_for_store('Chemist Warehouse', "Claratyne Children's 5mg Grape 50 Chewable Tablets") == 'health_vitamins'
assert classify_for_store('Chemist Warehouse', 'Wagner Milk Thistle One A Day 50000mg 60 Capsules') == 'health_vitamins'
assert classify_for_store('Coles', 'Coles Full Cream Milk 2L') == classify_for_store('Woolworths', 'Coles Full Cream Milk 2L')

print('test_chemist: OK', len(items), 'items', skipped)
