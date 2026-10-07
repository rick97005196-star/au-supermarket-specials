import os
import sys
import time
from typing import Dict, Any

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, save_specials, get_stats, clear_stale_next
from scrapers.coles_scraper import scrape_coles_all_weeks
from scrapers.woolies_scraper import scrape_woolies_all_weeks
from scrapers.aldi_scraper import scrape_aldi_specials

class _Skip(Exception):
    pass


def _aldi_recent(hours=3):
    """ALDI was read successfully within the last few hours, in the same Wednesday-to-Tuesday week
    (ALDI's own deal dates decide this week / next week, so a new week always reads ALDI again)."""
    import datetime as _dt
    try:
        from database import get_db
        with get_db() as conn:
            row = conn.execute("SELECT value FROM metadata WHERE key = 'last_updated_aldi_current'").fetchone()
        if not row:
            return False
        last = _dt.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')          # written in UTC on the runner
        now = _dt.datetime.now()
        if (now - last).total_seconds() > hours * 3600:
            return False
        bne = lambda d: (d + _dt.timedelta(hours=10)).date()
        wk = lambda day: day - _dt.timedelta(days=(day.weekday() - 2) % 7)
        return wk(bne(last)) == wk(bne(now))
    except Exception:
        return False


def update_all_stores(max_catalogue_pages: int = 50) -> Dict[str, Any]:
    """Runs all supermarket scrapers for both current week and next week preview."""
    print("=" * 65)
    print(f"Starting Full Supermarket Specials Update at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    
    init_db()
    results = {}

    # Wednesday safety net: yesterday's "next week" becomes "this week" before anything is scraped
    from database import promote_next_week
    for _store in ('Coles', 'Woolworths'):
        try:
            promote_next_week(_store)
        except Exception as e:
            print(f" Could not move {_store} next week to this week: {e}")

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
        else:
            clear_stale_next('Coles', curr_date)

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
        else:
            clear_stale_next('Woolworths', w_curr_date)

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

    # 3. ALDI (Current & Next Week)
    try:
        if _aldi_recent():
            raise _Skip('ALDI was read less than 3 hours ago - keeping the saved ALDI specials')
        from scrapers.aldi_scraper import scrape_aldi_all_weeks
        aldi_data = scrape_aldi_all_weeks()

        a_curr_items = aldi_data['current']['items']
        a_curr_date = aldi_data['current']['date_range']
        saved_a_curr = save_specials('ALDI', a_curr_items, period='current', date_range=a_curr_date)
        print(f" Saved {saved_a_curr} ALDI current week specials ({a_curr_date}).")

        a_next_items = aldi_data['next']['items']
        a_next_date = aldi_data['next']['date_range']
        saved_a_next = 0
        if a_next_items:
            saved_a_next = save_specials('ALDI', a_next_items, period='next', date_range=a_next_date)
            print(f" Saved {saved_a_next} ALDI NEXT week specials ({a_next_date}).")
        else:
            clear_stale_next('ALDI', a_curr_date)

        results['ALDI'] = {
            'current': saved_a_curr,
            'next': saved_a_next,
            'current_date': a_curr_date,
            'next_date': a_next_date,
            'status': 'success'
        }
    except _Skip as e:
        print(f" {e}")
        results['ALDI'] = {'status': 'kept'}
    except Exception as e:
        print(f" ALDI update error: {e}")
        results['ALDI'] = {'status': f'error: {e}'}

    try:
        from scrapers.polite import summary
        counts, blocked = summary()
        names = {'salefinder': '型錄網站', 'woolworths': 'Woolworths', 'coles': 'Coles 官網', 'aldi': 'ALDI'}
        txt = '、'.join(f"{names.get(k, k)} {v} 次" for k, v in counts.items()) or '0 次'
        print(f"::notice::本次更新對各網站的請求：{txt}" + (f"（被拒絕而停止：{'、'.join(names.get(k, k) for k in blocked)}）" if blocked else ''))
    except Exception:
        pass

    stats = get_stats()
    print("=" * 65)
    print("Update complete! Database stats:")
    print("本週 (Current):", stats['current'])
    print("下週 (Next):", stats['next'])
    print("=" * 65)

    # Auto-export static JSON and update translations (GitHub Actions runs these as separate steps)
    if os.environ.get('GITHUB_ACTIONS'):
        return {'results': results, 'stats': stats}

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
