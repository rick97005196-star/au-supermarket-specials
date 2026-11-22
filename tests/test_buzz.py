"""Checks for buzz.py (本週熱門: this week's OzBargain discussions, strict matching).

    python tests/test_buzz.py
"""
import datetime
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from buzz import matches, apply_buzz, load_deals, sizes, MAX_MATCHES  # noqa: E402

bad = []


def check(cond, msg):
    if not cond:
        bad.append(msg)


def item(title, price, store='Coles', was=None):
    return {'title': title, 'price': price, 'store': store, 'was_price': was}


def deal(title, store='Coles', up=20, down=0, comments=5, days_ago=1, did=1):
    posted = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_ago)
    return {'id': did, 'store': store, 'title': title, 'posted': posted.isoformat(), 'votes_pos': up,
            'votes_neg': down, 'comments': comments}


GYM = '½ Price: Gym Bod Protein Ice Cream Varieties 475mL $5.50 & Gym Bod Ultra High Protein Ice Cream Varieties 475mL $6.25 @ Coles'
# --- clear matches ---
check(matches(item('Gym Bod Salted Caramel Choc Top Protein Ice Cream 475mL', 5.5), deal(GYM)), 'product line deal')
check(matches(item('Cafe Peak Iced Coffee Latte Cans 240mL x 4 pack', 8.0, 'Woolworths'),
              deal('Cafe Peak Iced Coffee Latte Cans 240mL x 4 Pack $8 @ Woolworths', 'Woolworths')), 'full name deal')
check(matches(item('RED ISLAND Australian Extra Virgin Olive Oil 1L', 14.99, 'ALDI'),
              deal('Red Island Extra Virgin Olive Oil 1L $14.99 @ Aldi', 'ALDI')), 'ALDI, upper case name')
check(matches(item("Whittaker's Slab Milk Chocolate Bar 50g", 1.5, 'Woolworths', 3.0),
              deal("½ Price Whittaker's Slab Milk Chocolate Bar 50g $1.50 (Was $3) @ Woolworths", 'Woolworths')), "apostrophe brand")
# --- no guessing ---
check(not matches(item('Gym Bod Salted Caramel Choc Top Protein Ice Cream 475mL', 6.0), deal(GYM)), 'other price -> no')
check(not matches(item('Gym Bod Salted Caramel Choc Top Protein Ice Cream 1L', 5.5), deal(GYM)), 'other size -> no')
check(not matches(item('Peters Choc Top Ice Cream 475mL', 5.5), deal(GYM)), 'other brand -> no')
check(not matches(item('Gym Bod Protein Bar 60g', 5.5), deal(GYM)), 'same brand, other product -> no')
check(not matches(item('Muscle Nation Custardplant Protein Bar Banana Toffee 50g', 2.0),
                  deal('Muscle Nation Vegan Protein Bar 12-Pack $24 + Delivery @ Amazon AU / 1x Bar $2 @ Coles')),
      'deal word "vegan" not in the name -> no')
check(not matches(item('Coles Full Cream Milk 3L', 4.65), deal('3000 Flybuys Points for $250+ Online Spend @ Coles')),
      'points offer -> no')
check(not matches(item('Cadbury Dairy Milk 180g', 3.5), deal('Cadbury $3.50 @ Coles')), 'brand only -> no')
check(sizes('Cans 240mL x 4 Pack 1.25L 1kg') == {'240ml', '1250ml', '1000g'}, 'sizes in ml / g')

# --- apply: store, score, too general, online only, old deals ---
items = [item('Gym Bod Salted Caramel Choc Top Protein Ice Cream 475mL', 5.5),
         item('Gym Bod Salted Caramel Choc Top Protein Ice Cream 475mL', 5.5, 'Woolworths'),
         item('Cafe Peak Iced Coffee Latte Cans 240mL x 4 pack', 8.0, 'Woolworths')]
n = apply_buzz(items, [deal(GYM, up=12, comments=23, did=7),
                       deal('Cafe Peak Iced Coffee Latte Cans 240mL x 4 Pack $8 @ Woolworths', 'Woolworths', 7, 0, 14, did=8)])
check(n == 2, f'2 matched (got {n})')
check(items[0].get('bz') == 35 and items[0]['bzd'] == {'id': 7, 'v': 12, 'c': 23}, 'score = votes + comments')
check('bz' not in items[1], 'another store never gets the score')
many = [item(f'Gym Bod Flavour{i} Choc Top Protein Ice Cream 475mL', 5.5) for i in range(MAX_MATCHES + 1)]
check(apply_buzz(many, [deal(GYM)]) == 0, 'too general deal -> not used')

reg = [item('RED ISLAND Australian Extra Virgin Olive Oil 1L', 14.99, 'ALDI')]
check(apply_buzz(reg, [deal('Red Island Extra Virgin Olive Oil 1L $14.99 @ Aldi', 'ALDI')], skip=lambda it: True) == 0,
      'regular / everyday prices never get a score')

with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, 'buzz.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'deals': [deal(GYM, did=1), deal(GYM, days_ago=12, did=2),
                             deal('Cafe Peak Latte $8 (Online Only) @ Woolworths', 'Woolworths', did=3),
                             deal('PlayStation 5 $999 @ BIG W via Everyday Marketplace', 'Woolworths', did=4),
                             deal(GYM, up=1, down=9, comments=0, did=5),
                             deal('Gym Bod Ice Cream 475mL $5.50 @ Amazon AU', did=6)]}, f)
    ids = [d['id'] for d in load_deals(path)]
    check(ids == [1], f'only recent, in-store, liked deals naming the store are used (got {ids})')
    check(load_deals(os.path.join(tmp, 'missing.json')) == [], 'no file -> no deals')

if bad:
    print('FAILED:\n  ' + '\n  '.join(bad))
    sys.exit(1)
print('buzz.py: all checks passed')
