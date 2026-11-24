"""
Names of every 小黃屋 product in Traditional Chinese, Japanese and Korean, for the stand-alone 小黃屋 site.

The product list (data/chemist_all.json) has about 26,000 English names. They are translated a few thousand
at a time with the same AI translator as the supermarket site (scripts/auto_translate.py), and kept in
data/chemist_translations.json ({product number: [zh, ja, ko]}), so each name is translated only once.
Each run continues where the last one stopped; new products are added when the weekly list brings them.

    python scripts/translate_chemist.py              # up to MAX_BATCHES batches this run
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import auto_translate as at  # noqa: E402

ALL = os.path.join(ROOT, 'data', 'chemist_all.json')
OUT = os.path.join(ROOT, 'data', 'chemist_translations.json')
BATCH = 60
MAX_BATCHES = int(os.environ.get('CW_TRANSLATE_BATCHES', '70'))
MAX_SECONDS = 25 * 60


def main():
    key = at.get_gemini_api_key()
    if not key:
        print('translate_chemist: no AI key - names stay in English this time')
        return 0
    try:
        products = json.load(open(ALL, encoding='utf-8'))['products']
    except (OSError, ValueError, KeyError):
        print('translate_chemist: no product list yet')
        return 0
    try:
        done = json.load(open(OUT, encoding='utf-8'))
    except (OSError, ValueError):
        done = {}
    todo = [p for p in products if p['pid'] not in done]
    print(f'translate_chemist: {len(done)} translated, {len(todo)} to go')
    start = time.time()
    added = 0
    for b in range(MAX_BATCHES):
        chunk = todo[b * BATCH:(b + 1) * BATCH]
        if not chunk or time.time() - start > MAX_SECONDS or at._gemini_state['disabled']:
            break
        titles = [p['title'] for p in chunk]
        got = at.translate_batch_with_gemini(titles, key)
        for p in chunk:
            t = got.get(p['title'])
            if t and t.get('zh'):
                done[p['pid']] = [t['zh'], t.get('ja') or '', t.get('ko') or '']
                added += 1
        if (b + 1) % 10 == 0:               # save as we go: a stopped run keeps what it did
            json.dump(done, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
            print(f'  {b + 1} batches, {added} names added')
    json.dump(done, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'translate_chemist: added {added}; {len(done)} of {len(products)} names translated')
    return 0


if __name__ == '__main__':
    sys.exit(main())
