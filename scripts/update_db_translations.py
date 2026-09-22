# -*- coding: utf-8 -*-
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'specials.db')
TRANSLATIONS_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'data', 'translations.json')

if os.path.exists(DB_PATH) and os.path.exists(TRANSLATIONS_PATH):
    with open(TRANSLATIONS_PATH, 'r', encoding='utf-8') as f:
        translations = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if translations column exists
    cursor.execute("PRAGMA table_info(specials)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'translations' not in columns:
        cursor.execute("ALTER TABLE specials ADD COLUMN translations TEXT")
        conn.commit()

    # Update translations in database
    cursor.execute("SELECT id, title FROM specials")
    rows = cursor.fetchall()
    updated = 0
    for row_id, title in rows:
        if title in translations:
            trans_json = json.dumps(translations[title], ensure_ascii=False)
            cursor.execute("UPDATE specials SET translations = ? WHERE id = ?", (trans_json, row_id))
            updated += 1

    conn.commit()
    conn.close()
    print(f"Updated {updated} records in specials.db with translations JSON.")
else:
    print("Database or translations file not found.")
