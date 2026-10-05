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
};
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
    it._sub = '';
    for (const key in SUB_CATEGORY_RULES) {
        if (_inSub(it, key)) { it._sub = key; break; }
    }
    return it._sub;
}
if (typeof module !== 'undefined') module.exports = { SUB_CATEGORY_RULES, subCategoryOf };
