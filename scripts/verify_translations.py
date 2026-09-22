# -*- coding: utf-8 -*-
import json
import sys

# Ensure UTF-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

with open('static/data/specials.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

missing = 0
for it in items:
    t = it.get('translations', {})
    if not t or not t.get('zh') or not t.get('ja') or not t.get('ko'):
        missing += 1
        print('Missing translation for:', it.get('title'))

print(f'Checked {len(items)} items. Total missing: {missing}')

print('\nSample bilingual items:')
for it in items[::50]:
    print(f"Original : {it['title']}")
    print(f"  zh     : {it['translations']['zh']}")
    print(f"  ja     : {it['translations']['ja']}")
    print(f"  ko     : {it['translations']['ko']}")
    print('-' * 50)
