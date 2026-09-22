import re
import time
import html
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

def parse_price(text: str) -> float:
    match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
    return float(match.group(1)) if match else 0.0

def scrape_aldi_specials() -> Dict[str, Any]:
    """Scrapes ALDI Australia Super Savers and Special Buys."""
    print("Starting ALDI specials scrape...")
    products = []
    seen_titles = set()

    urls_to_scrape = [
        ("https://www.aldi.com.au/groceries/super-savers/", "Super Savers (本週特價)", "Super Savers"),
        ("https://www.aldi.com.au/special-buys/special-buys-wednesday/", "Special Buys (週三特選)", "Special Buys (Wed)"),
        ("https://www.aldi.com.au/special-buys/special-buys-saturday/", "Special Buys (週六特選)", "Special Buys (Sat)")
    ]

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By

        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)

        for target_url, display_cat, cat_name in urls_to_scrape:
            try:
                print(f"ALDI: loading {display_cat} ({target_url})...")
                driver.get(target_url)
                time.sleep(3)

                driver.execute_script("window.scrollTo(0, 1500);")
                time.sleep(1)

                tiles = driver.find_elements(By.CSS_SELECTOR, '[data-qa="product-tile"], .product-tile, [class*="product-tile"], [class*="tile"]')
                print(f"ALDI {display_cat}: found {len(tiles)} raw tiles.")

                for tile in tiles:
                    text = tile.text.strip()
                    if not text or '$' not in text:
                        continue

                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    if not lines:
                        continue

                    price = 0.0
                    unit_price = ""
                    for line in lines:
                        if line.startswith('$') and price == 0.0:
                            price = parse_price(line)
                        elif '(' in line and 'per' in line:
                            unit_price = line

                    if price == 0.0:
                        price = parse_price(text)
                    if price == 0.0:
                        continue

                    # Extract valid title candidates (skipping weight, price, and unit price lines)
                    real_title_candidates = [
                        l for l in lines
                        if not l.startswith('$')
                        and not re.match(r'^\(.*?per.*?\)$', l)
                        and not re.match(r'^\d+([,\.]\d+)?\s*(g|kg|ml|l)\s*\(.*?per.*?\)$', l, re.IGNORECASE)
                        and not re.match(r'^\d+([,\.]\d+)?\s*(g|kg|ml|l)$', l, re.IGNORECASE)
                        and not any(bad in l.lower() for bad in ['sign up', 'store locator', 'browse', 'privacy', 'terms', 'super savers', 'special buys'])
                    ]
                    if not real_title_candidates:
                        continue

                    if len(real_title_candidates) >= 2:
                        title = f"{real_title_candidates[0]} {real_title_candidates[1]}"
                    else:
                        title = real_title_candidates[0]

                    if title in seen_titles:
                        continue
                    seen_titles.add(title)

                    image_url = ""
                    product_url = target_url
                    try:
                        img_elem = tile.find_element(By.TAG_NAME, 'img')
                        image_url = img_elem.get_attribute('src') or ""
                    except Exception:
                        pass

                    try:
                        link_elem = tile.find_element(By.TAG_NAME, 'a')
                        product_url = link_elem.get_attribute('href') or target_url
                    except Exception:
                        pass

                    products.append({
                        'store': 'ALDI',
                        'title': html.unescape(title),
                        'price': price,
                        'price_display': f"${price:.2f}",
                        'was_price': 0.0,
                        'save_amount': 0.0,
                        'discount_desc': display_cat,
                        'unit_price': unit_price,
                        'image_url': image_url,
                        'category': cat_name,
                        'product_url': product_url,
                        'date_range': '本週 Super Savers & Special Buys'
                    })

            except Exception as page_err:
                print(f"Error scraping {display_cat}: {page_err}")

        driver.quit()

    except Exception as sel_err:
        print(f"Selenium ALDI scraping failed ({sel_err}), falling back to requests...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        }
        for target_url, display_cat, cat_name in urls_to_scrape:
            try:
                r = requests.get(target_url, headers=headers, timeout=15)
                soup = BeautifulSoup(r.text, 'html.parser')
                for item in soup.select('[class*="product"], [class*="tile"], [class*="card"]'):
                    text = item.get_text(separator=' ', strip=True)
                    if '$' not in text:
                        continue
                    price = parse_price(text)
                    if price <= 0:
                        continue
                    img = item.find('img')
                    img_src = img.get('src', '') if img else ''
                    title = text.split('$')[0].strip()[:60]
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        products.append({
                            'store': 'ALDI',
                            'title': html.unescape(title),
                            'price': price,
                            'price_display': f"${price:.2f}",
                            'was_price': 0.0,
                            'save_amount': 0.0,
                            'discount_desc': display_cat,
                            'unit_price': '',
                            'image_url': img_src,
                            'category': cat_name,
                            'product_url': target_url,
                            'date_range': '本週 Super Savers & Special Buys'
                        })
            except Exception as fb_err:
                print(f"Fallback error for {display_cat}: {fb_err}")

    print(f"ALDI scrape completed: {len(products)} products found.")
    return products

if __name__ == '__main__':
    items = scrape_aldi_specials()
    print("Preview first 3 ALDI items:")
    for item in items[:3]:
        print(item)
