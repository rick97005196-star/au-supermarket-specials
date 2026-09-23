import sqlite3
import json
import os

os.makedirs('static/data', exist_ok=True)

conn = sqlite3.connect('data/specials.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("""
    SELECT id, store, period, date_range, category, title, price, price_display,
           unit_price, was_price, save_amount, discount_desc, image_url, product_url
    FROM specials
    WHERE (save_amount > 0 OR (was_price > price AND price > 0)) OR store = 'ALDI'
    ORDER BY id ASC
""")
rows = c.fetchall()
items = [dict(r) for r in rows]

# Load translations if available
trans_path = 'static/data/translations.json'
translations = {}
if os.path.exists(trans_path):
    with open(trans_path, 'r', encoding='utf-8') as f:
        try:
            translations = json.load(f)
        except Exception:
            translations = {}

from categories import classify_product, is_popular_product, calculate_popularity_score

for it in items:
    t = it.get('title', '')
    it['category'] = classify_product(t, it.get('category') or '')
    it['is_popular'] = is_popular_product(t)
    it['popularity_score'] = calculate_popularity_score(it)
    if t in translations:
        it['translations'] = translations[t]

with open('static/data/specials.json', 'w', encoding='utf-8') as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"Exported {len(items)} specials to static/data/specials.json (with translations)")

# Also generate stats.json
import database
stats = database.get_stats()
with open('static/data/stats.json', 'w', encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print("Exported stats to static/data/stats.json")
conn.close()
