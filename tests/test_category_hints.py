"""Checks for how products that no category rule recognises are placed (categories.py):
rules first, then the AI's answer, then the supermarket's own aisle, then a last guess.

    python tests/test_category_hints.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import categories as c  # noqa: E402

AISLES = [
    # Coles website aisles
    ('Skin Care Facial Skincare', 'health_vitamins'), ('Water Value Added Waters', 'drinks'),
    ('Biscuits & Cookies Cream/Plain Biscuits', 'snacks'), ('Rice Ready To Eat', 'pantry'),
    ('Ice Cream Super Premium Tubs', 'frozen'), ('Infant Personal Baby Wipes', 'health_vitamins'),
    ('Skin Care Tanning', 'health_vitamins'), ('Vitamins Bone & Joint', 'health_vitamins'),
    ('Asian Foods Asian Sweet Snacks', 'snacks'), ('Cleaning Goods Surface Cleaners', 'household'),
    # Woolworths website departments
    ('["Beauty & Personal Care"] ["Hair Care"] Hair Styling', 'health_vitamins'),
    ('["Health & Wellness"] ["Sports Nutrition"]', 'health_vitamins'), ('["Pantry"] ["Health Foods"]', 'pantry'),
    ('["Meat & Seafood"] ["Fresh Seafood"]', 'seafood'), ('["Meat & Seafood"] ["Beef & Veal"]', 'meat'),
    ('["Dairy, Eggs & Fridge"]', 'dairy_eggs'), ('["Snacks & Confectionery"]', 'snacks'), ('["Freezer"]', 'frozen'),
    # catalogue links
    ('food and beverage groceries deli and chilled', 'dairy_eggs'), ('food and beverage confectionery', 'snacks'),
    ('food and beverage groceries beauty', 'health_vitamins'), ('food and beverage groceries seafood', 'seafood'),
    ('food and beverage groceries beer wine and spirit', 'liquor'), ('food and beverage groceries pet care', 'pet'),
    ('food and beverage groceries stationery and media', 'household'), ('food and beverage groceries toiletries', 'health_vitamins'),
    ('food and beverage groceries cooking seasoning and gravy', 'pantry'), ('food and beverage groceries frozen food', 'frozen'),
    # nothing useful: no hint
    ('Groceries', ''), ('household', ''), ('pantry', ''), ('', ''), ('food and beverage groceries baby', ''),
]

URLS = [
    ('https://www.salefinder.com.au/68146/food-and-beverage/groceries/deli-and-chilled/cucina-classica-meal/681461/',
     'food and beverage groceries deli and chilled'),
    # the product name ("dairy milk") is not part of the aisle
    ('https://www.salefinder.com.au/68143/food-and-beverage/confectionery/cadbury-dairy-milk-block-chocolate-160g190g/681431001/',
     'food and beverage confectionery'),
    ('https://www.coles.com.au/product/x-123', ''), ('', ''),
]


def main():
    bad = []
    for aisle, want in AISLES:
        got = c.aisle_category(aisle)
        if got != want:
            bad.append(f'aisle {aisle!r}: {got!r}, expected {want!r}')
    for url, want in URLS:
        got = c.aisle_from_url(url)
        if got != want:
            bad.append(f'url {url[:60]}: {got!r}, expected {want!r}')

    # use a temporary answers file, so the checks do not depend on the real data
    real_file = c.AI_CATEGORIES_FILE
    with tempfile.TemporaryDirectory() as tmp:
        c.AI_CATEGORIES_FILE = os.path.join(tmp, 'ai_categories.json')
        with open(c.AI_CATEGORIES_FILE, 'w', encoding='utf-8') as f:
            json.dump({'Zinda Cola Crush 250mL': {'category': 'drinks'},
                       'Mystery Thing 1 each': {'category': 'not-a-department'},     # invalid: ignored
                       'Coles Full Cream Milk 2L': {'category': 'household'}}, f)   # a rule knows milk: rule wins
        c.ai_categories(reload=True)
        checks = [
            # (title, aisle, url, expected department, expected way)
            ('Zinda Cola Crush 250mL', 'Indian Foods Authentic Indian', '', 'drinks', 'ai'),        # AI beats a vague aisle
            ('Cosrx Bha Blackhead Power Liquid 100mL', 'Skin Care Facial Skincare', '', 'health_vitamins', 'aisle'),
            ('Mystery Thing 1 each', '', '', 'household', 'guessed'),                                 # invalid AI answer ignored
            ('Coles Full Cream Milk 2L', 'Cleaning Goods', '', 'dairy_eggs', 'rule'),                 # rules always win
            ('Cucina Classica Meal 300g-350g', '', URLS[0][0], 'dairy_eggs', 'aisle'),                # aisle from the link
            # nothing known at all: the last guess still reads the title
            ('Zqx Gummi Fangs 300g', '', '', 'snacks', 'guessed'),
            ('Zqx Assorted Fruit Snacks 24 Pack 480g', '', '', 'snacks', 'guessed'),
            ('Zqx Metallic Gold Hair Claw Clip 2 Pack', '', '', 'health_vitamins', 'guessed'),
            ('Zqx Sheet Set Sateen 800TC Queen Bed', '', '', 'household', 'guessed'),
            ('Zqx Assorted Baking Spice 255g', '', '', 'pantry', 'guessed'),
        ]
        for title, aisle, url, want, way in checks:
            c.HINTED.clear()
            c.GUESSED.clear()
            got = c.classify_product(title, aisle, url)
            how = c.HINTED.get(title) or ('guessed' if title in c.GUESSED else 'rule')
            if (got, how) != (want, way):
                bad.append(f'{title}: {got} by {how}, expected {want} by {way}')
        # rules only (as used to find the products the AI is asked about)
        c.GUESSED.clear()
        c.classify_product('Zinda Cola Crush 250mL', 'Indian Foods', use_hints=False)
        if 'Zinda Cola Crush 250mL' not in c.GUESSED:
            bad.append('use_hints=False must not use the AI answers')
        # a missing or broken answers file never breaks classifying
        with open(c.AI_CATEGORIES_FILE, 'w', encoding='utf-8') as f:
            f.write('{not json')
        c.ai_categories(reload=True)
        if c.classify_product('Cosrx Bha Blackhead Power Liquid 100mL', 'Skin Care Facial Skincare') != 'health_vitamins':
            bad.append('a broken answers file must fall back to the aisle')
    c.AI_CATEGORIES_FILE = real_file
    c.ai_categories(reload=True)

    # every hand-checked answer in the real file is a real department
    with open(real_file, encoding='utf-8') as f:
        real = json.load(f)
    for title, e in real.items():
        if e.get('category') not in c.PRODUCT_CATEGORIES:
            bad.append(f'data/ai_categories.json: {title}: {e.get("category")!r} is not a department')

    total = len(AISLES) + len(URLS) + len(checks) + 2 + len(real)
    for b in bad:
        print('FAIL', b)
    print(f'{total - len(bad)}/{total} category-hint checks passed')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
