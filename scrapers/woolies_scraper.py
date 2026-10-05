import requests
from bs4 import BeautifulSoup
import re
import html
import os
import sys
from typing import List, Dict, Any

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from categories import classify_product

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-AU,en;q=0.9',
}

BASE_URL = 'https://www.salefinder.com.au'

# ---- Robust HTTP: behave like a real Chrome browser and retry, so a busy/blocked moment
#      on the catalogue site doesn't make a whole weekly update fail ----
import threading as _threading
_LOCAL = _threading.local()

def _session():
    # one browser-like session per thread (several states' catalogues are read in parallel)
    s = getattr(_LOCAL, 'session', None)
    if s is None:
        try:
            from curl_cffi import requests as _cffi_requests
            s = _cffi_requests.Session(impersonate='chrome')
        except Exception:
            s = requests.Session()
            s.headers.update(HEADERS)
        _LOCAL.session = s
    return s

def _get(url, timeout=20, **kwargs):
    import time as _t
    last = None
    for attempt in range(3):
        try:
            r = _session().get(url, timeout=timeout, **kwargs)
            if r.status_code == 200:
                return r
            last = r
        except Exception as e:
            last = e
        _t.sleep(3 * (attempt + 1))
    if isinstance(last, Exception):
        raise last
    return last

def pick_current_and_next(catalogues, today=None):
    """Choose this week's and next week's catalogue by their dates (Australian time),
    not by catalogue number, so the Wednesday switch-over is never late.
    Falls back to catalogue-number order when dates can't be read."""
    import datetime as _dt
    if today is None:
        try:
            from zoneinfo import ZoneInfo
            today = _dt.datetime.now(ZoneInfo('Australia/Sydney')).date()
        except Exception:
            today = (_dt.datetime.utcnow() + _dt.timedelta(hours=10)).date()

    def parse(rng):
        m = re.findall(r'(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s*(\d{4})?', rng or '')
        if len(m) < 2:
            return None
        year_end = int(m[1][2]) if m[1][2] else today.year
        year_start = int(m[0][2]) if m[0][2] else year_end
        try:
            s = _dt.datetime.strptime(f"{m[0][0]} {m[0][1]} {year_start}", "%d %b %Y").date()
            e = _dt.datetime.strptime(f"{m[1][0]} {m[1][1]} {year_end}", "%d %b %Y").date()
            if s > e:  # e.g. "30 Dec - 5 Jan 2027"
                s = s.replace(year=s.year - 1)
            return s, e
        except ValueError:
            return None

    dated = [(parse(c.get('date_range')), c) for c in catalogues]
    if not dated or any(d is None for d, _ in dated):
        by_id = sorted(catalogues, key=lambda x: x['id'])
        return (by_id[0] if by_id else None), (by_id[1] if len(by_id) > 1 else None)

    current = [c for (s, e), c in dated if s <= today <= e]
    upcoming = sorted([(s, c) for (s, e), c in dated if s > today], key=lambda x: x[0])
    cur = max(current, key=lambda c: c['id']) if current else None
    nxt = upcoming[0][1] if upcoming else None
    if cur is None:
        # nothing covers today (e.g. site still lists only last week) -> newest one that has started
        started = sorted([(s, c) for (s, e), c in dated if s <= today], key=lambda x: x[0])
        cur = started[-1][1] if started else (upcoming.pop(0)[1] if upcoming else None)
        if nxt is cur:
            nxt = None
    return cur, nxt

def parse_price(text: str) -> float:
    match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
    return float(match.group(1)) if match else 0.0

def clean_date_range(text: str) -> str:
    """Extract clean date range like '16 Sep 2026 - 22 Sep 2026'"""
    m = re.search(r'(\d{1,2}\s+[A-Za-z]{3}(?:\s+\d{4})?\s*-\s*\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', text)
    if m:
        return m.group(1)
    return text.replace('Offer valid', '').strip()

def discover_woolies_catalogues(postcode_id=None, region=None) -> List[Dict[str, Any]]:
    """Discovers available Woolworths catalogues (this week and next week preview)."""
    catalogues = []
    try:
        if postcode_id:
            from scrapers.regions import fetch_region_page
            page = fetch_region_page(f"{BASE_URL}/Woolworths-catalogue", postcode_id, region)
            if page is None:
                return []
        else:
            page = _get(f"{BASE_URL}/Woolworths-catalogue").text
        soup = BeautifulSoup(page, 'html.parser')
        
        links = soup.find_all('a', href=re.compile(r'/woolworths-catalogue/.+/\d+/catalogue2'))
        if region:
            # only this state's own catalogue (not Liquorland, not regional-town versions)
            from scrapers.regions import filter_region_links
            pairs = []
            for l in links:
                m = re.search(r'-catalogue/([^/]+)/\d+/catalogue2', l.get('href', ''))
                if m:
                    pairs.append((m.group(1), l))
            keep = {id(l) for _, l in filter_region_links(pairs, region, exact_prefix='weekly-catalogue')}
            links = [l for l in links if id(l) in keep]
        seen_ids = set()
        
        for link in links:
            href = link.get('href', '')
            cat_id_match = re.search(r'/(\d+)/catalogue2', href)
            if not cat_id_match:
                continue
            cat_id = cat_id_match.group(1)
            if cat_id in seen_ids:
                continue
            seen_ids.add(cat_id)

            list_url = f"{BASE_URL}{href}".replace('/catalogue2', '/list')
            cat_r = _get(list_url)
            cat_soup = BeautifulSoup(cat_r.text, 'html.parser')
            
            date_el = cat_soup.select_one('.sf-catalogue-dates, .sale-dates')
            date_str = clean_date_range(date_el.get_text(strip=True)) if date_el else ""

            catalogues.append({
                'id': int(cat_id),
                'url': list_url,
                'date_range': date_str,
                'soup': cat_soup
            })

        catalogues.sort(key=lambda x: x['id'])
    except Exception as e:
        print(f"::warning::Woolworths catalogue discovery failed: {e}")

    return catalogues

def scrape_woolies_catalogue_items(base_list_url: str, initial_soup: BeautifulSoup, max_pages: int = 50) -> List[Dict[str, Any]]:
    """Scrapes products from a specific Woolworths catalogue list URL across pages."""
    products = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        try:
            if page == 1 and initial_soup:
                soup = initial_soup
            else:
                page_url = f"{base_list_url}?qs={page},,,,"
                r = _get(page_url)
                if r.status_code != 200:
                    break
                soup = BeautifulSoup(r.text, 'html.parser')

            items = soup.select('.item-landscape')
            if not items:
                break

            for item in items:
                img_tag = item.select_one('.item-image')
                item_id = img_tag.get('data-itemid') if img_tag else None
                if item_id and item_id in seen_ids:
                    continue
                if item_id:
                    seen_ids.add(item_id)

                name_elem = item.select_one('.item-name')
                title = ""
                if img_tag and img_tag.get('data-itemname'):
                    title = img_tag.get('data-itemname')
                elif name_elem:
                    title = name_elem.get_text(strip=True)

                if not title:
                    continue

                desc_elem = item.select_one('.item-description')
                discount_desc = desc_elem.get_text(strip=True) if desc_elem else ""

                # Strictly exclude online only items
                if 'online only' in title.lower() or 'online only' in discount_desc.lower() or 'everyday market' in title.lower():
                    continue

                href = name_elem.get('href', '') if name_elem else ''
                product_url = f"{BASE_URL}{href}" if href.startswith('/') else href
                category = "Groceries"
                if href:
                    parts = [p.replace('-', ' ') for p in href.split('/') if p]
                    category = " ".join(parts[1:4])

                img = item.select_one('.item-image img')
                image_url = img.get('src', '') if img else ''
                if image_url and not image_url.startswith('http'):
                    image_url = f"https:{image_url}" if image_url.startswith('//') else f"{BASE_URL}{image_url}"

                price_box = item.select_one('.price-options')
                price_text = ""
                was_price = 0.0
                save_amount = 0.0
                price = 0.0

                if price_box:
                    full_text = price_box.get_text(separator=' ', strip=True)
                    price_elem = price_box.select_one('.price')
                    price_text = price_elem.get_text(strip=True) if price_elem else ""
                    price = parse_price(price_text) if price_text else parse_price(full_text)
                    now_m = re.search(r'\bNow\s+\$(\d+(?:\.\d{2})?)', full_text, re.IGNORECASE)
                    if now_m:   # "Price Drop, Was on 22/09 $50.00 Now $42.00"
                        price = float(now_m.group(1))
                    
                    was_match = re.search(r'Was(?:\s+on\s+[\d/]+)?\s+\$(\d+(?:\.\d{2})?)', full_text, re.IGNORECASE)  # also "Price Drop, Was on 22/09 $50.00 Now $42.00"
                    if was_match:
                        was_price = float(was_match.group(1))

                    save_match = re.search(r'Save\s+(?:from\s+|up\s+to\s+)?\$(\d+(?:\.\d{2})?)', full_text, re.IGNORECASE)
                    if save_match:
                        save_amount = float(save_match.group(1))

                if was_price > price > 0 and save_amount == 0.0:
                    save_amount = round(was_price - price, 2)
                elif save_amount > 0 and was_price == 0.0 and price > 0:
                    was_price = round(price + save_amount, 2)

                lower_desc = discount_desc.lower()
                if lower_desc.startswith('offers apply') or 'while stocks last' in lower_desc or 'specials not available' in lower_desc:
                    discount_desc = f"Save ${save_amount:.2f}" if save_amount > 0 else ""
                elif not discount_desc and save_amount > 0:
                    discount_desc = f"Save ${save_amount:.2f}"

                if was_price == 0 and ('1/2' in discount_desc or 'half' in discount_desc.lower()) and price > 0:
                    was_price = round(price * 2, 2)
                    save_amount = price

                # Only include products with real discounts (exclude non-discounted catalogue items)
                if save_amount <= 0 and (was_price <= price or was_price == 0):
                    continue

                products.append({
                    'store': 'Woolworths',
                    'title': html.unescape(title),
                    'price': price,
                    'price_display': price_text or f"${price:.2f}",
                    'was_price': was_price,
                    'save_amount': save_amount,
                    'discount_desc': discount_desc,
                    'unit_price': '',
                    'image_url': image_url,
                    'category': category,
                    'product_url': product_url
                })

        except Exception as e:
            print(f"Error scraping Woolworths catalogue page {page}: {e}")
            break

    return products

def scrape_woolies_online_half_price(max_pages: int = 100) -> List[Dict[str, Any]]:
    """Fetches ALL real in-store Half Price specials from Woolworths official API, strictly excluding online-only/marketplace."""
    import time
    products = []
    seen_names = set()
    url = 'https://www.woolworths.com.au/apis/ui/Search/products'
    page = 1
    excluded_online_count = 0

    # Woolworths blocks plain python-requests (403) from cloud servers such as GitHub Actions.
    # curl_cffi mimics a real Chrome browser, which the site accepts, so the update is fully automatic.
    try:
        from curl_cffi import requests as cffi_requests
        session = cffi_requests.Session(impersonate='chrome')
        print("Woolies API: using curl_cffi (Chrome impersonation)")
    except Exception:
        session = requests.Session()
        session.headers.update(HEADERS)
        print("Woolies API: curl_cffi not installed, falling back to requests")
    try:
        session.get('https://www.woolworths.com.au/', timeout=20)  # obtain session cookies first
    except Exception as e:
        print(f"Woolies homepage warm-up failed: {e}")
    
    # The official "Half Price" specials page (shop/browse/specials/half-price) is the complete list.
    # The old "half price" text search missed ~20 products a week, so it is only the fallback now.
    use_category = True
    while page <= max_pages:
        try:
            if use_category:
                body = {
                    'categoryId': 'specialsgroup.3676', 'pageNumber': page, 'pageSize': 36,
                    'sortType': 'TraderRelevance', 'url': '/shop/browse/specials/half-price',
                    'location': '/shop/browse/specials/half-price', 'formatObject': '{"name":"Half Price"}',
                    'isSpecial': True, 'isBundle': False, 'isMobile': False, 'filters': [], 'token': '',
                    'gpBoost': 0, 'isHideUnavailableProducts': False, 'isRegisteredRewardCardPromotion': False,
                    'enableAdReRanking': False, 'groupEdmVariants': False, 'categoryVersion': 'v2',
                    'flags': {'EnableProductBoostExperiment': False},
                }
                r = session.post('https://www.woolworths.com.au/apis/ui/browse/category', json=body, timeout=20)
                if r.status_code != 200 or not (r.json().get('Bundles') if r.status_code == 200 else None):
                    if page == 1:
                        print(f"Woolies half-price page unavailable (status {r.status_code}), using search instead")
                        use_category = False
                        continue
            else:
                params = {
                    'SearchTerm': 'half price',
                    'PageSize': 36,
                    'PageNumber': page
                }
                r = session.get(url, params=params, timeout=20)
            if r.status_code != 200:
                print(f"Woolies API status {r.status_code} at page {page}, stopping.")
                break
            data = r.json()
            bundles = (data.get('Bundles') if use_category else data.get('Products')) or []
            if not bundles:
                print(f"Woolies reached end of Half Price specials at page {page - 1}.")
                break
                
            page_added = 0
            for b in bundles:
                for pr in b.get('Products', []):
                    # STRICT IN-STORE ONLY CHECK: Exclude online-only and marketplace products
                    if pr.get('IsOnlineOnly') is True or pr.get('IsMarketProduct') is True or pr.get('ThirdPartyProductInfo'):
                        excluded_online_count += 1
                        continue

                    code = str(pr.get('Stockcode', ''))
                    name = (pr.get('Name') or '').strip()
                    if not name or name.lower() in seen_names:
                        continue

                    # Check title for online-only indicators
                    if 'online only' in name.lower() or 'everyday market' in name.lower():
                        excluded_online_count += 1
                        continue

                    seen_names.add(name.lower())
                    
                    # IN-STORE prices only. Never fall back to the online Price/WasPrice:
                    # the site lists specials you can get in the shop, not online-only deals.
                    if pr.get('InstoreWasPrice') is None:
                        excluded_online_count += 1
                        continue
                    was_price = float(pr.get('InstoreWasPrice') or 0)
                    if pr.get('InstorePrice') is None:
                        # On the official Half Price page but sold out at the reference store today:
                        # still a half-price special in other stores (Woolworths runs these nationally)
                        if not use_category:
                            excluded_online_count += 1
                            continue
                        price = round(was_price / 2, 2)
                    else:
                        price = float(pr.get('InstorePrice') or 0)

                    # Strictly half price in store: in-store price <= 55% of in-store was price
                    # (the InstoreIsOnSpecial flag is sometimes false for catalogue half-price items,
                    #  so the in-store prices themselves are the source of truth)
                    if not (was_price > 0 and 0 < price <= was_price * 0.55):
                        continue
                        
                    pkg = (pr.get('PackageSize') or '').strip()
                    full_title = f"{name} {pkg}".strip() if pkg and pkg not in name else name
                    
                    save_amt = round(was_price - price, 2)
                    img = pr.get('LargeImageFile') or pr.get('MediumImageFile') or ''
                    
                    # Product link
                    slug = re.sub(r'[^a-zA-Z0-9]+', '-', name).strip('-').lower()
                    prod_url = f"https://www.woolworths.com.au/shop/productdetails/{code}/{slug}" if code else f"https://www.woolworths.com.au/shop/search/products?searchTerm={requests.utils.quote(name)}"

                    # Determine category with full department metadata
                    attrs = pr.get('AdditionalAttributes', {})
                    dept = attrs.get('piesdepartmentnamesjson', '')
                    cat_json = attrs.get('piescategorynamesjson', '')
                    sap = attrs.get('sapcategoryname', '')
                    raw_cat = f"{dept} {cat_json} {sap}".strip()
                    cat = classify_product(full_title, raw_cat, prod_url)
                    
                    # Unit price
                    unit_p = pr.get('CupPrice')
                    unit_m = pr.get('CupMeasure')
                    unit_str = f"${unit_p} / {unit_m}" if unit_p and unit_m else ""
                    
                    products.append({
                        'store': 'Woolworths',
                        'category': cat,
                        'title': full_title,
                        'price': price,
                        'price_display': f"${price:.2f} ea",
                        'unit_price': unit_str,
                        'was_price': was_price,
                        'save_amount': save_amt,
                        'discount_desc': '1/2 PRICE',
                        'image_url': img,
                        'product_url': prod_url
                    })
                    page_added += 1
            
            if page % 5 == 0 or page_added == 0:
                print(f"Woolies Half Price page {page}: added {page_added} items (Total: {len(products)})")
            page += 1
            time.sleep(0.15)
        except Exception as e:
            print(f"Error fetching Woolies online half price page {page}: {e}")
            break
            
    print(f"Scraped {len(products)} online Half Price specials from Woolworths API across {page - 1} pages.")
    return products

def scrape_woolies_all_weeks(max_pages: int = 50) -> Dict[str, Dict[str, Any]]:
    """Scrapes Woolworths specials for both current week and next week (if available)."""
    from scrapers.regions import scrape_all_regions
    print("Scraping Woolworths (Current & Next Week, all states)...")
    res = scrape_all_regions('Woolworths', discover_woolies_catalogues, scrape_woolies_catalogue_items,
                             pick_current_and_next, max_pages=max_pages)

    # Merge online Half Price specials (Kinder Bueno, snacks, confectionery, etc.)
    try:
        online_half = scrape_woolies_online_half_price(max_pages=100)
        existing_titles = {it['title'].lower() for it in res['current']['items']}
        added = 0
        for oh in online_half:
            if oh['title'].lower() not in existing_titles:
                res['current']['items'].append(oh)
                existing_titles.add(oh['title'].lower())
                added += 1
        print(f"Merged {added} online Half Price specials into Woolworths current week specials.")
    except Exception as e:
        print(f"Error merging online half price specials: {e}")

    return res

if __name__ == '__main__':
    data = scrape_woolies_all_weeks(max_pages=2)
    print(f"Current: {len(data['current']['items'])} items ({data['current']['date_range']})")
    print(f"Next: {len(data['next']['items'])} items ({data['next']['date_range']})")
