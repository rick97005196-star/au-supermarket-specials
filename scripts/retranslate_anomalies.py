import json
import os
import urllib.request
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

TRANSLATIONS_FILE = 'static/data/translations.json'
SPECIALS_FILE = 'static/data/specials.json'
DB_FILE = 'specials.db'

# Read .env for GEMINI_API_KEY
key = ''
if os.path.exists('.env'):
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                key = line.strip().split('=', 1)[1]

if not key:
    print("Error: GEMINI_API_KEY not found in .env")
    sys.exit(1)

bad_keys = [
    "KB's Gyoza 750g",
    "Cadbury Crunchie Milk Chocolate Bar Chocolate Bar 50g",
    "Cadbury Picnic Milk Chocolate Bar Chocolate Bar 46g",
    "Morning Fresh Dishwashing Liquid Lemon Lemon Super Strength 900mL",
    "Cadbury Flake Milk Chocolate Bar Chocolate Bar 30g",
    "Sunbites Biscuit Crackers Share Pack Sour Cream & Chives 110g",
    "Connoisseur Gourmet Ice Cream Cookies & Cream Sticks 4 pack",
    "Connoisseur Gourmet Ice Cream Mini Cookies & Cream Sticks 6 pack",
    "Connoisseur Vanilla Ice Cream 4 pack",
    "Connoisseur Blood Orange & Chocolate Ice Cream 4 pack",
    "Red Rock Deli Biscuit Crackers Share Pack Honey Soy & Chicken 135g",
    "Connoisseur Mango & Coconut Ice Cream 4 pack",
    "Connoisseur Gourmet Ice Cream Mini Vanilla Sticks 360mL 6 pack",
    "Air Wick Pure Candle Celebrations Cake Delights 105g",
    "Famous Nutrition Sport Protein & Creatine Bar Cookies & Cream 60g",
    "Bonds Men's Xtemp Trunk L Assorted each",
    "Bonds Mens Guy Front Trunk Size Medium Assorted each",
    "Bonds Mens Xtemp Trunk XLarge Assorted each"
]

prompt = """You are an expert Australian supermarket grocery translator.
Translate the following Australian supermarket items into:
1. 'zh': Traditional Chinese (Taiwan/Hong Kong style, friendly and standard for supermarket shoppers).
CRITICAL RULES FOR CHINESE:
- Keep ALL famous brand names in English! Never translate brand names literally:
  * 'Connoisseur' -> KEEP 'Connoisseur' (NEVER '鑑賞家' or '行家')
  * 'Cadbury' -> KEEP 'Cadbury' (or 'Cadbury 吉百利')
  * 'Red Rock Deli' -> KEEP 'Red Rock Deli'
  * 'Sunbites' -> KEEP 'Sunbites'
  * 'Bonds' -> KEEP 'Bonds'
  * 'Morning Fresh' -> KEEP 'Morning Fresh'
- Fix flavors & cuts:
  * 'Cookies & Cream' -> '巧酥餅乾風味' or '奧利奧巧酥風味' (NEVER '餅乾和奶油')
  * 'Honey Soy & Chicken' -> '蜂蜜醬油雞汁風味' (NEVER '大豆和雞肉')
  * 'Sour Cream & Chives' -> '酸奶洋蔥風味' (NEVER '酸奶油和韭菜')
  * 'Gourmet Ice Cream Sticks' -> '頂級雪糕' (NEVER '美食冰淇淋棒')
  * 'Trunk' (for Bonds underwear) -> '男款平口四角內褲' (NEVER '前軀幹')
  * 'Cake Delights' (for Air Wick scented candle) -> '慶典蛋糕甜香香氛蠟燭' (NEVER '蛋糕美食')
  * 'Gyoza' -> '日式煎餃' (NEVER '日式日式')
  * Eliminate any stuttering or repeated words like '巧克力棒巧克力棒', '檸檬檸檬', '特大號特大號'.
2. 'ja': Japanese supermarket style (Katakana for brands/flavors).
3. 'ko': Korean supermarket style.

Items:
""" + json.dumps([{'title': t} for t in bad_keys], ensure_ascii=False) + """

Respond ONLY with raw JSON array of objects with keys: title, zh, ja, ko. No markdown backticks."""

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={key}"
body = {'contents': [{'parts': [{'text': prompt}]}]}
req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers={'Content-Type': 'application/json'})

print("Calling Gemini 3.1 Flash-Lite to re-translate defective items...")
resp = urllib.request.urlopen(req, timeout=30)
res_data = json.loads(resp.read().decode('utf-8'))
txt = res_data['candidates'][0]['content']['parts'][0]['text'].strip()
if txt.startswith('```'):
    txt = txt.split('\n', 1)[1]
    if txt.endswith('```'):
        txt = txt.rsplit('\n', 1)[0]

new_translations = json.loads(txt.strip())

# Load translations.json
with open(TRANSLATIONS_FILE, 'r', encoding='utf-8') as f:
    translations = json.load(f)

for it in new_translations:
    title = it['title']
    print(f"Updated: {title}")
    print(f"  -> ZH: {it['zh']}")
    print(f"  -> JA: {it['ja']}")
    print(f"  -> KO: {it['ko']}")
    translations[title] = {
        'zh': it['zh'],
        'ja': it['ja'],
        'ko': it['ko']
    }

# Save translations.json
with open(TRANSLATIONS_FILE, 'w', encoding='utf-8') as f:
    json.dump(translations, f, ensure_ascii=False, indent=2)
print("Saved updated static/data/translations.json")

# Enrich specials.json
if os.path.exists(SPECIALS_FILE):
    with open(SPECIALS_FILE, 'r', encoding='utf-8') as f:
        specials = json.load(f)
    for sp in specials:
        t = sp.get('title', '').strip()
        if t in translations:
            sp['translations'] = translations[t]
    with open(SPECIALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(specials, f, ensure_ascii=False, indent=2)
    print("Saved updated static/data/specials.json")

# Update SQLite
if os.path.exists(DB_FILE):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for title, tr in translations.items():
        if title in bad_keys:
            c.execute("UPDATE specials SET translations = ? WHERE title = ?", (json.dumps(tr, ensure_ascii=False), title))
    conn.commit()
    conn.close()
    print("Updated SQLite specials.db")

print("All defective translations successfully re-translated and updated!")
