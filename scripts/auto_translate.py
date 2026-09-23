# -*- coding: utf-8 -*-
"""
Automatic Grocery Translator for AU Supermarket Specials
Runs during weekly updates (GitHub Actions or local) to ensure 100% translation
coverage in Traditional Chinese (zh), Japanese (ja), and Korean (ko) for all items.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DATA_DIR = os.path.join(BASE_DIR, 'static', 'data')
TRANSLATIONS_FILE = os.path.join(DATA_DIR, 'translations.json')
SPECIALS_FILE = os.path.join(DATA_DIR, 'specials.json')
DB_FILE = os.path.join(BASE_DIR, 'data', 'specials.db')

GROCERY_TERMS = {
    'milk': {'zh': '牛奶', 'ja': '牛乳', 'ko': '우유'},
    'eggs': {'zh': '雞蛋', 'ja': '卵', 'ko': '계란'},
    'egg': {'zh': '雞蛋', 'ja': '卵', 'ko': '계란'},
    'butter': {'zh': '奶油', 'ja': 'バター', 'ko': '버터'},
    'cheese': {'zh': '起司', 'ja': 'チーズ', 'ko': '치즈'},
    'bread': {'zh': '麵包', 'ja': 'パン', 'ko': '식빵'},
    'chicken': {'zh': '雞肉', 'ja': '鶏肉', 'ko': '닭고기'},
    'beef': {'zh': '牛肉', 'ja': '牛肉', 'ko': '소고기'},
    'pork': {'zh': '豬肉', 'ja': '豚肉', 'ko': '돼지고기'},
    'lamb': {'zh': '羊肉', 'ja': '羊肉', 'ko': '양고기'},
    'salmon': {'zh': '鮭魚', 'ja': 'サーモン', 'ko': '연어'},
    'tuna': {'zh': '鮪魚', 'ja': 'ツナ', 'ko': '참치'},
    'prawns': {'zh': '鮮蝦', 'ja': 'エビ', 'ko': '새우'},
    'apples': {'zh': '蘋果', 'ja': 'りんご', 'ko': '사과'},
    'bananas': {'zh': '香蕉', 'ja': 'バナナ', 'ko': '바나나'},
    'potatoes': {'zh': '馬鈴薯', 'ja': 'じゃがいも', 'ko': '감자'},
    'tomatoes': {'zh': '番茄', 'ja': 'トマト', 'ko': '토마토'},
    'chocolate': {'zh': '巧克力', 'ja': 'チョコレート', 'ko': '초콜릿'},
    'chips': {'zh': '洋芋片', 'ja': 'ポテトチップス', 'ko': '감자칩'},
    'coffee': {'zh': '咖啡', 'ja': 'コーヒー', 'ko': '커피'},
    'tea': {'zh': '茶', 'ja': 'お茶', 'ko': '차'},
    'water': {'zh': '水', 'ja': '水', 'ko': '생수'},
    'juice': {'zh': '果汁', 'ja': 'ジュース', 'ko': '주스'},
    'ice cream': {'zh': '冰淇淋', 'ja': 'アイスクリーム', 'ko': '아이스크림'},
    'shampoo': {'zh': '洗髮精', 'ja': 'シャンプー', 'ko': '샴푸'},
    'conditioner': {'zh': '潤髮乳', 'ja': 'コンディショナー', 'ko': '린스/컨디셔너'},
    'body wash': {'zh': '沐浴乳', 'ja': 'ボディウォッシュ', 'ko': '바디워시'},
    'toothpaste': {'zh': '牙膏', 'ja': '歯磨き粉', 'ko': '치약'},
    'laundry liquid': {'zh': '洗衣精', 'ja': '液体洗剤', 'ko': '액체 세탁세제'},
    'laundry powder': {'zh': '洗衣粉', 'ja': '粉末洗剤', 'ko': '분말 세탁세제'},
    'dishwashing liquid': {'zh': '洗碗精', 'ja': '食器用洗剤', 'ko': '주방세제'},
    'toilet paper': {'zh': '衛生紙', 'ja': 'トイレットペーパー', 'ko': '두루마리 화장지'},
    'paper towel': {'zh': '廚房紙巾', 'ja': 'キッチンペーパー', 'ko': '키친타월'}
}

def translate_via_api(text, target_lang):
    """Query Google Translate free single-text translation API."""
    try:
        encoded = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={target_lang}&dt=t&q={encoded}"
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            translated_segments = []
            if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                for seg in data[0]:
                    if seg and len(seg) > 0 and seg[0]:
                        translated_segments.append(seg[0])
            result = "".join(translated_segments).strip()
            return result if result else text
    except Exception:
        return None

def fallback_translate(text, lang):
    lower = text.lower()
    for term, tr in GROCERY_TERMS.items():
        if term in lower:
            return f"{text} ({tr.get(lang, term)})"
    return text

def translate_title(title):
    zh = translate_via_api(title, 'zh-TW')
    time.sleep(0.04)
    ja = translate_via_api(title, 'ja')
    time.sleep(0.04)
    ko = translate_via_api(title, 'ko')
    time.sleep(0.04)
    return {
        'zh': zh or fallback_translate(title, 'zh'),
        'ja': ja or fallback_translate(title, 'ja'),
        'ko': ko or fallback_translate(title, 'ko')
    }

def run_auto_translate():
    print("=== Checking Multilingual Translation Coverage ===")
    os.makedirs(DATA_DIR, exist_ok=True)

    # 1. Load existing translations
    translations = {}
    if os.path.exists(TRANSLATIONS_FILE):
        with open(TRANSLATIONS_FILE, 'r', encoding='utf-8') as f:
            try:
                translations = json.load(f)
            except Exception:
                translations = {}
    print(f"Existing translations database contains {len(translations)} entries.")

    # 2. Load specials from DB or specials.json
    specials = []
    if os.path.exists(SPECIALS_FILE):
        with open(SPECIALS_FILE, 'r', encoding='utf-8') as f:
            specials = json.load(f)

    titles_to_check = set()
    for s in specials:
        t = s.get('title', '').strip()
        if t:
            titles_to_check.add(t)

    # Also check sqlite DB directly
    if os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT DISTINCT title FROM specials WHERE title IS NOT NULL AND title != ''")
        for r in c.fetchall():
            titles_to_check.add(r[0].strip())
        conn.close()

    # 3. Detect missing or untranslated items
    missing_titles = []
    for title in titles_to_check:
        tr = translations.get(title)
        if not tr or not tr.get('zh') or not tr.get('ja') or not tr.get('ko') or (tr.get('zh') == title and not title.replace(' ', '').isdigit()):
            missing_titles.append(title)

    missing_titles = list(dict.fromkeys(missing_titles))
    print(f"Total titles: {len(titles_to_check)}. Missing or untranslated: {len(missing_titles)}")

    # 4. Concurrently translate missing items
    if missing_titles:
        print(f"Translating {len(missing_titles)} new items concurrently...")
        workers = min(8, len(missing_titles))
        
        def task(title):
            try:
                return title, translate_title(title)
            except Exception:
                return title, None

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(task, t): t for t in missing_titles}
            count = 0
            for fut in as_completed(futures):
                t, res = fut.result()
                if res:
                    translations[t] = res
                count += 1
                if count % 20 == 0 or count == len(missing_titles):
                    print(f"  Translated [{count}/{len(missing_titles)}]")

        # Save updated translations.json
        with open(TRANSLATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(translations, f, ensure_ascii=False, indent=2)
        print(f"Updated {TRANSLATIONS_FILE} with {len(translations)} total entries.")
    else:
        print("All items are already 100% translated!")

    # 5. Enrich specials.json directly with translations field
    if specials:
        updated_count = 0
        for it in specials:
            t = it.get('title', '').strip()
            if t in translations:
                it['translations'] = translations[t]
                updated_count += 1

        with open(SPECIALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(specials, f, ensure_ascii=False, indent=2)
        print(f"Successfully enriched {updated_count}/{len(specials)} specials with inline translations.")

    # 6. Update SQLite translations column
    if os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        for title, tr in translations.items():
            tr_json = json.dumps(tr, ensure_ascii=False)
            c.execute("UPDATE specials SET translations = ? WHERE title = ? AND (translations IS NULL OR translations = '')", (tr_json, title))
        conn.commit()
        conn.close()

if __name__ == '__main__':
    run_auto_translate()
