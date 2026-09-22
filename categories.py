import re

# Standard Category Keys (Aligned with Australian Supermarket Departments)
CATEGORIES = [
    'all',
    'produce',
    'meat',
    'seafood',
    'dairy_eggs',
    'bakery',
    'pantry',
    'snacks',
    'drinks',
    'frozen',
    'health_vitamins',
    'household'
]

CATEGORY_RULES = {
    # 1. Health & Vitamins (vitamins, supplements, pain relief, health shots)
    'health_vitamins': [
        r'berocca', r'effervescents?', r'cenovis', r'voost', r'multivitamins?', r'multi-vitamins?',
        r'panadol', r'nurofen', r'paracetamol', r'band-aid', r'vitamins?', r'swisse',
        r'blackmores', r"nature['\u2019]?s\s*(?:way|own)", r'henry\s*blooms', r'magnesium',
        r'caltrate', r'centrum', r'vitaceuticals', r'hydralyte',
        r'(?:health|vitamin|oil|daily|herbal|dietary)\s*capsules?', r'chewables?', r'fish\s*oil',
        r'krill\s*oil', r'omega\s*3', r'probiotic\s*(?:daily|capsule|health)', r'zinc',
        r'iron\s*(?:tablets?|capsules?|supplements?)', r'calcium', r'biotin',
        r'melatonin', r'whey', r'protein\s*powder', r'glucosamine', r'collagen', r'peptides?'
    ],

    # 2. Household & Personal Care (cleaning, laundry, paper, toiletries, cosmetics, containers, pet)
    'household': [
        r'toilet\s*paper', r'toilet\s*tissue', r'quilton', r'kleenex', r'sorbent',
        r'paper\s*towel', r'facial\s*tissue', r'tissue', r'wipes?', r'wet\s*wipes?',
        r'laundry', r'detergent', r'washing\s*powder', r'washing\s*liquid', r'omo',
        r'cold\s*power', r'radiant', r'dynamo', r'vanish', r'fabric\s*softener',
        r'dishwash', r'dishwashing', r'dishwasher', r'finish', r'fairy', r'morning\s*fresh',
        r'sponge', r'scourer', r'bin\s*liners?', r'garbage\s*bags?', r'foil', r'cling\s*wrap',
        r'baking\s*paper', r'glad\s*wrap', r'sandwich\s*bags?',
        r'pine\s*o\s*cleen', r'cleaner', r'spray', r'disinfectant', r'ajax', r'harpic', r'duck',
        r'shampoo', r'conditioner', r'body\s*wash', r'shower\s*gel', r'hand\s*wash',
        r'soap', r'dove', r'nivea', r'palmolive', r'pantene', r'head\s*&\s*shoulders',
        r'garnier', r'tresemme', r'deodorant', r'antiperspirant', r'rexona', r'lynx',
        r'toothpaste', r'toothbrush', r'colgate', r'oral[- ]b', r'sensodyne', r'floss', r'mouthwash',
        r'razor', r'gillette', r'schick', r'shaving', r'pads?', r'tampons?', r'stayfree', r'carefree',
        r'kotex', r'napp(?:y|ies)', r'diapers?', r'huggies', r'babylove', r'curash',
        r'l[\'’]?or[eé]al', r'revitalift', r'serum', r'moisturis(?:er|ing)', r'moisturiz(?:er|ing)',
        r'cica', r'infallible', r'olay', r'regenerist', r'retinol', r'setting\s*mist',
        r'hair\s*dye', r'colourant', r'schwarzkopf', r'beauty',
        r'sunscreen', r'banana\s*boat', r'cancer\s*council',
        r'insect\s*spray', r'aerogard', r'raid', r'mortein', r'dettol', r'bleach',
        r'pet\s*food', r'dog\s*food', r'cat\s*food', r'dine', r'whiskas', r'pedigree',
        r'purina', r'supercoat', r'friskies', r'cat\s*litter', r'pooch', r'my\s*dog',
        r'batter(?:y|ies)', r'energizer', r'duracell', r'stationery', r'light\s*globe',
        r'container', r'sistema', r'd[eé]cor', r'locknlock', r'klip\s*it',
        r'bonds', r'socks?', r'briefs?', r'underwear', r'gift\s*cards?'
    ],

    # 3. Frozen Food (ice cream, frozen meals, frozen veggies, frozen snacks, pizza)
    'frozen': [
        r'from\s*the\s*freezer', r'freezer', r'ice\s*cream', r'gelato', r'sorbet',
        r'magnum', r'connoisseur', r'ben\s*&\s*jerry', r'peters', r'bulla',
        r'cyclone', r'calippo', r'paddle\s*pop', r'weis\s*bars?', r'ice\s*bars?',
        r'frozen\s*dessert', r'cornetto', r'frosty\s*fruit', r'frozen',
        r'pizza', r'dumplings?', r'gyoza', r'meat\s*pies?', r'party\s*pies?',
        r'herbert\s*adams', r'sausage\s*rolls?', r"four['\u2019]n\s*twenty", r'patties',
        r'fish\s*fingers?', r'fish\s*fillets?\s*frozen', r'chips\s*frozen', r'frozen\s*chips',
        r'birds\s*eye', r'golden\s*crunch', r'chicken\s*tenders?', r'chicken\s*chips',
        r'dino\s*nuggets', r'chiko\s*rolls?',
        r'potato\s*minis?', r'hash\s*browns?', r'wedges', r'frozen\s*berries',
        r'frozen\s*peas', r'frozen\s*veg', r'frozen\s*vegetables?', r'spring\s*rolls?',
        r'steam\s*buns?', r'dim\s*sims?', r'asian\s*selection', r'samosas?', r'frozen\s*meal'
    ],

    # 4. Drinks (coffee, tea, soft drinks, juices, water, cordial, energy drinks, alcohol)
    'drinks': [
        r'coffee', r'espresso', r'nescaf[eé]', r'moccona', r'vittoria', r'lavazza',
        r'starbucks', r'robert\s*timms', r'grinders', r"l['\u2019]or",
        r'tea', r'teabags?', r'twinings', r'dilmah', r'lipton', r'tetley', r'matcha',
        r'juice', r'orange\s*juice', r'apple\s*juice', r'daily\s*juice', r'nudie', r'golden\s*circle',
        r'coca-cola', r'coke', r'pepsi', r'sprite', r'fanta', r'schweppes', r'solo', r'kirks',
        r'kombucha', r'soda', r'soft\s*drink', r'cordial', r'water', r'sparkling\s*water',
        r'mineral\s*water', r'mt\s*franklin', r'pump', r'san\s*pellegrino',
        r'energy\s*drink', r'red\s*bull', r'monster\s*energy', r'v\s*energy',
        r'up&go', r'up\s*&\s*go', r'yakult', r'probiotic\s*drink',
        r'beer', r'corona', r'ale', r'lager', r'mid\s*strength', r"smithy['\u2019]?s",
        r'wine', r'cider', r'shiraz', r'sauvignon', r'tempranillo', r'rioja',
        r'hard\s*rated', r'zero\s*sugar', r'seltzer', r'cans?',
        r'beverage'
    ],

    # 5. Snacks & Confectionery (chips, chocolates, biscuits, nuts, candy, crackers, snack bars)
    'snacks': [
        r'chips?', r'crisps?', r'potato\s*chips', r'corn\s*chips', r'tortilla\s*chips',
        r'doritos', r"smith['\u2019]?s", r'red\s*rock\s*deli', r'cheezels', r'twisties',
        r'pringles', r'kettle', r'grainwaves', r'harvest\s*snaps', r'calbee', r'popcorn',
        r'chocolate', r'pralines?', r'toblerone', r'cadbury', r'lindt', r'kit\s*kat',
        r'm&m', r'maltesers', r'mars', r'snickers', r'twix', r'bounty', r'guylian', r'ferrero',
        r'biscuits?', r'cookies?', r'tim\s*tams?', r'crackers?', r'ritz', r'oreo',
        r"arnott['\u2019]?s", r"mcvitie['\u2019]?s", r'digestives?', r'shapes', r'belvita', r'wafer',
        r'nuts?', r'peanuts?', r'almonds?', r'cashews?', r'walnuts?', r'pistachios?',
        r'macadamias?', r'trail\s*mix',
        r'candy', r'candies', r'loll(?:y|ies)', r'gumm(?:y|ies)', r'haribo', r'mentos',
        r'chupa\s*chups', r"allen['\u2019]?s", r'skittles', r'starburst', r'mints?',
        r'liquorice', r'all\s*sorts', r'darrell\s*lea',
        r'pretzels?', r'muesli\s*bars?', r'protein\s*bars?', r'fibre\s*one', r'nature\s*valley',
        r'bliss\s*balls?', r'snack', r'jerky', r'biltong', r'fruit\s*snacks?', r'roll-ups?'
    ],

    # 6. Seafood (fish, prawns, salmon, tuna, calamari, squid, oysters, mussels)
    'seafood': [
        r'salmon', r'tuna', r'trout', r'barramundi', r'basa', r'cod', r'snapper',
        r'fish', r'prawns?', r'shrimps?', r'calamari', r'squid', r'octopus',
        r'oysters?(?!\s*blade)', r'mussels?', r'crabs?', r'lobster', r'seafood', r'just\s*caught'
    ],

    # 7. Meat & Poultry (beef, chicken, pork, lamb, mince, steak, deli, bacon, sausages)
    'meat': [
        r'beef', r'steak', r'rump', r'ribeye', r'scotch\s*fillet', r'sirloin', r'porterhouse',
        r'mince', r'meatballs?', r'beef\s*burgers?', r'burgers?(?!\s*(?:buns?|rolls?|sauce))',
        r'roast\s*beef', r'corned\s*beef', r'oyster\s*blade',
        r'chicken', r'drumsticks?', r'wings?', r'breast', r'thigh', r'tenderloins?',
        r'schnitzel', r'rspca\s*approved', r'whole\s*chicken', r'kiev',
        r'pork', r'pork\s*chops?', r'pork\s*belly', r'pork\s*roast', r'pork\s*ribs?',
        r'lamb', r'lamb\s*chops?', r'lamb\s*cutlets?', r'lamb\s*shanks?', r'lamb\s*leg',
        r'sausages?', r'chipolatas?', r'chorizo', r'bacon', r'ham', r'prosciutto',
        r'salami', r'deli\s*(?:meat|sliced|range)', r'mortadella', r'pancetta', r'frankfurts?', r'franks',
        r'twiggy\s*sticks?',
        r'hot\s*dogs?(?!\s*(?:rolls?|buns?))', r'footy\s*box', r'strasburg', r'd[\'’]orsogna',
        r'antipasto', r'grazing\s*platter', r'turkey', r'duck', r'meat', r'cutlets?'
    ],

    # 8. Fresh Produce (fresh fruits, vegetables, fresh herbs, fresh salads)
    'produce': [
        r'apples?', r'pink\s*lady', r'bananas?', r'oranges?', r'mandarins?', r'citrus',
        r'avocados?', r'tomatoes?', r'potatoes?', r'onions?', r'garlic', r'ginger',
        r'mushrooms?', r'strawberr(?:y|ies)', r'blueberr(?:y|ies)', r'raspberr(?:y|ies)',
        r'blackberr(?:y|ies)', r'berries', r'grapes?', r'lemons?', r'limes?',
        r'lettuces?', r'salads?', r'spinach', r'kale', r'carrots?', r'broccolis?',
        r'broccolini', r'wombok', r'cabbage', r'cauliflowers?', r'cucumbers?',
        r'capsicums?', r'peppers?', r'zucchinis?', r'pumpkins?', r'sweet\s*potatoes?',
        r'corn', r'watermelons?', r'rockmelons?', r'honeydew', r'pears?', r'mangos?',
        r'peaches?', r'nectarines?', r'plums?', r'cherries', r'kiwifruits?', r'papayas?',
        r'pineapples?', r'celery', r'asparagus', r'asian\s*veg', r'bok\s*choy',
        r'choy\s*sum', r'herbs?', r'coriander', r'parsley', r'basil', r'rosemary',
        r'thyme', r'chilli(?:es)?', r'fresh\s*produce'
    ],

    # 9. Dairy & Eggs (milk, butter, cheese, eggs, yogurt, cream, fresh dips)
    'dairy_eggs': [
        r'milk', r'dairy', r'almond\s*milk', r'oat\s*milk', r'soy\s*milk', r'lactose\s*free',
        r'eggs?', r'free\s*range\s*eggs?', r'caged\s*eggs?', r'egg\s*carton',
        r'butter', r'margarine', r'tablelands', r'western\s*star', r'nuttelex',
        r'cheeses?', r'cheddar', r'parmesan', r'mozzarella', r'feta', r'ricotta',
        r'brie', r'camembert', r'halloumi', r'paneer', r'kasseri', r'cream\s*cheese',
        r'philadelphia', r'bega\s*cheese', r'dairylea', r'cheese\s*slices?',
        r'fromager', r'd[\'’]affinois',
        r'yogurts?', r'yoghurts?', r'greek\s*yogurt', r'chobani', r'yoplait', r'danone',
        r'jalna', r'gourmet\s*yogurt', r'kefir',
        r'cream', r'sour\s*cream', r'thickened\s*cream', r'whipping\s*cream', r'custard',
        r'fresh\s*dips?', r'dips?', r'hummus', r'hommus', r'black\s*swan', r'obela',
        r'yumi[\'’]?s', r'tzatziki', r'guacamole'
    ],

    # 10. Bakery (bread, wraps, rolls, muffins, croissants, crumpets, fresh baked goods)
    'bakery': [
        r'garlic\s*(?:slices?|bread|baguette)', r'brioche\s*(?:milk\s*)?rolls?',
        r'bread', r'toast', r'wraps?', r'croissants?', r'bagels?', r'muffins?',
        r'crumpets?', r'rolls?', r'bread\s*rolls?', r'cheese\s*&\s*bacon\s*rolls?',
        r'loaf', r'loaves', r'buns?', r'brioche', r'pita', r'naan', r'sourdough',
        r'flatbread', r'baguettes?', r'pastr(?:y|ies)', r'pains?\s*au\s*chocolat', r'pains?\s*au',
        r'scones?', r'donuts?', r'doughnuts?', r'profiteroles?', r'puddings?',
        r'aunt\s*betty', r'cakes?', r'sponge\s*cake', r'banana\s*bread', r'bakery',
        r'tip\s*top', r"helga['\u2019]?s", r"abbott['\u2019]?s", r'wonder\s*white',
        r"baker['\u2019]?s\s*delight"
    ],

    # 11. Pantry & Staples (grains, pasta, rice, canned foods, cooking oils, sauces, breakfast, condiments)
    'pantry': [
        r'pesto', r'diced\s*tomatoes', r'canned\s*tomatoes', r'semi\s*dried\s*tomatoes', r'sundried\s*tomatoes',
        r'pasta', r'spaghetti', r'penne', r'fettuccine', r'macaroni', r'san\s*remo', r'barilla',
        r'rice', r'jasmine\s*rice', r'basmati\s*rice', r'brown\s*rice', r'sunrice', r'riviana',
        r'noodles?', r'ramen', r'instant\s*noodles?', r'indomie', r'maggi', r'suimin',
        r'sauces?', r'pasta\s*sauce', r'tomato\s*sauce', r'ketchup', r'masterfoods',
        r'heinz', r'barbeque\s*sauce', r'bbq\s*sauce', r'soy\s*sauce', r'oyster\s*sauce',
        r'fish\s*sauce', r'sweet\s*chilli', r'sriracha', r'curry\s*paste', r'curry\s*sauce',
        r'passata', r'dolmio', r'leggo', r'mingle',
        r'oils?', r'olive\s*oil', r'extra\s*virgin\s*olive\s*oil', r'canola\s*oil',
        r'vegetable\s*oil', r'sunflower\s*oil', r'cobram\s*estate', r'bertolli',
        r'soups?', r'continental', r"campbell['\u2019]?s",
        r'cereals?', r'weet-bix', r'weetbix', r'cornflakes', r'oats', r'porridge',
        r"carman['\u2019]?s", r'uncle\s*tobys', r"kellogg['\u2019]?s", r'muesli', r'milo',
        r'flour', r'sugar', r'salt', r'pepper', r'spices?', r'seasoning', r'herbs\s*&\s*spices',
        r'stock', r'bouillon', r'stock\s*powder', r'gravy', r'coconut\s*milk', r'coconut\s*cream',
        r'beans', r'baked\s*beans', r'lentils', r'chickpeas', r'canned\s*vegetables?',
        r'spreads?', r'vegemite', r'peanut\s*butter', r'bega\s*peanut\s*butter', r'nutella',
        r'jam', r'marmalade', r'honey', r'capilano', r'maple\s*syrup', r'pancake\s*mix',
        r'baking', r'yeast', r'vanilla', r'vinegar', r'balsamic', r'salad\s*dressing',
        r'mayonnaise', r'aioli', r'mustard', r'pickles?', r'olives?', r'prunes?'
    ]
}

def classify_product(title: str, raw_cat: str = "") -> str:
    """
    Classifies a product into one of the 11 standard Australian grocery categories:
    meat, seafood, produce, dairy_eggs, bakery, pantry, snacks, drinks, frozen, health_vitamins, household.
    """
    text = f"{title} {raw_cat}".lower().strip()

    # Priority order:
    priority_order = [
        'health_vitamins',
        'household',
        'frozen',
        'drinks',
        'snacks',
        'bakery',
        'seafood',
        'meat',
        'dairy_eggs',
        'produce',
        'pantry'
    ]

    for cat in priority_order:
        if cat == 'health_vitamins' and any(k in text for k in ['shampoo', 'conditioner', 'moisturis', 'moisturiz', 'spray', 'mask', 'cleanser', 'lotion']):
            continue
        if cat == 'produce':
            # Exclude non-fresh produce items matching vegetable names (sauces, pastes, canned, pesto, garlic bread, effervescent vitamins)
            if any(k in text for k in ['sauce', 'pesto', 'diced', 'canned', 'semi dried', 'sundried', 'effervescent', 'berocca', 'garlic slice', 'garlic bread', 'garlic baguette']):
                continue
        if cat == 'dairy_eggs':
            if any(k in text for k in ['mayonnaise', 'aioli']):
                continue
        if cat == 'snacks':
            if any(k in text for k in ['brioche', 'pain au', 'pastry', 'golden crunch chips']):
                continue
        patterns = CATEGORY_RULES[cat]
        for pat in patterns:
            if re.search(r'\b' + pat + r'\b', text, re.IGNORECASE):
                return cat

    # Step 2: Fallback based on raw category clues if present
    raw_lower = raw_cat.lower()
    if any(k in raw_lower for k in ['vitamin', 'supplement', 'health', 'medicine']):
        return 'health_vitamins'
    if any(k in raw_lower for k in ['seafood', 'fish', 'prawn', 'salmon']):
        return 'seafood'
    if any(k in raw_lower for k in ['meat', 'poultry', 'beef', 'chicken', 'pork', 'lamb', 'deli']):
        return 'meat'
    if any(k in raw_lower for k in ['fruit', 'veg', 'produce', 'salad']):
        return 'produce'
    if any(k in raw_lower for k in ['dairy', 'egg', 'cheese', 'milk', 'yogurt', 'dip']):
        return 'dairy_eggs'
    if any(k in raw_lower for k in ['bakery', 'bread', 'pastry']):
        return 'bakery'
    if any(k in raw_lower for k in ['drink', 'beverage', 'tea', 'coffee', 'juice']):
        return 'drinks'
    if any(k in raw_lower for k in ['frozen', 'ice cream', 'ice-cream']):
        return 'frozen'
    if any(k in raw_lower for k in ['snack', 'confectionery', 'chip', 'chocolate', 'biscuit']):
        return 'snacks'
    if any(k in raw_lower for k in ['household', 'clean', 'toilet', 'personal', 'baby', 'pet']):
        return 'household'

    return 'pantry'
