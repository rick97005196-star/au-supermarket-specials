# -*- coding: utf-8 -*-
import sys
import os
import json
import time
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

STATIC_DATA_DIR = os.path.join(BASE_DIR, 'static', 'data')
TRANSLATIONS_FILE = os.path.join(STATIC_DATA_DIR, 'translations.json')
SPECIALS_FILE = os.path.join(STATIC_DATA_DIR, 'specials.json')
DB_FILE = os.path.join(BASE_DIR, 'data', 'specials.db')

from scripts.auto_translate import translate_title

def main():
    print("=== Starting Batch Translation for All Untranslated Items ===")
    
    # 1. Load translations.json
    translations = {}
    if os.path.exists(TRANSLATIONS_FILE):
        with open(TRANSLATIONS_FILE, 'r', encoding='utf-8') as f:
            translations = json.load(f)
    print(f"Loaded {len(translations)} existing translations.")

    # 2. Load specials.json
    with open(SPECIALS_FILE, 'r', encoding='utf-8') as f:
        specials = json.load(f)
    print(f"Loaded {len(specials)} specials from specials.json.")

    # 3. Identify missing items
    missing_titles = []
    for s in specials:
        t = s.get('title', '').strip()
        if not t:
            continue
        tr = translations.get(t)
        if not tr or not tr.get('zh') or not tr.get('ja') or not tr.get('ko') or tr.get('zh') == t:
            missing_titles.append(t)

    unique_missing = list(dict.fromkeys(missing_titles))
    total_missing = len(unique_missing)
    print(f"Total unique items requiring translation: {total_missing}")

    if total_missing == 0:
        print("All items are already 100% translated!")
        return

    # 4. Concurrently translate
    workers = 8
    print(f"Translating {total_missing} items using {workers} concurrent workers...")
    
    completed = 0
    save_interval = 50
    start_time = time.time()

    def translate_task(title):
        try:
            res = translate_title(title)
            return title, res, None
        except Exception as e:
            return title, None, str(e)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(translate_task, title): title for title in unique_missing}
        
        for future in as_completed(futures):
            title, res, err = future.result()
            completed += 1
            if res:
                translations[title] = res
            
            if completed % 25 == 0 or completed == total_missing:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (total_missing - completed) / rate if rate > 0 else 0
                zh_sample = res.get('zh', '') if res else 'ERROR'
                print(f"[{completed}/{total_missing}] ({completed/total_missing*100:.1f}%) "
                      f"Speed: {rate:.1f} items/s | ETA: {eta:.0f}s | Sample: {title[:20]} -> {zh_sample[:15]}")

            # Intermediate save
            if completed % save_interval == 0 or completed == total_missing:
                with open(TRANSLATIONS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(translations, f, ensure_ascii=False, indent=2)

    total_time = time.time() - start_time
    print(f"Translation complete in {total_time:.1f}s! ({completed}/{total_missing} processed)")

    # 5. Update specials.json
    print("Updating static/data/specials.json...")
    enriched_count = 0
    for s in specials:
        t = s.get('title', '').strip()
        if t in translations:
            s['translations'] = translations[t]
            enriched_count += 1

    with open(SPECIALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(specials, f, ensure_ascii=False, indent=2)
    print(f"Successfully updated specials.json: {enriched_count}/{len(specials)} specials have translations.")

    # 6. Update specials.db SQLite database
    if os.path.exists(DB_FILE):
        print("Updating SQLite database data/specials.db...")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        db_updates = 0
        for title, tr in translations.items():
            tr_json = json.dumps(tr, ensure_ascii=False)
            cursor.execute("UPDATE specials SET translations = ? WHERE title = ?", (tr_json, title))
            db_updates += cursor.rowcount

        conn.commit()
        conn.close()
        print(f"SQLite database updated ({db_updates} rows updated).")

    print("=== All translation tasks completed successfully! ===")

if __name__ == '__main__':
    main()
