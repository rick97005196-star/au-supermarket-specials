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
import urllib.error
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
    # Nutella
    (r'費列羅花生醬', '能多益 榛果可可抹醬'),
    (r'(?<!Nutella )(?<!能多益 )榛果可可醬', 'Nutella 榛果可可醬'),
    # Connoisseur ice cream brand & styles
    (r'鑑賞家(?:美食)?(?:冰淇淋)?|行家冰淇淋', 'Connoisseur 頂級雪糕'),
    (r'餅乾和奶油棒', '巧酥雪糕'),
    (r'餅乾和奶油', '巧酥餅乾風味'),
    (r'迷你香草棒', '迷你香草雪糕'),
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
    (r'(?<!Bega )貝加', 'Bega 起司/乳酪'),
    # Sirena Tuna
    (r'塞雷娜', 'Sirena 頂級鮪魚罐頭'),
    # Flavor literal fixes
    (r'蜂蜜大豆和雞肉|大豆和雞肉', '蜂蜜醬油雞汁風味'),
    (r'酸奶油和韭菜', '酸奶油洋蔥口味'),
    # Underwear literal fixes
    (r'男士前軀幹|前軀幹尺寸|泳褲（各裝各裝）|前軀幹', '男款平口四角內褲'),
    (r'各裝各裝', '各款式'),
    # Reduplications
    (r'巧克力棒巧克力棒', '巧克力棒'),
    (r'檸檬檸檬', '檸檬'),
    (r'日式日式', '日式'),
    (r'特大號特大號', '特大號'),
    (r'餅乾餅乾', '薄脆餅乾')
]

def clean_translated_text(text, orig_title):
    if not text:
        return text
    clean = text.strip()
    clean = re.sub(r'[\r\n]+', ' ', clean)
    for pattern, repl in KNOWN_TRANSLATION_REPAIRS:
        clean = re.sub(pattern, repl, clean)
    # an AI glitch repeating the same word ("Nutella Nutella Nutella ...") -> once
    clean = re.sub(r"\b([A-Za-z][\w'’&.-]*)(?:\s+\1\b)+", r"\1", clean)
    return clean


_S2TW = None
def polish_zh(zh):
    """Taiwan wording and Traditional characters, fixed without asking the AI again."""
    global _S2TW
    if not zh:
        return zh
    from scripts.translation_check import simplified_chars, MAINLAND_WORDS
    bad = simplified_chars(zh)
    if bad:
        try:
            if _S2TW is None:
                from opencc import OpenCC
                _S2TW = OpenCC('s2tw')
            for c in bad:
                zh = zh.replace(c, _S2TW.convert(c))
        except Exception:
            pass
    for w, good in MAINLAND_WORDS.items():
        if '/' not in good:
            zh = zh.replace(w, good) if w != '酸奶' else re.sub(r'酸奶(?!油)', '優格', zh)
    return zh

# 1. Gemini AI Batch Translator (High Precision, Domain Aware)
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
# Preferred models, best first. Override with the GEMINI_MODEL env var / GitHub secret.
GEMINI_MODEL_PREFERENCE = [
    # "lite" models have the largest free-tier quota, ideal for bulk product-title translation
    'gemini-3.1-flash-lite', 'gemini-flash-lite-latest', 'gemini-3.5-flash-lite', 'gemini-2.5-flash-lite',
    'gemini-flash-latest', 'gemini-3.5-flash', 'gemini-2.5-flash',
]
_gemini_model_cache = {}
_gemini_state = {'disabled': False}  # set when quota is exhausted, to stop calling for this run

def gh_warning(msg):
    """Print a warning that also shows up as an annotation on the GitHub Actions run page."""
    print(f"::warning::{msg}" if os.environ.get('GITHUB_ACTIONS') else f"[WARN] {msg}")

def _gemini_request(url, api_key, body=None, timeout=60):
    headers = {'Content-Type': 'application/json', 'x-goog-api-key': api_key}
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method='POST' if body is not None else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))

def gemini_model_candidates(api_key):
    """Ordered list of models to try. The key's real model list is used, because hard-coded
    names disappear over time (a missing model silently broke AI translation before)."""
    if api_key in _gemini_model_cache:
        return _gemini_model_cache[api_key]
    wanted = [m for m in [os.environ.get('GEMINI_MODEL', '').strip()] if m] + GEMINI_MODEL_PREFERENCE
    available = []
    try:
        data = _gemini_request(f"{GEMINI_API_BASE}/models?pageSize=200", api_key)
        for m in data.get('models', []):
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                available.append(m['name'].split('/', 1)[-1])
    except Exception as e:
        gh_warning(f"Gemini: could not list models ({e})")
    text_models = [m for m in available if 'gemini' in m and not any(
        x in m for x in ('image', 'tts', 'live', 'audio', 'embedding', 'vision', 'robotics', 'computer-use', 'transcribe', 'omni', 'customtools'))]
    flash = [m for m in text_models if 'flash' in m]
    cands = [m for m in wanted if m in available]
    cands += [m for m in flash if m not in cands]
    cands = list(dict.fromkeys(cands)) or wanted
    print(f"[AI] Gemini candidate models: {', '.join(cands[:8])}")
    if os.environ.get('GITHUB_ACTIONS'):
        print(f"::notice::Gemini models available to this key: {', '.join(text_models[:25]) or 'none listed'}")
    _gemini_model_cache[api_key] = cands
    return cands

TRANSLATION_PROMPT = """You translate Australian supermarket product titles for a Taiwanese audience (working-holiday makers and students in Australia).

For each title return:
- "zh": Traditional Chinese as written in TAIWAN (台灣用語, 繁體字). Never use Simplified characters or Mainland/Hong Kong wording.
- "ja": natural Japanese supermarket wording.
- "ko": natural Korean supermarket wording.

Rules for "zh" (read carefully):
1. BRAND NAMES STAY IN ENGLISH, exactly as written: Smith's, Suntory Boss, Schweppes, Smash, Ingham's, Oreo, Arnott's, Tim Tam, Connoisseur, Bonds, Sistema, Revlon, Swisse, Coles, Woolworths, etc.
   Never translate a brand word literally (Smith's is NOT 史密斯, Boss is NOT 老闆, Smash is NOT 粉碎, Oreo is NOT 奧利奧).
   Only add a Chinese brand name if Taiwanese shoppers really use it (e.g. 可口可樂, 雀巢, 多芬, 露得清), placed after the English brand.
2. Format: <English brand> <short Chinese product name + flavour/variant> <size>. Keep it short like a Taiwanese supermarket (全聯/家樂福) shelf label.
3. Everyday Taiwanese terms: 洋芋片 (chips/crisps), 優格 (yoghurt), 起司 (cheese), 奶油 (butter), 冰淇淋 (ice cream), 餅乾, 汽水, 氣泡水, 通寧水 (tonic water), 麵 (noodles, never 面), 沐浴乳, 洗髮精, 潤髮乳, 洗衣精, 衛生紙, 廚房紙巾.
4. Packaging/size: "Pk 8" / "8 pack" -> 8入; "4 x 375mL" -> 375毫升 x 4入; g -> 克; kg -> 公斤; mL -> 毫升; L/Litre -> 公升; "Size 12" -> 12號.
5. "Assorted" -> 綜合款 (never 什錦); "Varieties"/"Selected varieties" -> 多款口味 (or 多款 for non-food); "each" -> leave out; "or" -> 或.
6. Flavours: "Sour Cream & Chives" -> 酸奶油洋蔥口味, "Honey Soy" -> 蜂蜜醬油口味, "Cookies & Cream" -> 巧克力餅乾奶油口味, "Salt & Vinegar" -> 鹽醋口味.
7. Pet food: "Adult" -> 成犬/成貓 (never 成人). Underwear "Trunk" -> 四角褲. SIM cards, phones and modems keep the product name in English.
8. Output only the translation - no notes, no explanations, no marketing words.
9. Keep EVERY number of the English title: sizes, pack counts, shade/step/size numbers ("Step 3" -> 3階段, "105-120g" -> 105-120克, "Shade 3" -> 3號).
10. Never repeat a word. The brand appears exactly once.
11. Traditional characters only (黃 not 黄, 強 not 强, 麥 not 麦, 蟎 not 螨). Taiwan words: 沐浴乳 (not 沐浴露), 優格 (yoghurt), 酸奶油 (sour cream).
12. Fish and seafood must match the English exactly: salmon=鮭魚, whiting=鱚魚, hoki=藍鱈, barramundi=尖吻鱸, dory=多利魚, basa=巴沙魚, tuna=鮪魚, prawn=蝦, squid/calamari=魷魚/中卷. Never swap one fish or meat for another.
13. If a list of problems is given for a title, the new translation must fix all of them.

Rules for ALL THREE languages (learned from a full human review of 6,000 translations):
14. The brand stays in English letters in "ja" and "ko" too (Cadbury, not キャドバリー / 캐드버리). Shoppers match it to the pack on the Australian shelf.
15. Translate only what the title says. Never add words, claims, sizes or brands that are not there (no 成犬 unless it says Adult, no 無毒/純水/抗菌/冷凍/保濕/經典, no Chinese brand of a DIFFERENT company: Garnier is not 露得清, Cadbury is not 吉力貝, Revlon is not 麗仕). Never drop a variant word that changes the product (Extra Strong, Sugar Free, Zero Carb = 零碳水 not 零碳, Dairy Free ≠ Lactose Free, Permanent, Leave-in, Sensitive, Anti-Fall = 防落髮).
16. Pack counts: "Pk 12" / "12 Pack" = 12 pieces -> zh 12入, ja 12個入/12本入/12枚入 (never 12パック), ko 12개입 (never 12팩). "2 Pack 450g" means 450g in total -> 450克（2入）, not 450克 x 2入. Write a pack count only ONCE ("85g x 12" -> 85克 x 12入, never "85克 x 12入 12入裝").
17. "per kg" means the price is per kilogram -> zh 每公斤 / ja 1kgあたり / ko kg당 (it is NOT a 1 kg pack).
18. Non-food items have a scent, not a flavour: candles, air fresheners, dish liquid, body wash -> 香 / 香り / 향 (never 口味 / 味 / 맛). "Original" on skincare = 經典款 (not 原味).
19. Meat cuts: Scotch Fillet = 肋眼 (rib eye), Rump = 牛臀肉, Porterhouse = 紐約客, Sirloin = 沙朗, Eye Fillet = 菲力, Forequarter Chops = 肩胛排, Loin Chops = 里肌排. "No Added Hormones" = 無添加荷爾蒙 / ホルモン剤不使用 / 호르몬 무첨가.
20. Hosiery & clothing: Tights = 褲襪, Knee Hi = 及膝襪, Footlet = 隱形襪, Brief = 三角褲, Trunk = 四角褲. Australian sizes stay as written ("Size 10" -> 10號 in zh, サイズ10 / 사이즈 10).
21. Taiwan wording in zh: 雷射 (not 激光), 嬌生 (Johnson's), 淡菜 (mussels, not 青口), 聖代 (not 新地), 番茄醬 only for ketchup (pasta sauce = 義大利麵醬).
22. Each field contains only its own language's script (no Korean inside "ja", no Japanese kana inside "zh" or "ko").

Titles:
"""

def translate_batch_with_gemini(titles, api_key, notes=None):
    """
    Translates a batch of titles with the Gemini API.
    Returns a dict mapping original title -> {'zh': ..., 'ja': ..., 'ko': ..., 'src': 'ai'}.
    """
    if not api_key or not titles or _gemini_state['disabled']:
        return {}

    cands = gemini_model_candidates(api_key)
    if not cands:
        return {}
    model = cands[0]
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": TRANSLATION_PROMPT + json.dumps(titles, ensure_ascii=False) +
                                  (("\n\nProblems found in the previous translations (fix every one):\n" +
                                    json.dumps({t: notes[t] for t in titles if notes and t in notes}, ensure_ascii=False))
                                   if notes else '') +
                                  "\n\nRespond with a JSON array of objects with keys: title (copied exactly), zh, ja, ko."}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }

    for attempt in range(8):
        try:
            resp_data = _gemini_request(url, api_key, body)
            candidates = resp_data.get('candidates', [])
            if not candidates:
                gh_warning(f"Gemini returned no candidates: {str(resp_data)[:200]}")
                return {}
            text_content = ''
            for p in candidates[0].get('content', {}).get('parts', []):
                if 'text' in p:
                    text_content = p['text'].strip()
                    break
            if text_content.startswith('```'):
                text_content = re.sub(r'^```(?:json)?\s*', '', text_content)
                text_content = re.sub(r'\s*```$', '', text_content)

            parsed_list = json.loads(text_content)
            wanted = set(titles)
            results = {}
            for item in parsed_list:
                orig = (item.get('title') or '').strip()
                if orig in wanted and item.get('zh'):
                    results[orig] = {
                        'zh': polish_zh(clean_translated_text(item.get('zh') or orig, orig)),
                        'ja': clean_translated_text(item.get('ja') or orig, orig),
                        'ko': clean_translated_text(item.get('ko') or orig, orig),
                        'src': 'ai'
                    }
            return results
        except urllib.error.HTTPError as e:
            detail = ''
            try:
                detail = e.read().decode('utf-8')[:300]
            except Exception:
                pass
            if e.code in (404, 429, 500, 503) and len(cands) > 1:
                gh_warning(f"Gemini model {model} unavailable (HTTP {e.code}), switching to {cands[1]}")
                cands.pop(0)
                model = cands[0]
                url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
                continue
            if e.code in (500, 503) and attempt < 2:
                wait = 15 * (attempt + 1)
                print(f"  Gemini HTTP {e.code}, retrying in {wait}s...")
                time.sleep(wait)
                continue
            gh_warning(f"Gemini translation failed: HTTP {e.code} (model {model}) {detail}")
            if e.code in (400, 401, 403, 404, 429):
                _gemini_state['disabled'] = True  # key/model/quota problem: no point retrying this run
            return {}
        except Exception as e:
            gh_warning(f"Gemini translation failed: {e}")
            return {}
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
    # Keep the original English title when no real translation is available.
    # (Appending a random glossary word like "(茶)" produced confusing titles.)
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
        print("[AI] Gemini API Key detected! Using Google Gemini for high-precision context translation.")
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

    # 2b. A product whose name changed slightly (footnote mark removed, different quote style)
    #     keeps its existing translation instead of showing up untranslated
    from scrapers.regions import clean_title
    _norm = lambda t: re.sub(r'\s+', ' ', clean_title(t or '')).strip().lower()
    by_norm = {}
    for k, v in translations.items():
        by_norm.setdefault(_norm(k), v)
    recovered = 0
    for title in titles_to_check:
        if title not in translations and _norm(title) in by_norm:
            translations[title] = dict(by_norm[_norm(title)])
            recovered += 1
    if recovered:
        print(f"Recovered {recovered} translations for slightly renamed products.")

    # 2c. Quality check: fix what can be fixed without AI (Traditional characters, Taiwan words,
    #     repeated words) and collect the rest for re-translation with the problems explained
    from scripts.translation_check import problems as tr_problems
    for title in titles_to_check:
        tr = translations.get(title)
        if tr and tr.get('zh'):
            tr['zh'] = polish_zh(clean_translated_text(tr['zh'], title))
    qa_notes = {}
    for title in titles_to_check:
        tr = translations.get(title)
        if not tr or tr.get('reviewed') or tr.get('qa_tries', 0) >= 2:
            continue
        p = tr_problems(title, tr)
        if p and p != ['沒有翻譯']:
            qa_notes[title] = p
    print(f"Quality check: {len(qa_notes)} translations need fixing.")

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

    # Titles translated earlier by the literal machine-translation fallback are re-done by AI,
    # a limited number per run so the free Gemini quota is never exhausted.
    upgrade_titles = []
    if gemini_key:
        missing_set = set(missing_titles)
        upgrade_titles = sorted(t for t in titles_to_check
                                if t not in missing_set and t not in qa_notes
                                and not (translations.get(t) or {}).get('reviewed')
                                and (translations.get(t) or {}).get('src') != 'ai')
        print(f"Non-AI translations waiting for AI upgrade: {len(upgrade_titles)}")

    # 4. Translate missing items
    if missing_titles or upgrade_titles or qa_notes:
        if gemini_key:
            BATCH_SIZE = 25
            max_calls = int(os.environ.get('GEMINI_MAX_CALLS_PER_RUN', '40'))
            qa_list = [t for t in qa_notes if t not in set(missing_titles)]
            queue = [(t, True) for t in missing_titles] + [(t, False) for t in qa_list] + [(t, False) for t in upgrade_titles]
            print(f"Translating with Gemini AI: {len(missing_titles)} new + {len(qa_list)} quality fixes + {len(upgrade_titles)} upgrades (max {max_calls} requests this run)...")
            calls = 0
            ai_ok = 0
            for i in range(0, len(queue), BATCH_SIZE):
                chunk = queue[i:i + BATCH_SIZE]
                batch_res = {}
                if calls < max_calls:
                    batch_res = translate_batch_with_gemini([t for t, _ in chunk], gemini_key, notes=qa_notes)
                    calls += 1
                    time.sleep(4.5)  # stay under the free-tier requests-per-minute limit
                for t, is_new in chunk:
                    if t in batch_res:
                        old = translations.get(t)
                        new = batch_res[t]
                        if t in qa_notes:
                            new['qa_tries'] = (old or {}).get('qa_tries', 0) + 1
                        # only accept a new translation that is not worse than the one we have
                        if old and old.get('zh') and len(tr_problems(t, new, style=True)) > len(tr_problems(t, old, style=True)):
                            if t in qa_notes:
                                old['qa_tries'] = old.get('qa_tries', 0) + 1
                            continue
                        translations[t] = new
                        ai_ok += 1
                    elif is_new:
                        translations[t] = translate_single_fallback(t)  # retried by AI on a later run
                if calls >= max_calls and all(not is_new for t, is_new in queue[i + BATCH_SIZE:]):
                    break
            print(f"Gemini AI translated {ai_ok} titles using {calls} requests.")
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
                tr['zh'] = polish_zh(clean_translated_text(tr.get('zh', ''), t))

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
        # always save: recovered names and quality fixes (step 2b/2c) must be kept too
        with open(TRANSLATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(translations, f, ensure_ascii=False, indent=2)
        if fixed_count > 0:
            print(f"Cleaned {fixed_count} existing translations with grocery glossary.")

    # 4b. Report what is still wrong (shown as a warning in the GitHub Actions run)
    remaining = {t: tr_problems(t, translations.get(t)) for t in titles_to_check}
    remaining = {t: p for t, p in remaining.items() if p}
    print(f"Translation quality: {len(titles_to_check) - len(remaining)}/{len(titles_to_check)} OK")
    if remaining:
        sample = '; '.join(f"{t[:40]} ({p[0]})" for t, p in list(remaining.items())[:5])
        gh_warning(f"{len(remaining)} translations still have problems (the AI retries each one up to 2 times; the data check emails the owner when many remain): {sample}")

    # 5. Enrich specials.json directly with translations field
    if specials:
        updated_count = 0
        for it in specials:
            t = it.get('title', '').strip()
            if t in translations:
                tr = translations[t]
                it['translations'] = {k: tr[k] for k in ('zh', 'ja', 'ko') if tr.get(k)}
                updated_count += 1

        with open(SPECIALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(specials, f, ensure_ascii=False, separators=(',', ':'))
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
