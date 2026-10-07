"""
Sorts the products that no category rule recognises, with the AI (Gemini), so new products land in
the right department without anyone adding rules by hand.

  * Only products no rule recognises are asked about; the rules in categories.py always win.
  * The AI sees the product title AND the supermarket's own aisle, when the supermarket gives one.
  * The AI may only answer one of the 13 departments; any other answer is ignored.
  * Answers are kept in data/ai_categories.json, so each product is asked about only once.
    Entries marked "reviewed" were checked by hand and are never replaced.
  * If the AI cannot be used (no key, quota used up, network), nothing breaks: the supermarket's
    aisle is used instead, then a last guess - and scripts/check_data.py emails the owner when too
    many products had to be guessed.

    python scripts/ai_categorize.py                   (normal: sort new unknown products)
    python scripts/ai_categorize.py --check-reviewed  (ask the AI about the hand-checked products
                                                       and report how often it agrees; changes nothing)
"""
import datetime
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import categories  # noqa: E402
from categories import (PRODUCT_CATEGORIES, AI_CATEGORIES_FILE, classify_product, norm_title,  # noqa: E402
                        aisle_from_url)

DB_FILE = os.path.join(ROOT, 'data', 'specials.db')
BATCH = 60
KEEP_DAYS = 120          # answers for products not seen for this long are dropped (asked again if they return)

DEPARTMENTS = {
    'produce': 'fresh fruit, vegetables, salads, fresh herbs',
    'meat': 'fresh or packaged meat and poultry, sausages, bacon, ham, salami and other deli meats',
    'seafood': 'fresh or chilled fish and seafood (canned tuna is pantry)',
    'dairy_eggs': 'milk, cheese, yoghurt, butter, cream, eggs, chilled desserts, and other fridge foods '
                  '(fresh pasta, gnocchi, dips, chilled ready meals)',
    'bakery': 'bread, rolls, wraps, cakes, pastries, muffins',
    'frozen': 'frozen meals and bowls, frozen vegetables, ice cream and ice-cream sandwiches, frozen desserts, '
              'frozen party food',
    'pantry': 'shelf-stable groceries: rice, pasta, noodles, sauces, spreads, canned food, cereal, baking mixes '
              'and ingredients, spices, dried fruit, shelf-stable ready meals (microwave rice bowls), '
              'international foods, baby food pouches',
    'snacks': 'chips, chocolate, lollies, biscuits, wafers, crackers, muesli bars, protein bars and protein balls, '
              'nuts, sweet treats',
    'drinks': 'non-alcoholic drinks: soft drinks, sparkling drinks, water, sports and electrolyte drinks, juice, '
              'cordial, coffee, tea, matcha powder, hot chocolate, iced coffee, ready-to-drink protein shakes',
    'liquor': 'beer, wine, spirits, cider, pre-mixed alcoholic drinks',
    'health_vitamins': 'health, beauty and personal care: vitamins, supplements, sports nutrition (energy gels, '
                       'protein or amino-acid powders, pre-workout), medicine, skin care, make-up, nails, '
                       'fake tan, hair care and hair accessories, deodorant, oral care, shaving, feminine care, '
                       'baby wipes and nappies, bath accessories',
    'household': 'cleaning, laundry, paper goods, napkins, kitchenware, containers, appliances, home, garden, '
                 'insect spray, matches, stationery, craft, toys, games, electronics, clothing, socks, '
                 'party goods',
    'pet': 'pet food, treats and pet care',
}

PROMPT = """You sort Australian supermarket products (Woolworths, Coles, ALDI) into departments.
Pick exactly ONE department key for each product, from this list:

{departments}

Use the product title; the supermarket's own aisle is given when known and is usually right, but
trust the title when the aisle is a general one (e.g. "Indian Foods" for a soft drink).
Respond with a JSON array of objects: {{"title": <copied exactly>, "category": <department key>}}.

Products:
{products}
"""


def gh(kind, msg):
    print(f"::{kind}::{msg}" if os.environ.get('GITHUB_ACTIONS') else f"[{kind.upper()}] {msg}")


def load_cache():
    try:
        with open(AI_CATEGORIES_FILE, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        gh('warning', f"data/ai_categories.json could not be read ({e}); starting a new one")
        return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(AI_CATEGORIES_FILE), exist_ok=True)
    tmp = AI_CATEGORIES_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(dict(sorted(cache.items())), f, ensure_ascii=False, indent=1)
        f.write('\n')
    os.replace(tmp, AI_CATEGORIES_FILE)       # never leaves a half-written file behind


def products_in_database():
    """{title: aisle text} for every product currently on the site (both weeks)."""
    out = {}
    if not os.path.exists(DB_FILE):
        return out
    conn = sqlite3.connect(DB_FILE)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(specials)").fetchall()}
        aisle_col = 'store_category' if 'store_category' in cols else "''"
        for title, aisle, url in conn.execute(f"SELECT title, {aisle_col}, product_url FROM specials"):
            if title:
                out[title] = (aisle or '').strip() or aisle_from_url(url or '')
    finally:
        conn.close()
    return out


def ask_ai(items, api_key):
    """items = [(title, aisle)] -> {title: department}. Returns {} when the AI cannot be used."""
    import auto_translate as at                      # shares the model list and request helper
    cands = at.gemini_model_candidates(api_key)
    if not cands:
        return {}
    departments = '\n'.join(f'- {k}: {v}' for k, v in DEPARTMENTS.items())
    products = json.dumps([{'title': t, 'aisle': a or 'unknown'} for t, a in items], ensure_ascii=False)
    body = {
        'contents': [{'parts': [{'text': PROMPT.format(departments=departments, products=products)}]}],
        'generationConfig': {'temperature': 0, 'responseMimeType': 'application/json'},
    }
    model = cands[0]
    for attempt in range(6):
        try:
            data = at._gemini_request(f"{at.GEMINI_API_BASE}/models/{model}:generateContent", api_key, body)
            parts = ((data.get('candidates') or [{}])[0].get('content') or {}).get('parts') or []
            text = next((p['text'] for p in parts if 'text' in p), '').strip()
            text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
            wanted = {t for t, _ in items}
            out = {}
            for row in json.loads(text):
                t, cat = (row.get('title') or '').strip(), (row.get('category') or '').strip()
                if t in wanted and cat in PRODUCT_CATEGORIES:     # only real departments are accepted
                    out[t] = cat
            return out
        except urllib.error.HTTPError as e:
            if e.code in (404, 429, 500, 503) and len(cands) > 1:
                cands.pop(0)
                model = cands[0]
                continue
            if e.code in (500, 503) and attempt < 3:
                time.sleep(15 * (attempt + 1))
                continue
            gh('warning', f"AI categories: Gemini answered HTTP {e.code}; the supermarket aisles are used instead")
            return {}
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
                continue
            gh('warning', f"AI categories: no usable answer ({str(e)[:120]}); the supermarket aisles are used instead")
            return {}
    return {}


def unknown_products(products):
    """Products that no rule recognises (rules only, no hints)."""
    categories.GUESSED.clear()
    for title, aisle in products.items():
        classify_product(title, aisle, use_hints=False)
    unknown = set(categories.GUESSED)
    categories.GUESSED.clear()
    return unknown


def check_reviewed(api_key):
    cache = load_cache()
    reviewed = [(t, e.get('aisle') or '') for t, e in cache.items() if isinstance(e, dict) and e.get('reviewed')]
    if not reviewed:
        print('no hand-checked products to compare with')
        return 0
    answers = {}
    for i in range(0, len(reviewed), BATCH):
        answers.update(ask_ai(reviewed[i:i + BATCH], api_key))
    same = [t for t, _ in reviewed if answers.get(t) == cache[t]['category']]
    differ = [f"{t[:40]}: AI {answers.get(t) or '-'} / 人工 {cache[t]['category']}" for t, _ in reviewed
              if t in answers and answers[t] != cache[t]['category']]
    gh('notice', f"AI 分類與人工檢查比對：{len(same)}/{len(reviewed)} 件相同（{len(reviewed) - len(answers)} 件 AI 沒回答）")
    if differ:
        gh('notice', 'AI 與人工不同：' + '；'.join(differ[:20]))
    return 0


def main():
    import auto_translate as at
    api_key = at.get_gemini_api_key()
    if '--check-reviewed' in sys.argv:
        return check_reviewed(api_key)

    products = products_in_database()
    cache = load_cache()
    today = datetime.date.today().isoformat()

    # forget old answers for products that left the site long ago (hand-checked ones are kept)
    cutoff = (datetime.date.today() - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    on_site = {norm_title(t) for t in products}
    for t in list(cache):
        e = cache[t]
        if not isinstance(e, dict) or (not e.get('reviewed') and norm_title(t) not in on_site
                                        and (e.get('date') or '') < cutoff):
            cache.pop(t)

    known = {norm_title(t) for t, e in cache.items() if isinstance(e, dict) and e.get('category') in PRODUCT_CATEGORIES}
    todo = sorted((t, products[t]) for t in unknown_products(products) if norm_title(t) not in known)
    if not todo:
        print('AI categories: no new products that the rules do not know')
        save_cache(cache)
        return 0
    if not api_key:
        gh('warning', f"AI categories: no GEMINI_API_KEY - {len(todo)} new products use the supermarket aisles instead")
        save_cache(cache)
        return 0

    added = {}
    for i in range(0, len(todo), BATCH):
        answers = ask_ai(todo[i:i + BATCH], api_key)
        if not answers:
            break                                    # AI unavailable: the next update tries again
        for t, aisle in todo[i:i + BATCH]:
            if t in answers:
                cache[t] = {'category': answers[t], 'aisle': aisle, 'date': today}
                added[t] = answers[t]
    save_cache(cache)
    missing = len(todo) - len(added)
    sample = '；'.join(f"{t[:30]}→{c}" for t, c in list(added.items())[:10])
    gh('notice', f"AI 分類了 {len(added)} 件規則認不出的新商品" + (f"（{missing} 件下次再問）" if missing else '')
       + (f"，例如：{sample}" if sample else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
