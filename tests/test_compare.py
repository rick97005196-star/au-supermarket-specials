# -*- coding: utf-8 -*-
"""Checks for the price comparison in static/compare.js: the unit price converter (per kg / litre / item)
and the "which supermarket is cheapest" pick, on hand-checked examples from the real data (Oct 2026).

    python tests/test_compare.py          -> exit code 1 and a list of problems if anything is off
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JS = r"""
const c = require(process.argv[1]);
const q = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const calls = q.calls.map(([fn, item]) => c[fn](item));
const vc = q.vc.map(([name, i]) => {
    const r = c.valueCompare(q.lists[name][i], q.lists[name]);
    return r && { verdict: r.verdict, diff: r.diff, lowest: r.lowest, basis: r.basis, mine: r.mine.value,
                  cheapest: r.cheapest.item.title, stores: r.rows.map(x => x.item.store) };
});
// a state's own price is a copy of the product with another price: it must get its own figure
const base = { title: 'Lodge Farms Barn Eggs 12 Pack 700g', price: 5.29, store: 'ALDI' };
c.cmpTypeOf(base);
const copy = Object.assign({}, base, { price: 7 });
c.cmpTypeOf(copy);
// the same product at another supermarket under another wording (the week's list is q.same)
const same = q.same;
const pairs = q.pairs.map(([i, j]) => c.isSameProduct(same[i], same[j], same));
const found = q.found.map(i => Object.fromEntries(Object.entries(c.findSameProducts(same[i], same)).map(([st, o]) => [st, same.indexOf(o)])));
const each = same.map(x => c.perItemPrice(x));
process.stdout.write(JSON.stringify({ calls, vc, copy: copy._cmpUp.value, pairs, found, each }));
"""

bad = []
total = 0


def check(cond, msg):
    global total
    total += 1
    if not cond:
        bad.append(msg)


def near(a, b, tol=0.005):
    return a is not None and abs(a - b) <= tol


EGGS = [
    {'store': 'ALDI', 'title': 'Lodge Farms Barn Eggs 12 Pack 700g', 'price': 5.29},           # 0  $7.56/kg
    {'store': 'Woolworths', 'title': 'Woolworths Cage Free Eggs 12 Pack 700g', 'price': 5.70, 'save_amount': 0.5},  # 1  $8.14/kg
    {'store': 'Woolworths', 'title': 'Woolworths Cage Free Eggs 18 Pack 900g', 'price': 8.00},  # 2  $8.89/kg
    {'store': 'Coles', 'title': 'Barossa Fresh Free Range Eggs 700g', 'price': 8.30},           # 3  free range: other kind
    {'store': 'ALDI', 'title': 'Lodge Farms Cage Eggs 12 Pack 700g', 'price': 5.00},            # 4  cage: other kind
    {'store': 'ALDI', 'title': 'Lodge Farms Barn Eggs 18 Pack 900g', 'price': 7.39},            # 5  $8.21/kg
    {'store': 'Coles', 'title': 'Coles Barn Eggs 12 Pack 700g', 'price': 4.00, 'period': 'next'},  # 6  next week: never mixed in
    {'store': 'Coles', 'title': 'Barossa Fresh Free Range Eggs 900g', 'price': 11.90},         # 7  free range, same store as 3
]
TABS = [
    {'store': 'ALDI', 'title': 'Power Force Dishwasher Tablets 46pk', 'price': 10.99, 'unit_price': '($0.24 per 1 each)'},  # 0
    {'store': 'Woolworths', 'title': 'Shine Dishwasher Tablets 30 Pack', 'price': 4.00, 'unit_price': '$0.13 / 1EA'},     # 1
    {'store': 'Coles', 'title': 'Finish Ultimate Dishwashing Tablets 46 Pack', 'price': 24.50},                           # 2  $0.53 from the title
    {'store': 'Coles', 'title': 'Finish Dishwasher Cleaner 250ml', 'price': 6.00},                                         # 3  not tablets
]

CALLS = [
    # 500 g and 1 kg at the same rate give the same price per kg; the shop's "$1.00 / 100G" says the same
    ('unitPriceOf', {'title': 'Rice 500g', 'price': 5.0}),
    ('unitPriceOf', {'title': 'Rice 1kg', 'price': 10.0}),
    ('unitPriceOf', {'title': 'Rice 1kg', 'price': 10.0, 'unit_price': '$1.00 / 100G'}),
    # 6 x 375 mL = 2.25 L
    ('unitPriceOf', {'title': 'Coca-Cola Classic Soft Drink Cans 6 x 375mL', 'price': 9.0}),
    # "2 for $12" is $6 each
    ('unitPriceOf', {'title': 'Olive Oil 1L', 'price': 7.0, 'price_display': '2 for $12.00'}),
    # sold per item: no per-kg price
    ('unitPriceOf', {'title': 'Fairy Dishwashing Tablets 46 Pack', 'price': 24.0, 'unit_price': '$0.52 / 1EA'}),
    # price per item
    ('eachPriceOf', {'title': 'Fairy Dishwashing Tablets', 'price': 24.0, 'unit_price': '$0.49/ 1ea'}),
    ('eachPriceOf', {'title': 'ALMAT Laundry Capsules 50 Pack', 'price': 11.99, 'unit_price': '($0.24 per 1 each)'}),
    ('eachPriceOf', {'title': 'Finish Ultimate Dishwashing Tablets 46 Pack', 'price': 24.50}),
    ('eachPriceOf', {'title': 'Earth Choice Dishwasher Tablets Pk 80', 'price': 20.0}),
    ('eachPriceOf', {'title': 'Omo Laundry Capsules 28 Washes 28 Pack', 'price': 14.0}),
    ('eachPriceOf', {'title': 'Omo Laundry Liquid 2 Litre or Capsules 28 Pack', 'price': 20.0}),    # a choice: no count
    ('eachPriceOf', {'title': 'Laundry Capsules 50 Pack', 'price': 11.99, 'unit_price': '$0.80 / 1EA'}),  # disagree: nothing
    # the kind of product
    ('cmpTypeOf', EGGS[0]),
    ('cmpTypeOf', EGGS[3]),
    ('cmpTypeOf', EGGS[4]),
    ('cmpTypeOf', {'title': 'Praise Whole Egg Mayonnaise with Eggs 400g', 'price': 4.0}),
    ('cmpTypeOf', {'title': 'Cadbury Mini Eggs 200g', 'price': 6.0}),
    ('cmpTypeOf', TABS[3]),
]

# the kinds added in Oct 2026: (item, expected kind key or None, what it guards). Real titles from the data.
KINDS = [
    ({'store': 'ALDI', 'title': 'WESTACRE DAIRY Tasty Cheese Block 500g', 'price': 5.99, 'unit_price': '($11.98 per 1 kg)'}, 'cheese||bltasty', 'ALDI tasty block'),
    ({'store': 'Woolworths', 'title': 'Woolworths Tasty Cheese Block 1kg', 'price': 10.50}, 'cheese||bltasty', 'Woolworths tasty block pairs with ALDI'),
    ({'store': 'Woolworths', 'title': 'Woolworths Tasty Shredded Cheese 500g', 'price': 8.30}, 'cheese||shtasty', 'shredded is not a block'),
    ({'store': 'Woolworths', 'title': 'Woolworths Light Tasty Cheese Block 250g', 'price': 4.90}, 'cheese||bllite', 'light cheese apart'),
    ({'store': 'Coles', 'title': 'Cobs Natural Popcorn Cheddar Cheese 100g', 'price': 3.50}, None, 'cheese popcorn is not cheese'),
    ({'store': 'Coles', 'title': 'Real Foods Corn Thins Tasty Cheese 125g', 'price': 3.00}, None, 'corn thins are not cheese'),
    ({'store': 'Coles', 'title': 'REMANO Long-life Grated Parmesan Cheese 100g', 'price': 3.00}, None, 'shelf parmesan is not fridge parmesan'),
    ({'store': 'Woolworths', 'title': 'Tasmanian Heritage Vintage Club Cheddar 140g', 'price': 7.00}, None, 'deli club cheddar'),
    ({'store': 'Woolworths', 'title': 'Farmers Union Greek Style Natural Yoghurt 1kg', 'price': 7.50}, 'yoghurt_greek||', 'plain greek yoghurt'),
    ({'store': 'Woolworths', 'title': 'Farmers Union Light Greek Style Yoghurt 1kg', 'price': 7.50}, 'yoghurt_greek||L', 'light greek yoghurt apart'),
    ({'store': 'Woolworths', 'title': 'Farmers Union Lactose Free Greek Style Yoghurt 500g', 'price': 5.30}, None, 'lactose free left out'),
    ({'store': 'Woolworths', 'title': 'Chobani Strawberry Greek Yogurt 160g', 'price': 1.95}, None, 'flavoured yoghurt left out'),
    ({'store': 'ALDI', 'title': 'BRAMWELLS Smooth Peanut Butter 375g', 'price': 2.25}, 'peanut_butter||', 'peanut butter'),
    ({'store': 'Coles', 'title': "Mayver's Natural Peanut Butter Smooth 375g", 'price': 5.00}, 'peanut_butter||N', 'natural peanut butter apart'),
    ({'store': 'Coles', 'title': "Reese's Peanut Butter Cups 46g", 'price': 2.50}, None, 'peanut butter cups are sweets'),
    ({'store': 'Woolworths', 'title': 'Tip Top The One White Bread 700g', 'price': 4.00}, 'bread||W', 'white loaf'),
    ({'store': 'Woolworths', 'title': "Helga's Wholemeal Bread 750g", 'price': 5.00}, 'bread||M', 'wholemeal loaf apart'),
    ({'store': 'Woolworths', 'title': 'Woolworths Banana Bread 450g', 'price': 5.00}, None, 'banana bread is cake'),
    ({'store': 'ALDI', 'title': 'MARKET FARE Baby Peas 1kg', 'price': 3.99, 'category': 'frozen'}, 'peas|F|', 'ALDI frozen peas (by category)'),
    ({'store': 'Woolworths', 'title': 'Bell Farms Frozen Baby Peas 1kg', 'price': 3.00}, 'peas|F|', 'frozen peas pair with ALDI'),
    ({'store': 'Woolworths', 'title': 'Baby Peas 1kg', 'price': 3.00, 'category': 'fruit-veg'}, None, 'peas not said to be frozen'),
    ({'store': 'Coles', 'title': 'Coles Chick Peas 400g', 'price': 1.00}, None, 'chick peas are not peas'),
    ({'store': 'Woolworths', 'title': 'Sorbent Soft & Strong 3 Ply Toilet Paper 20 pack', 'price': 8.50, 'unit_price': '$0.24 / 100 sheets'}, 'toilet_paper||3', '3 ply toilet paper'),
    ({'store': 'Woolworths', 'title': 'Quilton Gold King Size 4 Ply Toilet Paper 20 pack', 'price': 13.50, 'unit_price': '$0.56 / 100 sheets'}, 'toilet_paper||4', '4 ply apart from 3 ply'),
    ({'store': 'Woolworths', 'title': 'Kleenex Toilet Paper Flushable Wipes 42 pack', 'price': 4.00, 'unit_price': '$0.10 / 1EA'}, None, 'wipes are not toilet paper'),
    ({'store': 'Coles', 'title': 'Cold Power Laundry Liquid Advanced Clean 2L', 'price': 13.00}, 'laundry_liquid||', 'laundry liquid'),
    ({'store': 'Coles', 'title': 'Cold Power Laundry Powder Advanced Clean 2kg', 'price': 13.00}, 'laundry_powder||', 'powder apart from liquid'),
    ({'store': 'Coles', 'title': 'Morning Fresh Original Dishwashing Liquid 900mL', 'price': 5.00}, 'dish_liquid||', 'dishwashing liquid'),
    ({'store': 'Coles', 'title': 'Finish Dishwasher Powder Lemon 1kg', 'price': 8.00}, None, 'dishwasher powder is not dish liquid'),
    ({'store': 'Coles', 'title': 'Nescafe Blend 43 Instant Coffee 150g', 'price': 7.25}, 'coffee_instant||', 'instant coffee'),
    ({'store': 'Woolworths', 'title': 'Moccona Freeze Dried Coffee 400g', 'price': 26.00}, 'coffee_instant||P', 'freeze dried apart'),
    ({'store': 'Coles', 'title': 'Nescafe Cappuccino Instant Coffee Sachets 10 Pack', 'price': 6.00}, None, 'cappuccino sachets left out'),
    ({'store': 'Coles', 'title': 'Vittoria Espressotoria Espresso Coffee Capsules 12 Pack 78g', 'price': 5.50, 'unit_price': '$0.46/ 1ea'}, 'coffee_caps||E', 'Espressotoria capsules apart'),
    ({'store': 'Woolworths', 'title': 'Lavazza Classico Coffee Pods Nespresso Compatible 10 pack', 'price': 4.75, 'unit_price': '$0.48 / 1EA'}, 'coffee_caps||', 'Nespresso-type capsules'),
    # false pairings the 比價 filter showed side by side (Oct 2026 audit of every group)
    ({'store': 'Woolworths', 'title': 'Woolworths Chicken Breast Kyiv Kyiv 350g', 'price': 7.50}, None, 'chicken Kyiv is not chicken breast'),
    ({'store': 'ALDI', 'title': 'BERG Shredded Chicken Breast 500g', 'price': 6.99}, None, 'shredded chicken is deli'),
    ({'store': 'ALDI', 'title': 'BROAD OAK FARMS RSPCA Approved Chicken Breast Fillets per kg', 'price': 7.19, 'unit_price': '($11.99 per 1 kg)'}, 'chicken_breast||', 'plain chicken breast still compared'),
    ({'store': 'Woolworths', 'title': 'Woolworths Pork & Beef Mince 500g', 'price': 6.25}, None, 'pork & beef mince is not beef mince'),
    ({'store': 'Woolworths', 'title': 'Continental Classics Recipe Base Rich Beef Mince 50g', 'price': 1.80}, None, 'recipe base is a sauce mix'),
    ({'store': 'ALDI', 'title': 'JINDURRA STATION Regular Beef Mince 500g', 'price': 6.99}, 'beef_mince||r', 'plain beef mince still compared'),
    ({'store': 'ALDI', 'title': 'EL TORA Crunchy Corn Taco Shells 12 Pack 156g', 'price': 2.79}, None, 'taco shells are not pasta'),
    ({'store': 'Woolworths', 'title': 'Woolworths Large Pasta Shells 500g', 'price': 1.00}, 'pasta||', 'pasta shells still pasta'),
    ({'store': 'Woolworths', 'title': 'Lantern Alley Prawn Fried Rice 400g', 'price': 7.00}, None, 'prawn fried rice is not prawns'),
    ({'store': 'Woolworths', 'title': 'Woolworths Indian Lamb Rogan Josh With Basmati Rice 350g', 'price': 8.00}, None, 'curry with rice is a meal'),
    ({'store': 'Woolworths', 'title': 'Woolworths Tasmanian Salmon Fillet With Rice & Green Beans 400g', 'price': 13.00}, None, 'salmon with rice is a meal'),
    ({'store': 'ALDI', 'title': 'WHITE MILL Raw Sugar 2kg', 'price': 2.79}, 'sugar||raw', 'WHITE MILL raw sugar is raw, not white'),
    ({'store': 'ALDI', 'title': 'WHITE MILL Brown Sugar 1kg', 'price': 2.89}, 'sugar||brown', 'WHITE MILL brown sugar is brown'),
    ({'store': 'Woolworths', 'title': 'CSR White Sugar 2kg', 'price': 3.60}, 'sugar||white', 'white sugar'),
    ({'store': 'Woolworths', 'title': 'CSR White Sugar Sticks 50 pack', 'price': 3.00}, None, 'sugar sticks left out'),
    ({'store': 'Woolworths', 'title': 'Always Fresh Cucumbers Bread & Butter 380g', 'price': 3.00}, None, 'bread & butter pickles are not butter'),
    ({'store': 'Woolworths', 'title': 'Pampas Butter Puff Pastry 550g', 'price': 6.00}, None, 'puff pastry is not butter'),
    ({'store': 'Woolworths', 'title': 'MasterFoods Lemon Butter Spread 280g', 'price': 3.75}, None, 'lemon butter is a spread'),
    ({'store': 'Woolworths', 'title': 'Fix & Fogg Everything Butter 275g', 'price': 5.00}, None, 'everything butter is a nut spread'),
    ({'store': 'Woolworths', 'title': 'Woolworths Salted Butter 500g', 'price': 7.00}, 'butter||', 'plain butter still compared'),
    ({'store': 'Woolworths', 'title': 'Cobram Estate Truffle Infused Olive Oil 250mL', 'price': 10.80}, None, 'truffle oil is not olive oil'),
]
SHEETS = [
    ({'unit_price': '$0.24 / 100 sheets'}, 0.24),
    ({'unit_price': '$0.32/ 100ea'}, 0.32),               # Coles writes "100ea"
    ({'unit_price': '($0.19 per 100 sheets)'}, 0.19),     # ALDI
    ({'unit_price': '$0.48 / 1EA'}, None),                # per item, not per 100 sheets
]
TP = [
    {'store': 'ALDI', 'title': 'CONFIDENCE Toilet Tissue 3 Ply 24 Pack', 'price': 8.39, 'unit_price': '($0.19 per 100 sheets)'},  # 0
    {'store': 'Woolworths', 'title': 'Sorbent Soft & Strong 3 Ply Toilet Paper 20 pack', 'price': 8.50, 'unit_price': '$0.24 / 100 sheets'},  # 1
    {'store': 'Woolworths', 'title': 'Quilton Gold King Size 4 Ply Toilet Paper 20 pack', 'price': 13.50, 'unit_price': '$0.56 / 100 sheets'},  # 2  4 ply
]

# the same product under another shop's wording: real titles and prices from the week of 15 Oct 2026
SAME = [
    {'store': 'Coles', 'title': 'Dine Classic Collection Cat Food 85g', 'price': 0.95},                                   # 0
    {'store': 'Woolworths', 'title': 'Dine Classic Gravy Collection Wet Cat Food 85g x 24 pack', 'price': 26.00},         # 1
    {'store': 'Coles', 'title': 'Vaalia Kids Probiotics Yoghurt Pouch 140g', 'price': 1.50},                              # 2
    {'store': 'Woolworths', 'title': 'Vaalia Kids Probiotic Yoghurt Pouch Vanilla 140g', 'price': 10, 'price_display': '5 for $10.00'},  # 3
    {'store': 'Woolworths', 'title': 'Vaalia Kids Probiotic Yoghurt Pouch Limited Edition Honeycomb 140g', 'price': 10, 'price_display': '5 for $10.00'},  # 4
    {'store': 'Woolworths', 'title': 'Vaalia Kids Probiotic Yoghurt Pouch Banana 140g', 'price': 10, 'price_display': '5 for $10.00'},  # 5
    {'store': 'Coles', 'title': 'John West Tuna 95g', 'price': 2.00},                                                     # 6
    {'store': 'Woolworths', 'title': 'John West Tuna In Sesame Oil 95g', 'price': 1.45},                                  # 7
    {'store': 'Woolworths', 'title': 'John West Tuna Spread 95g', 'price': 2.85},                                         # 8
    {'store': 'Woolworths', 'title': 'John West Tuna With Tangy Jalapenos Jalapeno Tuna 95g', 'price': 1.45},             # 9
    {'store': 'Coles', 'title': 'Batiste Sensitive Dry Shampoo 200mL', 'price': 7.00},                                    # 10
    {'store': 'Woolworths', 'title': 'Batiste Dry Shampoo Original 200mL', 'price': 7.00},                                # 11
    {'store': 'Coles', 'title': 'Batiste Original Instant Refresh Dry Shampoo 200mL', 'price': 7.00},                     # 12
    {'store': 'Woolworths', 'title': 'White Wings Plain Flour 2kg', 'price': 4.40},                                       # 13
    {'store': 'ALDI', 'title': 'WHITE MILL Plain Flour 2kg', 'price': 2.39},                                              # 14
    {'store': 'Coles', 'title': 'Rexona Women Deodorant 48hr Aerosol Hypoallergenic 250mL', 'price': 4.25},               # 15
    {'store': 'Woolworths', 'title': 'Rexona Women 48hr Deodorant Aerosol Classic 250mL', 'price': 5.00},                 # 16
    {'store': 'Coles', 'title': 'Rexona Women Deodorant 48hr Aerosol Classic 250mL', 'price': 4.25},                      # 17
    {'store': 'Woolworths', 'title': 'Head & Shoulders Cool Menthol Anti Dandruff Shampoo for Irritated Scalp 660mL', 'price': 11.50},  # 18
    {'store': 'Coles', 'title': 'Head & Shoulders Anti-dandruff Shampoo Dry Scalp Care 660mL', 'price': 11.50},           # 19
    {'store': 'Woolworths', 'title': 'Head & Shoulders Dry Scalp Care Anti Dandruff Shampoo 660mL', 'price': 11.50},      # 20
    {'store': 'ALDI', 'title': "PRINGLES Mini's Sour Cream & Onion Potato Chips 5 Pack 19g", 'price': 3.49},              # 21
    {'store': 'Woolworths', 'title': 'Pringles Minis Sour Cream & Onion Potato Chips 19g x 5 pack', 'price': 7, 'price_display': '2 for $7.00'},  # 22
    {'store': 'Woolworths', 'title': 'Pringles Minis Original Potato Chips 19g x 5 pack', 'price': 7, 'price_display': '2 for $7.00'},  # 23
    {'store': 'Coles', 'title': 'Schweppes Natural Mineral Water 300ml 4 Pack', 'price': 4.00},                           # 24
    {'store': 'Woolworths', 'title': 'Schweppes Natural Mineral Water Glass Bottle 300mL x 4 pack', 'price': 11, 'price_display': '2 for $11.00'},  # 25
    {'store': 'Coles', 'title': 'Schweppes Natural Mineral Water Bottle 1.1L', 'price': 1.65},                            # 26
    {'store': 'Coles', 'title': 'Lipton Ice Tea Peach Tea Iced Tea Bottle 1.5L', 'price': 2.95},                          # 27
    {'store': 'Woolworths', 'title': 'Lipton Ice Tea Peach Flavour Iced Tea Peach 1.5L', 'price': 7.90, 'price_display': '2 for $7.90'},  # 28
    {'store': 'Coles', 'title': 'Coles Plain Flour 2kg', 'price': 2.60},                                                  # 29
    {'store': 'Woolworths', 'title': 'Woolworths Plain Flour 2kg', 'price': 2.60},                                        # 30
    {'store': 'Coles', 'title': 'Head & Shoulders Anti-dandruff Shampoo Smooth & Silky 660mL', 'price': 11.50},           # 31
    {'store': 'Woolworths', 'title': 'Head & Shoulders Smooth & Silky Anti Dandruff Shampoo 660mL', 'price': 11.50},      # 32
    {'store': 'Coles', 'title': 'Lipton Ice Tea Peach Tea Iced Tea Bottle 1.5L', 'price': 2.95, 'period': 'next'},        # 33
]
PAIRS = [
    (0, 1, False, 'one 85g tin is not a 24 pack'),
    (2, 3, False, 'unflavoured Vaalia is not vanilla'),
    (2, 4, False, 'Coles "Vaalia Kids ... Pouch" names the whole Woolworths range, not one flavour'),
    (6, 7, False, 'tuna is not tuna in sesame oil'),
    (6, 8, False, 'tuna is not tuna spread'),
    (6, 9, False, 'tuna is not jalapeno tuna'),
    (10, 11, False, 'Batiste Sensitive is not Original'),
    (11, 12, True, 'Batiste Original, worded differently'),
    (13, 14, False, 'White Wings is not WHITE MILL'),
    (15, 16, False, 'Rexona Hypoallergenic is not Classic'),
    (16, 17, True, 'Rexona Women Classic 250mL'),
    (18, 19, False, 'H&S Cool Menthol is not Dry Scalp Care'),
    (19, 20, True, 'H&S Dry Scalp Care shampoo 660mL'),
    (21, 22, True, 'Pringles Minis sour cream & onion 5 x 19g'),
    (21, 23, False, 'sour cream & onion is not original'),
    (24, 25, True, 'Schweppes mineral water 300mL 4 pack'),
    (25, 26, False, '4 x 300mL is not 1.1L'),
    (27, 28, True, 'Lipton peach iced tea 1.5L'),
    (29, 30, False, "shops' own brands are never paired on the words"),
    (31, 32, True, 'H&S Smooth & Silky shampoo 660mL'),
    (33, 28, False, 'next week is never paired with this week'),
]
FOUND = [(21, {'Woolworths': 22}), (2, {}), (6, {}), (0, {})]

res = subprocess.run(['node', '-e', JS, os.path.join(ROOT, 'static', 'compare.js')],
                     input=json.dumps({'calls': CALLS + [('cmpTypeOf', k[0]) for k in KINDS] + [('sheetPriceOf', x[0]) for x in SHEETS],
                                       'lists': {'eggs': EGGS, 'tabs': TABS, 'tp': TP},
                                       'vc': [['eggs', 0], ['eggs', 1], ['eggs', 3], ['eggs', 6],
                                              ['tabs', 0], ['tabs', 1], ['tabs', 3], ['tp', 1]],
                                       'same': SAME, 'pairs': [p[:2] for p in PAIRS], 'found': [f[0] for f in FOUND]}),
                     capture_output=True, text=True, encoding='utf-8')
if res.returncode != 0:
    print(res.stderr)
    sys.exit(1)
out = json.loads(res.stdout)
r = [x and x.get('value') if isinstance(x, dict) else x for x in out['calls']]

check(near(r[0], 10.0) and near(r[1], 10.0) and near(r[2], 10.0), f'500 g vs 1 kg per kg: {r[0:3]}')
check(near(r[3], 4.0) and out['calls'][3]['basis'] == 'L', f'6 x 375 mL -> $4.00/L: {out["calls"][3]}')
check(near(r[4], 6.0), f'2 for $12 -> $6/L: {r[4]}')
check(r[5] is None, f'per-item product has no per-kg price: {r[5]}')
check(near(r[6], 0.49) and out['calls'][6]['basis'] == 'ea', f'"$0.49/ 1ea": {out["calls"][6]}')
check(near(r[7], 0.24), f'"($0.24 per 1 each)": {r[7]}')
check(near(r[8], 24.50 / 46), f'"46 Pack" from the title: {r[8]}')
check(near(r[9], 0.25), f'"Pk 80": {r[9]}')
check(near(r[10], 0.5), f'"28 Washes 28 Pack" is one count: {r[10]}')
check(r[11] is None, f'"Liquid ... or Capsules 28 Pack" has no single count: {r[11]}')
check(r[12] is None, f'shop figure and pack count disagree -> nothing: {r[12]}')
check(out['calls'][13] == 'eggs||B', f'barn eggs: {out["calls"][13]}')
check(out['calls'][14] == 'eggs|R|', f'free range eggs: {out["calls"][14]}')
check(out['calls'][15] == 'eggs||C', f'cage eggs: {out["calls"][15]}')
check(out['calls'][16] is None, f'mayonnaise is not eggs: {out["calls"][16]}')
check(out['calls'][17] is None, f'chocolate eggs are not eggs: {out["calls"][17]}')
check(out['calls'][18] is None, f'dishwasher cleaner is not tablets: {out["calls"][18]}')
check(near(out['copy'], 10.0), f"a state's own price gets its own figure: {out['copy']}")

n = len(CALLS)
for (item, want, why), got in zip(KINDS, out['calls'][n:n + len(KINDS)]):
    check(got == want, f'{why}: {item["title"]} -> {got!r}, want {want!r}')
for (item, want), got in zip(SHEETS, out['calls'][n + len(KINDS):]):
    check((got is None) if want is None else (got and got['basis'] == 'sh' and near(got['value'], want)),
          f'price per 100 sheets from {item["unit_price"]!r}: {got}')

aldi_barn, wool_cf, fr, nxt, aldi_tabs, wool_tabs, cleaner, sorbent = out['vc']
# ALDI barn 700g $7.56/kg vs Woolworths cage free 700g $8.14/kg (Coles free range is another kind)
check(aldi_barn and aldi_barn['verdict'] == 'cheaper' and near(aldi_barn['diff'], 0.59) and aldi_barn['lowest']
      and aldi_barn['stores'] == ['Woolworths'] and '700g' in aldi_barn['cheapest'], f'ALDI barn eggs: {aldi_barn}')
check(wool_cf and wool_cf['verdict'] == 'dearer' and not wool_cf['lowest'] and wool_cf['stores'] == ['ALDI']
      and wool_cf['cheapest'] == EGGS[0]['title'], f'Woolworths cage free eggs: {wool_cf}')
check(fr is None, f'free range eggs: only Coles has them -> nothing to compare: {fr}')
check(nxt is None, f'next week is never compared with this week: {nxt}')
# dishwasher tablets per item: Woolworths $0.13 < ALDI $0.24 < Coles $0.53
check(aldi_tabs and aldi_tabs['verdict'] == 'dearer' and aldi_tabs['stores'] == ['Woolworths', 'Coles']
      and near(aldi_tabs['diff'], 0.11) and aldi_tabs['basis'] == 'ea' and not aldi_tabs['lowest'], f'ALDI tablets: {aldi_tabs}')
check(wool_tabs and wool_tabs['verdict'] == 'cheaper' and wool_tabs['lowest'], f'Woolworths tablets: {wool_tabs}')
check(cleaner is None, f'dishwasher cleaner: {cleaner}')
# toilet paper per 100 sheets: Woolworths 3 ply $0.24 vs ALDI 3 ply $0.19 (the 4 ply is another kind)
check(sorbent and sorbent['verdict'] == 'dearer' and sorbent['stores'] == ['ALDI'] and sorbent['basis'] == 'sh'
      and near(sorbent['diff'], 0.05), f'Woolworths 3 ply toilet paper: {sorbent}')

for (i, j, want, why), got in zip(PAIRS, out['pairs']):
    check(bool(got) == want, f'same product? {why}: {SAME[i]["title"]} / {SAME[j]["title"]} -> {got}')
for (i, want), got in zip(FOUND, out['found']):
    check(got == want, f'same product elsewhere for {SAME[i]["title"]}: {got}, want {want}')
check(near(out['each'][3], 2.0) and near(out['each'][22], 3.5) and near(out['each'][2], 1.5),
      f'"5 for $10.00" is $2.00 each, "2 for $7.00" $3.50: {[out["each"][k] for k in (2, 3, 22)]}')

# every kind compared gets a group name in all four languages (三家比價 group headers)
I18N_JS = r'''
const fs = require('fs'), vm = require('vm');
const store = { getItem: () => null, setItem() {}, removeItem() {} };
const ctx = { window: { localStorage: store }, localStorage: store, document: { querySelectorAll: () => [] }, console };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8') + '\n;this.I18N = I18N;', ctx);
const { CMP_TYPES } = require(process.argv[2]);
const out = [];
for (const lang of ['zh', 'en', 'ja', 'ko'])
    for (const ty of CMP_TYPES) if (!(ctx.I18N[lang].cmp_kind || {})[ty.k]) out.push(lang + ':' + ty.k);
// the product window's 本週三家價格 box (app.js renderSameProducts) in all four languages too
for (const lang of ['zh', 'en', 'ja', 'ko'])
    for (const k of ['cross_store_title', 'cross_store_title_next', 'cmp3_cheapest', 'cmp3_cheapest_next', 'cmp3_none',
                     'cmp3_none_next', 'cmp3_regular', 'cmp3_cheapest_of3', 'aldi_cmp_title', 'cmp_same_item'])
        if (!ctx.I18N[lang][k]) out.push(lang + ':' + k);
console.log(JSON.stringify(out));
'''
r = subprocess.run(['node', '-e', I18N_JS, os.path.join(ROOT, 'static', 'i18n.js'), os.path.join(ROOT, 'static', 'compare.js')],
                   capture_output=True, text=True, encoding='utf-8')
check(r.returncode == 0, 'i18n.js loads in node: ' + r.stderr[-300:])
missing = json.loads(r.stdout or '[]') if r.returncode == 0 else []
check(not missing, f'compare kinds without a group name, or 三家價格 text missing: {missing}')

for b in bad:
    print('FAIL', b)
print(f'{total - len(bad)}/{total} price comparison checks passed')
sys.exit(1 if bad else 0)
