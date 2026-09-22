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
    ORDER BY id ASC
""")
rows = c.fetchall()
items = [dict(r) for r in rows]

with open('static/data/specials.json', 'w', encoding='utf-8') as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"Exported {len(items)} specials to static/data/specials.json")

# Also generate stats.json
import database
stats = database.get_stats()
with open('static/data/stats.json', 'w', encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print("Exported stats to static/data/stats.json")
conn.close()
