/* Shortcut categories (the chips 冰淇淋, 巧克力, 洋芋片, 咖啡, 微波即食, 泡麵, 汽水, 洗衣精, 維他命).
 *
 * Each product sits in exactly ONE place: a product in a shortcut is not listed in its department
 * (a cola is under 汽水 only, not also under 飲料). The department ("category") comes from
 * categories.py; a shortcut only takes products from the departments listed in `cats`.
 *
 *   inc   = words that put a product in the shortcut
 *   exc   = words that keep it out (checked after inc)
 *   force = always in (when the department matches), even if exc matches
 *
 * Shared by the website and by tests/test_categories.py (run on every rule change), so a rule
 * change can never quietly move products to the wrong chip.
 */
const SUB_CATEGORY_RULES = {
    sub_icecream: { cats: ['frozen'],
        inc: /\b(ice\s*creams?|gelato|sorbet|magnum|cornetto|drumstick|paddle\s*pop|weis|frosty\s*fruits|icy\s*poles?|ice\s*blocks?|zooper|connoisseur|cremissimo|ben\s*&\s*jerry'?s|h[aä]agen|frozen\s*(?:dessert|yogh?urt)|yogh?urt\s*sticks|ice\s*sticks|sundae|golden\s*gaytime|splice|maxibon|bulla|twin\s*pole|lil'?\s*pops|proud\s*&\s*punch|tubs?|cones?|ripple|sandwich(?:es)?|sticks)\b|\b\d+(?:\.\d+)?\s*(?:ml|l)\b/i,
        exc: /\b(makers?|machines?|blenders?|chicken|fish|mozzarella|cheese|garlic|potato|wedges|dough|pastry|pizza|sausages?|spring\s*rolls?|dumplings?|vegetables?|juice|soup|stock)\b/i },
    sub_chocolate: { cats: ['snacks'],
        inc: /\b(chocolates?|choc|cadbury|lindt|lindor|ferrero|kinder|toblerone|maltesers|m&m'?s|mars|snickers|twix|bounty|milky\s*way|kit\s*kat|kitkat|aero|freddo|caramilk|cherry\s*ripe|crunchie|picnic|boost|moro|chomp|chokito|milkybar|smarties|reese'?s|violet\s*crumble|darrell\s*lea|whittaker'?s|nudo|raffaello|roses|old\s*gold|toffifee|allen'?s\s*block|fruchocs|moser\s*roth|truffles|nestl[eé]\s*mini)\b/i,
        exc: /\b(biscuits?|cookies?|digestives?|tim\s*tams?|timtams|tee\s*vee|wagon\s*wheels|fingers|nut\s*bars?|protein\s*bars?|muesli|fibre\s*one|oaty|brownies?|(?:cookie|brownie|baking|trail)\s*mix|popcorn|lollies|eclairs|cereal|crackers?|slice|allsorts|hobnobs|shortcake|hello\s*panda|yan\s*yan|toppo|pretzel|high\s*fibre|man\s*bar|lady\s*bar|nice\s*&\s*natural|apricot|protein)\b|^(?!.*\bchoc).*\b(?:liquorice|licorice)\b/i,
        // a KitKat / M&M's bar with a cookie flavour is still a chocolate bar
        force: /^(?!.*\b(?:popcorn|biscuits?|cones?|ice|ml)\b).*\b(?:m&m'?s|kit\s*kat|kitkat)\b|\bchoc(?:olate)?\s*block\b/i },
    sub_chips: { cats: ['snacks'],
        inc: /\b(chips|crisps|tortilla|twisties|cheezels|burger\s*rings|cheetos|doritos|pringles|thins|kettle|grain\s*waves|grainwaves|nibbles|samboy|jumpy'?s|smith'?s|smiths|red\s*rock\s*deli|cc'?s|tostitos|popcorners|dj&a|potato\s*stix|rice\s*wheels|florets|veggie\s*straws|vege?\s*chips|pickle\s*licious|french\s*fries\s*original)\b/i,
        exc: /\b(dips?|crackers?|choc(?:olate)?\s*chips|fruit\s*crisps|coconut\s*crisps|strawberry\s*crisps|apple\s*crisps|frisp|squid|edamame|nuts?|bars?|biscuits?|cookies?)\b/i },
    sub_coffee: { cats: ['drinks'],
        inc: /\b(coffee|espresso|latte|cappuccino|mocha|affogato|nescaf[eé]|moccona|nespresso|lungo|cold\s*brew)\b/i,
        exc: /\b(caffeine\s*free|decaffeinated\s+(?:black\s+)?tea|nail|machines?|makers?|grinders?(?!\s*coffee))\b|^(?!.*\bcoffee\b).*\b(?:matcha|chai)\b/i },
    // 微波即食: complete meals you only heat in the microwave and eat (Lean Cuisine, On The Menu,
    // supermarket ready meals like "Butter Chicken with Basmati Rice 350g", slow-cooked mains)
    sub_quickmeals: { cats: ['frozen', 'pantry', 'meat', 'dairy_eggs'],
        inc: /\b(microwave\s*(?:meals?|pouch|rice)|microwav\w*\s*meal|ready\s*meals?|frozen\s*meals?|lean\s*cuisine|on\s*the\s*menu|ruffie|strength\s*meals|core\s*powerfoods|cucina\s*classica\s*meal|youfoodz|muscle\s*chef|macro\s*meals?|big\s*feast|takeaway\s*main|with\s+(?:\w+\s+){0,2}(?:rice|mash)|slow\s*cooked|heat\s*(?:&|and)\s*eat|meal\s*\d{3}\s*g)\b/i,
        exc: /\b(sauce\s*\d|pasta\s*sauce|filled\s*pasta|simmer|paste|kits?|salad|soup|pasty|dumplings?|noodles?|chutney|relish|sirena|pies?|sausage\s*rolls?|tuna)\b/i,
        force: /\btakeaway\s*main\b/i },
    sub_noodles: { cats: ['pantry', 'frozen'],
        inc: /\b(noodles?|ramen|ramyun|ramyeon|udon|pho|laksa|mi\s*goreng|indomie|chapagetti)\b/i,
        exc: /\b(fresh\s*noodles|hokkien|wontons?)\b/i },
    sub_soda: { cats: ['drinks'],
        inc: /\b(soft\s*drinks?|cola|coke|pepsi|sprite|fanta|solo|kirks|schweppes|lemonade|ginger\s*(?:beer|ale)|creaming\s*soda|lemon\s*squash|tonic|mixers?|soda|sparkling|mineral\s*water|kombucha|sodaly|sunkist|mountain\s*dew|bundaberg|passiona|pasito|agrum|bitters)\b/i,
        exc: /\b(energy|monster|cordial)\b/i },
    sub_laundry: { cats: ['household'],
        inc: /\b(laundry|washing\s*powder|fabric\s*(?:softener|conditioner|rinse)|softener|napisan|stain\s*(?:remover|power|lifter)|booster\s*beads|omo|cold\s*power|biozet|dynamo|radiant|ka\s*pod|arfum|persil|surf\s*(?:laundry|capsules|powder|liquid)|fluffy|cuddly|comfort\s*(?:laundry|fabric|concentrate|softener)|vanish|oxi\s*action)\b/i,
        exc: /\b(dish\w*|toilet|floor|bowl|surface|kitchen|bathroom|oven|glass)\b/i },
    sub_vitamins: { cats: ['health_vitamins'],
        inc: /\b(vitamins?|vit|vita|multi-?vit\w*|magnesium|zinc|iron|calcium|fish\s*oil|omega|krill|probiotics?|prebiotic|glucosamine|collagen|coq10|b12|b\s*complex|d3|echinacea|electrolytes?|hydration\s*(?:powder|tablets?|drink\s*cubes|sachets|sticks)|hydrate\s*powder|effervescent|tablets?|tabs|capsules?|caplets?|gumm(?:y|ies)|vitagummies|chewable|pastilles|supplements?|evening\s*primrose|lutein|turmeric|ashwagandha|liver\s*detox|prostate|immune|ultiboost|ultivite|blackmores|cenovis|ostelin|centrum|caltrate|nature'?s\s*(?:way|own)|healthy\s*care|elevit|berocca|hydralyte|voost|metamucil|healthcarebear|haircarebear|life\s*botanics|greens|ozi\s*choice|milky\s*bites|waterdrop)\b/i,
        exc: /\b(lotion|wash|serum|moisturi[sz]er|primer|scrub|cuticle|nail|bubble\s*bath|bath|soap|cream|cleanser|cleansing|micellar|fluid|brightening|liquid\s*care|patch|shampoo|conditioner|lip|sunscreen|spf|deodorant|mask|toothpaste|mouthwash|makeup|foundation|mascara|protein|wipes|blush|sticks?|yogh?urts?)\b/i,
        // supplements whose names sound like beauty products
        force: /\b(?:hair\s*(?:scalp\s*)?skin\s*(?:&\s*)?nails?|beauty\s*from\s*within|prebiotic\s*fibre)\b/i },

    // ---------- The rest of each department, split the way people shop (checked after the chips above) ----------
    // 義大利麵・醬: dry / fresh pasta, gnocchi, pasta sauce
    sub_pasta: { cats: ['pantry', 'dairy_eggs', 'frozen'],
        inc: /\b(pasta|spaghetti|spaghettini|penne|fusilli|macaroni|lasagne|lasagna|fettuccine|fettucine|linguine|tagliatelle|pappardelle|rigatoni|farfalle|orecchiette|conchiglie|risoni|orzo|gnocchi|tortellini|tortelloni|ravioli|agnolotti|cannelloni|bucatini|casarecce|penne\s*rigate|dolmio|bolognese|carbonara|pesto|napoletana|arrabbiata|puttanesca|alfredo|sugo|passata|barilla|san\s*remo|la\s*molisana|de\s*cecco|latina|mac\s*(?:&|and|n)\s*cheese)\b/i,
        exc: /\b(salad|chips|crackers?|pizza|pasta\s*salad|soup|bowls?|tuna|sirena|bake\s*sauce\s*\d)\b|^(?=.*\bfrozen\b)(?!.*\b(?:pasta|gnocchi|ravioli|tortellini)\b)/i },
    // 餅乾: biscuits, cookies, crackers, rice cakes
    sub_biscuits: { cats: ['snacks'],
        inc: /\b(biscuits?|bikkies|cookies?|crackers?|tim\s*tams?|timtams|arnott'?s|oreos?|shapes|jatz|ritz|clix|vita-?weat|cruskits?|salada|sao|water\s*crackers|rice\s*crackers|rice\s*cakes?|corn\s*thins|digestives?|scotch\s*finger|wagon\s*wheels|monte\s*carlo|kingston|tee\s*vee|teevee|mint\s*slice|gingernut|shortbread|biscotti|wafers?|tiny\s*teddy|anzac|macarons?|biscoff|speculoos|speculaas|shortcake|delta\s*cream|milk\s*arrowroot|jaffa\s*cakes|hobnobs|mcvitie'?s|grissini|crustini|breadsticks|lavosh|crispbread|ryvita|savoy|pocky|yan\s*yan|hello\s*panda|koala'?s\s*march|toppo|le\s*snak|fruit\s*pillows|nice\b|marie|rusks?|stroopwafels?|lebkuchen|gingerbread|madeleines?|amaretti|cantuccini|florentines?)\b/i,
        exc: /\b(bars?|muesli|popcorn|cereal|chocolate\s*block|lollies)\b/i },
    // 糖果軟糖: lollies, gummies, mints, gum
    sub_lollies: { cats: ['snacks'],
        inc: /\b(lollies|lolly|lollipops?|gumm(?:y|ies)|jelly\s*(?:beans?|babies|snakes?|tots)|snakes|marshmallows?|licorice|liquorice|confectionery|candy|candies|mints?|mentos|chupa\s*chups|chewing\s*gum|gum|eclairs|allen'?s|sour\s*patch|skittles|haribo|starburst|maoam|fruit\s*tingles|minties|fantales|kool\s*mints|tic\s*tac|eclipse|extra\s*(?:gum|peppermint|spearmint|white)|life\s*savers|wizz\s*fizz|sherbet|pascall|sweetmans|fizzers|redskins|chicos|party\s*mix|milk\s*bottles|clinkers|columbines|toffees?|butterscotch|nerds|warheads|trolli|roll[- ]?ups|fruit\s*(?:bursts|sticks|straps)|sour\s*straps?|pez|freckles|chewy|fairy\s*floss|candy\s*canes?|nougat|turkish\s*delight|bubble\s*gum|jubes|pastilles|black\s*cats|jelly|snakes\s*alive|cola\s*bottles|strawberries\s*&\s*cream|fudge|caramels?|lifesavers|smurfs|natural\s*confectionery|squishies|fruity|sour)\b/i,
        exc: /\b(bars?|biscuits?|cookies?|nuts?|popcorn|chips|crackers?|protein|trail\s*mix|muesli|yogh?urt\s*coated)\b/i },
    // 能量・運動飲料
    sub_energy: { cats: ['drinks'],
        inc: /\b(energy|red\s*bull|monster|v\s*(?:green|blue|sugar\s*free|zero|refresh|original)|mother|rockstar|celsius|guru|prime\s*(?:hydration|energy)|gatorade|powerade|sports?\s*drinks?|electrolyte|hydration|maximus|musashi|c4|g\s*fuel|lucozade|staminade|mizone|hydralyte|isotonic|pre[- ]?workout)\b/i,
        exc: /\b(tablets?|gummies|capsules?)\b/i },
    // 茶・沖泡: tea, iced tea, Milo, hot chocolate
    sub_tea: { cats: ['drinks'],
        inc: /\b(teas?|tea\s*bags?|twinings|lipton|dilmah|bushells|tetley|madura|t2|nerada|chai|matcha|herbal|infusions?|rooibos|chamomile|peppermint|earl\s*grey|english\s*breakfast|oolong|jasmine|hot\s*chocolate|drinking\s*chocolate|cocoa|milo|ovaltine|aktavite|horlicks|malted|swiss\s*miss|nesquik\s*(?:powder|chocolate\s*powder|syrup|\d+\s*g)|sachets)\b/i,
        exc: /\b(tea\s*towels?|tea\s*lights?|tea\s*tree|kombucha|ready\s*to\s*drink\s*milk)\b/i },
    // 牛奶: drinking milk (fresh, long-life, lactose free, plant), flavoured milk, Up&Go
    sub_milk: { cats: ['dairy_eggs', 'drinks'],
        inc: /\b(milks?|m\*lk|long\s*life|uht|up\s*&?\s*go|liquid\s*breakfast|breakfast\s*drink|oak|big\s*m|moove|masters|breaka|yakult|vitasoy|so\s*good|bonsoy|alpro|oatly|minor\s*figures|almond\s*breeze|milklab|pura|norco|milkshakes?|smoothies?|kefir|lassi|protein\s*(?:drink|shake)|cultured\s*drink|probiotic\s*drink)\b/i,
        exc: /\b(chocolate\s*block|condensed|evaporated|powder|powdered|coconut\s*milk|coconut\s*cream|milk\s*arrowroot|biscuits?|cookies?|milk\s*bottles|bread|buns?|cheese|butter|yogh?urts?(?!\s*(?:drink|smoothie))|custard|cream\s*cheese|cereal|frozen|formula|toddler|infant|dessert|pudding|kefir\s*grains)\b/i },
    // 早餐穀片・抹醬: cereal, oats, muesli, peanut butter, jam, Vegemite, honey, Nutella
    sub_breakfast: { cats: ['pantry'],
        inc: /\b(cereals?|oats|oat\s*(?:sachets|porridge|bran|clusters)|porridge|muesli|granola|weet-?bix|weeties|corn\s*flakes|nutri-?grain|coco\s*pops|rice\s*bubbles|special\s*k|sultana\s*bran|all[- ]bran|just\s*right|froot\s*loops|cheerios|crunchy\s*nut|mini\s*wheats|kellogg'?s|sanitarium|carman'?s|be\s*natural|peanut\s*butter|nut\s*butter|almond\s*butter|cashew\s*butter|jams?|marmalade|conserve|vegemite|promite|marmite|honey|maple\s*syrup|golden\s*syrup|nutella|hazelnut\s*spread|chocolate\s*spread|biscoff\s*spread|spreads?|lemon\s*curd|pancake\s*(?:mix|shake|syrup)|shake\s*(?:&|n)\s*bake|breakfast)\b/i,
        exc: /\b(bars?|bites?|balls?|honey\s*(?:soy|mustard|garlic|bbq|chicken|joys|roasted|prawns?)|cheese\s*spread|dip|sauce|bowls?|seasoning|marinade)\b/i },
    // 罐頭・湯品: canned fish / beans / tomatoes / fruit, soup, coconut milk
    sub_canned: { cats: ['pantry'],
        inc: /\b(canned|tinned|cans?|tins?|tuna|sardines|mackerel|salmon|john\s*west|sirena|greenseas|safcol|baked\s*beans|beanz|heinz\s*(?:beans|spaghetti|big\s*red)|campbell'?s|cup\s*a\s*soup|soups?|broth|chowder|ramen\s*broth|diced\s*tomatoes|crushed\s*tomatoes|whole\s*(?:peeled\s*)?tomatoes|chopped\s*tomatoes|peeled\s*tomatoes|cherry\s*tomatoes|chickpeas|kidney\s*beans|four\s*bean|three\s*bean|black\s*beans|cannellini|butter\s*beans|borlotti|lentils|corn\s*kernels|creamed\s*corn|sweet\s*corn|beetroot|spc|ardmona|goulburn\s*valley|fruit\s*(?:cups|snack\s*pots|in\s*(?:juice|jelly|syrup))|peach(?:es)?\s*(?:slices|halves|in|\d)|peaches|pears\s*(?:in|halves|diced)|pineapple|mandarin\s*segments|two\s*fruits|fruit\s*salad|spam|corned\s*beef|luncheon|fray\s*bentos|stagg|coconut\s*(?:milk|cream)|in\s*(?:spring\s*water|brine|olive\s*oil|oil|tomato))\b/i,
        exc: /\b(kits?|noodles?|crackers?|rice\s*(?:\d|cups?|pouch)|seasoning|sauce\s*\d|stock|paste|loose|fresh|tripod|mounts?)\b/i },
    // 米・麵粉烘焙: rice, grains, flour, sugar, baking
    sub_rice: { cats: ['pantry'],
        inc: /\b(rice|jasmine|basmati|calrose|arborio|sunrice|quinoa|couscous|cous\s*cous|polenta|semolina|barley|flour|self[- ]raising|bread\s*mix|cake\s*mix|muffin\s*mix|brownie\s*mix|cookie\s*mix|slice\s*mix|baking|bicarb\w*|cornflour|yeast|sugar|caster|icing|sweetener|stevia|equal|natvia|cocoa\s*powder|cooking\s*chocolate|choc\s*(?:bits|melts|chips)|melts|vanilla\s*(?:essence|extract|bean)|essence|food\s*colou?r\w*|sprinkles|hundreds\s*(?:&|and)\s*thousands|desiccated|shredded\s*coconut|coconut\s*flakes|condensed\s*milk|evaporated\s*milk|custard\s*powder|jelly\s*(?:crystals|mix)|aeroplane|white\s*wings|edmonds|green'?s|betty\s*crocker|queen|breadcrumbs|panko|sultanas|raisins|currants|chia|flaxseed|linseed|lsa|almond\s*meal|meal\b|glace|gelatine|pastry\s*mix|scone\s*mix|pikelet|cake\s*decorat\w*)\b/i,
        exc: /\b(rice\s*(?:crackers?|cakes?|chips|bubbles|malt|paper|vinegar|wine|noodles?|pudding|crisps|bran\s*oil)|kits?|cups?|pouch|microwave|ready|fried\s*rice|seasoning|sauce|curry|risotto\s*(?:\d|sides)|sides|meal\s*base|soup)\b/i },
    // 清潔・洗碗: dishwashing, surfaces, toilet, air freshener, insect spray
    sub_cleaning: { cats: ['household'],
        inc: /\b(dishwash\w*|dishwasher|dish\s*(?:liquid|wash|soap|tablets?|brush)|washing\s*up|rinse\s*(?:aid|&\s*shine)|finish|^fairy|morning\s*fresh|toilet\s*(?:clean\w*|gel|blocks?|discs?|rim|brush)|in\s*the\s*bowl|bleach|disinfect\w*|antibacterial|surface|multi-?purpose|cleaning|cleaner|cleanser|degreaser|mould|mold|spray\s*(?:&|n)\s*wipe|glen\s*20|ajax|harpic|bref|domestos|^duck|pine\s*o\s*cleen|easy[- ]off|white\s*king|jif|mr\s*muscle|dettol|exit|shower\s*power|chux|vileda|scotch-?brite|sponges?|scourers?|mops?|brooms?|dustpan|gloves|wipes|air\s*fresh\w*|reed\s*diffuser|diffuser|air\s*wick|ambi\s*pur|febreze|glade|odou?r|deodoris\w*|candles?|insect|fly\s*spray|mortein|raid|baygon|cockroach|ants?|pest|repellent|aerogard|bushman|lint|mosquito|scent(?:ed)?\s*(?:oil|spray)|fresh\s*matic|plug[- ]?in|drain|unblock\w*|oven\s*clean\w*|stove|carpet|window\s*clean\w*|glass\s*clean\w*|floor\s*(?:clean\w*|wipes)|steel\s*wool|cloths?|microfibre)\b/i,
        exc: /\b(laundry|lamps?|lights?|led|vacuum|robot|stick\s*vac|steam\s*mop\s*(?:\d|pro)|car|motor|bbq\s*cover|garden|hair|olia|brite|mcobeauty|makeup)\b/i },
    // 紙品・保鮮: toilet paper, tissues, paper towel, bin bags, foil, cling wrap
    sub_paper: { cats: ['household'],
        inc: /\b(toilet\s*(?:paper|tissue|rolls?)|bathroom\s*tissue|tissues?|paper\s*towels?|kitchen\s*(?:towels?|rolls?)|serviettes|napkins|quilton|sorbent|kleenex|viva|handee|cottonelle|who\s*gives\s*a\s*crap|garbage\s*bags?|bin\s*liners?|rubbish\s*bags|kitchen\s*tidy|bin\s*bags|cling\s*wrap|plastic\s*wrap|foil|baking\s*paper|freezer\s*bags?|sandwich\s*bags?|snap\s*lock|zip\s*(?:lock|bags?)|resealable|glad|multix|albal|paper\s*(?:plates|cups|bags)|bin\s*bags|wrap\s*\d+m|oven\s*bags|lunch\s*bags|zipper\s*bags|storage\s*bags)\b/i,
        exc: /\b(cleaner|cleaning|wipes|holder|dispenser|bin\s*\d+\s*l|pedal\s*bin|bins?\b(?!\s*(?:liners?|bags?)))\b/i },
    // SIM卡・儲值: prepaid SIM starter kits and recharges (what every new arrival needs first)
    sub_mobile: { cats: ['household'],
        inc: /\b(sim|prepaid|pre-paid|starter\s*(?:pack|kit)|recharge)\b|\$\d+\s*(?:pre-?paid|plan|pack|kit)\b|^(?:boost|lebara|lyca|amaysim|belong|dodo|vodafone|aldimobile)\b/i,
        exc: /\b(boost(?:er)?\s*(?:beads|juice|bars?)|card\s*reader|sim\s*card\s*tray|router|modem)\b/i },
    // Personal care, split
    sub_oral: { cats: ['health_vitamins'], exc: /\b(fairy\s*floss|lip)\b/i,
        inc: /\b(tooth\w*|mouthwash|mouth\s*(?:rinse|wash|spray)|dental|floss\w*|interdental|denture|polident|steradent|colgate|oral[- ]?b|sensodyne|macleans|listerine|white\s*glo|plax|teeth|whitening|gum\s*care|orthodontic)\b/i },
    sub_feminine: { cats: ['health_vitamins', 'household'],
        inc: /\b(tampons?|pads?|liners?|period|incontinence|bladder|depend|poise|tena|kotex|libra|carefree|stayfree|modibodi|thinx|tom\s*organic|menstrual|maternity|sanitary)\b/i,
        exc: /\b(cotton\s*pads|cleans\w*\s*pads|makeup|make-up|eye|lip|brow|walking|light\s*pad|bench|boot|hot\s*plate|multimedia|nursing\s*pads|breast|pad\s*cleaner|scourer|scrub|mouse|heat\s*pads?|chair|knee|shoe|lip\s*liners?|eye\s*liners?|nappy\s*liners)\b/i },
    sub_baby: { cats: ['health_vitamins', 'pantry', 'dairy_eggs', 'snacks', 'household', 'drinks'],
        inc: /\b(nappy|nappies|babylove|huggies|baby|babies|curash|little\s*one'?s|rafferty'?s|bellamy'?s|aptamil|karicare|s-?26|toddler|infant|(?:infant|toddler|baby)\s*formula|formula\s*(?:stage|step)|kiddylicious|mumamoo|whole\s*kids|bubs|only\s*organic|purees?|teeth(?:ing)?\s*(?:gel|rusks)|wipes\s*(?:sensitive|fragrance\s*free|\d+\s*pack)\b(?=.*\b(?:water|baby|sensitive)\b)|sleepy\s*nights|dry\s*nites|pull[- ]?ups|johnson'?s\s*baby|sudocrem|\d+\+?\s*months?)\b/i,
        exc: /\b(baby\s*(?:spinach|carrots?|cos|potatoes?|qukes|cucumbers?|corn|leaves|beetroot|bok\s*choy|broccoli|capsicums?|tomatoes?|rocket|kale|chats|octopus|squid|calamari|back\s*ribs|shampoo\s*conditioner\s*for\s*dogs)|babybel|oh\s*baby|baby\s*(?:face|pink|blue|doll|lips)|body\s*care|dog|cat|puppy|kitten|oil\s*\d+\s*ml(?=.*\bmassage\b)|baby\s*(?:oil|powder)\s*(?=.*\bbody\b))\b/i },
    sub_hair: { cats: ['health_vitamins'],
        inc: /\b(shampoo|conditioner|co-?wash|hair\w*|leave[- ]in|detangl\w*|frizz|curls?|curly|styling|mousse|pomade|texturis\w*|texture\s*spray|beach\s*spray|sea\s*salt\s*spray|root|colourant|colorant|dye|keratin|bond\s*repair|scalp|scrunchies|claws?|clips?|ties|headbands?|bobby\s*pins|brush|comb|pantene|head\s*&\s*shoulders|herbal\s*essences|tresemm[eé]|schwarzkopf|clairol|hask|ogx|sunsilk|fructis|got2b|toni\s*&\s*guy|elvive|nice\s*'?n\s*easy|my\s*soda|olaplex|kristin\s*ess|garnier\s*(?:olia|nutrisse|colour)|l'or[eé]al\s*(?:excellence|preference|casting|elvive)|wax\s*stick|gel\s*\d+\s*(?:ml|g)\b(?=.*\bhair\b))\b/i,
        exc: /\b(mascara|lash\w*|3[- ]?in[- ]?1|hand\s*wash|kava|hair\s*removal|remover|removing|laser|ipl|trimmer|shaver|shaving|razors?|waxing|wax\s*strips|epilator|tooth\w*|makeup\s*brush|brows?|eyebrow|lash\w*|body\s*(?:wash|lotion|spray)|fragrance\s*mist|body\s*mist|hair\s*(?:&|and)\s*body\s*(?:wash|mist)|blush|foundation|skin\s*(?:&|and)\s*nails?|tablets?|gummies|capsules?|toilet|dish|nail\s*brush|bath\s*brush|body\s*brush|exfoliating\s*brush)\b/i },
    sub_makeup: { cats: ['health_vitamins'],
        inc: /\b(makeup|make-up|mascara|eyeliner|eye\s*liner|eyeshadow|eye\s*shadow|eyebrow|brows?|lash\w*|concealer|foundation|bb\s*cream|cc\s*cream|skin\s*tint|tinted|primer|setting\s*(?:spray|powder|mist)|pressed\s*powder|loose\s*powder|powder|bronz\w*|contour|blush\w*|highlighter|luminis\w*|illuminat\w*|lip\s*(?:stick|gloss|liner|stain|tint|plump\w*|colou?r|crayon|oil|balm|treatment|whip|conditioner|butter|mask|scrub|care)|lips?|lipstick|lipcolor|balm\s*\d+\s*g|blistex|chapstick|carmex|lucas\s*papaw|papaw|nail\w*|cuticle|manicure|press[- ]on|polish|makeup\s*remover|beauty\s*blender|sponges?|tweezers|revlon|rimmel|mcobeauty|maybelline|covergirl|max\s*factor|essence|nyx|elf|sally\s*hansen|ardell|models\s*prefer|poni|1000\s*hour|fragrance|perfume|eau\s*de|parfum|cologne|edt|edp|glitter|gloss)\b/i,
        exc: /\b(body\s*polish|fragrance\s*free|fine\s*fragrance|hair\s*(?:dye|colou?r)|colorsilk|permanent|body\s*(?:spray|wash|lotion|oil|butter|scrub|cream)|deodorant|antiperspirant|shampoo|conditioner|sunscreen|spf\s*50|talc|baby\s*powder|foot\s*powder|protein\s*powder|wash\s*powder)\b/i },
    sub_skincare: { cats: ['health_vitamins'],
        inc: /\b(skin\s*care|skincare|face|facial|serum|moisturi[sz]\w*|cleans\w*|micellar|toner|exfoliat\w*|peel|retinol|niacinamide|hyaluronic|ceramide|eye\s*(?:cream|gel|patch\w*|serum)|night\s*cream|day\s*cream|creme|crème|cream|mask\w*|pimple|blemish|acne|spot|pores?|blackhead|sunscreen|sun\s*screen|spf\s*\d+|spf|sun\s*protect\w*|after\s*sun|aloe|self[- ]tan\w*|tanning|tan\b|bronzing\s*(?:mousse|lotion|foam)|bondi\s*sands|banana\s*boat|cancer\s*council|le\s*tan|olay|neutrogena|cetaphil|cerave|la\s*roche|bioderma|ponds|sukin|natio|skin\s*republic|derm\w*|eulactol|sorbolene|qv|bio-?oil|rosken|dermaplan\w*|scar|stretch\s*marks?|wrinkle|anti[- ]?ag\w*|brightening|glow|vaseline\s*(?:lip|petroleum|original\s*jelly)|petroleum\s*jelly|lotion|body\s*(?:lotion|butter|cream|oil)|hand\s*cream|heel\s*balm|foot\s*(?:cream|peel|mask)|balm)\b/i,
        exc: /\b(hand\s*wash|body\s*wash|shower|bath|soap|bar\b|shaving|shave\s*cream|deodorant|antiperspirant|roll[- ]?on)\b/i },
};
// Products no rule above names stay together under their department's catch-all tag
// (snacks -> 堅果・其他零食, drinks -> 果汁・飲用水, household -> 居家雜貨…). Departments that are
// already one simple shelf (肉品, 海鮮, 蔬果, 麵包, 酒類, 寵物) use the department key itself.
const DEPT_DEFAULT_TAG = {
    produce: 'produce', meat: 'meat', seafood: 'seafood', bakery: 'bakery', liquor: 'liquor', pet: 'pet',
    dairy_eggs: 'sub_dairy', frozen: 'sub_frozen', pantry: 'sub_pantry', snacks: 'sub_snacks',
    drinks: 'sub_drinks', health_vitamins: 'sub_body', household: 'sub_home',
};
// The browse groups shown on the first row of the category menu; each tag belongs to exactly one.
const TAG_GROUPS = [
    { key: 'g_quick',  tags: ['sub_quickmeals', 'sub_noodles', 'sub_pasta', 'sub_frozen'] },
    { key: 'g_sweets', tags: ['sub_icecream', 'sub_chocolate', 'sub_chips', 'sub_biscuits', 'sub_lollies', 'sub_snacks'] },
    { key: 'g_drinks', tags: ['sub_soda', 'sub_coffee', 'sub_tea', 'sub_energy', 'sub_drinks', 'liquor'] },
    { key: 'g_fresh',  tags: ['meat', 'seafood', 'produce', 'sub_milk', 'sub_dairy', 'bakery'] },
    { key: 'g_cook',   tags: ['sub_rice', 'sub_pantry', 'sub_canned', 'sub_breakfast'] },
    { key: 'g_home',   tags: ['sub_laundry', 'sub_cleaning', 'sub_paper', 'sub_mobile', 'sub_home'] },
    { key: 'g_care',   tags: ['sub_vitamins', 'sub_hair', 'sub_body', 'sub_oral', 'sub_skincare', 'sub_makeup', 'sub_feminine', 'sub_baby'] },
    { key: 'g_pet',    tags: ['pet'] },
];
const TAG_GROUP_OF = {};
TAG_GROUPS.forEach(g => g.tags.forEach(t => { TAG_GROUP_OF[t] = g.key; }));
// ---------- Strong signals, checked BEFORE everything else and across departments ----------
// A brand or product type that settles the tag on its own, whichever department the product was
// filed under (e.g. "Clearasil cream" filed as dairy, "Weet-Bix Bites" filed as pantry, a phone
// handset next to the SIM cards, a "Lemon" soft drink filed as fruit). First match wins.
// cats = only from these departments (optional); exc = words that cancel the rule.
const FOOD_CATS = ['produce', 'meat', 'seafood', 'dairy_eggs', 'bakery', 'frozen', 'pantry', 'snacks', 'drinks', 'liquor', 'household'];
const TAG_OVERRIDES = [
    // ----- not groceries at all (toys, gadgets, containers, phones) -----
    { tag: 'sub_home', cats: [...FOOD_CATS, 'health_vitamins'],
      inc: /\b(nintendo|blind\s*egg|panzer\s*glass|apple\s*watch|startech|ogg\s*labs|phoenix\s*model|little\s*town|melii|crofton|audo\b|burger\s*maker|tea\s*set|elmer'?s|slime|air\s*fryer|air\s*purifier|coffee\s*machine|espresso\s*machine|capsule\s*machine|screen\s*protector|tempered\s*glass|tripod|plush|wooden\s*(?:toys?|kitchen|food)|grinders?\s*set|salt\s*(?:&|and)\s*pepper\s*grinders?|containers?|canisters?|lunch\s*box(?:es)?(?!\s*(?:multipack|\d|snack|pack))|bento|oven\s*gloves|oil\s*sprayer|floor\s*mat|gardening\s*gloves|led\s*candle|candle\s*(?:bulb|globe|led)|food\s*cover|tissue\s*box\s*cover|optus\s*x-|telstra\s*(?:t-|galaxy)|samsung\s*galaxy|galaxy\s*a\d+|iphone|smartphone|handset|modem|walking\s*pad|light\s*pad|multimedia\s*pad|bench\s*pad|boot\s*liner|hot\s*plate\s*liners?|hair\s*dryer|hot\s*air\s*brush|straightener|curling\s*(?:iron|wand))\b/i,
      exc: /\b(snack\s*bags?|zip|cling|foil)\b/i },
    // ----- personal care -----
    { tag: 'sub_vitamins', cats: ['health_vitamins', 'snacks', 'drinks', 'pantry', 'household', 'dairy_eggs', 'produce'],
      inc: /\b(protein\s*(?:powder|isolate|blend|\d+\s*(?:g|kg))|whey|wpi|casein|creatine|pre[- ]?workout|thermogenic|carnitine|eaa'?s|bcaa'?s?|testosterone|oxyshred|shred\s*gummies|weight\s*loss\s*shake|burn\s*&\s*energy|fat\s*(?:metaboli[sz]er|burner)|fatblaster|the\s*(?:lady|man)\s*shake|bsc\s*(?:protein|whey|hydroxyburn)|musashi\s*(?:\d|protein\s*powder|whey|bulk|high\s*protein\s*powder|shred)|muscle\s*nation\s*(?:protein|whey|custard|100%)|muscletech|famous\s*nutrition|gym\s*bod|instant\s*protein|vital\s*strength|elastoplast|band-?aids?|plasters|ointment|antiseptic|first\s*aid|bandages?|mylanta|belly\s*me|pain\s*away|amazonia\s*fibre|sup\s+(?:creatine|pre-?workout|testosterone|5\s*hour|shred))\b/i,
      exc: /\b(peanut\s*butter\s*cups?|cups?|bars?|cookies?|chips|crisp|balls?|protein\s*(?:drink|water|milk|yogh?urt|ice)|ready\s*to\s*drink|rtd|daily\s*shake)\b|\bprotein\b.*\b\d+\s*ml\b/i },
    { tag: 'sub_energy', inc: /\b(energy\s*gels?|g\s*active|rehydraid)\b/i },
    { tag: 'sub_body', cats: ['health_vitamins', 'household'],
      inc: /\b(veet|nad'?s|oneblade|razors?|razor\s*blades|blades\s*\d|shav\w*|dermaplan\w*|defuzz\w*|hair\s*removal|wax\s*strips|epilat\w*|beard|after\s*shave|aftershave|post[- ]shave|body\s*(?:&|and)\s*face\s*wash|body\s*(?:polish|scrub)|3[- ]?in[- ]?1\s*(?:body|hair|wash)|insect\s*repellent\s*(?:lotion|roll|pump)|personal\s*insect)\b/i },
    { tag: 'sub_oral', cats: ['health_vitamins'], inc: /\b(hismile|teeth|tooth\w*)\b/i, exc: /\b(teething)\b/i },
    { tag: 'sub_makeup', cats: ['health_vitamins'], inc: /\b(lip\s*(?:balm|conditioner|care)|chapstick|blistex|carmex|lucas\s*papaw)\b/i },
    { tag: 'sub_makeup', cats: ['health_vitamins', 'household', 'dairy_eggs'],
      inc: /\b(eye\s*liner|eyeliner|lip\s*liner|brow\s*liner|auto\s*liner|kohl|mascara|lash\s*curler|eyelash|lashes|brows?|eyebrows?|brow\s*(?:gel|pencil|pomade|wax|kit|lamination|tint)|makeup\s*brush\w*|brush\s*set|blender\s*sponges?|beauty\s*blender|lip\s*(?:balm|oil|gloss|stick|stain|tint|plump\w*|treatment|whip|conditioner|butter|mask|scrub|care|colou?r|liner|crayon)|lipstick|chapstick|blistex|carmex|lucas\s*papaw|maybelline|fairy\s*floss|fragrance\s*mist|body\s*mist|perfume|eau\s*de|parfum|cologne|edt|edp|nail\s*polish|nail\s*colou?r|press[- ]on\s*nails|foundation|concealer|bb\s*cream|cc\s*cream|skin\s*tint|primer|bronzer|contour|blush(?!\s*(?:hair|dye))|highlighter|setting\s*(?:spray|powder|mist))\b/i,
      exc: /\b(spf|sunscreen|hair\s*(?:dye|colou?r)|permanent|colorsilk|deodorant|antiperspirant|fine\s*fragrance\s*(?:deo|anti)|room|reed|candle|air|toothbrush|hair\s*brush|paddle\s*brush|body\s*brush|dish\s*brush|eyebrow\s*razor|brow\s*razor|razor|shav\w*)\b/i },
    { tag: 'sub_hair', cats: ['health_vitamins', 'household', 'drinks', 'dairy_eggs', 'pantry', 'bakery'],
      inc: /\b(magic\s*retouch|root\s*(?:touch|cover|concealer)|retouch|batiste|dry\s*shampoo|elnett|got2b|john\s*frieda|grow\s*(?:thicker|bomb)|growth\s*bomb|colorsilk|hair\s*(?:dye|colou?r|mask|serum|oil|spray|gel|wax|mousse|treatment|mist|brush|clips?|ties)|scalp|volume\s*powder|shine\s*gloss|heat\s*protect\w*|elvive|dove\s*damage\s*therapy|ogx|people\s+\w+\s*(?:spray|paste|powder|clay|wax|cream)|olia|briteplex|brite\s*white\s*toner|paddle\s*brush|radial\s*brush|toni\s*&\s*guy|bun\s*(?:roller|donut)|shea\s*moisture|curl\s*(?:smoothie|cream|defin\w*)|(?:oat\s*milk|coconut\s*milk)\s*(?:shampoo|conditioner))\b/i,
      exc: /\b(body\s*wash|hand\s*wash|3[- ]?in[- ]?1|hair\s*(?:&|and)\s*body|tablets?|gummies|capsules?|hair\s*removal|lash\w*|mascara)\b/i },
    { tag: 'sub_skincare', cats: ['health_vitamins', 'dairy_eggs', 'pantry', 'drinks', 'household'],
      inc: /\b(spf\s*\d+|spf|sunscreen|zinc\s*stick|sun\s*kids|nivea\s*sun|protect\s*&\s*play|soft\s*cr[eè]me|sun\s*screen|sun\s*(?:lotion|protect\w*|cream)|after\s*sun|makeup\s*remover|micellar|cleanser|cleansing|charcoal\s*(?:wash|scrub)|water\s*cream|face\s*cream|day\s*cream|night\s*cream|toner|serum|essence\s*water|moistur\w*|sheet\s*mask|face\s*mask|pimple|mighty\s*patch|eye\s*(?:cream|bag|gel|patch\w*)|face\s*wash|facial|clearasil|cosrx|mixa|essano|beauty\s*of\s*joseon|rosehip\s*oil|retinol|niacinamide|hyaluronic)\b/i,
      exc: /\b(hair|shampoo|conditioner|body\s*(?:wash|scrub|polish)|shower|hand\s*wash|lip|primer|foundation|concealer|tint\w*|bb\s*cream|cc\s*cream|bronz\w*|blush|mascara|setting|baby|infant|mixa\s*body\s*milk)\b/i },
    // ----- baby food & care (stage / months / baby brands) -----
    { tag: 'sub_baby', cats: ['pantry', 'dairy_eggs', 'drinks', 'snacks', 'produce', 'health_vitamins', 'household'],
      inc: /\b(\d+\s*m\+|\d+\s*months?\+?|stage\s*[1-4]|little\s*bellies|bubs|rafferty'?s|whole\s*kids|fruit\s*puree\s*pouch(?:es)?|purees?\s*pouch|baby\s*(?:food|cereal|snacks?|rice|porridge|wipes|wash|shampoo|lotion|sunscreen)|toddler\s*(?:milk|formula|snacks?)|infant\s*formula|sippy)\b/i,
      exc: /\b(dog|cat|puppy|kitten|baby\s*(?:spinach|carrots?|cos|potatoes?|qukes|cucumbers?|corn|leaves|beetroot|bok\s*choy|broccoli|capsicums?|tomatoes?|rocket|kale|octopus|back\s*ribs))\b/i },
    // ----- quick meals -----
    { tag: 'sub_pasta', cats: ['frozen', 'pantry', 'meat', 'dairy_eggs'],
      inc: /\b(ravioli|agnolotti|tortellini|tortelloni|gnocchi|cannelloni|pasta\s*sauce|on\s*the\s*menu\s*fresh\b.*\bsauce)\b/i,
      exc: /\b(soup|salad|bake\s*\d)\b/i },
    { tag: 'sub_quickmeals', cats: ['frozen', 'pantry', 'meat', 'dairy_eggs', 'snacks'],
      inc: /\b(lean\s*cuisine|ruffie|microwave\s*(?:rice|pouch|meals?)|rice\s*cups?|rice\s*pouch|lunch\s*bowl|ben'?s\s*original\s*(?:one\s*pan|special\s*fried|taste\s*of)|nasi\s*goreng\s*rice|sunrice\s*(?:protein\+?|plain\s*rice\s*cups|microwave)|(?:beef|chicken|vegetable|veg|simply\s*beef)\s*lasagne(?!\s*sheets))\b/i,
      exc: /\b(chips|crackers?|cakes?|\d+\s*kg|sheets|sauce\s*\d)\b/i },
    // ----- breakfast, baking -----
    { tag: 'sub_rice', cats: ['pantry', 'snacks', 'bakery', 'frozen', 'dairy_eggs'],
      inc: /\b((?:cookie|cake|cupcake|cheesecake|brownies?|muffins?|slice|pancake|scone|pikelet|bread)\s*mix|cake\s*in\s*a\s*cup|jumbl'?d|green'?s\s*(?:deluxe|gf|traditional|lemon))\b/i },
    { tag: 'sub_breakfast', cats: ['pantry', 'snacks', 'household'],
      inc: /\b(weet-?bix(?!\s*go)|fruity\s*bites|uncle\s*tobys\s*(?:plus|oats|quick\s*oats)|oats\s*big\s*bowl|(?:peanut|nut|cashew|almond)\s*(?:butter|spread)|creamy\s*caramel\s*spread)\b/i,
      exc: /\b(bars?|balls?|smooshed|drink|cups?|bites\s*(?:bar|snack)|cookies?|chocolate\s*block)\b/i },
    { tag: 'sub_milk', inc: /\b(up\s*&\s*go|up&go|yakult|kefir|daily\s*shake|so\s*good\s*(?:almond|soy|oat|barista|high\s*protein)|almond\s*(?:milk|barista)|protein\s*milk)\b/i, exc: /\b(kefir\s*grains)\b/i },
    // ----- sweets & snacks -----
    { tag: 'sub_icecream', cats: ['frozen', 'dairy_eggs', 'snacks'],
      inc: /\b(yo-?chi|frozen\s*yogh?urt|choc(?:olate)?\s*bar\s*sticks|mixed\s*pack\s*pops|pops\s*\d+\s*(?:pk|pack))\b/i },
    { tag: 'sub_chips', cats: ['snacks', 'pantry', 'dairy_eggs', 'household', 'produce', 'frozen'],
      inc: /\b(nongshim\s*(?:onion\s*rings|shrimp|honey\s*twist|banana\s*kick|snack\w*)|harvest\s*snaps|calbee|temole|infuzions|tostitos|veggie\s*(?:straws|rings)|shrimp\s*(?:chips|crackers)|prawn\s*crackers|twisties|turtle\s*chips|corn\s*puffs|broccoli\s*puffs|cauliflower\s*puffs|sunrice\s*protein\s*chips|twist\s*snack)\b/i,
      exc: /\b(frozen|mccain|birds\s*eye|\d\s*kg)\b/i },
    { tag: 'sub_frozen', cats: ['snacks'], inc: /\b(frozen|crumbed\s*chicken\s*chips)\b/i, exc: /\b(yogh?urt\s*(?:coated|bites)|freeze[- ]?dried)\b/i },
    { tag: 'sub_snacks', cats: ['snacks', 'pantry', 'household', 'meat', 'bakery', 'dairy_eggs', 'drinks', 'health_vitamins', 'produce'],
      inc: /\b(muesli\s*bars?|cereal\s*bars?|lcms?|quest\b|protein\s*(?:bar|crisp|balls?)|energy\s*bar|fibre\s*one|smooshed|nice\s*&\s*natural|haldiram'?s|bhuja|trek\b|biltong|jerky|health\s*lab|oaty\s*slices|messy\s*monkeys|rice\s*puff\s*bars?|nutri-?grain\s*bars?|rice\s*cakes?\s*(?:yogh?urt)|peanut\s*butter\s*cups|konjac\s*jelly)\b/i,
      exc: /\b(cookies?\s*mix|frozen)\b/i },
    { tag: 'sub_biscuits', cats: ['snacks', 'frozen', 'dairy_eggs', 'bakery', 'meat', 'household', 'pantry'],
      inc: /\b(shapes|ritz|crackers?|corn\s*thins|rice\s*cakes?|koala'?s\s*march|zimtsterne|hugos\s*bombs|meiji|crostini|crustini|grissini|chickadees|jumbl'?d\s*cookies)\b/i,
      exc: /\b(prawn\s*crackers|shrimp\s*crackers|dog|cat|cracker\s*barrel|nut\s*cracker|bhuja|haldiram|mix\b|cookies?\s*mix)\b/i },
    { tag: 'sub_chocolate', cats: ['snacks', 'liquor', 'dairy_eggs', 'pantry'],
      inc: /\b(twix|mars\s*bar|hershey'?s|cookies\s*n\s*cr[eè]me\s*bar|mozartkugeln|well\s*naturally\s*(?:bars?|no\s*sugar|milk|dark)|rum\s*(?:kugeln|balls)|baumkuchen|lebkuchen)\b/i,
      exc: /\b(ice\s*cream|frozen|sticks|slice\s*mix|biscuits?\s*\d+\s*g\s*(?:pack|\d+\s*pack))\b/i },
    { tag: 'sub_lollies', cats: ['snacks', 'bakery', 'produce', 'household', 'pantry'],
      inc: /\b(allsorts|lolliland|zappo|millions|sour\s*straps?|jellies|raspberry\s*twists|roll[- ]?ups|snakes|squashies|swizzels)\b/i,
      exc: /\b(choc\w*|chocolate\s*(?:coated|covered))\b/i },
    // ----- drinks -----
    { tag: 'sub_tea', cats: ['drinks', 'health_vitamins', 'pantry'], inc: /\b(ovaltine|hot\s*choc\b|hot\s*chocolate|kava)\b/i },
    { tag: 'sub_soda', cats: ['drinks', 'household', 'produce', 'pantry'],
      inc: /\b(jarritos|fever-?tree|bundaberg\s*mixed|zinda|solo\b(?!\s*energy))\b/i },
    { tag: 'liquor', cats: ['household', 'produce', 'drinks', 'pantry'],
      inc: /\b(kirin\s*hyo\w*|fireball|ros[eé]\b.*\b750\s*ml|pacific\s*ale|mid\s*strength|newtowner|young\s*henrys|lorry\s*boys|smithy'?s|bone\s*dry|champteloup)\b/i },
    // ----- fresh -----
    { tag: 'produce', cats: ['household'], inc: /\b(broccolini|asparagus|pumpkin|loose\s*sweet\s*corn)\b|\bbunch\b/i },
    { tag: 'produce', cats: ['pantry'], inc: /\b(loose\s*sweet\s*corn|baby\s*beetroot\s*\d+\s*g\s*pack|fresh\s*baby\s*beetroot)\b/i },
    { tag: 'sub_frozen', cats: ['household', 'pantry'], inc: /\b(footy\s*box|pigs\s*in\s*(?:a\s*)?blankets?|kransky\s*bites|party\s*pies)\b/i },
    { tag: 'sub_quickmeals', cats: ['household'], inc: /\b(falafel)\b/i },
    { tag: 'meat', cats: ['household'], inc: /\b(grazing\s*platter)\b/i },
    { tag: 'sub_quickmeals', cats: ['meat', 'bakery'], inc: /\bsandwich(?:es)?\b/i, exc: /\b(ice\s*cream|biscuits?|bread|loaf|thins|wraps?|white|wholemeal|grain|\d{3,}\s*g)\b/i },
    { tag: 'bakery', cats: ['frozen', 'dairy_eggs'], inc: /\bfrom\s*the\s*bakery\b/i },
    { tag: 'meat', cats: ['household', 'frozen', 'pantry', 'dairy_eggs'],
      inc: /\b(sop+ressa|sliced\s*meat|luv-?a-?duck|duck\s*breasts?|whole\s*duck|chicken\s*portions)\b|\bfrom\s*the\s*(?:deli|fridge|meat\s*dept)\b(?=.*\b(?:ham|salami|prosciutto|meat|chicken|beef|pork|sopressa)\b)/i,
      exc: /\b(sauce|pasta|tortellini|ravioli|cheese\s*(?!.*\bham\b))\b/i },
    { tag: 'sub_pantry', cats: ['meat', 'household'], inc: /\b(chicken\s*tonight|ayam\s*paste|kan\s*tong|relish|cooking\s*sauces?|stevia|tofu)\b/i },
    { tag: 'bakery', cats: ['pantry', 'snacks', 'chocolate'],
      inc: /\b(berry\s*pies|mooncakes?|mudcake\s*slice|mini\s*chocolate\s*cupcakes|mars\s*bar\s*slice)\b/i },
    { tag: 'sub_dairy', cats: ['snacks', 'chocolate', 'household'], inc: /\b(mousse|goraw)\b/i, exc: /\b(hair|styling)\b/i },
    { tag: 'sub_canned', cats: ['pantry'], inc: /\b(peach\s*slices|in\s*syrup)\b/i },
    // ----- household -----
    { tag: 'sub_cleaning', cats: ['household', 'pet', 'health_vitamins'],
      inc: /\b(glen\s*20|mclintocks|kitchen\s*wipe|fridge\s*wipe|scrub\s*brush|scentory|atlas\s*barrier|car\s*air\s*fresh\w*|ambi\s*pur|wd-?40)\b/i },
    { tag: 'sub_laundry', cats: ['household'], inc: /\b(sard\b|pegs|lint\s*roller)\b/i },
    { tag: 'sub_paper', cats: ['household'], inc: /\b(snack\s*bags?|compostic)\b/i },
];
function _overrideTag(it) {
    const title = it.title || '';
    for (const r of TAG_OVERRIDES) {
        if (r.cats && !r.cats.includes(it.category)) continue;
        if (r.inc.test(title) && !(r.exc && r.exc.test(title))) return r.tag;
    }
    return '';
}
const SUB_CATEGORY_TERMS = Object.fromEntries(Object.keys(SUB_CATEGORY_RULES).map(k => [k, k]));
function _inSub(it, key) {
    const rule = SUB_CATEGORY_RULES[key];
    const title = it.title || '';
    if (!rule.cats.includes(it.category)) return false;
    if (rule.force && rule.force.test(title)) return true;
    return rule.inc.test(title) && !(rule.exc && rule.exc.test(title));
}
// The one shortcut a product belongs to (first match wins, so nothing is listed twice)
function subCategoryOf(it) {
    if (it._sub !== undefined && it._subCat === it.category) return it._sub;
    it._subCat = it.category;
    it._sub = _overrideTag(it);
    if (it._sub) return it._sub;
    for (const key in SUB_CATEGORY_RULES) {
        if (_inSub(it, key)) { it._sub = key; break; }
    }
    return it._sub;
}
// The ONE tag a product is listed under on the website (a chip rule above, else its department's catch-all)
function tagOf(it) {
    return subCategoryOf(it) || DEPT_DEFAULT_TAG[it.category] || 'sub_home';
}
// ---------------- Quick searches (熱門搜尋 chips, and the same words typed in any language) ----------------
// These do NOT match words in product names (that is how "牛奶" used to show milk coffee, Up&Go and
// toddler formula). They use strict "what is this product" rules, like the categories:
//  - a word that has its own category chip (洋芋片, 咖啡, 巧克力, 泡麵, 洗衣精) shows exactly that category,
//    so the search and the chip always show the same products and the same number;
//  - 米 / 牛奶 / 衛生紙 have their own strict rules below.
// Every product that was ever wrongly shown is a test case in tests/search_cases.json.
const _T = (it) => it.title || '';
const QUICK_SEARCH = {
    rice: { terms: ['米', '白米', '大米', '米飯', '白飯', 'お米', 'ご飯', '쌀', '밥', 'rice'],
        match: (it) => it.category === 'pantry' && (['sub_rice', 'sub_pantry'].includes(tagOf(it)) || (tagOf(it) === 'sub_quickmeals' && /\brice\s*(?:pouch|cups?)\b|\blunch\s*bowl\b/i.test(_T(it)))) && /\brice\b/i.test(_T(it)) &&
            !/\b(?:kits?|tuna|salmon|sirena|crackers?|cakes?|rusks?|crisp\w*|bran|flour|vinegar|wine|paper|noodles?|milk|pudding|seasoning|stock|sauce|cereal|bubbles)\b/i.test(_T(it)) },
    milk: { terms: ['牛奶', '鮮奶', '奶', '牛乳', '鮮乳', '鲜奶', 'ミルク', '우유', 'milk'],
        // drinking milk: fresh / long-life / lactose-free / barista / plant milks / flavoured milk
        match: (it) => ['dairy_eggs', 'drinks'].includes(it.category) && ['sub_milk', 'sub_dairy', 'sub_drinks'].includes(tagOf(it)) && /\bmilk\b|\bm\*lk\b/i.test(_T(it)) &&
            !/\b(?:up\s*&?\s*go|liquid\s*breakfast|breakfast\s*drink|smoothies?|shakes?|protein\s*(?:drink|water)|coffee|espresso|latte|cappuccino|mocha|chocolate(?!\s*(?:flavoured\s*)?milk)|choc(?!\s*milk)|yogh?urt|custard|cheese|condensed|evaporated|powder|formula|toddler|infant|kefir|thistle|bottles|coconut|dessert|pudding|snack)\b/i.test(_T(it)) },
    toilet: { terms: ['衛生紙', '卫生纸', '廁紙', '廁所衛生紙', 'トイレットペーパー', '화장지', '휴지', 'toilet paper', 'toilet tissue'],
        match: (it) => it.category === 'household' && /\btoilet\s*(?:paper|tissue|rolls?)\b/i.test(_T(it)) &&
            !/\b(?:wipes|cleaner|cleaning|gel|brush|holder|freshener|spray|bombs?|blocks?|duck|bowl|rim)\b/i.test(_T(it)) },
    chips: { terms: ['洋芋片', '薯片', '馬鈴薯片', 'ポテトチップス', 'ポテチ', '감자칩', 'chips', 'crisps', 'potato chips'], sub: 'sub_chips' },
    coffee: { terms: ['咖啡', 'コーヒー', '커피', 'coffee'], sub: 'sub_coffee' },
    chocolate: { terms: ['巧克力', '朱古力', 'チョコ', 'チョコレート', '초콜릿', 'chocolate'], sub: 'sub_chocolate' },
    noodles: { terms: ['泡麵', '泡面', '即食麵', '方便麵', '拉麵', 'ラーメン', 'インスタント麺', 'カップ麺', '라면', 'noodles', 'instant noodles', 'ramen'], sub: 'sub_noodles' },
    laundry: { terms: ['洗衣精', '洗衣粉', '洗衣液', '洗衣球', '洗剤', '洗濯洗剤', '세탁세제', 'laundry', 'detergent', 'laundry detergent'], sub: 'sub_laundry' },
};
const _quickIndex = new Map();
for (const k in QUICK_SEARCH) QUICK_SEARCH[k].terms.forEach(t => _quickIndex.set(String(t).normalize('NFKC').toLowerCase(), k));
// "牛奶" / " Milk " / "ＭＩＬＫ" -> 'milk'; anything else -> '' (normal word search)
function quickSearchKey(query) {
    return _quickIndex.get(String(query || '').normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim()) || '';
}
function quickSearchMatch(it, key) {
    const q = QUICK_SEARCH[key];
    if (!q) return false;
    return q.sub ? subCategoryOf(it) === q.sub : !!q.match(it);
}
if (typeof module !== 'undefined') module.exports = { SUB_CATEGORY_RULES, TAG_OVERRIDES, subCategoryOf, tagOf, TAG_GROUPS, TAG_GROUP_OF, DEPT_DEFAULT_TAG, QUICK_SEARCH, quickSearchKey, quickSearchMatch };
