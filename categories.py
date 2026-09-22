# -*- coding: utf-8 -*-
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
    'frozen',
    'pantry',
    'snacks',
    'drinks',
    'health_vitamins',
    'household',
    'pet',
    'other'
]

INTERNAL_CATEGORY_KEYS = set(CATEGORIES) | {'groceries'}

def classify_product(title: str, raw_cat: str = "", product_url: str = "") -> str:
    """
    Classifies an Australian supermarket product into one of the standard categories:
    produce, meat, seafood, dairy_eggs, bakery, frozen, pantry, snacks, drinks, health_vitamins, household, pet, other.
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
    # 1. PET CARE & FOOD (寵物專區)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:cat\s*food|dog\s*food|pet\s*food|cat\s*treats?|dog\s*treats?|cat\s*litter)\b',
        r'\b(?:whiskas|pedigree|schmackos|purina|supercoat|fancy\s*feast|fussy\s*cat|dine\b|temptations|open\s*paddock|nature[\'’]?s\s*gift|my\s*dog|optimum\s*dog|optimum\s*cat|vip\s*petfoods|hartz)\b'
    ]):
        return 'pet'

    # -------------------------------------------------------------
    # 2. OTHER SPECIALS (其他專區: 電池、殺蟲除草、五金園藝、雜項)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:energizer|eveready|duracell|batteries|battery)\b',
        r'\b(?:mortein|raid\b|aerogard|insect\s*spray|pest\s*control|fly\s*spray)\b',
        r'\b(?:brunnings|roundup|weed\s*kill|weedkiller|fertiliser|fertilizer|potting\s*mix)\b',
        r'\b(?:armor\s*all|car\s*wash)\b'
    ]):
        return 'other'

    # -------------------------------------------------------------
    # 3. FROZEN FOOD (冷凍食品: 冰淇淋、冷凍點心、薯條、冷凍微波餐)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:ice\s*cream|gelato|sorbet|magnum|connoisseur|ben\s*&\s*jerry|peters|bulla|cornetto|paddle\s*pop|weis\s*bars?|crunch\s*pops)\b',
        r'\b(?:frozen|freezer|from the freezer)\b',
        r'\b(?:hash\s*browns?|potato\s*gems|wedges|shoestring\s*chips|steakhouse.*chips|french\s*fries)\b',
        r'\b(?:dumplings?|gyoza|samosas?|spring\s*rolls?|dim\s*sims?)\b'
    ]):
        if not any(k in title_l for k in ['chocolate block', 'biscuit']):
            return 'frozen'

    # -------------------------------------------------------------
    # 4. DRINKS (飲料沖調: 咖啡、茶、汽水、果汁、水、能量飲)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:coffee|coffee\s*beans|coffee\s*pods|nespresso|lavazza|moccona|nescafe|starbucks|vittoria|grinders)\b',
        r'\b(?:tea|tea\s*bags|twinings|lipton|dilmah|tetley)\b',
        r'\b(?:coca-cola|coke|pepsi|sprite|fanta|kirks|schweppes|bundle\s*drink)\b',
        r'\b(?:juice|fruit\s*drink|daily\s*juice|nudie|golden\s*circle)\b',
        r'\b(?:water|spring\s*water|sparkling\s*water|mount\s*franklin|pump\s*water)\b',
        r'\b(?:energy\s*drink|red\s*bull|monster\s*energy|v\s*energy|mother\s*energy|gatorade|powerade)\b',
        r'\b(?:kombucha|cordial)\b'
    ]):
        if not any(k in title_l for k in ['coffee cake', 'tea towel', 'shampoo', 'body wash', 'biscuit', 'chocolate block', 'ice cream']):
            return 'drinks'

    # -------------------------------------------------------------
    # 5. HEALTH & BEAUTY (保健美妝: 維他命、護膚洗沐、牙膏、防曬、衛生棉)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:vitamins?|supplements?|blackmores|swisse|nature[\'’]?s\s*own|cenovis|ostelin|bioglan|berocca)\b',
        r'\b(?:shampoo|conditioner|hair\s*treatment|hair\s*oil|hair\s*colour|hair\s*dye|hair\s*spray|hair\s*mask)\b',
        r'\b(?:pantene|head\s*&\s*shoulders|herbal\s*essences|tresemm[eé]|schwarzkopf|l\'or[eé]al|garnier|ogx|sukin|mixa|essano)\b',
        r'\b(?:body\s*wash|shower\s*gel|soap\s*bar|hand\s*wash|hand\s*sanitiser|palmolive|dove|lux\b|pears\b|vaseline)\b',
        r'\b(?:skincare|moisturiser|moisturizer|serum|facial|cleanser|micellar|eye\s*cream|face\s*mask|face\s*cream|olay|nivea|neutrogena)\b',
        r'\b(?:sunscreen|banana\s*boat|cancer\s*council|bondi\s*sands|dermaveen|spf\s*\d+)\b',
        r'\b(?:deodorant|antiperspirant|roll\s*on|body\s*spray|rexona|mitchum|lynx\b|brut\b|nivea\s*men)\b',
        r'\b(?:toothpaste|toothbrush|mouthwash|dental|colgate|oral[- ]b|sensodyne|white\s*glo)\b',
        r'\b(?:razor|shaving|gillette|schick|bic\b)\b',
        r'\b(?:tampons?|pads\s*with\s*wings|incontinence|liners?|u\s*by\s*kotex|libra|tom\s*organic|carefree|stayfree)\b',
        r'\b(?:nappies|nappy|babylove|huggies|baby\s*wipes|curash|little\s*one[\'’]?s)\b',
        r'\b(?:lip\s*balm|cosmetics?|mascara|lipstick|mcobeauty|maybelline)\b'
    ]):
        return 'health_vitamins'

    # -------------------------------------------------------------
    # 6. HOUSEHOLD (日用清潔: 洗衣精、洗碗錠、衛生紙、清潔劑、垃圾袋、保鮮膜)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:laundry|detergent|washing\s*powder|fabric\s*softener|omo\b|cold\s*power|dynamo|radiant|comfort|fluffy|biozet|earthwise|cuddly)\b',
        r'\b(?:dishwashing|dishwasher|finish\b|fairy\b|morning\s*fresh)\b',
        r'\b(?:toilet\s*paper|facial\s*tissues?|paper\s*towels?|quilton|kleenex|sorbent|viva\b)\b',
        r'\b(?:cleaner|disinfectant|bleach|pine\s*o\s*cleen|dettol|glen\s*20|ajax|harpic|bref|easy-off|chux|vileda)\b',
        r'\b(?:garbage\s*bags?|bin\s*liners?|multix|glad|albal|baking\s*paper|foil|cling\s*wrap)\b',
        r'\b(?:air\s*wick|ambipur|febreze|glade)\b'
    ]):
        return 'household'

    # -------------------------------------------------------------
    # 7. SEAFOOD (水產海鮮)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:salmon|prawns?|shrimp|calamari|squid|octopus|tuna\s*fillet|tuna\s*steak|barramundi|snapper|flathead|basa|fish\s*fillets?|mussels|oysters?|lobster|crab)\b'
    ]):
        if not any(k in title_l for k in ['canned', 'can ', 'tin ', 'cat food', 'dog food', 'oyster blade', 'oyster sauce']):
            return 'seafood'

    # -------------------------------------------------------------
    # 8. MEAT & POULTRY (生鮮肉品)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:beef|pork|lamb|chicken|steak|mince|sausages?|roast|chops?|cutlets?|veal|bacon|ham|prosciutto|salami|meatballs?|chicken\s*breast|chicken\s*thigh|drumsticks?|tenderloins?)\b'
    ]):
        if not any(k in title_l for k in ['soup', 'cat food', 'dog food', 'chips', 'flavoured', 'noodle', 'sauce', 'stock', 'pie', 'pizza', 'cracker', 'crisps']):
            return 'meat'

    # -------------------------------------------------------------
    # 9. FRESH PRODUCE (生鮮蔬果)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:apples?|bananas?|oranges?|mandarins?|grapes?|strawberries|blueberries|raspberries|avocados?|lemons?|limes?|mangoes?|peaches|plums|pears?)\b',
        r'\b(?:potatoes?|sweet\s*potatoes?|carrots?|onions?|broccoli|cauliflower|lettuce|salad|cabbage|zucchini|mushrooms?|capsicums?|cucumbers?|spinach|tomatoes?)\b'
    ]):
        if any(k in title_l for k in ['fresh', 'per kg', 'kg', 'punnet', 'bunch', 'bag', 'pack', 'truss']) and not any(k in title_l for k in ['chips', 'canned', 'sauce', 'paste', 'frozen', 'juice', 'soup', 'lotion', 'shampoo']):
            return 'produce'

    # -------------------------------------------------------------
    # 10. BAKERY (烘焙麵包)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:bread|toast|loaf|sourdough|buns?|rolls?|bagels?|croissants?|crumpets?|muffins?|scones?|wraps?|pita|flatbread|tortillas?|tip\s*top|helga|abbott|wonder\s*white)\b'
    ]):
        if not any(k in title_l for k in ['baking paper', 'baking powder', 'dog', 'cat']):
            return 'bakery'

    # -------------------------------------------------------------
    # 11. DAIRY & EGGS (乳品蛋類)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:milk|fresh\s*milk|almond\s*milk|oat\s*milk|soy\s*milk)\b',
        r'\b(?:eggs?|free\s*range\s*eggs?)\b',
        r'\b(?:butter|margarine|western\s*star|lurpak|nuttelex)\b',
        r'\b(?:cheese|cheddar|mozzarella|parmesan|feta|brie|camembert|cream\s*cheese|ricotta|bega\s*cheese|tasty\s*cheese)\b',
        r'\b(?:yogurt|yoghurt|chobani|goplain|jalna|gippsland|danone|yoplait)\b',
        r'\b(?:cream|sour\s*cream|custard)\b'
    ]):
        if not any(k in title_l for k in ['chocolate', 'biscuit', 'chips', 'shampoo', 'body wash', 'coconut milk', 'canned', 'condensed milk']):
            return 'dairy_eggs'

    # -------------------------------------------------------------
    # 12. SNACKS & CONFECTIONERY (休閒零食)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:chocolate|cadbury|lindt|kit\s*kat|m&m|maltesers|mars|snickers|twix|kinder|toblerone|ferrero)\b',
        r'\b(?:chips|crisps|doritos|smith[\'’]?s|red\s*rock\s*deli|kettle|pringles|thins|cheezels|twisties|grainwaves|sunbites)\b',
        r'\b(?:biscuits?|cookies?|tim\s*tam|arnott[\'’]?s|oreo|shapes|ritz|cruskit|water\s*crackers?)\b',
        r'\b(?:lollies|gummies|candy|mints|mentos|allens?|skittles|chupa\s*chups|gum)\b',
        r'\b(?:nuts?|peanuts?|almonds?|cashews?|pistachios?|popcorn)\b'
    ]):
        if not any(k in title_l for k in ['frozen', 'ice cream', 'shampoo', 'body wash']):
            return 'snacks'

    # -------------------------------------------------------------
    # 13. PANTRY (米麵調味 & 糧油罐頭)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:sauce|pasta|spaghetti|rice|noodles?|oil|olive\s*oil|canned|tin|beans?|spread|jam|cereal|oats|honey|mayonnaise|mustard|tuna\s*\d+g)\b'
    ]):
        return 'pantry'

    # 14. Fallback checking
    if 'soup' in title_l:
        return 'pantry'

    # Default fallback to pantry for foods, or other
    return 'pantry'
