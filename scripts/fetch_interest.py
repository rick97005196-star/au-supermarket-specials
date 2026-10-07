"""
Downloads the anonymous visitor interest (/api/popular) to data/interest.json for interest.py.

  * at most every 6 hours (the order does not need to change more often, and the repository
    does not get a new data file on every half-hourly update);
  * if the website cannot be reached, the last saved file is kept and the update carries on.

    python scripts/fetch_interest.py
"""
import datetime
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'interest.json')
URL = os.environ.get('INTEREST_URL', 'https://au-supermarket-specials.pages.dev/api/popular')
REFRESH_HOURS = 6


def note(msg):
    print(f"::notice::{msg}" if os.environ.get('GITHUB_ACTIONS') else msg)


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        with open(OUT, encoding='utf-8') as f:
            old = json.load(f)
        age = now - datetime.datetime.fromisoformat(old['fetched_at'])
        if age < datetime.timedelta(hours=REFRESH_HOURS) and '--force' not in sys.argv:
            print(f"visitor interest downloaded {int(age.total_seconds() // 60)} min ago - kept")
            return 0
    except Exception:
        pass
    try:
        req = urllib.request.Request(URL, headers={'User-Agent': 'au-specials-update', 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        if not data.get('ok') or not isinstance(data.get('items'), dict):
            raise ValueError(data.get('error') or 'unexpected answer')
        items = {str(k): float(v) for k, v in data['items'].items() if isinstance(v, (int, float)) and v > 0}
    except Exception as e:
        note(f"訪客興趣資料暫時無法下載（{str(e)[:80]}），沿用上次的資料")
        return 0
    out = {'fetched_at': now.isoformat(timespec='seconds'), 'weeks': data.get('weeks') or [],
           'total': float(data.get('total') or sum(items.values())), 'items': dict(sorted(items.items()))}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=0, sort_keys=False)
        f.write('\n')
    os.replace(tmp, OUT)
    note(f"訪客興趣資料：{len(items)} 件商品，累計 {out['total']:.0f} 次（近期加權）")
    return 0


if __name__ == '__main__':
    sys.exit(main())
