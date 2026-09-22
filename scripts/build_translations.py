# -*- coding: utf-8 -*-
import json
import os
import sys

# Add scripts directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from translations.seafood import SEAFOOD_TRANSLATIONS
from translations.produce import PRODUCE_TRANSLATIONS
from translations.health_vitamins import HEALTH_VITAMINS_TRANSLATIONS
from translations.pantry import PANTRY_TRANSLATIONS
from translations.dairy_eggs import DAIRY_EGGS_TRANSLATIONS
from translations.bakery import BAKERY_TRANSLATIONS
from translations.meat import MEAT_TRANSLATIONS
from translations.frozen import FROZEN_TRANSLATIONS
from translations.drinks import DRINKS_TRANSLATIONS
from translations.household import HOUSEHOLD_TRANSLATIONS
from translations.snacks import SNACKS_TRANSLATIONS

ALL_TRANSLATIONS = {}
for d in [
    SEAFOOD_TRANSLATIONS,
    PRODUCE_TRANSLATIONS,
    HEALTH_VITAMINS_TRANSLATIONS,
    PANTRY_TRANSLATIONS,
    DAIRY_EGGS_TRANSLATIONS,
    BAKERY_TRANSLATIONS,
    MEAT_TRANSLATIONS,
    FROZEN_TRANSLATIONS,
    DRINKS_TRANSLATIONS,
    HOUSEHOLD_TRANSLATIONS,
    SNACKS_TRANSLATIONS
]:
    ALL_TRANSLATIONS.update(d)

print(f"Total translations collected: {len(ALL_TRANSLATIONS)}")

# Load specials.json
specials_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'data', 'specials.json')
with open(specials_path, 'r', encoding='utf-8') as f:
    items = json.load(f)

print(f"Total items in specials.json: {len(items)}")

# Verify all titles are covered
missing = []
for it in items:
    title = it.get('title', '')
    if title not in ALL_TRANSLATIONS:
        missing.append(title)

if missing:
    print(f"WARNING: {len(missing)} items missing translation:")
    for m in set(missing):
        print(f" - {m}")
    sys.exit(1)
else:
    print("SUCCESS: All items in specials.json are 100% covered by translations!")

# Write translations.json
translations_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'data', 'translations.json')
with open(translations_path, 'w', encoding='utf-8') as f:
    json.dump(ALL_TRANSLATIONS, f, ensure_ascii=False, indent=2)
print(f"Wrote {len(ALL_TRANSLATIONS)} entries to {translations_path}")

# Enrich specials.json with translations field for each item
for it in items:
    title = it.get('title', '')
    it['translations'] = ALL_TRANSLATIONS.get(title, {})

with open(specials_path, 'w', encoding='utf-8') as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f"Updated {len(items)} items in {specials_path} with translations field.")
