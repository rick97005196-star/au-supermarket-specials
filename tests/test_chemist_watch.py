"""Checks for scripts/chemist_watch.py: start the update only between catalogues, and only when a new one is on."""
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from chemist_watch import decide, site_has_catalogue  # noqa: E402

today = datetime.date(2026, 11, 26)
old = [{'store': 'Chemist Warehouse', 'date_range': 'Thu 12 Nov 2026 - Wed 25 Nov 2026'},
       {'store': 'Coles', 'date_range': 'Wed 25 Nov 2026 - Tue 1 Dec 2026'}]
on = old + [{'store': 'Chemist Warehouse', 'date_range': 'Thu 26 Nov 2026 - Wed 9 Dec 2026'}]
new_cat = [{'title': 'Christmas', 'start': '2026-11-26', 'finish': '2026-12-09', 'nid_1': '123'}]
later_cat = [{'title': 'Christmas', 'start': '2026-11-27', 'finish': '2026-12-10', 'nid_1': '123'}]

assert not site_has_catalogue(old, today)            # last catalogue ended, Coles does not count
assert site_has_catalogue(on, today)
assert decide(on, None, today)[0] == 'has'           # a catalogue is on: nothing read, nothing started
assert decide(old, [], today)[0] == 'wait'           # "coming soon": empty list
assert decide(old, None, today)[0] == 'wait'         # list not readable: never start blindly
assert decide(old, later_cat, today)[0] == 'wait'    # published but not started yet: the regular update saves it
assert decide(old, new_cat, today)[0] == 'start'     # new catalogue on now: start the update
assert decide(old, new_cat, datetime.date(2026, 12, 10))[0] == 'wait'   # that one ended too
print('chemist_watch: all checks passed')
