"""Checks for interest.py (visitor interest blended into the default order) and the JS helpers.

    python tests/test_interest.py
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from interest import product_key, brand_of, interest_boost, apply_interest, CONFIDENT_TOTAL  # noqa: E402
from interest import load_retailer_ranks, apply_retailer_rank  # noqa: E402

bad = []


def check(cond, msg):
    if not cond:
        bad.append(msg)


def item(title, score, cat='snacks'):
    return {'title': title, 'popularity_score': score, 'category': cat}


# --- keys match the website's rule ---
check(product_key('  Smith\'s  Crinkle Cut\tChips 170g ') == "smith's crinkle cut chips 170g", 'key: spaces / case')
check(len(product_key('x' * 300)) == 160, 'key: 160 characters at most')
check(brand_of('tip top english muffins 6 pack') == 'tip top', 'brand: short first word -> two words')
check(brand_of('coles finest bread') == 'coles finest', 'brand: house brand -> two words')
check(brand_of('chobani flip 140g') == 'chobani', 'brand: single word')

# --- no data: nothing changes ---
items = [item('Chobani Flip 140g', 340), item('Unknown Crackers 200g', 0)]
check(apply_interest(items, {}, 0) == 0 and items[0]['popularity_score'] == 340, 'no data: unchanged')

# --- little data: small, gradual effect ---
few = {product_key('Unknown Crackers 200g'): 5.0}
b = interest_boost(items, few, 5.0)
check(0 <= b.get(id(items[1]), 0) <= 5, f'little data: tiny boost ({b.get(id(items[1]))})')

# --- plenty of data: what people really open rises above rule-only favourites ---
items = [item('Chobani Flip 140g', 340), item('Unknown Crackers 200g', 0), item('Nobody Wants This 1kg', 120)]
interest = {product_key('Unknown Crackers 200g'): 900.0, product_key('Chobani Flip 140g'): 30.0}
apply_interest(items, interest, CONFIDENT_TOTAL * 2)
scores = {it['title']: it['popularity_score'] for it in items}
check(scores['Unknown Crackers 200g'] >= 200, f'popular-in-practice product gets a real boost ({scores})')
check(scores['Nobody Wants This 1kg'] == 120, 'no interest: score unchanged')
check(scores['Chobani Flip 140g'] > 340, 'some interest: a smaller boost')
check(all(s % 5 == 0 for s in scores.values()), 'steps of 5')

# --- one product with a huge count does not bury the rest (log scale, capped points) ---
items = [item('Spammed Thing 1', 0), item('Normal Thing 2', 0)]
interest = {product_key('Spammed Thing 1'): 1_000_000.0, product_key('Normal Thing 2'): 300.0}
apply_interest(items, interest, CONFIDENT_TOTAL * 10)
s1, s2 = items[0]['popularity_score'], items[1]['popularity_score']
check(s1 <= int(1.6 * 140) + 5, f'maximum boost is capped ({s1})')
check(s2 >= 0.35 * s1, f'others keep a fair share ({s2} vs {s1})')

# --- products excluded on purpose stay excluded ---
items = [item('Big TV 65 inch', -999, 'household')]
apply_interest(items, {product_key('Big TV 65 inch'): 500.0}, CONFIDENT_TOTAL)
check(items[0]['popularity_score'] == -999, 'excluded (-999) products are not boosted')

# --- brand interest helps a brand's other products a little ---
items = [item('Moccona Coffee Sachets Caramel', 0, 'drinks')]
apply_interest(items, {product_key('Moccona Classic Medium 200g'): 400.0}, CONFIDENT_TOTAL)
check(0 < items[0]['popularity_score'] <= 70, f'brand-only boost is small but present ({items[0]["popularity_score"]})')

# --- 超市推薦順序: the position in the supermarket's own list joins by store + product name ---
import tempfile
_tmp = tempfile.mkdtemp()
_w, _c = os.path.join(_tmp, 'w.json'), os.path.join(_tmp, 'c.json')
with open(_w, 'w', encoding='utf-8') as f:
    json.dump({'items': {'tim tam 200g': {'title': 'Tim Tam 200g', 'rank': 3}},
               'groups': {'g': {'items': {'tim tam 200g': {'title': 'Tim Tam 200g', 'rank': 40},
                                          'milk': {'title': 'Milk &amp; Honey  1L', 'rank': 7}}}}}, f)
with open(_c, 'w', encoding='utf-8') as f:
    json.dump({'items': {'x': {'title': 'Tim Tam 200g', 'rank': 12}}, 'more': {'items': {'y': {'title': 'Coke 1.25L', 'rank': 90}}}}, f)
ranks = load_retailer_ranks(((_w, 'Woolworths'), (_c, 'Coles'), (os.path.join(_tmp, 'missing.json'), 'ALDI')))
its = [{'store': 'Woolworths', 'title': 'Tim Tam 200g'}, {'store': 'Coles', 'title': 'Tim Tam 200g'},
       {'store': 'Woolworths', 'title': 'Milk & Honey 1L'}, {'store': 'Coles', 'title': 'Coke 1.25L'}, {'store': 'ALDI', 'title': 'Coke 1.25L'}]
n = apply_retailer_rank(its, ranks)
check(n == 4, f'four specials are found in the lists: {n}')
check(its[0].get('rank') == 3 and its[1].get('rank') == 12, f'each store has its own list; the half-price list wins over a group: {its[:2]}')
check(its[2].get('rank') == 7, f'names match after HTML entities and double spaces are cleaned: {its[2]}')
check(its[3].get('rank') == 90, f'the all-specials list (more) counts too: {its[3]}')
check('rank' not in its[4], f'not in any list (or no file): no rank: {its[4]}')

# --- 熱門: Coles' best-seller order moves products up; the same brand at Woolworths moves up too ---
from interest import apply_best_sellers, BEST_SELLER_TOP  # noqa: E402
ranks = {('Coles', 'tim tam 200g'): 12, ('Coles', 'coke 1.25l'): 90, ('Woolworths', 'milk & honey 1l'): 1,
         ('Coles', 'slow seller 1kg'): BEST_SELLER_TOP + 1}
its = [item('Tim Tam 200g', 0), item('Tim Tam Double Coat 200g', 0), item('Milk & Honey 1L', 0),
       item('Coke 1.25L', -999), item('Slow Seller 1kg', 0)]
apply_best_sellers(its, ranks)
s = [it['popularity_score'] for it in its]
check(s[0] > s[1] > 0, f'a Coles best seller moves up most, another product of its brand (any store) a little: {s}')
check(s[2] == 0, f'a Woolworths list position is not a sales rank: {s}')
check(s[3] == -999, f'a product the rules exclude stays excluded: {s}')
check(s[4] == 0, f'below the top {BEST_SELLER_TOP}: no points: {s}')

# --- JavaScript side (functions/_lib/interest.js): same keys, weeks and scores ---
js = r"""
const src = require('fs').readFileSync(process.argv[1], 'utf8');
import('data:text/javascript,' + encodeURIComponent(src)).then(m => {
  const D = (s) => Date.parse(s);
  const out = {
    key: m.productKey("  Smith's  Crinkle Cut\tChips 170g "),
    wedNoon: m.specialsWeek(D('2026-10-07T02:00:00Z')),     // Wed 12:00 Brisbane
    tueNight: m.specialsWeek(D('2026-10-13T13:30:00Z')),    // Tue 23:30 Brisbane -> same week
    wedEarly: m.specialsWeek(D('2026-10-13T14:30:00Z')),    // Wed 00:30 Brisbane -> next week
    weeks: m.weekList(D('2026-10-08T00:00:00Z')),
    score: m.scoreRows([
      { week: '2026-10-07', k: 'a', views: 10, adds: 1, favs: 1 },
      { week: '2026-09-30', k: 'a', views: 10, adds: 0, favs: 0 },
      { week: '2026-08-01', k: 'a', views: 999, adds: 0, favs: 0 },
      { week: '2026-10-07', k: 'b', views: 0, adds: 0, favs: 0 }], m.weekList(D('2026-10-08T00:00:00Z')))
  };
  console.log(JSON.stringify(out));
});
"""
res = subprocess.run(['node', '-e', js, os.path.join(ROOT, 'functions', '_lib', 'interest.js')],
                     capture_output=True, text=True, timeout=60)
try:
    o = json.loads(res.stdout.strip().splitlines()[-1])
    check(o['key'] == product_key("  Smith's  Crinkle Cut\tChips 170g "), f"JS and Python keys differ: {o['key']}")
    check(o['wedNoon'] == '2026-10-07' and o['tueNight'] == '2026-10-07' and o['wedEarly'] == '2026-10-14',
          f"specials week boundaries: {o['wedNoon']} {o['tueNight']} {o['wedEarly']}")
    check(o['weeks'][:3] == ['2026-10-07', '2026-09-30', '2026-09-23'] and len(o['weeks']) == 6, f"week list {o['weeks']}")
    check(abs(o['score']['items']['a'] - (1 * (10 + 2 + 3) + 0.6 * 10)) < 0.01, f"score a {o['score']}")
    check('b' not in o['score']['items'], 'zero rows are left out')
except Exception as e:
    bad.append(f'JS helpers could not be checked: {e} {res.stderr[:300]}')

total = 28
for b in bad:
    print('FAIL', b)
print(f'{total - len(bad)}/{total} visitor-interest checks passed')
sys.exit(1 if bad else 0)
