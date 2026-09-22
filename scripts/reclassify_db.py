import sqlite3
import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from categories import classify_product

sys.stdout.reconfigure(encoding='utf-8')

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'specials.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Get before counts
c.execute("SELECT category, count(*) FROM specials GROUP BY category ORDER BY count(*) DESC")
print("=== BEFORE RECLASSIFICATION ===")
for cat, cnt in c.fetchall():
    print(f"  {cat:16}: {cnt}")

c.execute("SELECT id, title, category, product_url FROM specials")
rows = c.fetchall()

updated = 0
for row_id, title, old_cat, prod_url in rows:
    new_cat = classify_product(title, old_cat, prod_url or "")
    if new_cat != old_cat:
        c.execute("UPDATE specials SET category = ? WHERE id = ?", (new_cat, row_id))
        updated += 1

conn.commit()

# Get after counts
c.execute("SELECT category, count(*) FROM specials GROUP BY category ORDER BY count(*) DESC")
print(f"\n=== AFTER RECLASSIFICATION ({updated} / {len(rows)} items updated) ===")
for cat, cnt in c.fetchall():
    print(f"  {cat:16}: {cnt}")

print("\n=== BREAKDOWN BY STORE & CATEGORY ===")
c.execute("SELECT store, category, count(*) FROM specials GROUP BY store, category ORDER BY store, count(*) DESC")
for store, cat, cnt in c.fetchall():
    print(f"  [{store:10}] {cat:16}: {cnt}")

conn.close()
