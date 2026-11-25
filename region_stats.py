"""每州的特價數量（網站上方「特價／半價／各超市」統計）。

export_static_data.py 匯出時算一次；scripts/check_data.py 逐筆檢查下架不合理的商品後再算一次，
上方統計才會和清單一致（2026-11-25：下架 1 件後上方多算 1 件）。
"""
from scrapers.regions import ALL_REGIONS, BASE_REGION, is_everyday, is_regular
from database import is_half_price


def region_stats(items, region):
    out = {}
    for period in ('current', 'next'):
        total, by_store, half, everyday, everyday_by_store, regular, regular_by_store = 0, {}, 0, 0, {}, 0, {}
        for it in items:
            if it.get('period') != period or ('rg' in it and region not in it['rg']):
                continue
            if it.get('store') == 'Chemist Warehouse':
                continue               # 小黃屋 has its own site (chemist/): not in the supermarket numbers
            p = dict(it, **(it.get('rp', {}).get(region) or {}))
            if is_everyday(p):
                everyday += 1          # listed on the site, but not a special: not in the specials numbers
                everyday_by_store[p['store']] = everyday_by_store.get(p['store'], 0) + 1
                continue
            if is_regular(p):
                regular += 1           # listed on the site, but not a special
                regular_by_store[p['store']] = regular_by_store.get(p['store'], 0) + 1
                continue
            total += 1
            by_store[p['store']] = by_store.get(p['store'], 0) + 1
            if (p['store'] == 'ALDI' or (p.get('save_amount') or 0) > 0) and is_half_price(
                    p.get('price'), p.get('was_price'), p.get('save_amount'), p.get('discount_desc')):
                half += 1
        out[period] = {'total': total, 'by_store': by_store, 'half_price_count': half, 'everyday_count': everyday,
                       'everyday_by_store': everyday_by_store, 'regular_count': regular, 'regular_by_store': regular_by_store}
    return out


def apply_region_stats(stats, items):
    """Every state's numbers into stats; the default numbers (stats['current'] / ['next']) are Queensland's."""
    stats['base_region'] = BASE_REGION
    stats['regions'] = {r: region_stats(items, r) for r in ALL_REGIONS}
    for period in ('current', 'next'):
        stats.setdefault(period, {}).update(stats['regions'][BASE_REGION][period])
    return stats
