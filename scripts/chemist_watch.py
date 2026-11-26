"""
小黃屋: notice a new Chemist Warehouse catalogue within about 2 hours (instead of waiting up to 12 hours
for the next specials update on Thursday-Sunday).

Runs from .github/workflows/chemist_watch.yml every 2 hours. It does nothing (no request at all) while the
site already has a catalogue on now. Only between two catalogues it reads the catalogue list once
(1 small request to the same public file the specials update reads), and when a catalogue on now is
listed, it starts the specials update, which reads the catalogue and puts both sites online.

    python scripts/chemist_watch.py      (writes start=true|false to $GITHUB_OUTPUT)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from build_chemist import ended  # noqa: E402

STORE = 'Chemist Warehouse'


def site_has_catalogue(items, today=None):
    """Is a Chemist Warehouse catalogue on now (not ended) already saved?"""
    return any(it.get('store') == STORE and it.get('date_range') and not ended(it['date_range'], today)
               for it in items)


def decide(items, listed, today=None):
    """('start' | 'wait' | 'has', message). listed = the catalogue list read from Chemist Warehouse, or None
    when it was not read (then nothing is started)."""
    if site_has_catalogue(items, today):
        return 'has', '小黃屋 already has the catalogue on now - nothing to check'
    if listed is None:
        return 'wait', 'catalogue list not readable this time - checking again in 2 hours'
    from scrapers.chemist_scraper import pick_catalogues
    cur, _ = pick_catalogues(listed, today)
    if cur:
        return 'start', f"new catalogue on now: {cur[2].get('title')} ({cur[2].get('start')} - {cur[2].get('finish')})"
    return 'wait', 'no new catalogue yet (Chemist Warehouse shows "coming soon") - checking again in 2 hours'


def main():
    with open(os.path.join(ROOT, 'static', 'data', 'specials.json'), encoding='utf-8') as f:
        items = json.load(f)
    listed = None
    if not site_has_catalogue(items):
        import requests
        from scrapers.chemist_scraper import API, CLIENT_ID, HEADERS
        try:
            r = requests.get(f"{API}/client/{CLIENT_ID}/catalogues/json?_format=json", headers=HEADERS, timeout=40)
            data = r.json() if r.status_code == 200 else None
            listed = data if isinstance(data, list) else None
        except Exception as e:                      # never fail: the regular updates still read it
            print(f'::notice::catalogue list not read ({e})')
    state, msg = decide(items, listed)
    print(f'::notice::{msg}')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
            f.write(f"start={'true' if state == 'start' else 'false'}\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
