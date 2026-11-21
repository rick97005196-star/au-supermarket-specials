"""One-off check (saves nothing): would any product on Woolworths' ONLINE-ONLY specials lists get past the
in-store filters of the specials reader? And which flags do the department price cuts carry?"""
import collections
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.polite import request as polite  # noqa: E402
from scrapers.woolies_scraper import _woolies_tag_text, _cut_offer  # noqa: E402
from curl_cffi import requests  # noqa: E402

s = requests.Session(impersonate='chrome')
polite('woolworths', lambda: s.get('https://www.woolworths.com.au/', timeout=30))


def page(cid, path, n):
    body = {'categoryId': cid, 'pageNumber': n, 'pageSize': 36, 'sortType': 'TraderRelevance', 'url': path,
            'location': path, 'formatObject': '{"name":"x"}', 'isSpecial': True, 'isBundle': False, 'isMobile': False,
            'filters': [], 'token': '', 'gpBoost': 0, 'isHideUnavailableProducts': False,
            'isRegisteredRewardCardPromotion': False, 'enableAdReRanking': False, 'groupEdmVariants': False,
            'categoryVersion': 'v2', 'flags': {'EnableProductBoostExperiment': False}}
    r = polite('woolworths', lambda: s.post('https://www.woolworths.com.au/apis/ui/browse/category', json=body, timeout=30))
    return [] if r is None or r.status_code != 200 else [p for b in r.json().get('Bundles') or [] for p in b.get('Products') or []]


def passes(pr):   # the same in-store filters as scrape_woolies_specials_group + kind 'cut'
    if pr.get('IsOnlineOnly') is True or pr.get('IsMarketProduct') is True or pr.get('ThirdPartyProductInfo'):
        return False
    if pr.get('InstorePrice') is None:
        return False
    return bool(_cut_offer(pr.get('InstorePrice'), pr.get('InstoreWasPrice'), _woolies_tag_text(pr)))


FLAGS = ('IsOnlineOnly', 'IsMarketProduct', 'IsOnSpecial', 'InstoreIsOnSpecial', 'IsInStoreOnly', 'IsEdrSpecial')
for dep, nid in [('pantry', '1_39FD49C'), ('dairy-eggs-fridge', '1_6E4F4E4'), ('snacks-confectionery', '1_717445A'),
                 ('drinks', '1_5AF3A0A'), ('freezer', '1_ACA2FC2')]:
    path = f'/shop/browse/specials/online-only-specials/{dep}'
    seen, leaked = 0, []
    for n in range(1, 6):
        prods = page(f'specialsgroup.onlineonly.{nid}', path, n)
        if not prods:
            break
        seen += len(prods)
        leaked += [p for p in prods if passes(p)]
    print(f'ONLINE-ONLY {dep}: {seen} read, {len(leaked)} would pass our filter', flush=True)
    for p in leaked[:6]:
        print('   LEAK', p.get('Stockcode'), p.get('Name'), 'instore', p.get('InstorePrice'), p.get('InstoreWasPrice'),
              'online', p.get('Price'), p.get('WasPrice'), {k: p.get(k) for k in FLAGS}, flush=True)
    prods = page(f'{nid}_SPECIALS', f'/shop/browse/{dep}/{dep}-specials', 1) + page(f'{nid}_SPECIALS', f'/shop/browse/{dep}/{dep}-specials', 2)
    took = [p for p in prods if passes(p)]
    c = collections.Counter(tuple((k, p.get(k)) for k in FLAGS) for p in took)
    print(f'DEPT {dep}: took {len(took)} of {len(prods)}; flags: {dict(c)}', flush=True)
    diff = [p for p in took if (p.get('Price'), p.get('WasPrice')) != (p.get('InstorePrice'), p.get('InstoreWasPrice'))]
    print(f'   online and in-store prices differ on {len(diff)}', [(p.get('Name'), p.get('InstorePrice'), p.get('Price')) for p in diff[:4]], flush=True)
