# -*- coding: utf-8 -*-
"""
Learned popularity: what visitors really look at moves products up the default order.

The website counts, anonymously, how often each special is opened, saved and added to a shopping
list (functions/api/track.js). /api/popular sums the last six weeks, recent weeks counting most.
scripts/fetch_interest.py saves that to data/interest.json on each update (at most every 6 hours),
and export_static_data.py calls apply_interest() to blend it into each product's popularity score:

    final score = rule score (categories.calculate_popularity_score: known brands, half price, price...)
                  + confidence x 1.6 x (up to 100 for the product's own interest
                                        + up to 40 for interest in its brand)

  * confidence grows from 0 to 1 as interest data builds up (CONFIDENT_TOTAL weighted actions), so
    with little data the order stays as it is today and the visitors' choices take over gradually;
  * log scale: a product opened 1,000 times does not bury everything else;
  * products the rules exclude on purpose (TVs, appliances: score -999) stay excluded;
  * steps of 5, so tiny changes in the counts do not rewrite the data file every update.
"""
import json
import math
import os
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
INTEREST_FILE = os.path.join(ROOT, 'data', 'interest.json')
CONFIDENT_TOTAL = 2000.0
PRODUCT_POINTS = 100.0
BRAND_POINTS = 40.0
STRENGTH = 1.6
HOUSE_BRANDS = {'coles', 'woolworths', 'macro', 'essentials'}


def product_key(title):
    """Same rule as the website (functions/_lib/interest.js)."""
    return re.sub(r'\s+', ' ', str(title or '').strip()).lower()[:160]


def brand_of(key):
    words = re.sub(r"[^a-z0-9&' ]", ' ', key or '').split()
    if not words:
        return ''
    # two-word brands like "red rock", "tip top", "coles finest"
    return ' '.join(words[:2]) if words[0] in HOUSE_BRANDS or len(words[0]) <= 3 else words[0]


def load_interest(path=INTEREST_FILE):
    """({product key: score}, total) - empty when there is no usable file."""
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        items = data.get('items') or {}
        clean = {str(k): float(v) for k, v in items.items() if isinstance(v, (int, float)) and v > 0}
        return clean, float(data.get('total') or sum(clean.values()))
    except FileNotFoundError:
        return {}, 0.0
    except Exception as e:
        print(f"[WARN] {path} could not be read ({e}) - default order without visitor interest")
        return {}, 0.0


def interest_boost(items, interest, total):
    """{id(item): points to add} for a list of product dicts."""
    if not interest or total <= 0:
        return {}
    confidence = min(1.0, total / CONFIDENT_TOTAL)
    brand_sum = defaultdict(float)
    for k, s in interest.items():
        brand_sum[brand_of(k)] += s
    max_item = max(interest.values())
    max_brand = max(brand_sum.values())
    out = {}
    for it in items:
        k = product_key(it.get('title'))
        own = interest.get(k, 0.0)
        brand = brand_sum.get(brand_of(k), 0.0)
        points = 0.0
        if own > 0 and max_item > 0:
            points += PRODUCT_POINTS * math.log1p(own) / math.log1p(max_item)
        if brand > 0 and max_brand > 0:
            points += BRAND_POINTS * math.log1p(brand) / math.log1p(max_brand)
        boost = int(round(confidence * STRENGTH * points / 5.0) * 5)
        if boost:
            out[id(it)] = boost
    return out


def apply_interest(items, interest=None, total=None):
    """Adds the learned points to each item's 'popularity_score'. Returns how many items moved."""
    if interest is None:
        interest, total = load_interest()
    boosts = interest_boost(items, interest, total or 0.0)
    moved = 0
    for it in items:
        b = boosts.get(id(it), 0)
        if b and (it.get('popularity_score') or 0) > -999:
            it['popularity_score'] = int(it.get('popularity_score') or 0) + b
            moved += 1
    return moved
