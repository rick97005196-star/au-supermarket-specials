"""One-off: rebuild data/price_history.json from the site's own past data in git (static/data/specials.json,
the last version of each Brisbane day). Run from the repository root: python tools/backfill_price_history.py"""
import datetime, json, os, subprocess, sys
sys.path.insert(0, os.getcwd())
import price_history as ph

log = subprocess.run(['git', 'log', '--format=%H %ct', '--', 'static/data/specials.json'],
                     capture_output=True, text=True, check=True).stdout.split('\n')
last = {}
for line in log:
    if not line.strip():
        continue
    h, ts = line.split()
    day = (datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc) + datetime.timedelta(hours=10)).date()
    last.setdefault(day, h)                          # git log is newest first: the day's last version
today = ph.brisbane_today()
start = today - datetime.timedelta(days=ph.KEEP_DAYS)
hist = {'v': 1, 'items': {}}
for day in sorted(last):
    if day < start or day >= today:
        continue
    raw = subprocess.run(['git', 'show', f'{last[day]}:static/data/specials.json'], capture_output=True, check=True).stdout
    items = json.loads(raw)
    if isinstance(items, dict):
        items = items.get('items') or []
    n = ph.record(hist, items, day)
    print(day, n)
ph.save(hist)
print('products', len(hist['items']), 'runs', sum(len(v) for v in hist['items'].values()))
