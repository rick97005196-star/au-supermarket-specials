"""One-off check (no data saved, nothing published): which Woolworths specials lists hold the in-store
"Save $X" price cuts that the specials update does not read yet. About 10 polite requests."""
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.polite import request as polite          # noqa: E402
from scrapers.woolies_scraper import _woolies_tag_text, _MULTI_TAG  # noqa: E402
from curl_cffi import requests                          # noqa: E402

s = requests.Session(impersonate='chrome')
polite('woolworths', lambda: s.get('https://www.woolworths.com.au/', timeout=30))
r = polite('woolworths', lambda: s.get('https://www.woolworths.com.au/apis/ui/PiesCategoriesWithSpecials', timeout=30))
print('categories:', None if r is None else r.status_code)
nodes = []


def walk(cs, path=''):
    for c in cs or []:
        name = f"{path}/{c.get('UrlFriendlyName') or c.get('Description')}"
        if 'special' in json.dumps({k: c.get(k) for k in ('NodeId', 'UrlFriendlyName', 'Description')}).lower():
            nodes.append((c.get('NodeId'), name, c.get('ProductCount')))
        walk(c.get('Children'), name)


if r is not None and r.status_code == 200:
    walk(r.json().get('Categories'))
for n in nodes:
    print('  ', n)


def page(cid, slug, n):
    body = {'categoryId': cid, 'pageNumber': n, 'pageSize': 36, 'sortType': 'TraderRelevance',
            'url': f'/shop/browse/{slug}', 'location': f'/shop/browse/{slug}', 'formatObject': '{"name":"x"}',
            'isSpecial': True, 'isBundle': False, 'isMobile': False, 'filters': [], 'token': '', 'gpBoost': 0,
            'isHideUnavailableProducts': False, 'isRegisteredRewardCardPromotion': False, 'enableAdReRanking': False,
            'groupEdmVariants': False, 'categoryVersion': 'v2', 'flags': {'EnableProductBoostExperiment': False}}
    return polite('woolworths', lambda: s.post('https://www.woolworths.com.au/apis/ui/browse/category', json=body, timeout=30))


wanted = [n for n in nodes if n[1].rstrip('/').endswith('/specials')][:1] + \
         [n for n in nodes if 'pantry-specials' in n[1]][:1]
for cid, name, _ in wanted:
    kinds, total = {}, 0
    for n in (1, 2, 3):
        r = page(cid, name.strip('/'), n)
        if r is None or r.status_code != 200:
            print(name, 'stopped', None if r is None else r.status_code)
            break
        d = r.json()
        total = d.get('TotalRecordCount')
        for b in d.get('Bundles') or []:
            for pr in b.get('Products') or []:
                if pr.get('IsOnlineOnly') or pr.get('IsMarketProduct'):
                    k = 'online/market'
                else:
                    p, w = float(pr.get('InstorePrice') or 0), float(pr.get('InstoreWasPrice') or 0)
                    tag = _woolies_tag_text(pr)
                    k = ('multi' if _MULTI_TAG.search(tag) else 'half' if w and p <= w * 0.55 else
                         'cut (Save $X)' if w > p else 'other: ' + re.sub(r'\s+', ' ', tag)[:40])
                kinds[k] = kinds.get(k, 0) + 1
    print(f'{name} id={cid} total={total} first pages:', json.dumps(kinds, ensure_ascii=False))
