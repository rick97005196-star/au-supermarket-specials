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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'static', 'data')
TRANSLATIONS_FILE = os.path.join(DATA_DIR, 'translations.json')
SPECIALS_FILE = os.path.join(DATA_DIR, 'specials.json')

# Grocery dictionary fallback for brand/food terms
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
    """
    Query Google Translate free single-text translation API.
    target_lang: 'zh-TW' (Traditional Chinese), 'ja' (Japanese), 'ko' (Korean)
    """
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
    except Exception as e:
        return None

def fallback_translate(text, lang):
    """Simple dictionary substitution fallback if API is unreachable."""
    lower = text.lower()
    for term, tr in GROCERY_TERMS.items():
        if term in lower:
            return f"{text} ({tr.get(lang, term)})"
    return text

def translate_title(title):
    """Translates an English supermarket product title to zh, ja, ko."""
    # 1. Traditional Chinese
    zh = translate_via_api(title, 'zh-TW')
    time.sleep(0.05)
    
    # 2. Japanese
    ja = translate_via_api(title, 'ja')
    time.sleep(0.05)
    
    # 3. Korean
    ko = translate_via_api(title, 'ko')
    time.sleep(0.05)

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

    # 2. Load specials.json
    if not os.path.exists(SPECIALS_FILE):
        print(f"Error: {SPECIALS_FILE} does not exist. Run export_static_data.py first.")
        return

    with open(SPECIALS_FILE, 'r', encoding='utf-8') as f:
        specials = json.load(f)

    # 3. Detect missing or untranslated items
    missing_titles = []
    for it in specials:
        title = it.get('title', '').strip()
        if not title:
            continue
        if title not in translations:
            missing_titles.append(title)
        else:
            tr = translations[title]
            # Check if any translation is missing or identical to raw English title (unless title is numeric)
            if not tr.get('zh') or not tr.get('ja') or not tr.get('ko'):
                missing_titles.append(title)
            elif tr.get('zh') == title and not title.replace(' ', '').isdigit():
                # Untranslated fallback
                missing_titles.append(title)

    missing_titles = list(dict.fromkeys(missing_titles))
    print(f"Specials count: {len(specials)}. Missing or untranslated: {len(missing_titles)}")

    # 4. Automatically translate missing items
    if missing_titles:
        print(f"Translating {len(missing_titles)} new items automatically...")
        for i, title in enumerate(missing_titles):
            translated = translate_title(title)
            translations[title] = translated
            if (i + 1) % 10 == 0 or (i + 1) == len(missing_titles):
                print(f"  Translated [{i + 1}/{len(missing_titles)}]: {title[:30]} -> {translated['zh'][:20]}")

        # Save updated translations.json
        with open(TRANSLATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(translations, f, ensure_ascii=False, indent=2)
        print(f"Updated {TRANSLATIONS_FILE} with {len(translations)} total entries.")
    else:
        print("All items are already 100% translated!")

    # 5. Enrich specials.json directly with translations field
    updated_count = 0
    for it in specials:
        t = it.get('title', '').strip()
        if t in translations:
            it['translations'] = translations[t]
            updated_count += 1

    with open(SPECIALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(specials, f, ensure_ascii=False, indent=2)
    print(f"Successfully enriched {updated_count}/{len(specials)} specials with inline translations.")

if __name__ == '__main__':
    run_auto_translate()
