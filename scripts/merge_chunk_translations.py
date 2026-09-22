# -*- coding: utf-8 -*-
import json
import glob
import os

def merge_translations():
    translations_file = os.path.join('static', 'data', 'translations.json')
    specials_file = os.path.join('static', 'data', 'specials.json')

    with open(translations_file, 'r', encoding='utf-8') as f:
        translations = json.load(f)

    # Find all translated chunk files
    chunk_files = sorted(glob.glob('scratch/translate_batches/chunks/chunk_*_translated.json'))
    print(f"Found {len(chunk_files)} translated chunk files.")

    total_merged = 0
    for cf in chunk_files:
        try:
            with open(cf, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
            for title, t in chunk_data.items():
                if t.get('zh') and t['zh'] != title:
                    translations[title] = t
                    total_merged += 1
        except Exception as e:
            print(f"Error reading {cf}: {e}")

    print(f"Total entries merged/updated: {total_merged}")

    # Write back translations.json
    with open(translations_file, 'w', encoding='utf-8') as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)

    # Update specials.json
    with open(specials_file, 'r', encoding='utf-8') as f:
        specials = json.load(f)

    for it in specials:
        title = it.get('title', '')
        if title in translations:
            it['translations'] = translations[title]

    with open(specials_file, 'w', encoding='utf-8') as f:
        json.dump(specials, f, ensure_ascii=False, indent=2)

    print(f"Updated specials.json ({len(specials)} items).")

    # Check remaining untranslated
    untranslated = [t for t, tr in translations.items() if tr.get('zh') == t]
    print(f"Remaining untranslated items: {len(untranslated)} / {len(translations)}")

if __name__ == '__main__':
    merge_translations()
