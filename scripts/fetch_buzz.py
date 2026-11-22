"""
Saves this week's OzBargain deals for Coles, Woolworths and ALDI (votes, comments) to data/buzz.json,
for buzz.py (本週熱門 default order).

  * reads 4 public RSS feeds (each store's page and the Groceries category), one second apart, at most
    every 6 hours;
  * keeps the deals of the last 8 days (a supermarket week, plus the day-before previews); a deal seen before keeps its newest vote count, so deals that
    dropped off the feed still count until they are 7 days old;
  * if OzBargain cannot be reached, the last saved file is kept and the update carries on.

    python scripts/fetch_buzz.py [--force]
"""
import datetime
import email.utils
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'buzz.json')
# each store's page, plus the Groceries category (the store is then read from the title: "... @ Coles")
FEEDS = [('Coles', 'https://www.ozbargain.com.au/deals/coles.com.au/feed'),
         ('Woolworths', 'https://www.ozbargain.com.au/deals/woolworths.com.au/feed'),
         ('ALDI', 'https://www.ozbargain.com.au/deals/aldi.com.au/feed'),
         (None, 'https://www.ozbargain.com.au/cat/groceries/feed')]
STORES = ('Coles', 'Woolworths', 'ALDI')
WINDOW_DAYS = 8
REFRESH_HOURS = 6
OZB = '{https://www.ozbargain.com.au}'
UA = 'au-supermarket-specials/1.0 (weekly popularity of supermarket specials; reads public RSS)'


def note(msg):
    print(f"::notice::{msg}" if os.environ.get('GITHUB_ACTIONS') else msg)


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/rss+xml, application/xml'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def store_from_title(title):
    """'... $3 @ Coles' -> 'Coles' (only when exactly one of the three supermarkets is named after an @)."""
    found = {s for s in STORES for part in title.split('@')[1:] if re.search(rf'\b{s}\b', part, re.I)}
    return found.pop() if len(found) == 1 else None


def parse(xml_bytes, store):
    out = []
    for item in ET.fromstring(xml_bytes).iter('item'):
        link = (item.findtext('link') or '').strip()
        node = link.rstrip('/').rsplit('/', 1)[-1]
        meta = item.find(OZB + 'meta')
        if not node.isdigit() or meta is None:
            continue
        try:
            posted = email.utils.parsedate_to_datetime(item.findtext('pubDate')).astimezone(datetime.timezone.utc)
        except Exception:
            continue
        title = (item.findtext('title') or '').strip()
        st = store or store_from_title(title)
        if not st:
            continue
        out.append({'id': int(node), 'store': st, 'title': title,
                    'posted': posted.isoformat(timespec='seconds'),
                    'expiry': meta.get('expiry') or '',
                    'votes_pos': int(meta.get('votes-pos') or 0), 'votes_neg': int(meta.get('votes-neg') or 0),
                    'comments': int(meta.get('comment-count') or 0)})
    return out


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    old = {}
    try:
        with open(OUT, encoding='utf-8') as f:
            prev = json.load(f)
        age = now - datetime.datetime.fromisoformat(prev['fetched_at'])
        if age < datetime.timedelta(hours=REFRESH_HOURS) and '--force' not in sys.argv:
            print(f"this week's discussions downloaded {int(age.total_seconds() // 60)} min ago - kept")
            return 0
        old = {d['id']: d for d in prev.get('deals') or []}
    except Exception:
        pass
    cutoff = now - datetime.timedelta(days=WINDOW_DAYS)
    fresh, errors = {}, []
    for store, url in FEEDS:     # the feeds show the newest deals (about a week of supermarket deals each)
        try:
            for d in parse(fetch(url), store):
                fresh.setdefault(d['id'], d)
        except Exception as e:
            errors.append(f"{store or 'Groceries'}: {str(e)[:60]}")
        time.sleep(1)
    if not fresh:
        note(f"本週討論資料暫時無法下載（{'; '.join(errors)[:120]}），沿用上次的資料")
        return 0
    merged = {**old, **fresh}
    keep = sorted((d for d in merged.values() if datetime.datetime.fromisoformat(d['posted']) >= cutoff),
                  key=lambda d: d['id'], reverse=True)
    out = {'fetched_at': now.isoformat(timespec='seconds'), 'source': 'OzBargain', 'window_days': WINDOW_DAYS,
           'deals': keep}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
        f.write('\n')
    os.replace(tmp, OUT)
    per = {s: sum(1 for d in keep if d['store'] == s) for s in STORES}
    note(f"本週討論：{len(keep)} 則（Coles {per['Coles']}、Woolworths {per['Woolworths']}、ALDI {per['ALDI']}）"
         + (f"；部分讀取失敗：{'; '.join(errors)[:100]}" if errors else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
