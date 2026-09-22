import sqlite3
import os
import html
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
        # Check and migrate columns if table already existed
        cursor.execute("PRAGMA table_info(specials)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'period' not in columns:
            cursor.execute("ALTER TABLE specials ADD COLUMN period TEXT NOT NULL DEFAULT 'current'")
        if 'date_range' not in columns:
            cursor.execute("ALTER TABLE specials ADD COLUMN date_range TEXT")

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

from categories import classify_product

def save_specials(store: str, items: List[Dict[str, Any]], period: str = 'current', date_range: str = ''):
    """Replace specials for a given store and period (current / next) with the newly scraped list."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM specials WHERE store = ? AND period = ?', (store, period))
        
        insert_sql = '''
            INSERT INTO specials (
                store, period, date_range, title, price, price_display, was_price, save_amount,
                discount_desc, unit_price, image_url, category, product_url, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        rows = []
        seen_keys = set()
        for item in items:
            if not item.get('title'):
                continue
            title = html.unescape(item.get('title', '')).strip()
            p_url = item.get('product_url', '')
            dedup_key = (title.lower(), p_url) if p_url else title.lower()
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            price = float(item.get('price', 0.0) or 0.0)
            was_price = float(item.get('was_price', 0.0) or 0.0)
            save_amount = float(item.get('save_amount', 0.0) or 0.0)
            discount_desc = html.unescape(item.get('discount_desc', '') or '').strip()

            if was_price > price > 0 and save_amount <= 0:
                save_amount = round(was_price - price, 2)
            elif save_amount > 0 and was_price <= 0 and price > 0:
                was_price = round(price + save_amount, 2)

            lower_desc = discount_desc.lower()
            if lower_desc.startswith('offers apply') or 'while stocks last' in lower_desc or 'specials not available' in lower_desc:
                discount_desc = f"Save ${save_amount:.2f}" if save_amount > 0 else ""
            elif not discount_desc and save_amount > 0:
                discount_desc = f"Save ${save_amount:.2f}"

            # Only keep products that have a real discount (ALDI Super Savers & Special Buys are included)
            if store != 'ALDI' and save_amount <= 0 and (was_price <= price or was_price == 0):
                continue

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
                classify_product(title, item.get('category', ''), item.get('product_url', '')),
                item.get('product_url', ''),
                now
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

        if category and category.lower() != 'all':
            where_clauses.append('category = ?')
            params.append(category)

        where_str = f"WHERE {' AND '.join(where_clauses)}"

        # Count total
        count_sql = f"SELECT COUNT(*) FROM specials {where_str}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]

        # Sorting
        order_by = "id ASC"
        if sort_by == 'price_asc':
            order_by = "price ASC"
        elif sort_by == 'price_desc':
            order_by = "price DESC"
        elif sort_by == 'save_desc':
            order_by = "save_amount DESC"
        elif sort_by == 'title_asc':
            order_by = "title ASC"

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

def get_stats() -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Current stats
        cursor.execute("SELECT store, COUNT(*) as count FROM specials WHERE period = 'current' AND (save_amount > 0 OR was_price > price OR store = 'ALDI') GROUP BY store")
        counts_current = {row['store']: row['count'] for row in cursor.fetchall()}

        cursor.execute("SELECT category, COUNT(*) as count FROM specials WHERE period = 'current' AND (save_amount > 0 OR was_price > price OR store = 'ALDI') GROUP BY category")
        cats_current = {row['category']: row['count'] for row in cursor.fetchall()}
        
        # Next week stats
        cursor.execute("SELECT store, COUNT(*) as count FROM specials WHERE period = 'next' AND (save_amount > 0 OR was_price > price OR store = 'ALDI') GROUP BY store")
        counts_next = {row['store']: row['count'] for row in cursor.fetchall()}

        cursor.execute("SELECT category, COUNT(*) as count FROM specials WHERE period = 'next' AND (save_amount > 0 OR was_price > price OR store = 'ALDI') GROUP BY category")
        cats_next = {row['category']: row['count'] for row in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) FROM specials WHERE period = 'current' AND (save_amount > 0 OR was_price > price OR store = 'ALDI') AND (discount_desc LIKE '%1/2%' OR discount_desc LIKE '%half%')")
        half_price_current = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM specials WHERE period = 'next' AND (save_amount > 0 OR was_price > price OR store = 'ALDI') AND (discount_desc LIKE '%1/2%' OR discount_desc LIKE '%half%')")
        half_price_next = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM specials WHERE period = 'current' AND (save_amount > 0 OR was_price > price OR store = 'ALDI')")
        total_current = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM specials WHERE period = 'next' AND (save_amount > 0 OR was_price > price OR store = 'ALDI')")
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
