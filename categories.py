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
    # 2. DRINKS & LIQUOR (飲料酒水: 啤酒、紅白酒、調酒烈酒、咖啡、茶、汽水、果汁、能量飲)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        # Alcoholic beverages (Beer, Wine, Cider, Spirits, RTDs, Seltzers)
        r'\b(?:beer|lager|ale\b|pale\s*ale|hazy\s*pale|ipa\b|xpa\b|draught|stout|cider|seltzer|vodka|whisky|whiskey|gin\b|rum\b|bourbon|tequila|wine|shiraz|sauvignon|chardonnay|pinot|prosecco|champagne|liqueur|brandy|scotch|mid\s*strength|alcoholic|cask\b|tempranillo|merlot|semillon|riesling|cabernet|sauv\s*blanc)\b',
        r'(?:-196|\b196\b)',
        r'\b(?:hard\s*rated|vodka\s*cruiser|smirnoff|heineken|corona|peroni|carlton|great\s*northern|coopers|asahi|guinness|stella\s*artois|somersby|balter|smithy[\'’]?s|4\s*pines|bentspoke|stone\s*&\s*wood|lorry\s*boys|james\s*squire|canadian\s*club|jack\s*daniel|jim\s*beam|woodstock|wild\s*turkey|xxxx|de\s*bortoli|story\s*bay|bundaberg\s*rum|gordon[\'’]?s|tanqueray|baileys|kahlua|aperol|campari|jameson|moretti)\b',
        # Non-alcoholic drinks & beverages
        r'\b(?:coffee|coffee\s*beans|coffee\s*pods|nespresso|lavazza|moccona|nescafe|starbucks|vittoria|grinders)\b',
        r'\b(?:tea|tea\s*bags|twinings|lipton|dilmah|tetley)\b',
        r'\b(?:coca-cola|coke|pepsi|sprite|fanta|kirks|schweppes|bundle\s*drink|soft\s*drink|sodaly|tonic\s*water|mineral\s*water)\b',
        r'\b(?:juice|fruit\s*drink|daily\s*juice|nudie|golden\s*circle|cocobella)\b',
        r'\b(?:water|spring\s*water|sparkling\s*water|mount\s*franklin|pump\s*water)\b',
        r'\b(?:energy\s*drink|red\s*bull|monster\s*energy|v\s*energy|mother\s*energy|ghost\s*energy|gatorade|powerade|up&go|up\s*&\s*go|rokeby.*smoothie|ready\s*to\s*drink\s*protein)\b',
        r'\b(?:kombucha|cordial|bundaberg\s*brewed)\b'
    ]):
        if not any(k in title_l for k in ['coffee cake', 'tea towel', 'shampoo', 'body wash', 'biscuit', 'chocolate block', 'ice cream', 'beef', 'chicken', 'lamb', 'frother', 'maker', 'press', 'sauce']):
            return 'drinks'

    # -------------------------------------------------------------
    # 3. FROZEN FOOD (冷凍食品: 冰淇淋、冷凍肉品點心、薯條、冷凍微波餐、披薩、派)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:ice\s*cream|gelato|sorbet|magnum|connoisseur|ben\s*&\s*jerry|peters|bulla|cornetto|paddle\s*pop|weis\s*bars?|crunch\s*pops|mixed\s*pack\s*pops|proud\s*&\s*punch)\b',
        r'\b(?:frozen|freezer|from the freezer)\b',
        r'\b(?:hash\s*browns?|potato\s*gems|wedges|shoestring\s*chips|steakhouse.*chips|french\s*fries)\b',
        r'\b(?:dumplings?|gyoza|samosas?|spring\s*rolls?|dim\s*sims?|churros)\b',
        r'\b(?:birds\s*eye|fish\s*fingers|fish\s*bites|four[\'’]?n\s*twenty|patties\s*party|herbert\s*adams|meat\s*pies?|beef\s*pies?|dr\s*oetker|ristorante|pizza\s*395g|pizza\s*310g)\b'
    ]):
        if not any(k in title_l for k in ['chocolate block', 'biscuit', 'pizza base', 'pizza sauce']):
            return 'frozen'

    # -------------------------------------------------------------
    # 4. FRESH PRODUCE (生鮮蔬果)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:apples?|bananas?|oranges?|mandarins?|grapes?|strawberries|blueberries|raspberries|avocados?|lemons?|limes?|mangoes?|peaches|plums|pears?|pineapple|kiwifruit|wombok)\b',
        r'\b(?:potatoes?|sweet\s*potatoes?|carrots?|onions?|broccoli|cauliflower|lettuce|salad|cabbage|zucchini|mushrooms?|capsicums?|cucumbers?|spinach|tomatoes?|slaw\s*kit)\b'
    ]):
        if not any(k in title_l for k in ['chips', 'canned', 'sauce', 'paste', 'frozen', 'juice', 'soup', 'lotion', 'shampoo', 'pickle']):
            return 'produce'

    # -------------------------------------------------------------
    # 5. SEAFOOD (水產海鮮)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:salmon|prawns?|shrimp|calamari|squid|octopus|tuna\s*fillet|tuna\s*steak|barramundi|snapper|flathead|basa|fish\s*fillets?|mussels|oysters?|lobster|crab|just\s*caught|ocean\s*royale)\b'
    ]):
        if not any(k in title_l for k in ['canned', 'can ', 'tin ', 'cat food', 'dog food', 'oyster blade', 'oyster sauce', 'tuna 6', 'tuna 95g', 'tuna 185g', 'tuna 425g']):
            return 'seafood'

    # -------------------------------------------------------------
    # 6. MEAT & POULTRY (生鮮肉品 & 熟食肉品)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:beef|pork|lamb|chicken|steak|mince|sausages?|roast|chops?|cutlets?|veal|bacon|ham|prosciutto|salami|meatballs?|chicken\s*breast|chicken\s*thigh|drumsticks?|tenderloins?)\b',
        r'\b(?:frankfurts?|franks\b|chorizo|burgers?|twiggy\s*sticks?|d[\'’]orsogna|don\b.*from\s*the\s*deli|don\s*footy|primo.*hot\s*dog|tegel)\b'
    ]):
        if not any(k in title_l for k in ['soup', 'cat food', 'dog food', 'chips', 'flavoured', 'noodle', 'sauce', 'stock', 'pie', 'pizza', 'cracker', 'crisps', 'pies']):
            return 'meat'

    # -------------------------------------------------------------
    # 7. DAIRY & EGGS (乳品蛋類 & 起司優格抹醬)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:milk|fresh\s*milk|almond\s*milk|oat\s*milk|soy\s*milk)\b',
        r'\b(?:eggs?|free\s*range\s*eggs?)\b',
        r'\b(?:butter|margarine|western\s*star|lurpak|nuttelex)\b',
        r'\b(?:cheese|cheddar|mozzarella|parmesan|feta|brie|camembert|cream\s*cheese|ricotta|bega\s*cheese|tasty\s*cheese|haloumi|d[\'’]affinois)\b',
        r'\b(?:yogurt|yoghurt|chobani|goplain|jalna|gippsland|danone|yoplait)\b',
        r'\b(?:cream|sour\s*cream|custard|antipasto|dip\b|dips\b|hommus|tzatziki|obela|black\s*swan|meredith\s*dairy)\b'
    ]):
        if not any(k in title_l for k in ['chocolate', 'biscuit', 'chips', 'shampoo', 'body wash', 'coconut milk', 'canned', 'condensed milk', 'frother', 'maker']):
            return 'dairy_eggs'

    # -------------------------------------------------------------
    # 8. BAKERY (烘焙麵包、蛋糕點心)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:bread|toast|loaf|sourdough|buns?|rolls?|bagels?|croissants?|crumpets?|muffins?|scones?|wraps?|pita|flatbread|tortillas?|tip\s*top|helga|abbott|wonder\s*white|pane\s*di\s*casa|baguette|hot\s*dog\s*rolls?)\b',
        r'\b(?:cakes?|slices?|mr\s*kipling|pavlova|lamington|donuts?|doughnuts?|crust|pastry|danish|tart|pains?\s*au\s*chocolat|pudding|steamy\s*puds|brownie|profiteroles)\b'
    ]):
        if not any(k in title_l for k in ['baking paper', 'baking powder', 'dog', 'cat', 'rice cake', 'cake mix', 'bread maker']):
            return 'bakery'

    # -------------------------------------------------------------
    # 9. SNACKS & CONFECTIONERY (休閒零食、堅果、果乾)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:chocolate|cadbury|lindt|kit\s*kat|m&m|maltesers|mars|snickers|twix|kinder|toblerone|ferrero)\b',
        r'\b(?:chips|crisps|doritos|smith[\'’]?s|red\s*rock\s*deli|kettle|pringles|thins|cheezels|twisties|grainwaves|sunbites)\b',
        r'\b(?:biscuits?|cookies?|tim\s*tam|arnott[\'’]?s|oreo|shapes|ritz|cruskit|water\s*crackers?|crackers?|digestives)\b',
        r'\b(?:lollies|gummies|candy|mints|mentos|allens?|skittles|chupa\s*chups|gum|liquorice|licorice|darrell\s*lea|haribo|life\s*savers)\b',
        r'\b(?:nuts?|peanuts?|almonds?|cashews?|pistachios?|walnuts?|pecans?|macadamias?|popcorn|seaweed)\b',
        r'\b(?:le\s*snak|protein\s*bar|man\s*bar|lady\s*bar|fibre\s*one|nature\s*valley|kiddylicious|koala[\'’]?s\s*march|meiji|smooshed|prunes|pitted\s*prunes)\b'
    ]):
        if not any(k in title_l for k in ['frozen', 'ice cream', 'shampoo', 'body wash', 'dip']):
            return 'snacks'

    # -------------------------------------------------------------
    # 10. HEALTH & BEAUTY (保健美妝: 彩妝、美髮梳具、護膚洗沐、維他命、牙膏、防曬、女性/失禁護理)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:vitamins?|supplements?|blackmores|swisse|nature[\'’]?s\s*own|cenovis|ostelin|bioglan|berocca|voost|collagen|peptides|protein\s*powder|effervescent|creatine|pre\s*workout|greens\s*powder|shake\s*burn)\b',
        r'\b(?:shampoo|conditioner|hair\s*treatment|hair\s*oil|hair\s*colour|hair\s*dye|hair\s*spray|hair\s*mask|mousse|got2b|leave\s*in\s*spray|clairol|hask|detangle)\b',
        r'\b(?:pantene|head\s*&\s*shoulders|herbal\s*essences|tresemm[eé]|schwarzkopf|l\'or[eé]al|garnier|ogx|sukin|mixa|essano|toni\s*&\s*guy|hair\s*brush|comb\b)\b',
        r'\b(?:body\s*wash|shower\s*gel|soap\s*bar|hand\s*wash|hand\s*sanitiser|palmolive|dove|lux\b|pears\b|vaseline|beard\s*oil|jack\s*the\s*barber|bubble\s*bath|shower\s*foam)\b',
        r'\b(?:skincare|moisturiser|moisturizer|serum|facial|cleanser|micellar|eye\s*cream|face\s*mask|face\s*cream|olay|nivea|neutrogena|pore\s*strips|skin\s*republic|foot\s*peel)\b',
        r'\b(?:sunscreen|banana\s*boat|cancer\s*council|bondi\s*sands|dermaveen|spf\s*\d+)\b',
        r'\b(?:deodorant|antiperspirant|roll\s*on|body\s*spray|rexona|mitchum|lynx\b|brut\b|nivea\s*men)\b',
        r'\b(?:toothpaste|toothbrush|mouthwash|dental|colgate|oral[- ]b|sensodyne|white\s*glo)\b',
        r'\b(?:razor|shaving|gillette|schick|bic\b|billie\b|wax\s*strips|veet|hair\s*remover)\b',
        r'\b(?:tampons?|pads\s*with\s*wings|incontinence|depend|poise|tena|underwear\s*for\s*women|liners?|u\s*by\s*kotex|libra|tom\s*organic|carefree|stayfree)\b',
        r'\b(?:nappies|nappy|babylove|huggies|baby\s*wipes|curash|little\s*one[\'’]?s)\b',
        r'\b(?:lip\s*balm|cosmetics?|mascara|lipstick|lipcolor|lip\s*oil|eyeliner|eyeshadow|foundation|concealer|revlon|rimmel|mcobeauty|maybelline|covergirl|1000hour|eyebrow|microblading|blender\s*sponge|luminiser)\b'
    ]):
        return 'health_vitamins'

    # -------------------------------------------------------------
    # 11. HOUSEHOLD (日用清潔: 洗衣精、去漬、洗碗錠、衛生紙、芳香擴香、清潔劑、垃圾袋、保鮮膜)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:laundry|detergent|washing\s*powder|fabric\s*softener|omo\b|cold\s*power|dynamo|radiant|comfort|fluffy|biozet|earthwise|cuddly|scent\s*booster|stain\s*remover|sard\b|vanish)\b',
        r'\b(?:dishwashing|dishwasher|finish\b|fairy\b|morning\s*fresh)\b',
        r'\b(?:toilet\s*paper|toilet\s*tissue|facial\s*tissues?|paper\s*towels?|quilton|kleenex|sorbent|viva\b)\b',
        r'\b(?:cleaner|cleaning\s*wipes|disinfectant|bleach|pine\s*o\s*cleen|dettol|glen\s*20|ajax|harpic|bref|easy-off|chux|vileda|elbow\s*grease|degreaser|scourers|wash\s*wild)\b',
        r'\b(?:garbage\s*bags?|bin\s*liners?|multix|glad|albal|baking\s*paper|foil|cling\s*wrap|pegs\b)\b',
        r'\b(?:air\s*wick|ambipur|febreze|glade|diffuser|reed\s*diffuser|maison\s*&\s*muse)\b'
    ]):
        return 'household'

    # -------------------------------------------------------------
    # 12. PANTRY (米麵調味 & 糧油罐頭乾貨)
    # -------------------------------------------------------------
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:sauce|pasta|spaghetti|rice|noodles?|ramyun|cous\s*cous|risotto|oil|olive\s*oil|canned|tin\b|beans?|spread|jam\b|cereal|oats|weet-bix|honey|mayonnaise|mustard|tuna\b|maple\s*syrup)\b',
        r'\b(?:flour|sugar|salt\b|pepper|vinegar|simmer\s*sauce|curry|gravy|seasoning|spice|dressing|stock|soup|chilli|tomato\s*paste|pesto|olives|sugo|polpa|diced\s*tomatoes)\b',
        r'\b(?:leggo[\'’]?s|barilla|san\s*remo|old\s*el\s*paso|maggi|continental|masterfoods|heinz|sharwood[\'’]?s|colway|nongshim|mutti|remano|john\s*west|uncle\s*tobys|kellogg|sanitarium)\b',
        r'\b(?:baby\s*food|formula|porridge|rafferty)\b'
    ]):
        return 'pantry'

    if 'soup' in title_l:
        return 'pantry'

    # -------------------------------------------------------------
    # 13. OTHER (其他專區: 禮券SIM卡、五金園藝、廚具小家電、保鮮盒、服飾襪類、玩具百貨雜項)
    # -------------------------------------------------------------
    # Any general merchandise / unclassified department store item belongs to 'other'
    return 'other'
