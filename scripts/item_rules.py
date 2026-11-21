# -*- coding: utf-8 -*-
"""
Strict per-product rules (逐筆防呆), used by scripts/check_data.py before anything is published.

Every special on the site must pass ALL of these. A product that breaks one is taken off the site
(never "fixed" by guessing); the reason is printed on the run page. Many broken products in one
store at once = the scraper is broken -> the whole update is held back and the owner gets an email.

    problems(item, today) -> list of reasons (empty list = OK)
"""
import re

STORES = ('Woolworths', 'Coles', 'ALDI')
DOMAINS = {
    'Woolworths': ('woolworths.com.au', 'salefinder.com.au'),
    'Coles': ('coles.com.au', 'salefinder.com.au'),
    'ALDI': ('aldi.com.au',),
}
# highest believable price for one special (ALDI Special Buys include TVs, e-bikes, furniture)
MAX_PRICE = {'Woolworths': 1000.0, 'Coles': 1000.0, 'ALDI': 3000.0}
TOL = 0.011                      # cents rounding
ONLINE_WORDS = re.compile(r'online\s*only|online\s*exclusive|web\s*only|everyday\s*market|marketplace', re.I)
SAVE_RE = re.compile(r'\bSave\s+\$\s*(\d+(?:\.\d{1,2})?)', re.I)
MULTI_RE = re.compile(r'(\d+)\s*for\s*\$\s*(\d+(?:\.\d{1,2})?)', re.I)


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def problems(it, today=None, range_end=None):
    bad = []
    store = it.get('store')
    if store not in STORES:
        return [f"不認得的超市：{store}"]
    if it.get('period') not in ('current', 'next'):
        bad.append(f"檔期不對：{it.get('period')}")
    title = (it.get('title') or '').strip()
    if not title:
        bad.append('沒有商品名稱')
    desc = it.get('discount_desc') or ''
    if ONLINE_WORDS.search(title) or ONLINE_WORDS.search(desc):
        bad.append('網路限定（本站只收實體門市特價）')

    price, was, save = _num(it.get('price')), _num(it.get('was_price')) or 0.0, _num(it.get('save_amount')) or 0.0
    if price is None or price <= 0:
        bad.append(f"價格不正確：{it.get('price')}")
        return bad
    if price > MAX_PRICE[store]:
        bad.append(f"價格 ${price} 高得不合理")
    if was < 0 or save < 0:
        bad.append('原價或省下金額是負數')
    if was:
        if was <= price + TOL / 2:
            bad.append(f"原價 ${was} 沒有高於特價 ${price}")
        elif price / was < 0.05:
            bad.append(f"特價 ${price} 不到原價 ${was} 的 5%，不合理")
        if save and abs((was - price) - save) > TOL:
            bad.append(f"省下金額 ${save} ≠ 原價 ${was} − 特價 ${price}")
    elif save:
        bad.append(f"寫了省 ${save} 卻沒有原價")
    up = desc.upper()
    if was and '1/2' in up:
        limit = 0.5 if 'BETTER THAN' in up else 0.55
        if price > was * limit + TOL:
            bad.append(f"標半價但 ${price} 超過原價 ${was} 的一半")
    m = SAVE_RE.search(desc)
    if m and abs(float(m.group(1)) - save) > TOL:
        bad.append(f"標示 Save ${m.group(1)}，但省下金額是 ${save}")
    m = MULTI_RE.search(it.get('price_display') or '')
    if m and abs(float(m.group(2)) - price) > TOL:
        bad.append(f"多件優惠 {m.group(0)} 和價格 ${price} 不一致")

    url = it.get('product_url') or ''
    if not re.match(r'https://', url):
        bad.append('沒有官方商品連結')
    elif not any(d in url.split('/')[2] for d in DOMAINS[store]):
        bad.append(f"商品連結不是 {store} 的網站")

    rng = it.get('date_range') or ''
    if not rng:
        bad.append('沒有特價日期')
    elif today and range_end and it.get('period') == 'current':
        end = range_end(rng)
        if end and (today - end).days >= 2:
            bad.append(f"特價已過期（{rng}）")
    return bad
