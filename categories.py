import re
import json

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

INTERNAL_CATEGORY_KEYS = {
    'all', 'produce', 'meat', 'seafood', 'dairy_eggs', 'bakery',
    'pantry', 'snacks', 'drinks', 'frozen', 'health_vitamins', 'household', 'groceries'
}

HOUSEHOLD_BRANDS = [
    r"l'or[eé]al", r"nivea", r"neutrogena", r"olay", r"mixa", r"sukin", r"garnier",
    r"mcobeauty", r"essano", r"vaseline", r"dove", r"palmolive", r"schwarzkopf",
    r"tresemm[eé]", r"pantene", r"head\s*&\s*shoulders", r"herbal\s*essences",
    r"mitchum", r"rexona", r"brut", r"colgate", r"oral[- ]b", r"sensodyne",
    r"white\s*glo", r"gillette", r"schick", r"dettol", r"\bbref\b", r"harpic",
    r"\bfinish\b", r"\bfairy\b", r"morning\s*fresh", r"omo\b", r"cold\s*power", r"radiant",
    r"dynamo", r"comfort", r"\bvanish\b", r"pine\s*o\s*cleen", r"glen\s*20", r"\bajax\b",
    r"\bchux\b", r"vileda", r"quilton", r"kleenex", r"sorbent", r"viva\b", r"huggies",
    r"babylove", r"little\s*one['\u2019]?s", r"curash", r"libra\b", r"tom\s*organic",
    r"carefree", r"stayfree", r"kotex", r"dine\b", r"whiskas", r"fancy\s*feast",
    r"purina", r"supercoat", r"fussy\s*cat", r"pedigree", r"schmackos", r"temptations",
    r"open\s*paddock", r"ultimates\b", r"my\s*dog", r"nature['\u2019]?s\s*gift",
    r"energizer", r"eveready", r"duracell", r"brunnings", r"aerogard", r"raid\b",
    r"mortein", r"easy-off", r"armor\s*all", r"air\s*wick", r"ambipur", r"febreze",
    r"\bglade\b", r"biozet", r"pears\b"
]

def classify_product(title: str, raw_cat: str = "", product_url: str = "") -> str:
    """
    Classifies a product into one of the 11 standard Australian grocery categories:
    produce, meat, seafood, dairy_eggs, bakery, pantry, snacks, drinks, frozen, health_vitamins, household.
    """
    title_l = title.lower().strip()
    url_l = product_url.lower().strip()
    raw_l = raw_cat.lower().strip()
    if raw_l in INTERNAL_CATEGORY_KEYS:
        raw_l = ""

    # Cadbury chocolate collaboration exception (e.g. Cadbury x MCoBeauty chocolate block)
    if 'cadbury' in title_l or 'chocolate block' in title_l:
        return 'snacks'

    # -------------------------------------------------------------
    # 1. HOUSEHOLD BRANDS (100% Household / Personal Care / Pets)
    # -------------------------------------------------------------
    for b in HOUSEHOLD_BRANDS:
        if re.search(b, title_l):
            return 'household'

    # Household general patterns
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:soap|soap\s*bar|handwash|hand\s*wash|body\s*wash|body\s*scrub|exfoliating|shower\s*gel|body\s*lotion|body\s*milk)\b',
        r'\b(?:day\s*cream|night\s*cream|eye\s*cream|face\s*cream|facial|cleanser|micellar|toner|serum)\b',
        r'\b(?:sunscreen|banana\s*boat|cancer\s*council|lip\s*balm|chapstick|lip\s*gloss|lipstick|mascara|beauty)\b',
        r'\bspf\s*\d+',
        r'\b(?:shampoo|conditioner|hair\s*colour|hair\s*dye|hair\s*spray|hair\s*mask)\b',
        r'\b(?:deodorant|antiperspirant|roll\s*on|toothpaste|toothbrush|mouthwash|dental\s*floss|razor|shaving)\b',
        r'\b(?:tampons?|pads\s*with\s*wings|incontinence|liners?|nappies|nappy|diapers?|baby\s*wipes?)\b',
        r'\b(?:toilet\s*paper|facial\s*tissue|paper\s*towel|dishwashing|dishwasher|laundry|detergent|fabric\s*softener)\b',
        r'\b(?:bin\s*liners?|garbage\s*bags?|cleaner|disinfectant|bleach)\b',
        r'\b(?:baking\s*paper|foil|cling\s*wrap|albal|multix|glad\s*wrap)\b',
        r'\b(?:weed\s*kill|weedkiller|roundup|pest\s*control|insect\s*spray|batteries|battery)\b',
        r'\b(?:cat\s*food|dog\s*food|cat\s*treats?|dog\s*treats?|pet\s*food)\b'
    ]):
        return 'household'

    # -------------------------------------------------------------
    # 2. SOUP (Pantry) - Check before Meat! (Prevents chicken soup -> meat)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:soup|cup\s*a\s*soup|continental\s*classics)\b'
    ]):
        return 'pantry'

    # -------------------------------------------------------------
    # 3. FROZEN FOOD (Ice Cream, Gelato, Frozen Desserts, Frozen Meals, Frozen Chips/Pies/Veg)
    # Check before Snacks & Pantry so "From the Freezer", "Frozen dessert", "Ice cream", "Frozen chips" -> frozen
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:ice\s*cream|gelato|sorbet|magnum|connoisseur|ben\s*&\s*jerry|peters|bulla|cornetto|paddle\s*pop|weis\s*bars?|ice\s*bars?|crunch\s*pops)\b',
        r'\b(?:frozen\s*dessert|frozen\s*yogurt|frozen\s*yoghurt|yo-chi)\b',
        r'\b(?:party\s*pies|meat\s*pies|four\'n\s*twenty|pastizzis?|party\s*pack)\b',
        r'\b(?:from the freezer|freezer)\b',
        r'\b(?:hash\s*browns?|potato\s*gems|wedges|shoestring\s*chips|steakhouse.*chips|french\s*fries)\b',
        r'\b(?:dumplings?|gyoza|samosas?|spring\s*rolls?|dim\s*sims?)\b',
        r'\b(?:frozen\s*(?:meals?|pizza|chips|peas|berries|vegetables?|fruit|veg|pastry|churros|pancakes?))\b',
        r'\b(?:dr\s*oetker|ristorante|mccain|birds\s*eye|superfries|fropro|della\s*rosa)\b',
        r'\b(?:pizza|pizzas|dino\s*nuggets?)\b'
    ]):
        if not any(k in title_l for k in ['pizza base', 'pizza shapes', 'pizza roll', 'pizza sauce', 'shapes', 'bakery fridge', 'from the bakery']):
            # Don't steal seafood if it contains clear fish/prawn/calamari/salmon
            if not any(re.search(s_pat, title_l) for s_pat in [
                r'\b(?:salmon|tuna|trout|barramundi|basa|cod|snapper|prawns?|shrimps?|calamari|squid|octopus|mussels?|crabs?|lobster|seafood)\b',
                r'\bfish\b'
            ]):
                if not any(k in title_l for k in ['dog food', 'cat food', 'pet food']):
                    return 'frozen'

    # -------------------------------------------------------------
    # 4. SNACKS & CONFECTIONERY - Check before Meat!
    # Prevents "chicken crimpy biscuits", "bacon shapes", "burger rings", "red rock deli chips" -> meat
    # -------------------------------------------------------------
    if not any(k in title_l for k in ['crumbed chicken', 'chicken chips 1kg', 'chicken tenders', 'mud cake', 'mudcake', 'cake slice', 'sponge cake']):
        if any(re.search(pat, title_l) for pat in [
            r'\b(?:red\s*rock\s*deli|doritos|smith\'s|smiths|cheezels|twisties|pringles|kettle|popcorn)\b',
            r'\b(?:chips?|crisps?|puffs|onion\s*rings|burger\s*rings|cheetos)\b',
            r'\b(?:chocolate|pralines?|toblerone|cadbury|lindt|kit\s*kat|kitkat|m&m|maltesers|mars|snickers|twix|kinder|pods|darrell\s*lea|bullets)\b',
            r'\b(?:biscuits?|cookies?|tim\s*tams?|crackers?|ritz|oreo|arnott\'s|arnotts|shapes|belvita|digestives|koala\'s\s*march|lotte)\b',
            r'\b(?:lollies|lolly|candy|gummies|haribo|mentos|chupa\s*chups|allen\'s|skittles|pretzels?|sour\s*patch|jelly|jellies|konjac|confectionery)\b',
            r'\b(?:nuts?|peanuts?|almonds?|cashews?|walnuts?|macadamias?|nut\s*bars?|muesli\s*bars?|protein\s*bars?|oaty\s*slices?|harvest\s*snaps|rocklea\s*road)\b',
            r'\b(?:temole|nongshim)\b'
        ]):
            return 'snacks'

    # -------------------------------------------------------------
    # 5. DRINKS (Water, Soft Drinks, Tea, Coffee, Sports Drinks, Juice, Alcohol)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'-196\b|\b(?:hard\s*rated|alcoholic|nomikai)\b',
        r'\b(?:sparkling|mineral\s*water|spring\s*water|soda\s*water|tonic\s*water|water\s*bottle)\b',
        r'\b(?:mount\s*franklin|pump\s*water|san\s*pellegrino|perrier)\b',
        r'\b(?:soft\s*drink|carbonated|coca[- ]cola|coke|pepsi|sprite|fanta|schweppes|solo|kirks)\b',
        r'\b(?:gatorade|powerade|sports?\s*drink|energy\s*drink|red\s*bull|monster\s*energy|v\s*energy|ghost\s*energy)\b',
        r'\b(?:kombucha|cordial|cocobella|coconut\s*water|poppers?\b|fruit\s*drink|juice|nudie|daily\s*juice)\b',
        r'\b(?:tea|tea\s*bags?|twinings|dilmah|lipton|tetley|coffee|espresso|moccona|nescafe|lavazza|vittoria)\b',
        r'\b(?:beer|wine|cider|lager|ale|bourbon|whisky|vodka|gin|rum)\b',
        r'\b(?:up&go|up\s*&\s*go|ready\s*to\s*drink|protein\s*water)\b'
    ]):
        if not any(k in title_l for k in ['biscuit', 'cookie', 'cracker', 'chips', 'chocolate block', 'ice cream']):
            return 'drinks'

    # -------------------------------------------------------------
    # 6. HEALTH & VITAMINS (Vitamins, Supplements, Pain Relief, Protein Powder)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:berocca|cenovis|voost|swisse|blackmores|nature\'s\s*(?:way|own)|bioglan|hydralyte)\b',
        r'\b(?:panadol|nurofen|paracetamol)\b',
        r'\b(?:multivitamins?|multi-vitamins?|vitamin\s*[a-z0-9]+)\b',
        r'\b(?:fish\s*oil|krill\s*oil|magnesium|caltrate|centrum|iron\s*tablets?|zinc|calcium|biotin|melatonin)\b',
        r'\b(?:protein\s*powder|whey\s*protein|creatine|collagen\s*powder|effervescent\s*tablets?|metamucil)\b'
    ]):
        return 'health_vitamins'

    # -------------------------------------------------------------
    # 7. SEAFOOD (Fresh, Canned, Frozen Fish, Prawns, Salmon, Tuna)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:salmon|tuna|trout|barramundi|basa|cod|snapper|prawns?|shrimps?|calamari|squid|octopus|mussels?|crabs?|lobster|seafood)\b',
        r'\boysters?(?!\s*blade)\b',
        r'\bfish\b'
    ]):
        if not any(k in title_l for k in ['cat food', 'dog food', 'cat treat', 'dog treat', 'dine']):
            return 'seafood'

    # -------------------------------------------------------------
    # 8. MEAT & DELI (Beef, Pork, Lamb, Chicken, Sausages, Ham, Bacon, Salami)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:beef|steak|rump|ribeye|sirloin|porterhouse|mince|meatballs?|burgers?|oyster\s*blade)\b',
        r'\b(?:chicken|drumsticks?|wings?|breast|thigh|tenderloins?|schnitzel)\b',
        r'\b(?:pork|pork\s*chops?|pork\s*belly|lamb|lamb\s*chops?|lamb\s*cutlets?|lamb\s*shanks?)\b',
        r'\b(?:sausages?|chipolatas?|chorizo|bacon|ham|prosciutto|salami|sopressa|frankfurts?|twiggy\s*sticks?)\b',
        r'\b(?:from the deli|deli\s*(?:meat|counter|service|range|sliced|shaved))\b',
        r'\b(?:grazing\s*platter|snackers\s*delight|symphony\s*platter|artisan\s*grazing|luv-a-duck|luv\s*a\s*duck|duck\s*breast|duck\s*leg|whole\s*duck)\b'
    ]):
        return 'meat'

    # -------------------------------------------------------------
    # 9. BAKERY (Bread, Rolls, Wraps, Croissants, Cakes, Cake Mixes)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\bgarlic\s*(?:slices?|bread|baguette|toast)\b',
        r'\b(?:bread|toast|wraps?|croissants?|bagels?|muffins?|crumpets?|rolls?|loaf|loaves|buns?|brioche|pita|naan|sourdough|flatbread|baguettes?)\b',
        r'\b(?:pastr(?:y|ies)|scones?|donuts?|doughnuts?|profiteroles?|puddings?|cupcakes?|mud\s*cakes?|mudcakes?|cheesecakes?|cake\s*mix|cheesecake\s*mix|from the bakery)\b'
    ]):
        return 'bakery'

    # -------------------------------------------------------------
    # 10. DAIRY & EGGS (Milk, Butter, Cheese, Yogurt, Dips, Eggs)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:milk|eggs?|butter|margarine|cheeses?|cheddar|parmesan|mozzarella|feta|ricotta|brie|camembert|halloumi|haloumi|paneer)\b',
        r'\b(?:yogurts?|yoghurts?|chobani|custard|sour\s*cream|thickened\s*cream|whipping\s*cream|cream\s*cheese|hommus|hummus|dips?|falafel)\b'
    ]):
        return 'dairy_eggs'

    # -------------------------------------------------------------
    # 11. FRESH PRODUCE (Raw Fresh Fruit, Fresh Veg, Salads, Herbs)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:apples?|bananas?|oranges?|mandarins?|avocados?|tomatoes?|potatoes?|onions?|garlic|ginger|mushrooms?|beetroot)\b',
        r'\b(?:strawberr(?:y|ies)|blueberr(?:y|ies)|raspberr(?:y|ies)|grapes?|lemons?|limes?|berries)\b',
        r'\b(?:lettuces?|salad\s*kit|slaw\s*kit|spinach|kale|carrots?|broccolis?|broccolini|cabbage|wombok|cauliflowers?|cucumbers?|capsicums?|zucchinis?|pumpkins?|sweet\s*potatoes?|watermelon|rockmelon|pears?|mangos?|peaches?|nectarines?|plums?|cherries|kiwifruits?|celery|asparagus|corn)\b',
        r'\b(?:herbs?|coriander|parsley|basil|mint|rosemary|thyme|chillies?|chili|chilis)\b'
    ]):
        if not any(w in title_l for w in [
            'sauce', 'canned', 'polpa', 'diced', 'paste', 'soup', 'chips', 'crisps', 'drink',
            'juice', 'sparkling', 'water', 'soap', 'scrub', 'handwash', 'body wash', 'face wash', 'puffs', 'rings',
            'biscuit', 'biscuits', 'cookie', 'cookies', 'crackers', 'mix', 'lollies', 'candy',
            'jelly', 'jellies', 'confectionery',
            'beans', 'quinoa', 'chia', 'sopressa', 'salami', 'pastizzis', 'lip balm', 'sunscreen',
            'garlic slices', 'garlic bread', 'pesto', 'semi dried', 'sun dried', 'pickled', 'always fresh', 'dips?'
        ]):
            return 'produce'

    # -------------------------------------------------------------
    # 12. PANTRY (Grains, Pasta, Rice, Canned, Sauces, Spices, Oils)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\balways\s*fresh\b',
        r'\b(?:pasta|spaghetti|penne|noodles?|ramen|rice|jasmine\s*rice|basmati)\b',
        r'\b(?:sauces?|pasta\s*sauce|tomato\s*sauce|curry\s*paste|mayo|mayonnaise|mustard)\b',
        r'\b(?:oils?|olive\s*oil|canola\s*oil|vegetable\s*oil)\b',
        r'\b(?:canned|polpa|peeled\s*tomatoes|semi\s*dried|beans|quinoa|chia\s*seeds|lentils|chickpeas)\b',
        r'\b(?:cereals?|weet-bix|cornflakes|oats|porridge|muesli|milo|flour|sugar|salt|pepper|honey|jam|spreads?|vegemite|peanut\s*butter)\b'
    ]):
        return 'pantry'

    # Fallback department hints
    if any(k in raw_l or ('/' + k + '/') in url_l for k in ['cleaning & maintenance', 'cleaning goods', 'household-cleaning', 'papergoods', 'beauty', 'pet care', 'pet food']):
        return 'household'
    if 'baby-care' in raw_l or '/baby-care/' in url_l or '/baby/' in url_l or 'baby-formula' in raw_l:
        return 'household'
    if any(k in raw_l or k in url_l for k in ['drinks', 'soft drinks', 'tea & coffee', 'tea and coffee', 'carbonated soft drinks', 'beverages']):
        return 'drinks'
    if any(k in raw_l or k in url_l for k in ['snacks & confectionery', 'confectionery', 'biscuits & crackers', 'biscuits-and-snacks', 'chips']):
        return 'snacks'
    if any(k in raw_l or k in url_l for k in ['health & wellness', 'health-and-wellbeing']):
        return 'health_vitamins'
    if any(k in raw_l or k in url_l for k in ['packaged bread & bakery', 'proprietary bakery', 'bakery']):
        return 'bakery'
    if any(k in raw_l or k in url_l for k in ['freezer', 'frozen meals', 'frozen pies']):
        return 'frozen'
    if any(k in raw_l or k in url_l for k in ['fruit & veg', 'fruit-and-vegetables', 'produce']):
        return 'produce'
    if any(k in raw_l or k in url_l for k in ['poultry, meat & seafood', 'meat', 'deli meats', 'deli service']):
        return 'meat'
    if any(k in raw_l or k in url_l for k in ['dairy, eggs & fridge', 'dairy - yoghurt', 'dairy']):
        return 'dairy_eggs'

    return 'pantry'
