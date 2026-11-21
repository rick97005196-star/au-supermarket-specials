# -*- coding: utf-8 -*-
"""
Spot check (抽查): compare a random sample of the specials on the site with the supermarkets'
own product pages, one product at a time, politely (scrapers/polite.py: slow pace, and we stop
asking a site the moment it refuses us - no bot-check workarounds).

  python scripts/spot_check.py [per_store]      (default 40 per supermarket)

Writes data/spot_check.json and a short summary for the GitHub run page. Exit code 1 (the run is
marked failed -> the owner gets an email) when too many checked products do not match.

A product "matches" when the supermarket's page shows the same price (and, when it shows one, the
same "was" price). Products the page could not be read for are counted separately as "unchecked":
they are neither right nor wrong.
"""
import datetime as dt
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scrapers.polite import request as polite, summary as polite_summary, mark_blocked  # noqa: E402

DATA = os.path.join(ROOT, 'static', 'data')
REPORT = os.path.join(ROOT, 'data', 'spot_check.json')
MISMATCH_ALERT = 0.10       # more than 10% of the checked products wrong -> email the owner
TOL = 0.011                 # cents rounding

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-AU,en;q=0.9',
}


def session():
    try:
        from curl_cffi import requests as cr
        return cr.Session(impersonate='chrome')
    except Exception:
        import requests
        s = requests.Session()
        s.headers.update(HEADERS)
        return s


def num(x):
    try:
        return round(float(x), 2)
    except Exception:
        return None


# ---------------- Woolworths: the product's own page data ----------------
def woolies(items, s, log):
    polite('woolworths', lambda: s.get('https://www.woolworths.com.au/', timeout=20))
    out = []
    for it in items:
        m = re.search(r'/productdetails/(\d+)', it.get('product_url') or '')
        if not m:
            continue
        r = polite('woolworths', lambda: s.get(f'https://www.woolworths.com.au/apis/ui/product/detail/{m.group(1)}', timeout=20))
        if r is None or r.status_code != 200:
            out.append(dict(it=it, status='unchecked', why=f"HTTP {getattr(r, 'status_code', 'none')}"))
            continue
        try:
            p = (r.json() or {}).get('Product') or {}
        except Exception:
            out.append(dict(it=it, status='unchecked', why='unreadable'))
            continue
        if len(log) < 2:
            log.append({k: p.get(k) for k in ('Name', 'Price', 'WasPrice', 'InstorePrice', 'InstoreWasPrice', 'IsOnSpecial',
                                               'InstoreIsOnSpecial', 'IsOnlineOnly', 'IsMarketProduct', 'CupString')})
        now = num(p.get('InstorePrice'))
        was = num(p.get('InstoreWasPrice'))
        if now is None:
            out.append(dict(it=it, status='unchecked', why='no in-store price on the page'))
            continue
        out.append(compare(it, now, was, extra={'instore_special': p.get('InstoreIsOnSpecial'),
                                                'online_only': p.get('IsOnlineOnly') or p.get('IsMarketProduct')}))
    return out


# ---------------- Coles: the product page (polite, stops when refused) ----------------
NEXT = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def coles(items, s, log):
    out = []
    for it in items:
        url = it.get('product_url') or ''
        if 'coles.com.au/product/' not in url:
            continue
        r = polite('coles', lambda: s.get(url, timeout=25))
        if r is not None and 'Pardon Our Interruption' in (r.text or '')[:5000]:
            mark_blocked('coles', 'bot check page')     # Coles asked us to stop: no more Coles pages this run
        if r is None or r.status_code != 200 or 'Pardon Our Interruption' in (r.text or '')[:5000]:
            out.append(dict(it=it, status='unchecked', why='Coles 網站暫停讀取（禮貌停止，不繞過）'))
            continue
        m = NEXT.search(r.text)
        try:
            prod = json.loads(m.group(1))['props']['pageProps']['product']
            pr = prod.get('pricing') or {}
        except Exception:
            out.append(dict(it=it, status='unchecked', why='no product data on the page'))
            continue
        if len(log) < 2:
            log.append({'name': prod.get('name'), 'pricing': pr})
        now, was = num(pr.get('now')), num(pr.get('was'))
        if not now:
            out.append(dict(it=it, status='unchecked', why='no price (unavailable?)'))
            continue
        multi = re.search(r'(\d+)\s*for\s*\$\s*(\d+(?:\.\d{1,2})?)', pr.get('offerDescription') or '', re.I)
        extra = {'online_special': pr.get('onlineSpecial')}
        if re.search(r'\d+\s*for\s*\$', it.get('price_display') or '', re.I) and multi:
            n, deal = int(multi.group(1)), float(multi.group(2))
            out.append(compare(it, deal, round(n * now, 2), extra=extra))
        else:
            out.append(compare(it, now, was, extra=extra))
    return out


# ---------------- ALDI: the product page ----------------
def aldi(items, s, log):
    import requests
    out = []
    for it in items:
        url = it.get('product_url') or ''
        if 'aldi.com.au/product' not in url:
            continue
        r = polite('aldi', lambda: requests.get(url, headers=HEADERS, timeout=20))
        if r is None or r.status_code != 200:
            out.append(dict(it=it, status='unchecked', why=f"HTTP {getattr(r, 'status_code', 'none')}"))
            continue
        html = r.text
        price = None
        for blk in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S):
            mm = re.search(r'"price"\s*:\s*"?(\d+(?:\.\d+)?)', blk)
            if mm:
                price = num(mm.group(1))
                break
        if price is None:
            mm = re.search(r'base-price__regular[^>]*>\s*<span[^>]*>\s*\$(\d+(?:\.\d{2})?)', html)
            price = num(mm.group(1)) if mm else None
        if len(log) < 2:
            log.append({'url': url, 'price': price})
        if price is None:
            out.append(dict(it=it, status='unchecked', why='no price on the page'))
            continue
        out.append(compare(it, price, None))
    return out


def compare(it, now, was, extra=None):
    """now/was = the supermarket's own single-item price and its "was" price (was == now: no "was" shown)."""
    site_now, site_was = num(it.get('price')), num(it.get('was_price')) or 0
    wrong, notes = [], []
    multi = re.search(r'(\d+)\s*for\s*\$\s*(\d+(?:\.\d{1,2})?)', it.get('price_display') or '', re.I)
    if multi and abs(site_now - now) > TOL:
        # "2 for $14": the site keeps the deal price; its "was" is 2 x the normal single price
        n = int(multi.group(1))
        single = was if was and was > now else now
        if site_was and abs(site_was - n * single) > TOL:
            wrong.append(f"多件優惠原價 網站 ${site_was} / 官網 {n} × ${single}")
        if site_now >= n * now - TOL:
            wrong.append(f"多件優惠 ${site_now} 沒有比官網 {n} 件 ${round(n * now, 2)} 便宜")
    else:
        if abs(now - site_now) > TOL:
            wrong.append(f"價格 網站 ${site_now} / 官網 ${now}")
        if was and was > now + TOL and site_was and abs(was - site_was) > TOL:
            wrong.append(f"原價 網站 ${site_was} / 官網 ${was}")
    if extra and extra.get('online_only'):
        wrong.append('官網標示只限網路')
    if extra and extra.get('online_special'):
        wrong.append('官網標示網路限定特價')
    if extra and extra.get('instore_special') is False and site_was:
        notes.append('官網沒有標「特價」（多為 Lower Shelf Price 長期降價或多件優惠）')
    return dict(it=it, status='wrong' if wrong else 'ok', why='；'.join(wrong + notes), now=now, was=was)


def main():
    per = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    items = json.load(open(os.path.join(DATA, 'specials.json'), encoding='utf-8'))
    items = [i for i in items if i.get('period') == 'current']
    rnd = random.Random(dt.date.today().isoformat())
    picks = {}
    for store, key in (('Woolworths', 'woolworths.com.au/shop/productdetails'), ('Coles', 'coles.com.au/product/'),
                       ('ALDI', 'aldi.com.au/product')):
        pool = [i for i in items if i.get('store') == store and key in (i.get('product_url') or '')]
        picks[store] = rnd.sample(pool, min(per, len(pool)))
    s = session()
    logs = {'Woolworths': [], 'Coles': [], 'ALDI': []}
    res = {
        'Woolworths': woolies(picks['Woolworths'], s, logs['Woolworths']),
        'ALDI': aldi(picks['ALDI'], s, logs['ALDI']),
        'Coles': coles(picks['Coles'], s, logs['Coles']),
    }
    print('sample of what the supermarkets answered:', json.dumps(logs, ensure_ascii=False)[:3000])
    report = {'checked_at': dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z', 'stores': {}}
    tot_ok = tot_wrong = 0
    lines = []
    for store, rows in res.items():
        ok = sum(r['status'] == 'ok' for r in rows)
        wrong = [r for r in rows if r['status'] == 'wrong']
        unchecked = [r for r in rows if r['status'] == 'unchecked']
        tot_ok += ok
        tot_wrong += len(wrong)
        report['stores'][store] = {
            'ok': ok, 'wrong': len(wrong), 'unchecked': len(unchecked),
            'wrong_items': [{'title': r['it']['title'], 'url': r['it']['product_url'], 'why': r['why']} for r in wrong],
            'unchecked_reasons': sorted({r['why'] for r in unchecked}),
        }
        lines.append(f"{store}: 抽查 {len(rows)} 件，正確 {ok}、不符 {len(wrong)}、讀不到 {len(unchecked)}")
        for r in wrong:
            lines.append(f"   ✗ {r['it']['title'][:60]} — {r['why']}  {r['it']['product_url']}")
    print('\n'.join(lines))
    print('requests made / refused:', polite_summary())
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    step = os.environ.get('GITHUB_STEP_SUMMARY')
    if step:
        with open(step, 'a', encoding='utf-8') as f:
            f.write('## 超市資料抽查（和超市官網逐筆比對）\n\n' + '\n'.join(f'- {l}' if not l.startswith('   ') else f'  - {l.strip()}' for l in lines) + '\n')
    checked = tot_ok + tot_wrong
    if checked and tot_wrong / checked > MISMATCH_ALERT:
        print(f"::error::抽查不符比例 {tot_wrong}/{checked} 超過 {int(MISMATCH_ALERT * 100)}%，請查看")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
