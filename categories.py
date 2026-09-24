# -*- coding: utf-8 -*-
import re
import json

# Standard 13 Category Keys (Aligned strictly with Australian supermarket departments & user needs)
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
    'liquor',
    'health_vitamins',
    'household',
    'pet'
]

INTERNAL_CATEGORY_KEYS = set(CATEGORIES) | {'groceries', 'other'}

def classify_product(title: str, raw_cat: str = "", product_url: str = "") -> str:
    """
    Logically sound, real-world supermarket department classifier for Australian specials.
    """
    t = title.strip()
    tl = f" {t.lower()} "

    # -------------------------------------------------------------
    # 1. PET CARE (Highest priority: never let dog/cat food into meat, pantry, or health!)
    # Exclude "hot dog", "hot dog rolls"
    # -------------------------------------------------------------
    is_hot_dog = bool(re.search(r'\bhot\s*dogs?\b', tl))
    is_bulldog_skincare = bool(re.search(r'\bbulldog\b.*(?:skincare|wash|scrub|oil|moisturiser|moisturizer)', tl))
    if not is_hot_dog and not is_bulldog_skincare:
        if re.search(r'\b(?:dog|dogs|puppy|puppies|cat|cats|kitten|kittens|canine|feline)\b', tl) or \
           re.search(r'\b(?:pet\s*food|pet\s*treats?|cat\s*litter|cat\s*food|dog\s*food|dog\s*treats?|cat\s*treats?|pet\s*dental|dog\s*chews)\b', tl) or \
           re.search(r'\b(?:purina|whiskas|pedigree|dine\b|felix|fancy\s*feast|supercoat|optimum\s*(?:dog|cat|adult|puppy)|schmackos|my\s*dog|fussy\s*cat|temptations|hartz|billie\'?s\s*bowl|vip\s*petfoods|open\s*paddock|the\s*paw\s*grocer)\b', tl):
            return 'pet'

    # -------------------------------------------------------------
    # 2. LIQUOR & ALCOHOL
    # Exclude: ginger ale (soft drink), cider vinegar (pantry), champagne blonde hair (health), scotch finger (biscuit), scotch fillet (meat), sauces with bourbon/wine, pizzas
    # -------------------------------------------------------------
    is_ginger_ale = bool(re.search(r'\bginger\s*ale\b', tl))
    is_cider_vinegar = bool(re.search(r'\bcider\s*vinegar\b', tl))
    is_scotch_finger = bool(re.search(r'\bscotch\s*finger\b', tl))
    is_scotch_fillet = bool(re.search(r'\bscotch\s*fillet\b', tl))
    is_hair_product = bool(re.search(r'\b(?:root\s*concealer|concealer\s*wand|hair\s*colour|hair\s*color|hair\s*dye|permanent|blonde|brunette|clairol|schwarzkopf)\b', tl))
    is_food_product = bool(re.search(r'\b(?:pizza|pizzas|biscuit|biscuits|chocolate|ice\s*cream|chips|crisps|snack)\b', tl))

    if not is_ginger_ale and not is_cider_vinegar and not is_scotch_finger and not is_scotch_fillet and not is_hair_product and not is_food_product:
        if not re.search(r'\b(?:sauce|biscuit|chocolate|ice\s*cream|non[- ]alcoholic|zero\s*alcohol)\b', tl):
            if re.search(r'\b(?:beer|lager|pale\s*ale|ipa\b|xpa\b|draught|stout|cider|seltzer|vodka|whisky|whiskey|gin\b|rum\b|bourbon|tequila|wine|shiraz|sauvignon|chardonnay|pinot|prosecco|champagne|liqueur|brandy|scotch\b|alcoholic|tempranillo|merlot|semillon|riesling|cabernet)\b', tl) or \
               re.search(r'\b(?:-196|\b196\b|\bhard\s*rated|vodka\s*cruiser|smirnoff|heineken|corona\b|\bperoni\b|carlton|great\s*northern|coopers|asahi|guinness|stella\s*artois|somersby|balter|stone\s*&\s*wood|canadian\s*club|jack\s*daniels?|jim\s*beam|bundaberg\s*rum|xxxx\s*gold|\bmoretti\b|wild\s*turkey)\b', tl):
                return 'liquor'

    # -------------------------------------------------------------
    # 3. HEALTH & BEAUTY / VITAMINS & PERSONAL CARE
    # Checked before household and general groceries to catch skincare, oral care, cosmetics, vitamins, shakes
    # Exclude: fresh meat steaks (Flat iron steak), chocolates, noodles, bread
    # -------------------------------------------------------------
    is_chocolate_bar = bool(re.search(r'\b(?:chocolate\s*block|choc\s*block|chocolate\s*bar|milk\s*choc|dairy\s*milk)\b', tl))
    is_meat_or_fresh = bool(re.search(r'\b(?:beef|steak|mince|chicken|pork|lamb|sausages?|bacon|ham\b)\b', tl))
    is_edible_bakery_or_snack = bool(re.search(r'\b(?:chocolate\s*block|choc\s*block|chocolate\s*bar|milk\s*choc|dairy\s*milk|bread|buns?|rolls?|bagels?|crumpets?|cookies?|biscuits?|chips|crackers?)\b', tl))

    is_personal_care = bool(re.search(r'\b(?:toothpaste|toothbrush|mouthwash|dental\s*floss|oral[- ]b|colgate|sensodyne|white\s*glo|polident)\b', tl)) or \
        bool(re.search(r'\b(?:shampoo|hair\s*conditioner|\bconditioner\b|hair\s*oil|hair\s*treatment|hair\s*colour|hair\s*color|hair\s*dye|hair\s*spray|hair\s*mask|leave[- ]in|dry\s*shampoo|texturising\s*spray|pantene|head\s*&\s*shoulders|herbal\s*essences|tresemm[eé]|schwarzkopf|clairol|hask|ogx|sunsilk|l\'or[eé]al|garnier\s*fructis|root\s*concealer|got2b|hair\s*mousse|hair\s*jelly|styling\s*gel|hair\s*wax|hair\s*wand|sculpting\s*cream|detangler|heat\s*protect|hair\s*primer|hair\s*styling|my\s*soda)\b', tl)) or \
        bool(re.search(r'\b(?:body\s*wash|shower\s*gel|shower\s*oil|shower\s*foam|shower\s*steamer|hand\s*wash|soap\s*bar|\bsoap\b|liquid\s*soap|palmolive.*wash|dove|radox|lux\b|freshwater\s*farm|original\s*source|thanks\s*to\s*nature|bath\s*salts?|epsom\s*salts?|bubble\s*bath|body\s*scrub|exfoliat|anihana)\b', tl)) or \
        bool(re.search(r'\b(?:razor|shaving|shave\s*gel|shave\s*cream|pre[- ]shave|gillette|schick|bic\s*(?:comfort|flex|hybrid|soleil)|veet|hair\s*removal|wax\s*strips|waxing|dermaplane|billie\b)\b', tl)) or \
        bool(re.search(r'\b(?:skincare|moisturis|sorbolene|serum|facial|cleanser|micellar|eye\s*cream|face\s*mask|face\s*wash|face\s*cream|sorbet\s*(?:cream|face)|sheet\s*mask|\bmask\b|\bscrub\b|olay|nivea|neutrogena|dermaveen|cetaphil|aveeno|qv\b|suk[ií]n|bioderma|garnier|body\s*lotion|body\s*oil|shimmer\s*body\s*oil|hand\s*cream|heel\s*balm|foot\s*peel|pedi\s*mask|pore\s*strip|pimple\s*patch|spot\s*clear|salicylic|rosken|scholl|eulactol|skin\s*republic|vaseline|bulldog\s*skincare)\b', tl)) or \
        bool(re.search(r'\b(?:lip\s*balm|lip\s*oil|lipstick|lipcolor|lip\s*gloss|lip\s*plump|lip\s*treatment|mascara|eyeliner|eyeshadow|foundation|concealer|luminiser|highlighter|eyebrow|revlon|rimmel|mcobeauty|maybelline|covergirl|1000hour|tanning|fake\s*tan|bondi\s*sands|booie|poni)\b', tl)) or \
        bool(re.search(r'\b(?:deodorant|antiperspirant|roll\s*on|body\s*spray|rexona|mitchum|lynx\b|brut\b)\b', tl)) or \
        bool(re.search(r'\b(?:sunscreen|sun\s*screen|sun\s*lotion|banana\s*boat|cancer\s*council)\b', tl)) or \
        bool(re.search(r'\b(?:tampons?|pads\s*with\s*wings|maternity\s*pads|incontinence|depend|poise|tena|u\s*by\s*kotex|libra|tom\s*organic|carefree|stayfree)\b', tl)) or \
        bool(re.search(r'\b(?:nappies|nappy|babylove|huggies|baby\s*wipes|curash|little\s*one[\'’]?s)\b', tl)) or \
        bool(re.search(r'\b(?:vitamins?|multivitamin|supplements?|magnesium|calcium|iron\s*(?:tablets?|capsules?|supplements?|gummies|liquid|chews?)|zinc\b|fish\s*oil|glucosamine|probiotics?|berocca|voost|blackmores|swisse|nature[\'’]?s\s*own|cenovis|ostelin|bioglan|effervescent|kava)\b', tl)) or \
        bool(re.search(r'\b(?:protein\s*powder|protein\s*water|creatine|pre[- ]workout|collagen|peptides|fibre\s*boost|swisse.*gummies|metamucil|vita\s*gummies|fatblaster|weight\s*loss\s*shake|the\s*man\s*shake|the\s*lady\s*shake|muscle\s*nation|famous\s*nutrition)\b', tl))

    if is_personal_care and not is_meat_or_fresh and not is_edible_bakery_or_snack:
        return 'health_vitamins'

    # -------------------------------------------------------------
    # 4. FROZEN FOODS
    # (Ice cream, frozen meals, pizzas, dumplings, gyoza, dim sim, frozen chicken tenders/nuggets, frozen chips)
    # -------------------------------------------------------------
    is_packet_chips = bool(re.search(r'\b(?:potato\s*chips|corn\s*chips|tortilla\s*chips|turtle\s*chips|french\s*fries\s*original|thins\s*wedges|smith[\'’]?s|red\s*rock|doritos|cheezels|twisties|grainwaves|pringles)\b', tl))
    is_pizza_base = bool(re.search(r'\bpizza\s*bases?\b', tl))

    if not is_packet_chips and not is_pizza_base and not is_edible_bakery_or_snack:
        if re.search(r'\b(?:from\s*the\s*freezer|freezer|frozen|water\s*ice|zooper\s*dooper|ice\s*pole)\b', tl) or \
           re.search(r'\b(?:ice\s*cream|gelato|sorbet|magnum|connoisseur|ben\s*&\s*jerry|peters\b|bulla\b|cornetto|paddle\s*pop|weis\s*bars?|crunch\s*pops|proud\s*&\s*punch|drumstick|golden\s*gaytime|maxibon)\b', tl) or \
           re.search(r'\b(?:dumplings?|gyoza|samosas?|spring\s*rolls?|dim\s*sims?|siu\s*mai|mandu|churros|pastizzi|pastizzis)\b', tl) or \
           re.search(r'\b(?:hash\s*browns?|potato\s*gems|french\s*fries|shoestring\s*chips|superfries)\b', tl) or \
           re.search(r'\b(?:chicken\s*tenders?|nuggets?|tegel\s*take\s*outs|wing\s*nibbles|crumbed\s*(?:calamari|squid|fish|prawns?)|fish\s*bites|fish\s*fingers)\b', tl) or \
           re.search(r'\b(?:birds\s*eye|four[\'’]?n\s*twenty|patties\s*party|herbert\s*adams|meat\s*pies?|beef\s*pies?|dr\s*oetker|ristorante|frozen\s*pizza|mccain.*pizza|party\s*pizzas?|coles\s*kitchen\s*pizza|buonissimo\s*party\s*pizzas?|pizza\b)\b', tl):
            if not re.search(r'\b(?:biscuit|cookie|baking\s*paper|pan\b|tray|air\s*fryer|pizza\s*base)\b', tl):
                return 'frozen'

    # -------------------------------------------------------------
    # 5. HOUSEHOLD (Laundry, Dishwashing, Cleaning, Paper Goods, Batteries, Cookware, Bags, Bedding, Garden, Telecom, Apparel)
    # Avoid stealing food items (noodle bowls, snack pots, hot dog rolls, etc.)
    # -------------------------------------------------------------
    is_fabric_conditioner = bool(re.search(r'\bfabric\s*(?:conditioner|softener)\b', tl))
    is_gardening = bool(re.search(r'\b(?:potting\s*mix|garden\s*tonic|fertiliser|fertilizer|hose\s*on|lawn|weed\s*kill)\b', tl))
    is_bedding = bool(re.search(r'\b(?:pillow|pillows|quilt|blanket|bedsheet|towel|towels|clothes\s*airer)\b', tl))
    is_food_or_drink_clash = bool(re.search(r'\b(?:instant\s*noodle|protein|snack\s*pot\b|hot\s*dog|seaweed|taco|oil\s*4\s*(?:l|litre)|tea\s*bags?|latte|matcha|pho\s*kit)\b', tl))

    if not is_food_or_drink_clash:
        if is_gardening or is_bedding or is_fabric_conditioner or \
           re.search(r'\b(?:laundry|detergent|washing\s*powder|washing\s*liquid|fabric\s*softener|scent\s*booster|cuddly|fluffy|comfort\s*(?:laundry|fabric|amazon)|omo\b|cold\s*power|dynamo|radiant|biozet|earthwise|sard\b|vanish)\b', tl) or \
           re.search(r'\b(?:dishwashing|dishwasher|dish\s*soap|dish\s*tablets|finish\b|fairy\b|morning\s*fresh|lucent\s*globe)\b', tl) or \
           re.search(r'\b(?:toilet\s*paper|toilet\s*tissue|facial\s*tissues?|paper\s*towels?|quilton|kleenex|sorbent|viva\b|handee)\b', tl) or \
           re.search(r'\b(?:garbage\s*bags?|bin\s*liners?|multix|glad\b|albal|baking\s*paper|aluminium\s*foil|foil\b|cling\s*wrap|freezer\s*bags?|snack\s*bags?|bbq\s*foil\s*trays?)\b', tl) or \
           re.search(r'\b(?:toilet\s*cleaner|bleach|disinfectant|cleaner\s*spray|cleaning\s*wipes|floor\s*wipes|multipurpose\s*cleaner|pine\s*o\s*cleen|glen\s*20|ajax|harpic|bref|easy[- ]off|chux|vileda|degreaser|duck\s*(?:deep|toilet|fresh))\b', tl) or \
           re.search(r'\b(?:air\s*freshener|reed\s*diffuser|air\s*wick|ambipur|ambi\s*pur|febreze|glade|essential\s*mist|plug[- ]in\s*diffuser|scentory|candle|candles)\b', tl) or \
           re.search(r'\b(?:insect\s*spray|mortein|surface\s*spray|pest\s*control|fly\s*spray|bushman|repellent|lint\s*roller)\b', tl) or \
           re.search(r'\b(?:batteries|battery\b|energizer|duracell|philips\s*led|led\s*globe|light\s*bulb|mirabella|charger|cable|usb)\b', tl) or \
           re.search(r'\b(?:baccarat|essteele|anolon|raco|sistema|d[eé]cor|locknlock|cookware|saucepan|frypan|wok\b|skillet|knife\s*block|knife\s*sharpener|storage\s*container|food\s*container|water\s*bottle|smash\s*(?:blue|stainless|bento|snack\s*pot|coffee\s*cup)|tritan\s*canister|storage\s*canister)\b', tl) or \
           re.search(r'\b(?:sim\s*(?:kit|pack|starter)|prepaid\s*sim|boost\s*mobile|telstra\s*prepaid|optus\s*prepaid|vodafone\s*prepaid|amaysim|belong|lebara|dodo|lyca|starter\s*pack|telstra|optus)\b', tl) or \
           re.search(r'\b(?:bonds\b.*(?:sock|tights|underwear|brief|trunk|hipster|singlet|crop)|pantyhose|razzamatazz|clogs)\b', tl) or \
           re.search(r'\b(?:armor\s*all|car\s*wash|wash\s*&\s*wax|crayons?|creativity\s*set)\b', tl):
            return 'household'

    # -------------------------------------------------------------
    # 6. DRINKS (Non-Alcoholic)
    # (Coffee, Tea, Soda, Juice, Bottled Water, Energy Drinks, Flavoured Milk)
    # Exclude: Reusable cups/bottles (smash coffee cup), body wash
    # -------------------------------------------------------------
    is_reusable_cup = bool(re.search(r'\b(?:coffee\s*cup|water\s*bottle|travel\s*mug)\b', tl))
    if not is_reusable_cup:
        if is_ginger_ale or re.search(r'\b(?:coffee|coffee\s*beans|coffee\s*pods?|coffee\s*capsules?|instant\s*coffee|nespresso|lavazza|moccona|nescafe|starbucks|vittoria|grinders|l\'or\s*espresso|espresso|matcha\s*latte|cafe\s*peak)\b', tl) or \
           re.search(r'\b(?:tea\b|tea\s*bags|twinings|lipton|dilmah|tetley)\b', tl) or \
           re.search(r'\b(?:coca-cola|coke|pepsi|sprite|fanta|kirks|schweppes|soft\s*drink|sodaly|tonic\s*water|mineral\s*water)\b', tl) or \
           re.search(r'\b(?:juice|nectar|fruit\s*drink|daily\s*juice|nudie|golden\s*circle|cocobella|coconut\s*water)\b', tl) or \
           re.search(r'\b(?:spring\s*water|sparkling\s*water|mount\s*franklin|pump\s*water|genki\s*forest|water\s*\d+(?:\.\d+)?\s*(?:l|ml))\b', tl) or \
           re.search(r'\b(?:energy\s*drink|red\s*bull|monster\s*energy|monster\s*energy\s*ultra|v\s*energy|mother\s*energy|ghost\s*energy|gatorade|powerade|up&go|up\s*&\s*go|oak\s*flavoured\s*milk|oak\s*milk)\b', tl) or \
           re.search(r'\b(?:kombucha|cordial|bundaberg\s*brewed|passiona|cottee\'?s)\b', tl):
            if not re.search(r'\b(?:coffee\s*cake|tea\s*towel|biscuit|chocolate|ice\s*cream|sauce|powder\b)\b', tl):
                return 'drinks'

    # -------------------------------------------------------------
    # 7. BAKERY (Bread, Buns, Rolls, Bagels, Muffins, Croissants, Pastries, Cakes, Garlic Bread, Puddings)
    # Exclude: Yoghurt (e.g. yoghurt inspired pudding), pasta & sauce, cookies/biscuits
    # -------------------------------------------------------------
    is_yoghurt_product = bool(re.search(r'\b(?:yoghurt|yogurt)\b', tl))
    is_pasta_sauce_mix = bool(re.search(r'\b(?:pasta\s*&\s*sauce|mac\s*&\s*cheese)\b', tl))
    is_cookie_biscuit = bool(re.search(r'\b(?:cookies?|biscuits?|jaffa\s*cakes?)\b', tl))

    if not is_yoghurt_product and not is_pasta_sauce_mix and not is_cookie_biscuit:
        if re.search(r'\b(?:bread|toast|loaf|sourdough|buns?|rolls?|bagels?|croissants?|crumpets?|muffins?|scones?|wraps?|pita|flatbread|tip\s*top|helga|abbott|wonder\s*white|pane\s*di\s*casa|baguette|hot\s*dog\s*rolls?|pizza\s*bases?|mighty\s*soft|brioche)\b', tl) or \
           re.search(r'\b(?:cakes?|vanilla\s*slice|caramel\s*slice|bakery\s*slice|garlic\s*slices?|pastry\s*slice|mr\s*kipling|pavlova|lamington|donuts?|doughnuts?|crust|pastry|danish|tart|pains?\s*au\s*chocolat|pudding|steamy\s*puds?|brownie|profiteroles|la\s*famiglia|garlic\s*bread|sausage\s*rolls?|aunt\s*betty)\b', tl):
            if not is_packet_chips and not re.search(r'\b(?:cheese|cheddar|chips|tortilla\s*chips|baking\s*paper|baking\s*powder|cake\s*mix|rice\s*cake|shampoo|dog\s*food|cat\s*food)\b', tl):
                return 'bakery'

    # -------------------------------------------------------------
    # 8. SNACKS (Chocolates, Chips, Biscuits, Cookies, Lollies, Snacking Nuts, Snack Bars, Seaweed)
    # -------------------------------------------------------------
    if is_chocolate_bar or is_scotch_finger or is_packet_chips or is_cookie_biscuit or \
       re.search(r'\b(?:chocolate|cadbury|lindt|kit\s*kat|m&m|maltesers|mars\b|snickers|twix|kinder|toblerone|ferrero|darrell\s*lea|reese\'?s)\b', tl) or \
       re.search(r'\b(?:chips|crisps|doritos|smith[\'’]?s|red\s*rock\s*deli|kettle|pringles|thins|cheezels|twisties|grainwaves|sunbites|cc\'?s|takis|cheetos|mini\s*canister)\b', tl) or \
       re.search(r'\b(?:biscuits?|cookies?|tim\s*tam|arnott[\'’]?s|oreo|shapes|ritz|cruskit|vitaweat|water\s*crackers?|crackers?|digestives|biscotti|shortcake|speculaas)\b', tl) or \
       re.search(r'\b(?:lollies|gummies|candy|mints|mentos|allens?|skittles|chupa\s*chups|gum\b|liquorice|licorice|haribo|life\s*savers|natural\s*confectionery|sour\s*patch)\b', tl) or \
       re.search(r'\b(?:peanuts?|almonds?|cashews?|pistachios?|walnuts?|pecans?|macadamias?|popcorn|corn\s*puffs|seaweed|roasted\s*nuts|roasted\s*nut\s*bars?|trail\s*mix)\b', tl) or \
       re.search(r'\b(?:le\s*snak|protein\s*bar|the\s*man\s*bar|the\s*lady\s*bar|bsc.*bar|nice\s*&\s*natural|fibre\s*one|nature\s*valley|kiddylicious|koala[\'’]?s\s*march|meiji|smooshed|prunes|pitted\s*prunes|noshu|oat\s*bars?|pick\s*up\s*sticks?|lcms?|nutri[- ]grain\s*bars?|rice\s*rusks?|toppo)\b', tl):
        if not re.search(r'\b(?:hair\s*dye|lip\s*balm|shampoo|shower|body\s*wash|storage|container|garden\s*tonic)\b', tl):
            return 'snacks'

    # -------------------------------------------------------------
    # 9. PANTRY (CRITICAL: EVALUATED BEFORE RAW MEAT / PRODUCE / DAIRY!)
    # Packaged ambient grocery items:
    # - Instant Noodles, Ramen, Laksa, Udon, Dry Pasta, Spaghetti, Mac & Cheese
    # - Packet Soups, Cup-a-soup, Soup Sensations, Canned Soups
    # - Cooking Sauces, Pasta Sauces, BBQ / Tomato Sauce, Mayonnaise, Mustard, Pesto, Simmer Sauce
    # - Rice, Grains, Couscous, Oats, Cereals, Porridge, Taco Kits, Pho Kits, Meal Kits
    # - Cooking Oils (Olive oil, Canola oil, Sunflower oil, Farmers Harvest)
    # - Canned tuna, Canned beans, Canned tomatoes, Pickles, Olives
    # - Spreads (Peanut butter, Honey, Nutella, Jam, Vegemite)
    # -------------------------------------------------------------
    is_deli_salad = bool(re.search(r'\b(?:coleslaw|potato\s*salad|pasta\s*salad|salad\s*kit|prepacked\s*salad)\b', tl))

    is_pantry_product = not is_deli_salad and (
        is_cider_vinegar or is_pasta_sauce_mix or \
        bool(re.search(r'\b(?:noodle|noodles|instant\s*noodles|ramen|ramyun|laksa|udon|pasta|spaghetti|macaroni|cous\s*cous|risotto|mac\s*&\s*cheese|pho\s*kit|taco\s*kit|meal\s*kit)\b', tl)) or \
        bool(re.search(r'\b(?:soup|cup\s*a\s*soup|soup\s*sensations|broth|laksa)\b', tl)) or \
        bool(re.search(r'\b(?:sauce|ketchup|bbq\s*sauce|tomato\s*sauce|pasta\s*sauce|sugo|polpa|pesto|simmer\s*sauce|curry\s*paste|gravy|marinade)\b', tl)) or \
        bool(re.search(r'\b(?:mayonnaise|mayo|aioli|dressing|vinegar|mustard|chilli\s*paste|soy\s*sauce)\b', tl)) or \
        bool(re.search(r'\b(?:rice\b|jasmine\s*rice|basmati\s*rice|calrose\s*rice|long\s*grain\s*rice)\b', tl)) or \
        bool(re.search(r'\b(?:cereal|oats|weet-bix|porridge|nutri-grain|coco\s*pops|milo\s*cereal|corn\s*flakes|uncle\s*tobys)\b', tl)) or \
        bool(re.search(r'\b(?:cooking\s*oil|vegetable\s*oil|olive\s*oil|canola\s*oil|sunflower\s*oil|extra\s*virgin\s*olive\s*oil|farmers\s*harvest\s*oil|farmers\s*harvest)\b', tl)) or \
        bool(re.search(r'\b(?:canned|tin\b|baked\s*beans|canned\s*tomatoes|diced\s*tomatoes|peeled\s*tomatoes|canned\s*tuna|yellowfin\s*tuna|cucumbers\s*350g|pickle\s*licious|olives\s*450g)\b', tl)) or \
        bool(re.search(r'\b(?:spread|peanut\s*butter|honey|maple\s*syrup|nutella|jam\b|vegemite|sweet\s*condensed\s*milk|evaporated\s*milk)\b', tl)) or \
        bool(re.search(r'\b(?:baby\s*food|formula|rafferty|mumamoo)\b', tl)) or \
        bool(re.search(r'\b(?:leggo[\'’]?s|barilla|san\s*remo|old\s*el\s*paso|la\s*mesita|maggi|continental|masterfoods|heinz|sharwood[\'’]?s|colway|nongshim|mutti|remano|john\s*west\s*yellowfin|kellogg|sanitarium)\b', tl))
    )

    if is_pantry_product:
        # Exclude slow cooked whole meat roasts from butcher dept with bbq sauce
        if not re.search(r'\bfrom\s*the\s*meat\s*dept\b', tl):
            return 'pantry'

    # -------------------------------------------------------------
    # 10. DAIRY & EGGS
    # (Fresh chilled milk, fresh eggs, butter/margarine, cheese blocks/slices, chilled yogurt, chilled dips)
    # Exclude: Hand cream, body cream, curl cream, instant mac & cheese
    # -------------------------------------------------------------
    is_non_dairy_cream = bool(re.search(r'\b(?:hand\s*cream|body\s*cream|face\s*cream|curl|sculpting|shaving|ice\s*cream)\b', tl))
    if not is_non_dairy_cream and not is_pasta_sauce_mix:
        if re.search(r'\b(?:fresh\s*milk|almond\s*milk|oat\s*milk|soy\s*milk|lite\s*milk|full\s*cream\s*milk|long\s*life.*milk|dairy\s*farmers|paul\'?s|devondale)\b', tl) or \
           re.search(r'\b(?:eggs?|free\s*range\s*eggs?)\b', tl) or \
           re.search(r'\b(?:butter|margarine|western\s*star|lurpak|nuttelex)\b', tl) or \
           re.search(r'\b(?:cheese|cheddar|mozzarella|parmesan|feta|brie|camembert|cream\s*cheese|ricotta|bega\s*cheese|tasty\s*cheese|haloumi|d[\'’]affinois)\b', tl) or \
           re.search(r'\b(?:yogurt|yoghurt|chobani|goplain|jalna|gippsland|danone|yoplait|yo\s*pro|snack\s*pot|rokeby)\b', tl) or \
           re.search(r'\b(?:cream\b|sour\s*cream|custard|antipasto|dip\b|dips\b|hommus|tzatziki|obela|black\s*swan|meredith\s*dairy)\b', tl):
            if not re.search(r'\b(?:soup|noodle|ramen|pasta|biscuit|chips|chocolate|coconut\s*milk|canned|peanut\s*butter)\b', tl):
                return 'dairy_eggs'

    # -------------------------------------------------------------
    # 11. SEAFOOD
    # (Raw/fresh fish fillets, raw/cooked whole prawns, oysters, fresh barramundi/salmon, smoked salmon)
    # Exclude oyster blade steak, canned tuna, crumbed frozen squid
    # -------------------------------------------------------------
    is_oyster_blade = bool(re.search(r'\boyster\s*blade\b', tl))
    if not is_oyster_blade and not re.search(r'\b(?:soup|noodle|rice|capsules?|tablets?|gummies|canned|tin\b|crumbed)\b', tl):
        if re.search(r'\b(?:salmon|prawns?|shrimp|calamari|squid|octopus|barramundi|snapper|flathead|basa|fish\s*fillets?|mussels|oysters?|lobster|crab|scallops?|ocean\s*blue|just\s*caught|tassal|huon)\b', tl):
            return 'seafood'

    # -------------------------------------------------------------
    # 12. MEAT (生鮮肉品、屠宰部位肉、生鮮肉排、絞肉、生鮮香腸/熱狗/漢堡排、熟食切片火腿培根)
    # MUST NOT CONTAIN: noodle, ramen, laksa, soup, sauce, chips
    # -------------------------------------------------------------
    is_meat_steak = is_oyster_blade or is_scotch_fillet or bool(re.search(r'\b(?:flat\s*iron\s*steak|rump\s*steak|rib\s*eye|sirloin|t[- ]bone|porterhouse)\b', tl))
    if is_meat_steak or is_hot_dog or \
       re.search(r'\b(?:beef|pork|lamb|chicken|steak|mince|sausages?|roast|chops?|cutlets?|veal|bacon|ham\b|prosciutto|salami|meatballs?|chicken\s*breast|chicken\s*thigh|drumsticks?|tenderloins?)\b', tl) or \
       re.search(r'\b(?:frankfurts?|franks\b|chorizo|burgers?|twiggy\s*sticks?|d[\'’]orsogna|don\b.*from\s*the\s*deli|don\s*footy|primo\s*bacon|primo\s*rindless|turkey\s*breast|mon\s*deli|chicken\s*schnitzel|beef\s*brisket|meat\s*dept)\b', tl):
        if not re.search(r'\b(?:noodle|noodles|ramen|ramyun|laksa|soup|cup\s*a\s*soup|broth|chips|biscuit)\b', tl):
            return 'meat'

    # -------------------------------------------------------------
    # 13. PRODUCE (生鮮蔬果、冷藏生鮮沙拉盒、涼拌捲心菜)
    # -------------------------------------------------------------
    if not re.search(r'\b(?:soup|noodle|powder|shake|biscotti|drops|chips|canned|juice|sauce|jam)\b', tl):
        if is_deli_salad or \
           re.search(r'\b(?:apples?|bananas?|oranges?|mandarins?|grapes?|strawberries|blueberries|raspberries|avocados?|lemons?|limes?|mangoes?|peaches|plums|pears?|pineapple|kiwifruit|wombok)\b', tl) or \
           re.search(r'\b(?:potatoes?|sweet\s*potatoes?|carrots?|onions?|broccoli|cauliflower|lettuce|salad|salads?|cabbage|zucchini|mushrooms?|capsicums?|cucumbers?|spinach|tomatoes?|slaw\s*kit|qukes|snackables|prepacked\s*salads?|coleslaw)\b', tl):
            return 'produce'

    # Fallback to pantry if edible food grocery, else household
    if any(k in tl for k in ['snack', 'food', 'baking', 'flavour', 'sweet', 'organic', 'syrup', 'mix', 'noodle', 'rice', 'meal', 'pasta', 'taco', 'pho']):
        return 'pantry'

    return 'household'


APPLIANCE_HARDWARE_REGEX = re.compile(
    r'\b(?:kettle\s*\d|electric\s*toothbrush|toothbrush\s*handle|saucepan|frypan|cookware|knife\s*block|toaster|air\s*fryer|steam\s*iron|vacuum|pillow|quilt|bedsheet|blanket|storage\s*box|clothes\s*airer|pressure\s*cooker|slow\s*cooker|blender|mixer|armor\s*all|car\s*wash|motor\s*oil|windscreen|protectant\s*spray|tyre\s*shine)\b',
    re.IGNORECASE
)

SUPERSTAR_REGEX = re.compile(
    r'\b(?:shapes|red\s*rock\s*deli|coca-cola|coke|doritos|smith[\'’]?s|tim\s*tam|cadbury|magnum|drumstick|connoisseur|moccona|omo|cold\s*power|weet-bix|milo|vegemite|chobani|bega|western\s*star|dare|up\s*&\s*go|quilton|sorbent|morning\s*fresh|primo\s*(?:rindless|bacon|ham)|heinz\s*(?:ketchup|baked|beans|soup)|natural\s*confectionery|sour\s*patch|birds\s*eye|mccain|twinings|la\s*famiglia|helga[\'’]?s|tip\s*top|barilla|cobram\s*estate)\b|'
    r'\bfinish\s*(?:quantum|powerball|ultimate|all\s*in\s*1|dishwasher|rinse\s*aid|tablets?|capsules?)\b|'
    r'\bfairy\s*(?:platinum|dish|clean|laundry|capsules?|tablets?|wash)\b',
    re.IGNORECASE
)

POPULAR_PATTERNS = [
    # Snacks & Treats
    r'\b(tim\s*tam|arnott[\'’]?s|shapes|jatz|clix|teevee|wagon\s*wheels?|cadbury|favourites|roses|twirl|flake|marvellous|red\s*rock(\s*deli)?|smith[\'’]?s|doritos|kettle\s*(?:chips?|potato|brand|sea\s*salt|honey)|cheezels|grain\s*waves|twisties|burger\s*rings|pods|maltesers|m&m[\'’]?s|skittles|allen[\'’]?s|lindt|ferrero|kinder|nutella|biscoff|oreo|kit\s*kat|mars|snickers|twix|pringles)\b',
    # Pantry & Breakfast & Coffee/Tea
    r'\b(weet-bix|sanitarium|corn\s*flakes|nutri-grain|coco\s*pops|special\s*k|sultana\s*bran|froot\s*loops|milo|nesquik|vegemite|promite|moccona|nescafe|vittoria|lavazza|grinders|l\'or|starbucks|twinings|lipton|dilmah|tetley|bushells|carman[\'’]?s|uncle\s*tobys|barilla|san\s*remo|leggo[\'’]?s|dolmio|heinz|masterfoods|praise|hellmann[\'’]?s|sirena|john\s*west|greenseas|cobram\s*estate|moro|bertolli|crisco|campbell[\'’]?s|spam|old\s*el\s*paso)\b',
    # Drinks & Beverages
    r'\b(coca-cola|coke|pepsi|solo|sunkist|mountain\s*dew|7up|sprite|fanta|schweppes|bundaberg|mount\s*franklin|pump|cool\s*ridge|san\s*pellegrino|kirks|golden\s*circle|daily\s*juice|v\s*energy|red\s*bull|monster|dare|farmers\s*union\s*iced\s*coffee|oak\s*milk|ice\s*break|up\s*&\s*go)\b',
    # Dairy, Chilled & Deli
    r'\b(bega|mainland|cheer|cracker\s*barrel|mersey\s*valley|chobani|gippsland|dairy\s*farmers|jalna|western\s*star|lurpak|devondale|flora|nuttelex|philadelphia|perfect\s*italiano|d[\'’]orsogna|primo|don)\b',
    # Frozen
    r'\b(magnum|cornetto|golden\s*gaytime|paddle\s*pop|blue\s*ribbon|connoisseur|peters|drumstick|maxibon|ben\s*&\s*jerry[\'’]?s|h[aä]agen-dazs|bulla|weis|birds\s*eye|ingham[\'’]?s|steggles|four[\'’]?n\s*twenty|patties|sara\s*lee|mccain)\b',
    # Bakery
    r'\b(tip\s*top|helga|abbott|la\s*famiglia|wonder\s*white|mighty\s*soft|mr\s*kipling)\b',
    # Household, Laundry & Cleaning
    r'\b(finish\s*(?:quantum|powerball|ultimate|all\s*in\s*1|dishwasher|rinse)|fairy\s*(?:platinum|dish|clean|laundry|capsules?|tablets?)|omo|dynamo|cold\s*power|radiant|biozet|comfort|fluffy|cuddly|morning\s*fresh|dawn|palmolive|pine\s*o\s*cleen|dettol|domestos|harpic|duck|bref|ajax|glen\s*20|quilton|sorbent|kleenex|viva|handee|glad)\b',
    # Personal Care, Health & Vitamins
    r'\b(swisse|blackmores|nature[\'’]?s\s*own|cenovis|centrum|berocca|colgate|oral-b|sensodyne|listerine|rexona|nivea|dove|lynx|gillette|schick|head\s*&\s*shoulders|pantene|l[\'’]or[eé]al|garnier|sunsilk|tresemme|radox|aveeno|cetaphil|qv|cancer\s*council|banana\s*boat|huggies|babylove|curash)\b',
    # Fresh Produce & Meat staples
    r'\b(bananas?|hass\s*avocados?|pink\s*lady\s*apples?|strawberries|blueberries|carrots?|potatoes?|broccoli|chicken\s*breast|beef\s*mince|rump\s*steak|rib\s*eye|atlantic\s*salmon|tiger\s*prawns?)\b'
]
POPULAR_REGEX = re.compile('|'.join(POPULAR_PATTERNS), re.IGNORECASE)

def is_popular_product(title: str) -> bool:
    if not title:
        return False
    if APPLIANCE_HARDWARE_REGEX.search(title):
        return False
    if re.search(r'fairy\s*floss', title, re.IGNORECASE):
        return False
    return bool(POPULAR_REGEX.search(title))

def calculate_popularity_score(item: dict) -> int:
    title = item.get('title', '')
    if not title or APPLIANCE_HARDWARE_REGEX.search(title):
        return -999

    is_fairy_floss = bool(re.search(r'fairy\s*floss', title, re.IGNORECASE))

    score = 0
    if SUPERSTAR_REGEX.search(title) and not is_fairy_floss:
        score += 200
    elif POPULAR_REGEX.search(title) and not is_fairy_floss:
        score += 120
    elif item.get('is_popular') and not is_fairy_floss:
        score += 60
    else:
        return 0

    price = float(item.get('price') or 0)
    was_price = float(item.get('was_price') or 0)
    save_amount = float(item.get('save_amount') or 0)
    desc = item.get('discount_desc') or ''

    # Half Price boost
    is_half_price = (price > 0 and was_price > 0 and price <= was_price * 0.52) or bool(re.search(r'1/2|50%|half', desc, re.I))
    if is_half_price:
        score += 60
    elif save_amount > 0 and was_price > 0 and (save_amount / was_price) >= 0.3:
        score += 30

    # Everyday volume / affordability boost ($1.50 - $12 sell in astronomical unit numbers)
    if 1 <= price <= 6:
        score += 50
    elif 6 < price <= 15:
        score += 35
    elif 15 < price <= 30:
        score += 15
    elif price > 30:
        score -= 20

    if was_price > 0 and save_amount > 0:
        score += int((save_amount / was_price) * 10)

    # Category weighting for balanced supermarket popularity
    cat = item.get('category')
    if cat in ['bakery', 'produce', 'meat', 'dairy_eggs', 'seafood']:
        score += 25  # Fresh food staple boost
    elif cat in ['snacks', 'drinks', 'frozen', 'pantry']:
        score += 15  # Packaged grocery staple boost
    elif cat in ['household', 'health_vitamins']:
        score -= 10  # Mild dampener so chemical bottles do not choke out food staples

    return score
