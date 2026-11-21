"""The price under each card in a sensible unit (per can / bottle / egg / roll / item, else per kg / litre),
and 同品牌放一起比價 grouping by brand (compare.js sensibleUnitOf, brandKeyOf)."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = r"""
const c = require(process.argv[1]);
const cases = JSON.parse(process.argv[2]);
console.log(JSON.stringify(cases.map(x => {
    const u = c.sensibleUnitOf(x.item);
    return { u: u ? [u.basis, Math.round(u.value * 100) / 100] : null, k: c.brandKeyOf(x.item, x.kind), v: c.variantKeyOf(x.item) };
})));
"""


def it(title, price, display=None, unit='', cat='drinks', store='Coles', was=0):
    return {'title': title, 'price': price, 'price_display': display or f'${price:.2f}', 'unit_price': unit,
            'category': cat, 'store': store, 'was_price': was}


UNITS = [   # (item, expected [basis, value] or None)
    (it('Monster Energy Drink Ultra 4x500ml 2L', 10.50, unit='$5.25/ 1L'), ['can', 2.63]),
    (it('Monster Energy Cans Green 6x250ml 1.5L', 10.50), ['can', 1.75]),
    (it('Monster Energy Drink Lando Norris 500mL 4 Pack', 10.50, unit='$5.25/ 1L'), ['can', 2.63]),
    (it('Monster Energy Drink Bad Apple 500mL', 4.70, '2 for $7.90', '$9.40/ 1L', was=9.40), ['can', 3.95]),
    (it('Coca-Cola Soft Drink 30x375mL', 32.00, '$32.00 each'), ['can', 1.07]),
    (it('COCA-COLA Coke Coca Cola Soft Drink 600ml', 4.19, store='ALDI'), ['btl', 4.19]),
    (it('Coca-Cola Classic Soft Drink 2 Litre', 4.00), ['L', 2.0]),                # a big bottle stays per litre
    (it('Bundaberg Brewed Ginger Beer 750mL', 3.00), ['btl', 3.0]),
    (it('Coles Free Range Eggs 12 Pack 700g', 5.90, cat='dairy_eggs'), ['egg', 0.49]),
    (it('LODGE FARMS Cage Eggs 700g', 5.00, unit='($0.71 per 100 g)', cat='dairy_eggs', store='ALDI'), ['kg', 7.1]),  # no count: no guess
    (it('DAIRY FINE Solid Milk Chocolate Eggs 400g', 4.99, cat='snacks', store='ALDI'), ['kg', 12.48]),
    (it('CONFIDENCE Toilet Tissue 3 Ply 24 Pack', 8.39, cat='household', store='ALDI'), ['roll', 0.35]),
    (it('Viva White Paper Towel 120 Sheets 2 x 60 pack', 2.00, cat='household'), ['roll', 1.0]),
    (it('POWER FORCE Dishwashing Tablets 45 Pack', 5.99, unit='($0.13 per 1 each)', cat='household', store='ALDI'), ['ea', 0.13]),
    (it('CUCINA Red Wine Vinegar 500ml', 2.49, cat='liquor', store='ALDI'), ['L', 4.98]),   # not a drink
    (it('Cut Watermelon per kg', 2.99, cat='produce', store='ALDI'), ['kg', 2.99]),
]
KEYS = [   # (item, kind, expected brand key)
    (it('Monster Energy Drink Ultra 4x500ml 2L', 10.5), 'sub_energy', 'monster|sub_energy'),
    (it('Monster Energy Aussie Lemonade Can 500mL', 3.95), 'sub_energy', 'monster|sub_energy'),
    (it('RED BULL Red Bull Energy Drink 4x250ml', 8.99, store='ALDI'), 'sub_energy', 'red bull|sub_energy'),
    (it('Red Bull Energy Drink Original 4x250ml 1L', 6.5), 'sub_energy', 'red bull|sub_energy'),
    (it('Mr Kipling Lemon Cake Slices 6 Pack', 3.1), 'bakery', 'mr kipling|bakery'),
    (it('Coles Free Range Eggs 12 Pack 700g', 5.9), 'eggs', 'coles|eggs|egg'),
    (it("Smith's Thinly Cut Potato Chips 175g", 3.0), 'chips', 'smiths|chips'),
]

VARIANTS = [   # (title A, title B, same flavour?)
    ('Monster Energy Drink Ultra Violet 4x500ml 2L', 'Monster Energy Ultra Violet Cans 500mL x 4 pack', True),
    ('Monster Energy Drink Green 4x500ml 2L', 'Monster Energy Cans Green 6x250ml 1.5L', True),
    ('Monster Energy Ultra Can 500mL', 'Monster Energy Cans Ultra 6x250ml 1.5L', True),
    ('Monster Energy Drink Ultra 4x500ml 2L', 'Monster Energy Drink Ultra Violet 4x500ml 2L', False),   # strict
    ('Monster Energy Drink Peach 4x500ml 2L', 'Monster Energy Ultra Peachy Keen Can 500mL', False),
]

fails = 0


def check(cond, msg):
    global fails
    if not cond:
        fails += 1
        print('FAIL', msg)


cases = [{'item': x[0]} for x in UNITS] + [{'item': x[0], 'kind': x[1]} for x in KEYS] + \
    [{'item': it(t, 1.0)} for v in VARIANTS for t in v[:2]]
r = subprocess.run(['node', '-e', JS, os.path.join(ROOT, 'static', 'compare.js'), json.dumps(cases)], capture_output=True, text=True)
check(r.returncode == 0, 'node runs: ' + r.stderr[-300:])
out = json.loads(r.stdout) if r.returncode == 0 else []
for (item, want), got in zip(UNITS, out[:len(UNITS)]):
    ok = (want is None and got['u'] is None) or (got['u'] and got['u'][0] == want[0] and abs(got['u'][1] - want[1]) < 0.02)
    check(ok, f"unit {item['title']}: want {want}, got {got['u']}")
for (item, kind, want), got in zip(KEYS, out[len(UNITS):]):
    check(got['k'] == want, f"brand {item['title']}: want {want}, got {got['k']}")
vo = out[len(UNITS) + len(KEYS):]
for n, (a, b, same) in enumerate(VARIANTS):
    if len(vo) > 2 * n + 1:
        check((vo[2 * n]['v'] == vo[2 * n + 1]['v']) == same, f"variant {a} / {b}: {vo[2 * n]['v']!r} vs {vo[2 * n + 1]['v']!r}")
total = len(UNITS) + len(KEYS) + len(VARIANTS)
print(f'{total - fails}/{total} sensible-unit checks passed')
sys.exit(1 if fails else 0)
