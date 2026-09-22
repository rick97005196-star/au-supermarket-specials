# -*- coding: utf-8 -*-
import re
import json

# Standard 12 Category Keys (Aligned strictly with user requirements)
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
    'pet'
]

INTERNAL_CATEGORY_KEYS = set(CATEGORIES) | {'groceries', 'other'}

def classify_product(title: str, raw_cat: str = "", product_url: str = "") -> str:
    """
    Classifies an Australian supermarket product strictly into one of the 12 standard categories:
    produce, meat, seafood, dairy_eggs, bakery, frozen, pantry, snacks, drinks, health_vitamins, household, pet.
    """
    title_l = title.lower().strip()
    url_l = product_url.lower().strip()

    # 1. Official Supermarket Department Mapping via Salefinder URL
    if 'salefinder.com.au' in url_l:
        m = re.search(r'groceries/([^/]+)/', url_l)
        if not m:
            m = re.search(r'food-and-beverage/([^/]+)/', url_l)
        if m:
            dept = m.group(1).lower()
            if dept in ['fruit-and-vegetables']:
                return 'produce'
            if dept in ['meat']:
                return 'meat'
            if dept in ['seafood']:
                return 'seafood'
            if dept in ['dairy']:
                return 'dairy_eggs'
            if dept in ['bakery']:
                return 'bakery'
            if dept in ['frozen-food', 'desserts']:
                return 'frozen'
            if dept in ['canned-and-packet-food', 'cooking-seasoning-and-gravy', 'condiments', 'breakfast-foods', 'jams-and-spreads', 'baking']:
                return 'pantry'
            if dept in ['biscuits-and-snacks', 'confectionery']:
                return 'snacks'
            if dept in ['drinks', 'beer-wine-and-spirit']:
                return 'drinks'
            if dept in ['beauty', 'toiletries', 'health-and-wellbeing', 'health-foods', 'baby']:
                return 'health_vitamins'
            if dept in ['household-cleaning', 'papergoods-wraps-and-bags', 'home-and-outdoor', 'stationery-and-media', 'clothing']:
                return 'household'
            if dept in ['pet-care']:
                return 'pet'
            if dept in ['deli-and-chilled']:
                if any(k in title_l for k in ['salad', 'coleslaw']):
                    return 'produce'
                if any(k in title_l for k in ['dip', 'cheese', 'yogurt', 'yoghurt', 'antipasto']):
                    return 'dairy_eggs'
                return 'meat'

    # Special Cadbury rule
    if 'cadbury' in title_l or 'chocolate block' in title_l:
        return 'snacks'

    # 2. HOUSEHOLD & CLEANING (Must evaluate before fruit scent keywords like lemon, orange, apple!)
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:laundry|detergent|washing\s*powder|washing\s*liquid|fabric\s*softener|scent\s*booster|stain\s*remover)\b',
        r'\b(?:omo\b|cold\s*power|dynamo|radiant|comfort|fluffy|biozet|earthwise|cuddly|sard\b|vanish)\b',
        r'\b(?:dishwashing|dishwasher|dish\s*soap|finish\b|fairy\b|morning\s*fresh|lucent\s*globe)\b',
        r'\b(?:toilet\s*paper|toilet\s*tissue|facial\s*tissues?|paper\s*towels?|quilton|kleenex|sorbent|viva\b)\b',
        r'\b(?:toilet\s*cleaner|bleach|disinfectant|cleaner\s*spray|cleaning\s*wipes|floor\s*wipes|multipurpose\s*cleaner|multipurpose\s*wipes)\b',
        r'\b(?:pine\s*o\s*cleen|dettol.*wipes|dettol.*spray|dettol.*floor|glen\s*20|ajax|harpic|bref|easy-off|chux|vileda|degreaser)\b',
        r'\b(?:air\s*freshener|essential\s*mist|diffuser|reed\s*diffuser|air\s*wick|ambipur|febreze|glade)\b',
        r'\b(?:garbage\s*bags?|bin\s*liners?|multix|glad|albal|baking\s*paper|aluminium\s*foil|foil\b|cling\s*wrap|pegs\b)\b',
        r'\b(?:insect\s*spray|mortein|surface\s*spray|pest\s*control|lint\s*buddy|lint\s*roller|seasol)\b',
        r'\b(?:cookware|saucepan|frypan|skillet|casserole|roaster|wok\b|woks\b|grill\s*plate)\b',
        r'\b(?:air\s*fryer|slow\s*cooker|multicooker|juicer|blender|food\s*chopper|bread\s*maker|stand\s*mixer|knife\s*sharpener|vacuum\s*sealer|knife\s*block)\b',
        r'\b(?:baccarat|essteele|anolon|raco|sistema|d[eé]cor|locknlock|appetito|bento|canister|leak\s*proof\s*container|food\s*container|storage\s*container|compostic)\b',
        r'\b(?:batteries|battery|energizer|duracell|philips\s*led|led\s*globe|light\s*bulb)\b',
        r'\b(?:bonds\b.*sock|bonds\b.*tights|bonds\b.*underwear|bonds\b.*brief|bonds\b.*trunk|tights\b|pantyhose|razzamatazz|footlets)\b',
        r'\b(?:sim\s*kit|sim\s*pack|starter\s*pack|prepaid\s*sim|month-to-month\s*sim|telstra|optus|boost|vodafone|amaysim|belong|lebara|dodo|lyca)\b',
        r'\b(?:case\s*protector|tempered\s*glass|watch\s*series|usb\s*cable|charger|headphones?|headset|screen\s*protector)\b'
    ]):
        return 'household'

    # 3. HEALTH & BEAUTY (Must evaluate before fruit words like orange vitamin, grape eyeliner, lemon lip balm, strawberry wax!)
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:vitamins?|supplements?|magnesium|calcium|iron\b|zinc\b|fish\s*oil|glucosamine|probiotic|effervescent|berocca|voost)\b',
        r'\b(?:blackmores|swisse|nature[\'’]?s\s*own|cenovis|ostelin|bioglan)\b',
        r'\b(?:protein\s*powder|creatine|pre\s*workout|greens\s*powder|shake\s*burn|muscle\s*nation|raw\s*organic\s*fibre|collagen|peptides|kava)\b',
        r'\b(?:sunscreen|sun\s*screen|sun\s*lotion|banana\s*boat|cancer\s*council|bondi\s*sands|dermaveen|spf\s*\d+)\b',
        r'\b(?:shampoo|conditioner|hair\s*treatment|hair\s*oil|hair\s*colour|hair\s*dye|hair\s*spray|hair\s*mask|hair\s*chalk|mousse|got2b|leave\s*in\s*spray|clairol|hask|detangle)\b',
        r'\b(?:pantene|head\s*&\s*shoulders|herbal\s*essences|tresemm[eé]|schwarzkopf|l\'or[eé]al|garnier|ogx|sukin|mixa|essano|toni\s*&\s*guy|hair\s*brush|comb\b)\b',
        r'\b(?:body\s*wash|shower\s*gel|soap\s*bar|soap\b|hand\s*wash|hand\s*sanitiser|palmolive|dove|lux\b|pears\b|vaseline|beard\s*oil|jack\s*the\s*barber|bubble\s*bath|shower\s*foam|bath\s*salts?|epsom)\b',
        r'\b(?:skincare|moisturiser|moisturizer|serum|facial|cleanser|micellar|eye\s*cream|face\s*mask|face\s*cream|face\s*wash|sheet\s*mask|olay|nivea|neutrogena|pore\s*strips|skin\s*republic|foot\s*peel|arch\s*cushion)\b',
        r'\b(?:deodorant|antiperspirant|roll\s*on|body\s*spray|rexona|mitchum|lynx\b|brut\b|nivea\s*men)\b',
        r'\b(?:toothpaste|toothbrush|mouthwash|dental|colgate|oral[- ]b|sensodyne|white\s*glo)\b',
        r'\b(?:razor|shaving|gillette|schick|bic\b|billie\b|wax\s*strips|veet|hair\s*remover|waxing\s*dots|nad[\'’]?s)\b',
        r'\b(?:tampons?|pads\s*with\s*wings|incontinence|depend|poise|tena|underwear\s*for\s*women|liners?|u\s*by\s*kotex|libra|tom\s*organic|carefree|stayfree)\b',
        r'\b(?:nappies|nappy|babylove|huggies|baby\s*wipes|curash|little\s*one[\'’]?s)\b',
        r'\b(?:lip\s*balm|lip\s*treatment|cosmetics?|mascara|lipstick|lipcolor|lip\s*oil|eyeliner|eyeshadow|foundation|concealer|revlon|rimmel|mcobeauty|maybelline|covergirl|1000hour|eyebrow|microblading|blender\s*sponge|luminiser)\b'
    ]):
        return 'health_vitamins'

    # 4. DRINKS (Must evaluate before fruit words like orange juice, lemon soda, apple cider!)
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:beer|lager|ale\b|pale\s*ale|hazy\s*pale|ipa\b|xpa\b|draught|stout|cider|seltzer|vodka|whisky|whiskey|gin\b|rum\b|bourbon|tequila|wine|shiraz|sauvignon|chardonnay|pinot|prosecco|champagne|liqueur|brandy|scotch|mid\s*strength|alcoholic|cask\b|tempranillo|merlot|semillon|riesling|cabernet|sauv\s*blanc)\b',
        r'(?:-196|\b196\b)',
        r'\b(?:hard\s*rated|vodka\s*cruiser|smirnoff|heineken|corona|peroni|carlton|great\s*northern|coopers|asahi|guinness|stella\s*artois|somersby|balter|smithy[\'’]?s|4\s*pines|bentspoke|stone\s*&\s*wood|lorry\s*boys|james\s*squire|canadian\s*club|jack\s*daniel|jim\s*beam|woodstock|wild\s*turkey|xxxx|de\s*bortoli|story\s*bay|bundaberg\s*rum|gordon[\'’]?s|tanqueray|baileys|kahlua|aperol|campari|jameson|moretti)\b',
        r'\b(?:coffee|coffee\s*beans|coffee\s*pods?|coffee\s*capsules?|nespresso|lavazza|moccona|nescafe|starbucks|vittoria|grinders|l\'or\s*espresso|l’or\s*espresso|espresso)\b',
        r'\b(?:tea|tea\s*bags|twinings|lipton|dilmah|tetley)\b',
        r'\b(?:coca-cola|coke|pepsi|sprite|fanta|kirks|schweppes|bundle\s*drink|soft\s*drink|sodaly|tonic\s*water|mineral\s*water)\b',
        r'\b(?:juice|nectar|fruit\s*drink|daily\s*juice|nudie|golden\s*circle|cocobella)\b',
        r'\b(?:water\b.*litre|water\b.*ml|spring\s*water|sparkling\s*water|mount\s*franklin|pump\s*water)\b',
        r'\b(?:energy\s*drink|red\s*bull|monster\s*energy|v\s*energy|mother\s*energy|ghost\s*energy|gatorade|powerade|up&go|up\s*&\s*go|rokeby.*smoothie|ready\s*to\s*drink\s*protein)\b',
        r'\b(?:kombucha|cordial|bundaberg\s*brewed)\b'
    ]):
        if not any(k in title_l for k in ['coffee cake', 'tea towel', 'biscuit', 'chocolate block', 'ice cream', 'sauce', 'stand mixer']):
            return 'drinks'

    # 5. FROZEN FOOD (Must evaluate before fruit words like mango ice cream, berry sorbet, spinach pastizzis!)
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:ice\s*cream|gelato|sorbet|magnum|connoisseur|ben\s*&\s*jerry|peters|bulla|cornetto|paddle\s*pop|weis\s*bars?|crunch\s*pops|mixed\s*pack\s*pops|proud\s*&\s*punch)\b',
        r'\b(?:frozen|freezer|from the freezer)\b',
        r'\b(?:hash\s*browns?|potato\s*gems|wedges|shoestring\s*chips|steakhouse.*chips|french\s*fries)\b',
        r'\b(?:dumplings?|gyoza|samosas?|spring\s*rolls?|dim\s*sims?|churros|pastizzi|pastizzis)\b',
        r'\b(?:birds\s*eye|fish\s*fingers|fish\s*bites|four[\'’]?n\s*twenty|patties\s*party|herbert\s*adams|meat\s*pies?|beef\s*pies?|dr\s*oetker|ristorante|pizza\s*395g|pizza\s*310g)\b'
    ]):
        if not any(k in title_l for k in ['chocolate block', 'biscuit', 'pizza base', 'pizza sauce']):
            return 'frozen'

    # 6. DAIRY & EGGS (Must evaluate before fruit words like strawberry yoghurt, lemon cream yoghurt!)
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:milk|fresh\s*milk|almond\s*milk|oat\s*milk|soy\s*milk)\b',
        r'\b(?:eggs?|free\s*range\s*eggs?)\b',
        r'\b(?:butter|margarine|western\s*star|lurpak|nuttelex)\b',
        r'\b(?:cheese|cheddar|mozzarella|parmesan|feta|brie|camembert|cream\s*cheese|ricotta|bega\s*cheese|tasty\s*cheese|haloumi|d[\'’]affinois)\b',
        r'\b(?:yogurt|yoghurt|dairy\s*farmers|chobani|goplain|jalna|gippsland|danone|yoplait)\b',
        r'\b(?:cream\b|sour\s*cream|custard|antipasto|dip\b|dips\b|hommus|tzatziki|obela|black\s*swan|meredith\s*dairy|protein\s*dessert)\b'
    ]):
        if not any(k in title_l for k in ['chocolate', 'biscuit', 'chips', 'coconut milk', 'canned', 'condensed milk']):
            return 'dairy_eggs'

    # 7. BAKERY (Must evaluate before fruit words like apple pie, banana bread!)
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:bread|toast|loaf|sourdough|buns?|rolls?|bagels?|croissants?|crumpets?|muffins?|scones?|wraps?|pita|flatbread|tortillas?|tip\s*top|helga|abbott|wonder\s*white|pane\s*di\s*casa|baguette|hot\s*dog\s*rolls?|pizza\s*base|pizza\s*bases|mighty\s*soft)\b',
        r'\b(?:cakes?|slices?|mr\s*kipling|pavlova|lamington|donuts?|doughnuts?|crust|pastry|danish|tart|pains?\s*au\s*chocolat|pudding|steamy\s*puds|brownie|profiteroles)\b'
    ]):
        if not any(k in title_l for k in ['baking paper', 'baking powder', 'dog', 'cat', 'rice cake', 'cake mix', 'bread maker', 'stand mixer']):
            return 'bakery'

    # 8. SNACKS (Must evaluate before fruit words like mushroom crisps, banana kick corn puffs, apple biscuits!)
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:chocolate|cadbury|lindt|kit\s*kat|m&m|maltesers|mars|snickers|twix|kinder|toblerone|ferrero)\b',
        r'\b(?:chips|crisps|doritos|smith[\'’]?s|red\s*rock\s*deli|kettle|pringles|thins|cheezels|twisties|grainwaves|sunbites)\b',
        r'\b(?:biscuits?|cookies?|tim\s*tam|arnott[\'’]?s|oreo|shapes|ritz|cruskit|water\s*crackers?|crackers?|digestives)\b',
        r'\b(?:lollies|gummies|candy|mints|mentos|allens?|skittles|chupa\s*chups|gum|liquorice|licorice|darrell\s*lea|haribo|life\s*savers)\b',
        r'\b(?:nuts?|peanuts?|almonds?|cashews?|pistachios?|walnuts?|pecans?|macadamias?|popcorn|corn\s*puffs|seaweed)\b',
        r'\b(?:le\s*snak|protein\s*bar|man\s*bar|lady\s*bar|fibre\s*one|nature\s*valley|kiddylicious|koala[\'’]?s\s*march|meiji|smooshed|prunes|pitted\s*prunes|noshu|oat\s*bars?|pick\s*up\s*sticks?)\b'
    ]):
        return 'snacks'

    # 9. PANTRY (Must evaluate before fruit words like diced tomatoes, canned pineapple, pickled cucumbers!)
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:sauce|pasta|spaghetti|rice|noodles?|ramyun|cous\s*cous|risotto|oil|olive\s*oil|canned|tin\b|beans?|spread|jam\b|cereal|oats|weet-bix|honey|mayonnaise|mustard|tuna\b|maple\s*syrup)\b',
        r'\b(?:flour|sugar|salt\b|pepper|vinegar|simmer\s*sauce|curry|gravy|seasoning|spice|dressing|stock|soup|chilli|tomato\s*paste|pesto|olives|sugo|polpa|diced\s*tomatoes|peeled\s*tomatoes|tomatoes\s*400g)\b',
        r'\b(?:leggo[\'’]?s|barilla|san\s*remo|old\s*el\s*paso|maggi|continental|masterfoods|heinz|sharwood[\'’]?s|colway|nongshim|mutti|remano|john\s*west|uncle\s*tobys|kellogg|sanitarium)\b',
        r'\b(?:baby\s*food|formula|porridge|rafferty|pickle\s*licious|pickles?|pickled|cucumbers\s*350g)\b'
    ]):
        return 'pantry'

    # 10. PET (寵物用品)
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:cat\s*food|dog\s*food|pet\s*food|cat\s*treats?|dog\s*treats?|cat\s*litter)\b',
        r'\b(?:whiskas|pedigree|schmackos|purina|supercoat|fancy\s*feast|fussy\s*cat|dine\b|temptations|open\s*paddock|nature[\'’]?s\s*gift|my\s*dog|optimum\s*dog|optimum\s*cat|vip\s*petfoods|hartz)\b'
    ]):
        return 'pet'

    # 11. MEAT & SEAFOOD
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:salmon|prawns?|shrimp|calamari|squid|octopus|tuna\s*fillet|tuna\s*steak|barramundi|snapper|flathead|basa|fish\s*fillets?|mussels|oysters?|lobster|crab|just\s*caught|ocean\s*royale)\b'
    ]):
        return 'seafood'

    if any(re.search(pat, title_l) for pat in [
        r'\b(?:beef|pork|lamb|chicken|steak|mince|sausages?|roast|chops?|cutlets?|veal|bacon|ham|prosciutto|salami|meatballs?|chicken\s*breast|chicken\s*thigh|drumsticks?|tenderloins?)\b',
        r'\b(?:frankfurts?|franks\b|chorizo|burgers?|twiggy\s*sticks?|d[\'’]orsogna|don\b.*from\s*the\s*deli|don\s*footy|primo.*hot\s*dog|tegel|turkey\s*breast|mon\s*deli)\b'
    ]):
        return 'meat'

    # 12. PRODUCE (NOW only real fresh produce remains!)
    if any(re.search(pat, title_l) for pat in [
        r'\b(?:apples?|bananas?|oranges?|mandarins?|grapes?|strawberries|blueberries|raspberries|avocados?|lemons?|limes?|mangoes?|peaches|plums|pears?|pineapple|kiwifruit|wombok)\b',
        r'\b(?:potatoes?|sweet\s*potatoes?|carrots?|onions?|broccoli|cauliflower|lettuce|salad|salads?|cabbage|zucchini|mushrooms?|capsicums?|cucumbers?|spinach|tomatoes?|slaw\s*kit|qukes|snackables)\b'
    ]):
        return 'produce'

    # Fallback to household
    return 'household'
