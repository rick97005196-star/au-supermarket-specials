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

BASE_URL = 'https://www.salefinder.com.au'

def parse_price(text: str) -> float:
    match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
    return float(match.group(1)) if match else 0.0

def clean_date_range(text: str) -> str:
    """Extract clean date range like '16 Sep 2026 - 22 Sep 2026'"""
    m = re.search(r'(\d{1,2}\s+[A-Za-z]{3}(?:\s+\d{4})?\s*-\s*\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', text)
    if m:
        return m.group(1)
    return text.replace('Offer valid', '').strip()

def discover_coles_catalogues() -> List[Dict[str, Any]]:
    """Discovers available Coles catalogues (this week and next week preview)."""
    catalogues = []
    try:
        r = requests.get(f"{BASE_URL}/Coles-catalogue", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Find catalogue links (only Coles supermarket, exclude liquorland)
        links = soup.find_all('a', href=re.compile(r'/coles-catalogue/coles-catalogue-.+/\d+/catalogue2'))
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
            cat_r = requests.get(list_url, headers=HEADERS, timeout=15)
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
        print(f"Error discovering Coles catalogues: {e}")

    return catalogues

def scrape_coles_catalogue_items(base_list_url: str, initial_soup: BeautifulSoup, max_pages: int = 10) -> List[Dict[str, Any]]:
    """Scrapes products from a specific catalogue list URL across pages."""
    products = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        try:
            if page == 1 and initial_soup:
                soup = initial_soup
            else:
                page_url = f"{base_list_url}?qs={page},,,,"
                r = requests.get(page_url, headers=HEADERS, timeout=15)
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
                    
                    was_match = re.search(r'Was\s+\$(\d+(?:\.\d{2})?)', full_text, re.IGNORECASE)
                    if was_match:
                        was_price = float(was_match.group(1))

                    save_match = re.search(r'Save\s+\$(\d+(?:\.\d{2})?)', full_text, re.IGNORECASE)
                    if save_match:
                        save_amount = float(save_match.group(1))

                desc_elem = item.select_one('.item-description')
                discount_desc = desc_elem.get_text(strip=True) if desc_elem else ""
                if not discount_desc and save_amount > 0:
                    discount_desc = f"Save ${save_amount:.2f}"

                if was_price == 0 and ('1/2' in discount_desc or 'half' in discount_desc.lower()) and price > 0:
                    was_price = round(price * 2, 2)
                    save_amount = price

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

def scrape_coles_all_weeks(max_pages: int = 10) -> Dict[str, Dict[str, Any]]:
    """Scrapes Coles specials for both current week and next week (if available)."""
    print("Scraping Coles (Current & Next Week)...")
    catalogues = discover_coles_catalogues()
    res = {
        'current': {'items': [], 'date_range': ''},
        'next': {'items': [], 'date_range': ''}
    }

    if not catalogues:
        # Fallback to direct page 1
        print("No sub-catalogues found, using default Coles catalogue...")
        items = scrape_coles_catalogue_items(f"{BASE_URL}/Coles-catalogue", None, max_pages=max_pages)
        res['current']['items'] = items
        return res

    # The first is current week
    current_cat = catalogues[0]
    print(f"Coles Current Week ({current_cat['date_range']}) - ID {current_cat['id']}")
    res['current']['date_range'] = current_cat['date_range']
    res['current']['items'] = scrape_coles_catalogue_items(current_cat['url'], current_cat['soup'], max_pages=max_pages)

    # If there's a second one, it's next week's preview!
    if len(catalogues) > 1:
        next_cat = catalogues[1]
        print(f"Coles Next Week ({next_cat['date_range']}) - ID {next_cat['id']}")
        res['next']['date_range'] = next_cat['date_range']
        res['next']['items'] = scrape_coles_catalogue_items(next_cat['url'], next_cat['soup'], max_pages=max_pages)

    return res

if __name__ == '__main__':
    data = scrape_coles_all_weeks(max_pages=2)
    print(f"Current: {len(data['current']['items'])} items ({data['current']['date_range']})")
    print(f"Next: {len(data['next']['items'])} items ({data['next']['date_range']})")
