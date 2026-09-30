import json
import sqlite3
import os
import html
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_DIR = os.path.join(os.path.dirname(__file__), 'data')
DB_PATH = os.path.join(DB_DIR, 'specials.db')

def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS specials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store TEXT NOT NULL,
                period TEXT NOT NULL DEFAULT 'current',
                date_range TEXT,
                title TEXT NOT NULL,
                price REAL DEFAULT 0.0,
                price_display TEXT,
                was_price REAL DEFAULT 0.0,
                save_amount REAL DEFAULT 0.0,
                discount_desc TEXT,
                unit_price TEXT,
                image_url TEXT,
                category TEXT,
                product_url TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute("PRAGMA table_info(specials)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'period' not in columns:
            cursor.execute("ALTER TABLE specials ADD COLUMN period TEXT NOT NULL DEFAULT 'current'")
        if 'date_range' not in columns:
            cursor.execute("ALTER TABLE specials ADD COLUMN date_range TEXT")
        if 'is_popular' not in columns:
            cursor.execute("ALTER TABLE specials ADD COLUMN is_popular INTEGER DEFAULT 0")
        if 'popularity_score' not in columns:
            cursor.execute("ALTER TABLE specials ADD COLUMN popularity_score INTEGER DEFAULT 0")
        # State availability: '' = every state, otherwise e.g. 'QLD,NSW' (see scrapers/regions.py)
        if 'regions' not in columns:
            cursor.execute("ALTER TABLE specials ADD COLUMN regions TEXT DEFAULT ''")
        if 'region_prices' not in columns:
            cursor.execute("ALTER TABLE specials ADD COLUMN region_prices TEXT DEFAULT ''")

        cursor.execute("PRAGMA table_info(shopping_list)")
        sl_columns = [row[1] for row in cursor.fetchall()]
        if 'period' not in sl_columns:
            cursor.execute("ALTER TABLE shopping_list ADD COLUMN period TEXT DEFAULT 'current'")
        if 'date_range' not in sl_columns:
            cursor.execute("ALTER TABLE shopping_list ADD COLUMN date_range TEXT")
        if 'was_price' not in sl_columns:
            cursor.execute("ALTER TABLE shopping_list ADD COLUMN was_price REAL DEFAULT 0.0")

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_specials_store_period ON specials (store, period)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_specials_title ON specials (title)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_specials_pop ON specials (is_popular, popularity_score)
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shopping_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                store TEXT NOT NULL,
                period TEXT DEFAULT 'current',
                date_range TEXT,
                title TEXT NOT NULL,
                price REAL DEFAULT 0.0,
                price_display TEXT,
                quantity INTEGER DEFAULT 1,
                is_bought INTEGER DEFAULT 0,
                image_url TEXT,
                save_amount REAL DEFAULT 0.0,
                was_price REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        conn.commit()

from categories import classify_product, is_popular_product, calculate_popularity_score


_MONTHS = {m: i for i, m in enumerate(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'], 1)}

def _range_start(date_range: str):
    """Return the (month, day) a date_range starts on, e.g. 'Wed 30 Sep 2026 - ...' or 'ALDI ... (09/30 - 10/06)'."""
    if not date_range:
        return None
    m = re.search(r'(\d{1,2})\s+([A-Za-z]{3})', date_range)
    if m and m.group(2).lower() in _MONTHS:
        return (_MONTHS[m.group(2).lower()], int(m.group(1)))
    m = re.search(r'(\d{1,2})/(\d{1,2})', date_range)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return None

def _start_offset_days(a, b):
    """Days from start a to start b (month/day tuples), wrapping around the year boundary."""
    da = datetime(2001, a[0], a[1]).timetuple().tm_yday
    db = datetime(2001, b[0], b[1]).timetuple().tm_yday
    diff = (db - da) % 365
    return diff - 365 if diff > 182 else diff

def save_specials(store: str, items: List[Dict[str, Any]], period: str = 'current', date_range: str = ''):
    """Replace specials for a given store and period (current / next) with the newly scraped list."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM specials WHERE store = ? AND period = ?', (store, period))
        existing_count = cursor.fetchone()[0]
        # A new promotional week (different start date) must always replace last week's specials,
        # otherwise expired specials would stay online. The guard only protects the SAME week.
        new_week = False
        if date_range and len(items) >= 20:
            cursor.execute('SELECT date_range FROM specials WHERE store = ? AND period = ? LIMIT 1', (store, period))
            row = cursor.fetchone()
            old_start, new_start = _range_start(row[0] if row else ''), _range_start(date_range)
            new_week = bool(old_start and new_start and old_start != new_start)
        # A failed scrape must never wipe good data (this emptied Coles once, when it had < 400 items):
        #  - no date range found = the catalogue page failed to load -> keep what we have
        #  - same week but far fewer items than before -> probably a partial failure -> keep
        cursor.execute("SELECT date_range FROM specials WHERE store = ? AND period = ? AND date_range != '' LIMIT 1", (store, period))
        had_dated = cursor.fetchone() is not None
        if existing_count >= 20 and not new_week and (
            (not date_range and had_dated) or len(items) < existing_count * 0.6
        ):
            msg = f"Anti-wipeout guard: {store} ({period}) kept {existing_count} existing items (new scrape: {len(items)} items, date range '{date_range}')"
            print(f"::warning::{msg}" if os.environ.get('GITHUB_ACTIONS') else f"⚠️ {msg}")
            return existing_count
        if existing_count > 400 and len(items) < 300 and not new_week:
            print(f"⚠️ Anti-wipeout guard triggered: {store} ({period}) has {existing_count} existing items, but scraper only found {len(items)}. Preserving existing database!")
            return existing_count

        cursor.execute('DELETE FROM specials WHERE store = ? AND period = ?', (store, period))
        
        insert_sql = '''
            INSERT INTO specials (
                store, period, date_range, title, price, price_display, was_price, save_amount,
                discount_desc, unit_price, image_url, category, product_url, is_popular, popularity_score, updated_at,
                regions, region_prices
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        rows = []
        seen_keys = set()
        for item in items:
            if not item.get('title'):
                continue
            from scrapers.regions import clean_title
            title = clean_title(html.unescape(item.get('title', '')))

            # Strictly enforce in-store specials only (reject online-only / marketplace items)
            lower_title = title.lower()
            if any(term in lower_title for term in ['online only', 'online exclusive', 'everyday market', 'marketplace']):
                continue

            discount_desc = html.unescape(item.get('discount_desc', '') or '').strip()
            lower_desc = discount_desc.lower()
            if any(term in lower_desc for term in ['online only', 'online exclusive', 'web only']):
                continue

            p_url = item.get('product_url', '')
            dedup_key = (title.lower(), p_url) if p_url else title.lower()
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            price = float(item.get('price', 0.0) or 0.0)
            if price <= 0:
                continue  # no valid selling price (would show as $0.00)
            was_price = float(item.get('was_price', 0.0) or 0.0)
            save_amount = float(item.get('save_amount', 0.0) or 0.0)

            if was_price > price > 0 and save_amount <= 0:
                save_amount = round(was_price - price, 2)
            elif save_amount > 0 and was_price <= 0 and price > 0:
                was_price = round(price + save_amount, 2)

            if lower_desc.startswith('offers apply') or 'while stocks last' in lower_desc or 'specials not available' in lower_desc:
                discount_desc = f"Save ${save_amount:.2f}" if save_amount > 0 else ""
            elif not discount_desc and save_amount > 0:
                discount_desc = f"Save ${save_amount:.2f}"

            # Only keep products that have a real discount (ALDI Super Savers & Special Buys are included)
            if store != 'ALDI' and save_amount <= 0 and (was_price <= price or was_price == 0):
                continue

            cat = classify_product(title, item.get('category', ''), item.get('product_url', ''))
            is_pop = 1 if is_popular_product(title) else 0
            score = calculate_popularity_score({
                'title': title, 'price': price, 'was_price': was_price,
                'save_amount': save_amount, 'discount_desc': discount_desc,
                'category': cat, 'is_popular': bool(is_pop)
            })

            rows.append((
                store,
                period,
                date_range or item.get('date_range', ''),
                title,
                price,
                html.unescape(item.get('price_display', '')).strip(),
                was_price,
                save_amount,
                discount_desc,
                html.unescape(item.get('unit_price', '')).strip(),
                item.get('image_url', ''),
                cat,
                item.get('product_url', ''),
                is_pop,
                score,
                now,
                ','.join(item.get('regions') or []),
                json.dumps(item['region_prices'], ensure_ascii=False, separators=(',', ':')) if item.get('region_prices') else ''
            ))
        cursor.executemany(insert_sql, rows)
        
        # Update metadata timestamp and date range
        cursor.execute(
            'INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)',
            (f'last_updated_{store.lower()}_{period}', now)
        )
        if date_range:
            cursor.execute(
                'INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)',
                (f'date_range_{store.lower()}_{period}', date_range)
            )
            if any(m in date_range for m in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', '2026', '2027', '2028']):
                cursor.execute(
                    'INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)',
                    (f'date_range_{period}', date_range)
                )

        cursor.execute(
            'INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)',
            ('last_updated_all', now)
        )
        conn.commit()
    return len(rows)

def clear_stale_next(store: str, current_date_range: str) -> int:
    """After the weekly rollover, last week's 'next' preview has become the current week.
    If no new preview was found, remove the stale preview so it is not shown twice."""
    cur = _range_start(current_date_range)
    if not cur:
        return 0
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT DISTINCT date_range FROM specials WHERE store = ? AND period = 'next'", (store,))
        removed = 0
        for (dr,) in c.fetchall():
            st = _range_start(dr or '')
            if st and _start_offset_days(cur, st) <= 0:
                c.execute("DELETE FROM specials WHERE store = ? AND period = 'next' AND date_range = ?", (store, dr))
                removed += c.rowcount
        if removed:
            c.execute("DELETE FROM metadata WHERE key = ?", (f'date_range_{store.lower()}_next',))
            print(f" Removed {removed} stale {store} 'next' items (that week is now current).")
        conn.commit()
        return removed

def get_specials(
    query: Optional[str] = None,
    store: Optional[str] = None,
    period: str = 'current',
    discount_only: bool = False,
    category: Optional[str] = None,
    sort_by: str = 'relevance',
    limit: int = 150,
    offset: int = 0
) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        where_clauses = ['period = ?', '(save_amount > 0 OR was_price > price OR store = "ALDI")']
        params = [period]

        if store and store.lower() != 'all':
            where_clauses.append('LOWER(store) = LOWER(?)')
            params.append(store)

        if query:
            words = query.strip().split()
            for word in words:
                where_clauses.append('(title LIKE ? OR category LIKE ? OR discount_desc LIKE ?)')
                pattern = f'%{word}%'
                params.extend([pattern, pattern, pattern])

        if discount_only:
            where_clauses.append("(discount_desc LIKE '%1/2%' OR discount_desc LIKE '%half%' OR save_amount > 0)")

        if category and category.lower() == 'popular':
            where_clauses.append("(is_popular = 1 AND popularity_score > 0)")
        elif category and category.lower() != 'all':
            where_clauses.append('category = ?')
            params.append(category)

        # Sorting & Filtering for popular
        order_by = "id ASC"
        if sort_by == 'popular':
            where_clauses.append("(is_popular = 1 AND popularity_score > 0)")
            order_by = "popularity_score DESC, save_amount DESC"
        elif sort_by == 'price_asc':
            order_by = "price ASC"
        elif sort_by == 'price_desc':
            order_by = "price DESC"
        elif sort_by == 'save_desc':
            order_by = "save_amount DESC"
        elif sort_by == 'title_asc':
            order_by = "title ASC"

        where_str = f"WHERE {' AND '.join(where_clauses)}"

        # Count total
        count_sql = f"SELECT COUNT(*) FROM specials {where_str}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]

        select_sql = f'''
            SELECT * FROM specials
            {where_str}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        '''
        params_with_paging = params + [limit, offset]
        cursor.execute(select_sql, params_with_paging)
        rows = []
        for row in cursor.fetchall():
            d = dict(row)
            if 'translations' in d and isinstance(d['translations'], str):
                try:
                    import json
                    d['translations'] = json.loads(d['translations'])
                except Exception:
                    pass
            rows.append(d)

        return {
            'total': total,
            'period': period,
            'limit': limit,
            'offset': offset,
            'items': rows
        }

def is_half_price(price, was_price, save_amount, discount_desc) -> bool:
    """Same rule as isItemHalfPrice() in static/app.js."""
    desc = (discount_desc or '').lower()
    if '1/2' in desc or 'half price' in desc or '50%' in desc:
        return True
    price = float(price or 0); was = float(was_price or 0); save = float(save_amount or 0)
    eff_was = was if was > 0 else (price + save if save > 0 else 0)
    if eff_was > 0 and price > 0 and (eff_was - price) / eff_was >= 0.495:
        return True
    if save > 0 and price > 0 and save >= price - 0.05 and save / (price + save) >= 0.495:
        return True
    return False

def get_stats() -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Current stats
        cursor.execute("SELECT store, COUNT(*) as count FROM specials WHERE period = 'current' AND (save_amount > 0 OR was_price > price OR store = 'ALDI') AND price > 0 GROUP BY store")
        counts_current = {row['store']: row['count'] for row in cursor.fetchall()}

        cursor.execute("SELECT category, COUNT(*) as count FROM specials WHERE period = 'current' AND (save_amount > 0 OR was_price > price OR store = 'ALDI') AND price > 0 GROUP BY category")
        cats_current = {row['category']: row['count'] for row in cursor.fetchall()}
        
        # Next week stats
        cursor.execute("SELECT store, COUNT(*) as count FROM specials WHERE period = 'next' AND (save_amount > 0 OR was_price > price OR store = 'ALDI') AND price > 0 GROUP BY store")
        counts_next = {row['store']: row['count'] for row in cursor.fetchall()}

        cursor.execute("SELECT category, COUNT(*) as count FROM specials WHERE period = 'next' AND (save_amount > 0 OR was_price > price OR store = 'ALDI') AND price > 0 GROUP BY category")
        cats_next = {row['category']: row['count'] for row in cursor.fetchall()}

        # Half-price count uses exactly the same rule as the website's "1/2 price only" filter
        cursor.execute("SELECT period, store, price, was_price, save_amount, discount_desc FROM specials WHERE (save_amount > 0 OR was_price > price OR store = 'ALDI') AND price > 0")
        half_counts = {'current': 0, 'next': 0}
        for r in cursor.fetchall():
            if r['store'] != 'ALDI' and not (r['save_amount'] or 0) > 0:
                continue
            if is_half_price(r['price'], r['was_price'], r['save_amount'], r['discount_desc']):
                half_counts[r['period']] = half_counts.get(r['period'], 0) + 1
        half_price_current = half_counts.get('current', 0)
        half_price_next = half_counts.get('next', 0)

        cursor.execute("SELECT COUNT(*) FROM specials WHERE period = 'current' AND (save_amount > 0 OR was_price > price OR store = 'ALDI') AND price > 0")
        total_current = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM specials WHERE period = 'next' AND (save_amount > 0 OR was_price > price OR store = 'ALDI') AND price > 0")
        total_next = cursor.fetchone()[0]

        cursor.execute('SELECT key, value FROM metadata')
        meta = {row['key']: row['value'] for row in cursor.fetchall()}

        return {
            'current': {
                'total': total_current,
                'by_store': counts_current,
                'by_category': cats_current,
                'half_price_count': half_price_current,
                'date_range': meta.get('date_range_current', '本週特價檔期')
            },
            'next': {
                'total': total_next,
                'by_store': counts_next,
                'by_category': cats_next,
                'half_price_count': half_price_next,
                'date_range': meta.get('date_range_next', '下週特價預告') if total_next > 0 else '下週型錄尚未公佈'
            },
            'last_updated': meta.get('last_updated_all', '尚未更新')
        }

def get_shopping_list() -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM shopping_list ORDER BY store, id DESC')
        return [dict(row) for row in cursor.fetchall()]

def add_to_shopping_list(item: Dict[str, Any]) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        price = float(item.get('price', 0.0) or 0.0)
        was_price = float(item.get('was_price', 0.0) or 0.0)
        save_amount = float(item.get('save_amount', 0.0) or 0.0)
        if was_price > price > 0 and save_amount <= 0:
            save_amount = round(was_price - price, 2)
        elif save_amount > 0 and was_price <= 0 and price > 0:
            was_price = round(price + save_amount, 2)

        cursor.execute('''
            INSERT INTO shopping_list (
                product_id, store, period, date_range, title, price, price_display,
                quantity, is_bought, image_url, save_amount, was_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.get('product_id'),
            item.get('store', 'Other'),
            item.get('period', 'current'),
            item.get('date_range', ''),
            item.get('title', ''),
            price,
            item.get('price_display', ''),
            item.get('quantity', 1),
            0,
            item.get('image_url', ''),
            save_amount,
            was_price
        ))
        conn.commit()
        return cursor.lastrowid

def toggle_shopping_item(item_id: int, is_bought: bool):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE shopping_list SET is_bought = ? WHERE id = ?', (1 if is_bought else 0, item_id))
        conn.commit()

def delete_shopping_item(item_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM shopping_list WHERE id = ?', (item_id,))
        conn.commit()

def clear_shopping_list(store: Optional[str] = None):
    with get_db() as conn:
        cursor = conn.cursor()
        if store:
            cursor.execute('DELETE FROM shopping_list WHERE store = ?', (store,))
        else:
            cursor.execute('DELETE FROM shopping_list')
        conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized at", DB_PATH)
