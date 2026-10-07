import os
import sys
import requests
from bs4 import BeautifulSoup
import re
import html
from typing import List, Dict, Any, Tuple

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-AU,en;q=0.9',
}

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    """Polite GET on the catalogue site (paced, one browser identity, stops when refused).
    Returns the response, or None when the site is refusing us / unreachable."""
    from scrapers.polite import request
    return request('salefinder', lambda: _session().get(url, timeout=timeout, **kwargs))

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

def discover_coles_catalogues(postcode_id=None, region=None, known_dates=None) -> List[Dict[str, Any]]:
    """Discovers available Coles catalogues (this week and next week preview)."""
    catalogues = []
    try:
        if postcode_id:
            from scrapers.regions import fetch_region_page
            page = fetch_region_page(f"{BASE_URL}/Coles-catalogue", postcode_id, region)
            if page is None:
                return []
        else:
            r0 = _get(f"{BASE_URL}/Coles-catalogue")
            if r0 is None or r0.status_code != 200:
                return []
            page = r0.text
        soup = BeautifulSoup(page, 'html.parser')
        
        # Find catalogue links (only Coles supermarket, exclude liquorland)
        links = soup.find_all('a', href=re.compile(r'/coles-catalogue/coles-catalogue-.+/\d+/catalogue2'))
        if region:
            # only this state's own catalogue (not Liquorland, not regional-town versions)
            from scrapers.regions import filter_region_links
            pairs = []
            for l in links:
                m = re.search(r'-catalogue/([^/]+)/\d+/catalogue2', l.get('href', ''))
                if m:
                    pairs.append((m.group(1), l))
            keep = {id(l) for _, l in filter_region_links(pairs, region, exact_prefix=None)}
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

            # Check dates from the catalogue page
            list_url = f"{BASE_URL}{href}".replace('/catalogue2', '/list')
            # a catalogue seen before: its dates are already known, no need to open it again
            if known_dates and str(cat_id) in known_dates:
                catalogues.append({'id': int(cat_id), 'url': list_url, 'date_range': known_dates[str(cat_id)], 'soup': None})
                continue
            cat_r = _get(list_url)
            if cat_r is None or cat_r.status_code != 200:
                continue
            cat_soup = BeautifulSoup(cat_r.text, 'html.parser')
            
            date_el = cat_soup.select_one('.sf-catalogue-dates, .sale-dates')
            date_str = clean_date_range(date_el.get_text(strip=True)) if date_el else ""

            catalogues.append({
                'id': int(cat_id),
                'url': list_url,
                'date_range': date_str,
                'soup': cat_soup
            })

        # Sort by catalogue ID: smaller ID is current, larger ID is next week
        catalogues.sort(key=lambda x: x['id'])
    except Exception as e:
        print(f"::warning::Coles catalogue discovery failed: {e}")

    return catalogues

def scrape_coles_catalogue_items(base_list_url: str, initial_soup: BeautifulSoup, max_pages: int = 50) -> List[Dict[str, Any]]:
    """Scrapes products from a specific catalogue list URL across pages (in-store specials only)."""
    from scrapers.regions import ItemList
    products = ItemList()
    seen_ids = set()

    for page in range(1, max_pages + 1):
        try:
            if page == 1 and initial_soup:
                soup = initial_soup
            else:
                page_url = f"{base_list_url}?qs={page},,,,"
                r = _get(page_url)
                if r is None or r.status_code != 200:
                    break                       # refused / failed: NOT complete, read again next time
                soup = BeautifulSoup(r.text, 'html.parser')

            items = soup.select('.item-landscape')
            if not items:
                products.complete = True        # past the last page: the whole catalogue was read
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

                # Strict in-store check: exclude online only items
                lower_title = title.lower()
                if any(x in lower_title for x in ['online only', 'online exclusive', 'everyday market', 'marketplace']):
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

                desc_elem = item.select_one('.item-description')
                discount_desc = desc_elem.get_text(strip=True) if desc_elem else ""

                lower_desc = discount_desc.lower()
                # Exclude if description indicates online only
                if any(x in lower_desc for x in ['online only', 'online exclusive', 'web only']):
                    continue

                if was_price > price > 0 and save_amount == 0.0:
                    save_amount = round(was_price - price, 2)
                elif save_amount > 0 and was_price == 0.0 and price > 0:
                    was_price = round(price + save_amount, 2)

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
                    'store': 'Coles',
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
            print(f"Error scraping Coles catalogue page {page}: {e}")
            break

    return products

def scrape_coles_all_weeks(max_pages: int = 50) -> Dict[str, Dict[str, Any]]:
    """Coles specials for this week and next week, for every state (Queensland is the main one)."""
    from scrapers.regions import scrape_all_regions
    print("Scraping Coles (Current & Next Week, all states)...")
    res = scrape_all_regions('Coles', discover_coles_catalogues, scrape_coles_catalogue_items,
                             pick_current_and_next, max_pages=max_pages)

    # The printed catalogue only shows ~300 highlights; coles.com.au lists every in-store Half Price
    # special (~1,200). Add those (online-only deals are excluded inside scrape_coles_web_half_price).
    try:
        from scrapers.coles_web import scrape_coles_web_half_price
        if res['current']['items']:
            web = scrape_coles_web_half_price()
            existing = {it['title'].lower() for it in res['current']['items']}
            by_title = {it['title'].lower(): it for it in res['current']['items']}
            added = 0
            for it in web:
                if it['title'].lower() not in existing:
                    res['current']['items'].append(dict(it))
                    existing.add(it['title'].lower())
                    added += 1
                elif it.get('store_category') and not by_title.get(it['title'].lower(), {}).get('store_category'):
                    by_title[it['title'].lower()]['store_category'] = it['store_category']   # catalogue copy learns the aisle
            print(f"Merged {added} Coles website in-store Half Price specials into Coles current week.")
    except Exception as e:
        print(f"Error merging Coles website half price specials: {e}")
    return res

if __name__ == '__main__':
    data = scrape_coles_all_weeks(max_pages=2)
    print(f"Current: {len(data['current']['items'])} items ({data['current']['date_range']})")
    print(f"Next: {len(data['next']['items'])} items ({data['next']['date_range']})")
