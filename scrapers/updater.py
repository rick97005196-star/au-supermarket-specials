import os
import sys
import time
from typing import Dict, Any

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, save_specials, get_stats
from scrapers.coles_scraper import scrape_coles_all_weeks
from scrapers.woolies_scraper import scrape_woolies_all_weeks
from scrapers.aldi_scraper import scrape_aldi_specials

def update_all_stores(max_catalogue_pages: int = 10) -> Dict[str, Any]:
    """Runs all supermarket scrapers for both current week and next week preview."""
    print("=" * 65)
    print(f"Starting Full Supermarket Specials Update at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    
    init_db()
    results = {}

    # 1. Coles (Current & Next Week)
    try:
        coles_data = scrape_coles_all_weeks(max_pages=max_catalogue_pages)
        
        # Save current week
        curr_items = coles_data['current']['items']
        curr_date = coles_data['current']['date_range']
        saved_c_curr = save_specials('Coles', curr_items, period='current', date_range=curr_date)
        print(f" Saved {saved_c_curr} Coles current week specials ({curr_date}).")

        # Save next week (if available)
        next_items = coles_data['next']['items']
        next_date = coles_data['next']['date_range']
        saved_c_next = 0
        if next_items:
            saved_c_next = save_specials('Coles', next_items, period='next', date_range=next_date)
            print(f" Saved {saved_c_next} Coles NEXT week specials ({next_date}).")

        results['Coles'] = {
            'current': saved_c_curr,
            'next': saved_c_next,
            'current_date': curr_date,
            'next_date': next_date,
            'status': 'success'
        }
    except Exception as e:
        print(f" Coles update error: {e}")
        results['Coles'] = {'status': f'error: {e}'}

    # 2. Woolworths (Current & Next Week)
    try:
        woolies_data = scrape_woolies_all_weeks(max_pages=max_catalogue_pages)
        
        # Save current week
        w_curr_items = woolies_data['current']['items']
        w_curr_date = woolies_data['current']['date_range']
        saved_w_curr = save_specials('Woolworths', w_curr_items, period='current', date_range=w_curr_date)
        print(f" Saved {saved_w_curr} Woolworths current week specials ({w_curr_date}).")

        # Save next week (if available)
        w_next_items = woolies_data['next']['items']
        w_next_date = woolies_data['next']['date_range']
        saved_w_next = 0
        if w_next_items:
            saved_w_next = save_specials('Woolworths', w_next_items, period='next', date_range=w_next_date)
            print(f" Saved {saved_w_next} Woolworths NEXT week specials ({w_next_date}).")

        results['Woolworths'] = {
            'current': saved_w_curr,
            'next': saved_w_next,
            'current_date': w_curr_date,
            'next_date': w_next_date,
            'status': 'success'
        }
    except Exception as e:
        print(f" Woolworths update error: {e}")
        results['Woolworths'] = {'status': f'error: {e}'}

    # 3. ALDI
    try:
        aldi_items = scrape_aldi_specials()
        saved_aldi = save_specials('ALDI', aldi_items, period='current', date_range='本週 Super Savers & Special Buys')
        results['ALDI'] = {'count': saved_aldi, 'status': 'success'}
        print(f" Saved {saved_aldi} ALDI specials to database.")
    except Exception as e:
        print(f" ALDI update error: {e}")
        results['ALDI'] = {'count': 0, 'status': f'error: {e}'}

    stats = get_stats()
    print("=" * 65)
    print("Update complete! Database stats:")
    print("本週 (Current):", stats['current'])
    print("下週 (Next):", stats['next'])
    print("=" * 65)

    # Auto-export static JSON and update translations
    try:
        from scripts.auto_translate import run_auto_translate
        run_auto_translate()
    except Exception as e:
        print(f"Notice: Auto translate skipped or failed: {e}")

    try:
        import subprocess
        exp_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'export_static_data.py')
        subprocess.run([sys.executable, exp_script], check=False)
    except Exception as e:
        print(f"Notice: Static export skipped or failed: {e}")

    return {
        'results': results,
        'stats': stats
    }

if __name__ == '__main__':
    pages = 50
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        pages = int(sys.argv[1])
    update_all_stores(max_catalogue_pages=pages)
