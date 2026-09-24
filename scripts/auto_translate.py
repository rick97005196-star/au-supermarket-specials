# -*- coding: utf-8 -*-
"""
Automatic Grocery Translator for AU Supermarket Specials with Google Gemini API & Multi-tier Fallback.
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
ENV_FILE = os.path.join(BASE_DIR, '.env')

def load_env():
    """Load variables from .env file if present."""
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            print(f"[WARN] Failed to read .env file: {e}")

load_env()

def get_gemini_api_key():
    return os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or ''

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

# Post-processing glossary guard to fix notorious machine translation blunders
KNOWN_TRANSLATION_REPAIRS = [
    # Pet items where "Adult" becomes "成人"
    (r'成人(?=狗|犬|貓|寵物|糧|飼料)', '成犬/成貓'),
    (r'超級外套\s*成人', 'Supercoat 成犬'),
    (r'超級外套', 'Supercoat'),
    # Peters Drumstick cone ice cream
    (r'彼得斯(?:的)?(?:小?雞腿|雞腿)', 'Peters Drumstick 甜筒冰淇淋'),
    (r'棒棒糖\s*冰淇淋', 'Drumstick 甜筒冰淇淋'),
    # Continental soup
    (r'歐洲大陸湯|大陸湯', 'Continental 濃湯調理包'),
    (r'大陸\s*義大利麵', 'Continental 義大利麵料理包'),
    # Arnott's Shapes
    (r'阿諾特(?:的)?形狀|形狀餅乾', "Arnott's Shapes 鹹脆餅乾"),
    (r'形狀\s*披薩', 'Shapes 披薩風味鹹餅乾'),
    # Cold Power laundry detergent
    (r'冷能(?=洗衣|液|粉)?|寒冷力量', 'Cold Power 強效洗衣精'),
    # Morning Fresh dishwashing liquid
    (r'早晨新鮮', 'Morning Fresh 洗碗精'),
    # Fairy Platinum Plus
    (r'仙女鉑金', 'Fairy 高效洗碗膠囊'),
    # Twinings tea
    (r'川寧', 'Twinings 唐寧茶'),
    # Bega Cheese
    (r'貝加', 'Bega 起司/乳酪'),
    # Sirena Tuna
    (r'塞雷娜', 'Sirena 頂級鮪魚罐頭')
]

def clean_translated_text(text, orig_title):
    if not text:
        return text
    clean = text.strip()
    clean = re.sub(r'[\r\n]+', ' ', clean)
    for pattern, repl in KNOWN_TRANSLATION_REPAIRS:
        clean = re.sub(pattern, repl, clean)
    return clean

# 1. Gemini AI Batch Translator (High Precision, Domain Aware)
def translate_batch_with_gemini(titles, api_key):
    """
    Translates up to 30 titles at once with Google Gemini 2.5 Flash API.
    Returns a dict mapping original title -> {'zh': ..., 'ja': ..., 'ko': ...}.
    """
    if not api_key or not titles:
        return {}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    system_instruction = (
        "You are an expert translator and Australian supermarket merchandiser. "
        "Translate Australian grocery titles into: "
        "1. 'zh': Traditional Chinese (Taiwan/Hong Kong style, friendly for backpackers and locals in Australia). "
        "Keep famous brand names (e.g. Arnott's, Tim Tam, Vegemite, Moccona, Finish, Fairy, Connoisseur, Peters Drumstick) "
        "intact with concise Chinese descriptors. Translate grocery cuts, flavors, and packaging accurately "
        "(e.g., 'Adult Dog Food' -> '成犬乾糧', NOT '成人'). "
        "2. 'ja': Japanese supermarket grocery style. "
        "3. 'ko': Korean supermarket grocery style. "
        "Output MUST be a JSON array of objects with keys: 'title', 'zh', 'ja', 'ko'."
    )

    prompt_payload = [
        {"title": t} for t in titles
    ]

    body = {
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [
            {
                "parts": [
                    {"text": f"Translate the following Australian grocery items:\n{json.dumps(prompt_payload, ensure_ascii=False)}"}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        }
    }

    try:
        data_bytes = json.dumps(body).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_data = json.loads(resp.read().decode('utf-8'))
            candidates = resp_data.get('candidates', [])
            if not candidates:
                return {}
            text_content = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            parsed_list = json.loads(text_content)
            
            results = {}
            for item in parsed_list:
                orig = item.get('title')
                if orig:
                    results[orig] = {
                        'zh': clean_translated_text(item.get('zh', orig), orig),
                        'ja': clean_translated_text(item.get('ja', orig), orig),
                        'ko': clean_translated_text(item.get('ko', orig), orig)
                    }
            return results
    except Exception as e:
        print(f"[WARN] Gemini batch translation failed: {e}")
        return {}

# 2. Free Google Translate Fallback
def translate_via_free_api(text, target_lang):
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

def translate_single_fallback(title):
    zh = translate_via_free_api(title, 'zh-TW')
    time.sleep(0.03)
    ja = translate_via_free_api(title, 'ja')
    time.sleep(0.03)
    ko = translate_via_free_api(title, 'ko')
    time.sleep(0.03)
    return {
        'zh': clean_translated_text(zh or fallback_translate(title, 'zh'), title),
        'ja': clean_translated_text(ja or fallback_translate(title, 'ja'), title),
        'ko': clean_translated_text(ko or fallback_translate(title, 'ko'), title)
    }

def run_auto_translate():
    print("=== Checking Multilingual Translation Coverage ===")
    os.makedirs(DATA_DIR, exist_ok=True)
    gemini_key = get_gemini_api_key()

    if gemini_key:
        print("[AI] Gemini API Key detected! Using Google Gemini 2.5 Flash for high-precision context translation.")
    else:
        print("[INFO] GEMINI_API_KEY not set in .env or environment. Using intelligent rule-based glossary and fallback translator.")
        print("       (Tip: Add GEMINI_API_KEY to your .env or GitHub Secrets for 100% human-grade AI translations)")

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
            try:
                specials = json.load(f)
            except Exception:
                specials = []

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
        # Check if missing or broken
        if not tr or not tr.get('zh') or not tr.get('ja') or not tr.get('ko'):
            missing_titles.append(title)
        elif tr.get('zh') == title and not title.replace(' ', '').isdigit():
            missing_titles.append(title)
        elif '成人' in tr.get('zh', '') and ('dog' in title.lower() or 'cat' in title.lower() or 'pet' in title.lower()):
            missing_titles.append(title)

    missing_titles = list(dict.fromkeys(missing_titles))
    print(f"Total titles: {len(titles_to_check)}. Missing, flawed, or untranslated: {len(missing_titles)}")

    # 4. Translate missing items
    if missing_titles:
        if gemini_key:
            print(f"Translating {len(missing_titles)} items with Gemini AI batch engine...")
            BATCH_SIZE = 25
            for i in range(0, len(missing_titles), BATCH_SIZE):
                batch = missing_titles[i:i + BATCH_SIZE]
                print(f"  Batch {i//BATCH_SIZE + 1}/{(len(missing_titles) + BATCH_SIZE - 1)//BATCH_SIZE} ({len(batch)} items)...")
                batch_res = translate_batch_with_gemini(batch, gemini_key)
                
                # Check for any items that failed in batch
                for t in batch:
                    if t in batch_res:
                        translations[t] = batch_res[t]
                    else:
                        translations[t] = translate_single_fallback(t)
                time.sleep(1.0)
        else:
            print(f"Translating {len(missing_titles)} new items concurrently via fallback...")
            workers = min(8, len(missing_titles))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(translate_single_fallback, t): t for t in missing_titles}
                count = 0
                for fut in as_completed(futures):
                    t = futures[fut]
                    try:
                        res = fut.result()
                        if res:
                            translations[t] = res
                    except Exception as err:
                        print(f"Failed fallback for {t}: {err}")
                    count += 1
                    if count % 20 == 0 or count == len(missing_titles):
                        print(f"  Translated [{count}/{len(missing_titles)}]")

        # Run glossary cleanup on all translations to ensure zero defects
        for t, tr in translations.items():
            if tr and isinstance(tr, dict):
                tr['zh'] = clean_translated_text(tr.get('zh', ''), t)

        # Save updated translations.json
        with open(TRANSLATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(translations, f, ensure_ascii=False, indent=2)
        print(f"Updated {TRANSLATIONS_FILE} with {len(translations)} total entries.")
    else:
        print("All items are already 100% translated!")
        # Run cleaner across existing to fix any known defects
        fixed_count = 0
        for t, tr in translations.items():
            if tr and isinstance(tr, dict):
                old_zh = tr.get('zh', '')
                new_zh = clean_translated_text(old_zh, t)
                if old_zh != new_zh:
                    tr['zh'] = new_zh
                    fixed_count += 1
        if fixed_count > 0:
            with open(TRANSLATIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(translations, f, ensure_ascii=False, indent=2)
            print(f"Cleaned {fixed_count} existing translations with grocery glossary.")

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
        c.execute("PRAGMA table_info(specials)")
        cols = [col[1] for col in c.fetchall()]
        if 'translations' not in cols:
            c.execute("ALTER TABLE specials ADD COLUMN translations TEXT")
        
        for title, tr in translations.items():
            tr_json = json.dumps(tr, ensure_ascii=False)
            c.execute("UPDATE specials SET translations = ? WHERE title = ?", (tr_json, title))
        conn.commit()
        conn.close()
        print("Synced translations into SQLite specials.db.")

if __name__ == '__main__':
    run_auto_translate()
