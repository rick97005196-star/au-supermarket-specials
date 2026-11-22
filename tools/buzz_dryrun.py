"""Prints which specials this week's OzBargain deals match (check by eye). python tools/buzz_dryrun.py"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from buzz import load_deals, matches, deal_score, MAX_MATCHES, apply_buzz
items = json.load(open(os.path.join(ROOT, 'static', 'data', 'specials.json'), encoding='utf-8'))
deals = load_deals()
print(f"{len(deals)} usable deals")
for d in sorted(deals, key=deal_score, reverse=True):
    found = [it for it in items if it.get('store') == d['store'] and (it.get('price') or 0) > 0 and matches(it, d)]
    flag = ' (TOO MANY - skipped)' if len(found) > MAX_MATCHES else ''
    print(f"\n[{deal_score(d):>4}] {d['store']}: {d['title']}  -> {len(found)}{flag}")
    for it in found[:15]:
        print(f"        {it['period']:7} ${it['price']:<6} {it['title']}")
print('\nmatched items:', apply_buzz(items, deals))
