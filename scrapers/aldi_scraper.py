import re
import html
import datetime
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
import os
import sys

# Ensure root directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from categories import classify_product

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-AU,en-US;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
}

def parse_price(text: str) -> float:
    m = re.search(r'\$(\d+(?:\.\d{2})?)', text)
    if m:
        return float(m.group(1))
    c_m = re.search(r'(\d+)c\b', text)
    if c_m:
        return float(c_m.group(1)) / 100.0
    return 0.0

def get_australian_supermarket_cycle():
    """Calculates Wednesday to Tuesday cycle dates for current and next week."""
    today = datetime.date.today()
    days_since_wed = (today.weekday() - 2) % 7
    current_cycle_wed = today - datetime.timedelta(days=days_since_wed)
    current_cycle_tue = current_cycle_wed + datetime.timedelta(days=6)
    next_cycle_wed = current_cycle_wed + datetime.timedelta(days=7)
    next_cycle_tue = current_cycle_tue + datetime.timedelta(days=7)
    return current_cycle_wed, current_cycle_tue, next_cycle_wed, next_cycle_tue

def discover_aldi_endpoints():
    """
    Discovers all dynamic ALDI Special Buys dates & themes, plus Super Savers.
    Separates endpoints into 'current' and 'next' cycle.
    """
    current_wed, current_tue, next_wed, next_tue = get_australian_supermarket_cycle()
    
    endpoints = [
        ('Super Savers', 'https://www.aldi.com.au/groceries/super-savers/', 'current')
    ]
    seen_urls = set(['https://www.aldi.com.au/groceries/super-savers/'])
    
    try:
        r = requests.get('https://www.aldi.com.au/special-buys/', headers=HEADERS, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/special-buys/' in href:
                    full_url = f"https://www.aldi.com.au{href}" if href.startswith('/') else href
                    if full_url in seen_urls:
                        continue
                    m = re.search(r'/special-buys/(\d{4}-\d{2}-\d{2})', full_url)
                    if m:
                        date_str = m.group(1)
                        try:
                            deal_date = datetime.date.fromisoformat(date_str)
                        except ValueError:
                            continue
                        
                        if deal_date <= current_tue:
                            period = 'current'
                        elif deal_date <= next_tue:
                            period = 'next'
                        else:
                            # Beyond next week
                            continue
                        
                        seen_urls.add(full_url)
                        endpoints.append((f"Special Buys {date_str}", full_url, period))
    except Exception as e:
        print(f"Warning: Failed to discover ALDI Special Buys endpoints: {e}")
        
    return endpoints, (current_wed, current_tue, next_wed, next_tue)

def scrape_aldi_all_weeks() -> Dict[str, Any]:
    """
    Scrapes ALDI Australia for both Current Week (Super Savers + Wednesday/Saturday Special Buys)
    and Next Week Preview.
    """
    print("Starting ALDI Australia multi-week specials scrape...")
    endpoints, (c_wed, c_tue, n_wed, n_tue) = discover_aldi_endpoints()
    print(f"ALDI: Discovered {len(endpoints)} endpoints to scrape.")
    
    current_items_map = {}
    next_items_map = {}
    
    for label, url, period in endpoints:
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, 'html.parser')
            tiles = soup.select('a.product-tile__link, [data-qa="product-tile"]')
            
            # Fallback if modern tile selector is absent
            if not tiles:
                tiles = soup.select('.box--wrapper[href*="/product/"], a[href*="/product/"]')
                
            for tile in tiles:
                # 1. Brand & Name extraction
                brand_el = tile.select_one('[data-test="product-tile__brandname"]')
                name_el = tile.select_one('[data-test="product-tile__name"]')
                
                brand = brand_el.get_text(strip=True).rstrip(',') if brand_el else ""
                name = name_el.get_text(strip=True).rstrip(',') if name_el else ""
                
                if brand and name:
                    title = f"{brand} {name}"
                elif name:
                    title = name
                elif brand:
                    title = brand
                else:
                    title_el = tile.select_one('.box--description--header, .box--title, h3, h4')
                    raw = title_el.get_text(strip=True) if title_el else ""
                    href_attr = tile.get('href', '')
                    slug = href_attr.split('/product/')[-1].rsplit('-', 1)[0].replace('-', ' ').title() if '/product/' in href_attr else ""
                    title = raw if len(raw) > 3 else slug
                
                title = html.unescape(title).strip()
                if not title or len(title) < 2:
                    continue
                    
                # 2. Real selling price extraction (avoids unit comparison price trap)
                price_el = tile.select_one('[data-test="product-tile__price"], .base-price__regular')
                if price_el:
                    price = parse_price(price_el.get_text())
                else:
                    clone_tile = BeautifulSoup(str(tile), 'html.parser')
                    comp_el = clone_tile.select_one('[data-test="product-tile__comparison-price"], .box--baseprice')
                    if comp_el:
                        comp_el.decompose()
                    price = parse_price(clone_tile.get_text())
                    
                if price <= 0:
                    continue
                    
                # 3. Unit comparison price
                unit_el = tile.select_one('[data-test="product-tile__comparison-price"], .box--baseprice')
                unit_price = unit_el.get_text(strip=True) if unit_el else ""
                
                # 4. Badge / On-sale label
                badge_el = tile.select_one('[data-test="product-tile__on-sale-label"]')
                badge = badge_el.get_text(strip=True) if badge_el else ("Super Savers" if "super-savers" in url else "Special Buys")
                
                # 5. Image URL (High-res)
                img = tile.select_one('img')
                img_src = ""
                if img:
                    img_src = img.get('src') or img.get('data-src') or ''
                    if not img_src and img.get('srcset'):
                        img_src = img.get('srcset').split(',')[0].split(' ')[0]
                        
                # 6. Canonical Product URL
                href = tile.get('href', '')
                prod_url = f"https://www.aldi.com.au{href}" if href.startswith('/') else (href or url)
                
                # Department categorization
                cat = classify_product(title, badge, prod_url)
                
                date_range_str = f"本週特價 ({c_wed.strftime('%m/%d')} - {c_tue.strftime('%m/%d')})" if period == 'current' else f"下週預告 ({n_wed.strftime('%m/%d')} - {n_tue.strftime('%m/%d')})"
                
                item_data = {
                    'store': 'ALDI',
                    'title': title,
                    'price': price,
                    'price_display': f"${price:.2f}",
                    'was_price': 0.0,
                    'save_amount': 0.0,
                    'discount_desc': badge,
                    'unit_price': unit_price,
                    'image_url': img_src,
                    'category': cat,
                    'product_url': prod_url,
                    'period': period,
                    'date_range': date_range_str
                }
                
                dedup_key = prod_url if prod_url and '/product/' in prod_url else title.lower()
                if period == 'current':
                    if dedup_key not in current_items_map:
                        current_items_map[dedup_key] = item_data
                else:
                    if dedup_key not in next_items_map:
                        next_items_map[dedup_key] = item_data
        except Exception as e:
            print(f"Error scraping ALDI endpoint {url}: {e}")
            
    current_list = list(current_items_map.values())
    next_list = list(next_items_map.values())
    print(f"ALDI scrape completed: {len(current_list)} current items, {len(next_list)} next week items.")
    
    return {
        'current': {
            'items': current_list,
            'date_range': f"Super Savers & Special Buys ({c_wed.strftime('%m/%d')} - {c_tue.strftime('%m/%d')})"
        },
        'next': {
            'items': next_list,
            'date_range': f"Special Buys 預告 ({n_wed.strftime('%m/%d')} - {n_tue.strftime('%m/%d')})"
        }
    }

def scrape_aldi_specials() -> List[Dict[str, Any]]:
    """Backward compatibility wrapper returning current week ALDI specials."""
    data = scrape_aldi_all_weeks()
    return data['current']['items']

if __name__ == '__main__':
    res = scrape_aldi_all_weeks()
    print(f"Current count: {len(res['current']['items'])}")
    print(f"Next count: {len(res['next']['items'])}")
