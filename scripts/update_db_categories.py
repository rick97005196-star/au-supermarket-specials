# -*- coding: utf-8 -*-
import sys
import os
import sqlite3
import json

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from categories import classify_product

DB_FILE = os.path.join(BASE_DIR, 'data', 'specials.db')

def update_categories():
    print("=== Updating Categories in data/specials.db ===")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT id, title, category, product_url FROM specials")
    rows = c.fetchall()

    changed = 0
    cat_counts = {}
    for row_id, title, old_cat, product_url in rows:
        new_cat = classify_product(title, old_cat or '', product_url or '')
        cat_counts[new_cat] = cat_counts.get(new_cat, 0) + 1
        if new_cat != old_cat:
            c.execute("UPDATE specials SET category = ? WHERE id = ?", (new_cat, row_id))
            changed += 1

    conn.commit()
    conn.close()

    print(f"Total rows in DB: {len(rows)}")
    print(f"Reclassified rows: {changed}")
    print("\nUpdated DB Category Counts:")
    for cat, count in sorted(cat_counts.items()):
        print(f"  {cat:16}: {count}")

if __name__ == '__main__':
    update_categories()
