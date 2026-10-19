/* Price comparison across Coles, Woolworths and ALDI (specials and everyday prices alike).
 *
 * Exact same product: app.js (getCompareKey). Here: the same KIND of product (any brand),
 * compared per kg, per litre or per item, and the unit price converter behind it.
 *
 * Shared by the website and by tests/test_compare.py, so a rule change is checked before it goes live.
 */

// ---------------- Unit price: everything as $/kg or $/L ----------------
// ALDI never shows a "was" price, so value = price per kg / litre, compared with Coles & Woolworths.
// Sources, most trusted first: "$12.00 kg" prices, the shop's own unit price, then the pack size in the title.
function _perItemPrice(item) {
    const price = (typeof item.price === 'number') ? item.price : (parseFloat(item.price) || 0);
    const m = String(item.price_display || '').match(/(\d+)\s*for\s*\$\s*([\d,]+(?:\.\d+)?)/i);   // "2 for $12.00"
    if (m) {
        const n = parseInt(m[1], 10), total = parseFloat(m[2].replace(/,/g, ''));
        if (n > 0 && total > 0) return total / n;
    }
    return price;
}
function _toBasis(qty, unit) {   // -> { basis, qty in kg or L }
    unit = unit.toLowerCase();
    if (unit === 'kg') return { basis: 'kg', qty };
    if (unit === 'g') return { basis: 'kg', qty: qty / 1000 };
    if (unit === 'l' || unit.startsWith('litre') || unit.startsWith('liter')) return { basis: 'L', qty };
    if (unit === 'ml') return { basis: 'L', qty: qty / 1000 };
    return null;
}
function _parseUnitString(s) {
    if (!s || typeof s !== 'string') return null;
    // "$0.92 / 100G" (Woolworths)  "$1.20/ 100g" (Coles)  "($13.99 per 1 kg)" (ALDI)
    const m = s.replace(/A\$/gi, '$').match(/\$\s*(\d[\d,]*(?:\.\d+)?)\s*(?:\/|per)\s*(\d+(?:\.\d+)?)?\s*(kg|g|ml|l|litres?|liters?)\b/i);
    if (!m) return null;
    const v = parseFloat(m[1].replace(/,/g, '')), q = m[2] ? parseFloat(m[2]) : 1;
    const b = _toBasis(q, m[3]);
    if (!b || !(v > 0) || !(b.qty > 0)) return null;
    return { basis: b.basis, value: v / b.qty };
}
function _titleSize(title) {
    const t = String(title || '').toLowerCase().replace(/(\d),(\d{3})\b/g, '$1$2');
    // "5G" on a phone is the network, not 5 grams
    if (/\b(optus|telstra|vodafone|samsung|galaxy|iphone|pixel|oppo|motorola|nokia|phones?|mobile|modem|router|sim)\b/.test(t)) return null;
    const U = '(kg|g|ml|l|litres?|liters?)';
    // "6x250mL", "4 x 100g", "(3x225g)"
    const mx = t.match(new RegExp(`(\\d+)\\s*[x×]\\s*(\\d+(?:\\.\\d+)?)\\s*${U}\\b`));
    if (mx) {
        const b = _toBasis(parseFloat(mx[2]) * parseInt(mx[1], 10), mx[3]);
        return b && b.qty > 0 ? b : null;
    }
    // ranges or choices ("600g-1 kg", "127g/130g", "Shampoo or Conditioner") have no single size
    if (new RegExp(`\\d\\s*${U}?\\s*[-–/]\\s*\\d`).test(t) || /\bor\b|\bassorted\b|\bvarieties\b/.test(t)) return null;
    const all = [...t.matchAll(new RegExp(`(\\d+(?:\\.\\d+)?)\\s*${U}\\b`, 'g'))];
    if (all.length !== 1) return null;
    const b = _toBasis(parseFloat(all[0][1]), all[0][2]);
    return b && b.qty > 0 ? b : null;
}
function unitPriceOf(item) {
    if (!item) return null;
    // keyed by the price fields: a state's own price (regionize copies the object) must never reuse another state's figure
    const sig = `${item.price}|${item.price_display}|${item.unit_price}|${item.title}`;
    if (item._up !== undefined && item._upSig === sig) return item._up;
    item._upSig = sig;
    let r = null;
    const per = _perItemPrice(item);
    const disp = String(item.price_display || '').toLowerCase().trim();
    const fromStr = _parseUnitString(item.unit_price);
    // A size in the name of a container / appliance is its capacity, not what you get ("Cooler Ice Box 25L"),
    // and when the shop itself prices it "per each" there is no per-kg / litre price to work out
    const shopSaysEach = !fromStr && /\/\s*\d*\s*(ea|each)\b|per\s*\d*\s*(ea|each)\b/i.test(String(item.unit_price || ''));
    const isContainer = /\b(storer|storage|container|canister|ice ?box|cooler|esky|bins?|bin liners?|buckets?|baskets?|backpack|(?:garbage|rubbish|kitchen tidy|shopping|cooler|lunch|tote|freezer|zip|sandwich|bin) bags?|lunch ?box|drink bottle|water bottle|flask|tumbler|kettle|fryer|cooker|blender|saucepan|frypan|fry pan|stockpot|tote|crate|tank|vacuum|humidifier|dehumidifier|dispenser|organiser|organizer|caddy|hamper|trolley|suitcase|luggage|watering can|sprayer|mister|chest freezer|upright freezer|bar fridge|fridge|refrigerator|home gym|dip station|bench|rack|stand|dumbbells?|kettlebells?|weights?|capacity|max(?:imum)? load|holds? up to|up to \d|bento|machine(?! cleaner)|maker|appliance|stand mixer|hand mixer|food processor|juicer|toaster|microwave oven|benchtop oven|pizza oven|air fryer|heater|fan|lamp|tent|chair|dining table|side table|folding table|coffee table|mattress|paddling pool|pool float)\b/i
        .test(String(item.title || '').replace(/\s*[–—-]\s*from the [a-z ]+$/i, ''));   // "– From the Fridge" is where it's sold
    const size = (shopSaysEach || isContainer) ? null : _titleSize(item.title);
    const fromTitle = (size && per > 0) ? { basis: size.basis, value: per / size.qty } : null;
    if (/^\$?\s*\d[\d,]*(\.\d+)?\s*(\/\s*|per\s+)?kg$/.test(disp) && per > 0) {
        r = { basis: 'kg', value: per };                       // priced by the kilo ("$12.00 kg")
    } else if (fromStr && fromTitle && fromStr.basis === fromTitle.basis) {
        const ratio = fromStr.value / fromTitle.value;
        if (ratio > 0.8 && ratio < 1.25) r = fromStr;          // they agree -> the shop's own figure
        else if (ratio > 50 || ratio < 0.02) r = fromTitle;     // shop typo ("$1,599.00 per 100 g" for 1kg at $15.99)
        else r = null;                                          // unclear -> show nothing rather than a wrong number
    } else {
        r = fromStr || fromTitle;
    }
    if (r && !(r.value >= 0.05 && r.value <= 3000)) r = null;
    item._up = r;
    return r;
}
// Price per item, for things sold by the count (dishwasher tablets, laundry capsules).
// Sources: the shop's own "$0.49/ 1ea" / "($0.24 per 1 each)", the pack count in the title ("46 Pack", "Pk 80", "46pk").
function eachPriceOf(item) {
    if (!item) return null;
    const per = _perItemPrice(item);
    const title = String(item.title || '').toLowerCase();
    const m = String(item.unit_price || '').replace(/A\$/gi, '$').match(/\$\s*(\d[\d,]*(?:\.\d+)?)\s*(?:\/|per)\s*(\d+)?\s*(?:ea|each)\b/i);
    const fromStr = m ? parseFloat(m[1].replace(/,/g, '')) / (m[2] ? parseInt(m[2], 10) : 1) : 0;
    // a choice ("Laundry Liquid 2 Litre or Capsules 28 Pack") has no single count; "28 Washes 28 Pack" is one count
    const counts = /\bor\b|\bassorted\b|\bvarieties\b/.test(title) ? [] :
        [...title.matchAll(/\b(\d+)\s*(?:pack|pk|tablets|capsules|pods|washes)\b|\b(?:pk|pack of)\s*(\d+)\b/g)].map(x => parseInt(x[1] || x[2], 10));
    const n = counts.length && counts.every(c => c === counts[0]) ? counts[0] : 0;
    const fromTitle = (n > 1 && per > 0) ? per / n : 0;
    let v = fromStr || fromTitle;
    if (fromStr && fromTitle && !(fromStr / fromTitle > 0.8 && fromStr / fromTitle < 1.25)) v = 0;   // unclear -> nothing rather than a wrong number
    return (v >= 0.01 && v <= 1000) ? { basis: 'ea', value: v } : null;
}
// Toilet paper: the shop's own price per 100 sheets ("$0.24 / 100 sheets"; Coles writes "$0.32/ 100ea").
// Rolls differ a lot in length (double / triple length), so a price per roll would mislead.
function sheetPriceOf(item) {
    const m = String((item && item.unit_price) || '').replace(/A\$/gi, '$').match(/\$\s*(\d+(?:\.\d+)?)\s*(?:\/|per)\s*100\s*(?:sheets?|ea)\b/i);
    const v = m ? parseFloat(m[1]) : 0;
    return (v >= 0.01 && v <= 100) ? { basis: 'sh', value: v } : null;
}
function cmpPriceOf(item, basis) {
    if (basis === 'ea') return eachPriceOf(item);
    if (basis === 'sh') return sheetPriceOf(item);
    const up = unitPriceOf(item);
    return (up && up.basis === basis) ? up : null;
}

// ---------------- Same kind of product at the three supermarkets: per kg / litre / item ----------------
// Strict on purpose: only plain everyday cuts and staples, never marinated / crumbed / cooked / flavoured,
// and fresh vs frozen, free range and organic must match. Brands can differ (that is the point with ALDI).
const _CMP_MEAT_EXC = /\b(crumbed|schnitzels?|kiev|kyiv|shredded|pulled|recipe|nuggets?|munchies|tenders|tenderloins?|popcorn|marinated|marinade|seasoned|stuffed|smoked|cooked|roasted|carved|shaved|sliced|deli|bbq|peri|garlic|herbs?|honey|teriyaki|satay|lemon|lime|zesty|pepper|chilli|spicy|hot|flaming|buffalo|smoky|sticky|sweet|maple|mint|tikka|southern|flavou?r(ed)?|style|kebabs?|skewers?|burgers?|patties|sausages?|chipolatas?|rissoles?|meatballs?|kofta|pies?|dumplings?|wraps?|sandwich|soup|stir ?fry|strips|sous vide|ready|made easy|capers|butter|crispy|crunchy|glazed|bulgogi|korean|mexican|indian|thai|chinese|italian|greek|portuguese|cajun|tandoori|gravy|sauce|wellington|rolls?|bites|pieces?|cubes?|diced|stuffing|baby food|pet|dog|cat)\b/;
const _CMP_FISH_EXC = /\b(with|rice|meals?|crumbed|battered|tempura|smoked|cooked|marinated|seasoned|flavou?r(ed)?|tinned|canned|in oil|springwater|capers|butter|sauce|cakes?|patties|pie|pet|cat|dog|sushi|sashimi|style|lemon|lime|zesty|pepper|garlic|chilli|herbs?|teriyaki|bites|pieces?)\b/;
// Per-type details that must also match (a different cut / variety / grade is a different price class)
const _fxSkin = (f) => (/\bskin ?off\b|\bskinless\b/.test(f) ? 'S' : '');
const _fxMince = (f) => (/\b(extra lean|heart smart|premium|5 star|4 star)\b/.test(f) ? 'x' : (/\blean\b/.test(f) ? 'l' : 'r'));
const _fxChops = (f) => (/\bforequarter\b/.test(f) ? 'Q' : /\bchump\b/.test(f) ? 'C' : /\bcutlet\b/.test(f) ? 'T' : 'L');
const _fxBeef = (f) => (/\b(grass fed|graze|wagyu|angus|dry aged|black angus|premium)\b/.test(f) ? 'P' : '');
const _fxLambLeg = (f) => (/\bsteaks?\b/.test(f) ? 'T' : (/\bboneless|easy carve\b/.test(f) ? 'B' : ''));
const _fxRice = (f) => (f.match(/\b(basmati|jasmine|brown|sushi|arborio|medium grain|calrose|long grain|white)\b/) || [''])[0].replace('calrose', 'medium grain');
const _fxOil = (f) => (f.match(/\b(canola|vegetable|sunflower)\b/) || [''])[0];
const _fxFlour = (f) => (f.match(/\b(plain|self raising|self-raising|bread)\b/) || [''])[0].replace('-', ' ');
const _fxSugar = (f) => (f.match(/\b(white|raw|caster|brown) sugar\b/) || ['', ''])[1];
const _fxMilk = (f) => (/\b(lite|light|skim|reduced fat)\b/.test(f) ? 'lo' : 'full');
// cheese: block / shredded / slices, and the variety (tasty, extra tasty and cheddar count as one)
const _fxCheese = (f) => (/\b(shredded|grated)\b/.test(f) ? 'sh' : (/\bslices?\b/.test(f) ? 'sl' : 'bl')) +
    (/\bmozzarella\b/.test(f) ? 'mozz' : /\bparmesan\b/.test(f) ? 'parm' : /\bcolby\b/.test(f) ? 'colby' :
        /\b(light|lite|reduced fat|less fat)\b/.test(f) ? 'lite' : /\b(vintage|extra sharp|bitey)\b/.test(f) ? 'vint' : 'tasty');
const _fxBread = (f) => (/\bwholemeal\b/.test(f) ? 'M' : /\brye\b/.test(f) ? 'R' : /\b(multigrain|grains?|seeds?|wholegrain|linseed)\b/.test(f) ? 'G' : 'W');
const CMP_TYPES = [
    { k: 'chicken_breast', re: /\bchicken breasts?\b/, exc: _CMP_MEAT_EXC },
    { k: 'chicken_thigh', re: /\bchicken thighs?\b/, exc: _CMP_MEAT_EXC },
    { k: 'chicken_drum', re: /\bchicken drumsticks?\b/, exc: /\bboneless\b|\bfillets?\b/, exc2: _CMP_MEAT_EXC },
    { k: 'chicken_wing', re: /\bchicken wings?\b/, exc: _CMP_MEAT_EXC },
    { k: 'chicken_whole', re: /\bwhole (?:fresh |free range |rspca approved |australian )*chicken\b/, exc: _CMP_MEAT_EXC },
    { k: 'chicken_mince', re: /\bchicken mince\b/, exc: _CMP_MEAT_EXC, fx: _fxMince },
    { k: 'beef_mince', re: /\bbeef mince\b|\bmince beef\b/, exc: /\b(pork|lamb|veal|chicken)\b|&/, exc2: _CMP_MEAT_EXC, fx: _fxMince },
    { k: 'pork_mince', re: /\bpork mince\b/, exc: _CMP_MEAT_EXC, fx: _fxMince },
    { k: 'lamb_mince', re: /\blamb mince\b/, exc: _CMP_MEAT_EXC, fx: _fxMince },
    { k: 'pork_chops', re: /\bpork (?:loin |cutlet |forequarter )?chops?\b|\bpork cutlets?\b/, exc: _CMP_MEAT_EXC, fx: _fxChops },
    { k: 'pork_scotch', re: /\bpork scotch\b/, exc: _CMP_MEAT_EXC },
    { k: 'pork_shoulder', re: /\bpork shoulder\b/, exc: _CMP_MEAT_EXC },
    { k: 'pork_belly', re: /\bpork belly\b/, exc: _CMP_MEAT_EXC },
    { k: 'beef_scotch', re: /\bscotch fillet\b/, not: /\b(pork|lamb)\b/, exc: _CMP_MEAT_EXC, fx: _fxBeef },
    { k: 'beef_rump', re: /\brump steaks?\b/, not: /\b(pork|lamb)\b/, exc: _CMP_MEAT_EXC, fx: _fxBeef },
    { k: 'beef_sirloin', re: /\b(sirloin|porterhouse)\b/, not: /\b(pork|lamb)\b/, exc: _CMP_MEAT_EXC, fx: _fxBeef },
    { k: 'lamb_cutlets', re: /\blamb cutlets?\b/, exc: _CMP_MEAT_EXC },
    { k: 'lamb_leg', re: /\blamb leg\b|\bleg of lamb\b/, exc: _CMP_MEAT_EXC, fx: _fxLambLeg },
    { k: 'lamb_chops', re: /\blamb (?:loin |forequarter |chump )?chops?\b/, exc: _CMP_MEAT_EXC, fx: _fxChops },
    { k: 'salmon', re: /\bsalmon (?:fillets?|portions?)\b/, exc: _CMP_FISH_EXC, fx: _fxSkin },
    { k: 'barramundi', re: /\bbarramundi (?:fillets?|portions?)\b/, exc: _CMP_FISH_EXC, fx: _fxSkin },
    { k: 'prawns', re: /\bprawns?\b/, exc: /\b(fried|rice|tempura|crumbed|battered|cooked|marinated|seasoned|garlic|chilli|siu mai|dim sims?|dumplings?|har gow|gyoza|wontons?|spring rolls?|toast|cutlets|cakes?|pork|chicken|mushroom|crackers?|chips|noodles?|soup|laksa|sauce|skewers?|bacon|pet|cat|dog|treats?)\b/ },
    { k: 'milk', re: /\b(full cream|whole|lite|light|skim|reduced fat) milk\b/, basis: 'L', fx: _fxMilk, exc: /\b(flavou?red|chocolate|strawberry|banana|coffee|iced|powder|powdered|condensed|evaporated|lactose|a2|protein|almond|oat|soy|rice|coconut|macadamia|kids|toddler|formula|goat|body|lotion|wash|soap|bath|cleanser)\b/ },
    { k: 'peanut_butter', re: /\bpeanut butter\b/, fx: (f) => (/\b(natural|simply nuts)\b|100% peanuts?/.test(f) ? 'N' : ''), exc: /\b(bars?|cookies?|biscuits?|treats?|dog|cat|pet|clusters?|granola|muesli|pieces|cups?|choc|chocolate|ice cream|whisky|wafers?|pretzels?|protein|light|lite|powder|sauce|chicken|satay|brownie|caramel|crackers?|balls|bites|smoothie|milk|honey|jelly|jam|cereal|oats?|squares|filled|dark roast(?:ed)?)\b|\bor\b/ },
    { k: 'butter', re: /\bbutter\b/, exc: /\b(bread|cucumbers?|pickles?|puff|pastry|lemon|spread|everything|peanut|almond|nut|cashew|cocoa|shea|mango|coconut|body|lotion|scrub|wash|gel|soap|balm|lip|gloss|deodorant|spray|diffuser|garlic|herb|biscuits?|cookies?|chicken|popcorn|cake|croissants?|shortbread|chocolate|blend|spreadable|soft|ghee|light|salmon|sauce|paste|caramel|beans?|lettuce|menthol|scotch|chips|crisps|seaweed|kombu|cups|pieces|chicken|steak|porterhouse|capers|me up)\b/ },
    { k: 'rice', re: /\b(jasmine|basmati|long grain|medium grain|white|brown|calrose|sushi) rice\b/, fx: _fxRice, exc: /\b(with|curry|dahl|microwave|cups?|pouch|express|cakes?|crackers?|noodles?|flour|bran|milk|pudding|paper|vinegar|wine|chips|ready|instant|fried|seasoned|flavou?r(ed)?|risotto|mexican|coconut|garlic|chicken|tomato)\b/ },
    { k: 'pasta', re: /\b(spaghetti|penne|fusilli|spirals|linguine|fettuccine|rigatoni|macaroni|farfalle|shells)\b/, exc: /\b(taco|sauce|fresh|filled|ravioli|tortellini|gnocchi|ready|meals?|feast|menu|cups?|bake|kit|tinned|canned|tin|heinz|spc|beanz|beans|cheesy|cheese|beef|bacon|chicken|tomato|bolognese|carbonara|microwave|soup|salad|gluten|protein|wholemeal|lentil|chickpea|kids|snack|pot|loaded)\b|&/ },
    { k: 'flour', re: /\b(plain|self raising|self-raising|bread) flour\b/, fx: _fxFlour, exc: /\b(almond|coconut|rice|gluten|corn|wholemeal|spelt|mix|pizza)\b/ },
    { k: 'sugar', re: /\b(white|raw|caster|brown) sugar\b/, fx: _fxSugar, exc: /\b(sticks|sachets|icing|free|no added|lollies|syrup|coconut|cinnamon|doughnuts?|cookies?|biscuits?|cereal|gum|oreo|pancake|hair|dye|scrub|body|polish|candle)\b/ },
    { k: 'olive_oil', re: /\bolive oil\b/, basis: 'L', fx: (f) => (/\bextra virgin\b/.test(f) ? 'V' : ''), exc: /\b(truffle|infused|spray|tuna|sardines|in olive oil|with olive oil|blend|mayo|mayonnaise|spread|chips|crackers|soap|body|hair|skin|cat|dog|food)\b/ },
    { k: 'veg_oil', re: /\b(canola|vegetable|sunflower) oil\b/, basis: 'L', fx: _fxOil, exc: /\b(spray|tuna|sardines|in |with |mayo|spread|chips|soap|body|hair|cat|dog)\b/ },
    // eggs by weight (a 700g dozen vs a 900g pack of 18); cage / barn (cage free) / free range (flag R) never mixed
    { k: 'eggs', re: /\beggs\b/, fx: (f) => (/\bbarn\b|\bcage[ -]free\b/.test(f) ? 'B' : (/\bcage\b/.test(f) ? 'C' : '')), exc: /\b(mayo|mayonnaise|noodles?|pasta|chocolate|choc|kinder|cadbury|lindt|easter|hollow|surprise|spice|seasoning|blend|whites?|scrambled|liquid|custard|lice|treatment|toy)\b/ },
    { k: 'dish_tabs', re: /\bdish(?:washer|washing)\b.*\b(tablets?|capsules?|pods?|tabs)\b|\b(tablets?|capsules?|pods?|tabs)\b.*\bdish(?:washer|washing)\b/, basis: 'ea', exc: /\b(cleaner|freshener|deodoriser|salt|rinse)\b/ },
    { k: 'laundry_caps', re: /\blaundry\b.*\b(capsules?|pods?)\b|\b(capsules?|pods?)\b.*\blaundry\b/, basis: 'ea', exc: /\b(sheets?|soaker|stain|softener|freshener|booster)\b/ },
    { k: 'laundry_liquid', re: /\blaundry (?:liquid|detergent)\b|\bliquid laundry\b|\bwashing liquid\b/, basis: 'L', exc: /\b(capsules?|pods?|sheets?|softener|conditioner|stain|soaker|booster|wool|delicates|hand ?wash|powder|sanitiser|sanitizer|rinse|beads|freshener|or)\b/ },
    { k: 'laundry_powder', re: /\blaundry (?:detergent )?powder\b|\bwashing powder\b|\bpowder laundry\b/, exc: /\b(capsules?|pods?|sheets?|softener|stain|soaker|booster|wool|sanitiser|sanitizer|liquid|or)\b/ },
    { k: 'dish_liquid', re: /\bdish(?:washing)? liquid\b|\bwashing up liquid\b/, basis: 'L', exc: /\b(dishwasher|tablets?|capsules?|pods?|powder|rinse|cleaner|brush|scrubber|sponges?|cloths?|gloves|rack|dispenser|machine|or)\b/ },
    { k: 'toilet_paper', re: /\btoilet (?:paper|tissues?|rolls?)\b/, basis: 'sh', fx: (f) => (f.match(/\b([1-6]) ?ply\b/) || ['', ''])[1], exc: /\b(wipes?|flushable|moist|holder|brush|cleaner|freshener|spray|seat|bowl|block|kitchen|facial|towels?|or)\b/ },
    // cheese: a variety and a form (block / shredded / slices) both named, never snacks, spreads or flavoured
    { k: 'cheese', re: /^(?=.*\b(tasty|cheddar|vintage|colby|mozzarella|parmesan)\b)(?=.*\b(cheese|block|shredded|grated|slices?)\b)/, fx: _fxCheese, exc: /\b(dairy free|plant|plants|vegan|crackers?|cracker cuts|snacks?|chips|crisps|lunch|on the go|spread|cream cheese|cream|pickled|smoked|flavou?r(ed)?|sticks?|babybel|portions?|bites|minis?|biscuits?|pizza|pasta|sauce|bread|rolls?|scrolls?|twists?|puffs?|balls|sausages?|kabana|kransky|toasties?|jalapeno|chilli|garlic|herbs?|onion|bacon|ham|chicken|beef|dip|soup|mac|macaroni|burgers?|pies?|quiche|pet|dog|cat|treats?|string|grater|knife|board|slicer|blend|mix|popcorn|corn|thins|rice cakes?|club|trilogy|classic|long[ -]life|and|with)\b|&/ },
    { k: 'yoghurt_greek', re: /^(?=.*\bgreek\b)(?=.*\byogh?urt\b)/, fx: (f) => (/\b(light|lite|low fat|no fat|fat free|skim)\b/.test(f) ? 'L' : ''), exc: /\b(lactose|vanilla|strawberry|mango|berry|berries|blueberry|cherry|honey|passionfruit|peach|banana|raspberry|caramel|choc|chocolate|coconut|lemon|fig|tropical|mixed|fruit|swirl|protein|kids|pouch|pouches|baby|bars?|nuts?|frozen|ice cream|flip|smoothie|trail|dip|dressing|tzatziki|granola|muesli|bites|coated|flavou?r(ed)?|or)\b/ },
    // sandwich loaves only (white / wholemeal / grain / rye), never sourdough, wraps, rolls or sweet breads
    { k: 'bread', re: /^(?=.*\bbread\b)(?=.*\b(white|wholemeal|rye|multigrain|grains?|seeds?|wholegrain|linseed|sandwich|toast)\b)/, fx: _fxBread, exc: /\b(banana|fruit|raisin|sultana|spiced|garlic|cheese|naan|pita|pitta|lebanese|turkish|wraps?|tortillas?|flatbread|flat|mix|premix|improver|flour|crumbs?|maker|machine|bin|box|knife|board|tin|pan|rolls?|buns?|thins|cake|sticks|croutons|bagels?|muffins?|crumpets?|english|gluten|keto|low carb|protein|sourdough|brioche|panini|pudding|sauce|soup|pizza|crackers?|chips|crisps|corn|soda|damper|gingerbread|shortbread|zucchini|pumpkin|dates?|walnut|olive|tomato|onion|herbs?|bao|steamed|dog|cat|pet|bird|half|mini|or)\b/ },
    // frozen only: the title says frozen or the shop files it under frozen (ALDI's "Baby Peas 1kg" does not say it)
    { k: 'peas', re: /\bpeas\b/, fz: true, exc: /\b(chick|snow|sugar ?snap|split|wasabi|crunchy|seasoned|bhuja|snacks?|corn|carrots?|mixed|vegetables|veg|soup|pies?|mushy|dried|sprouts?|pods|rice|pasta|ham|mint|dog|cat|pet)\b|&/ },
    { k: 'coffee_instant', re: /\binstant coffee\b|\bcoffee\b.*\b(?:instant|freeze dried)\b|\bfreeze dried coffee\b/, fx: (f) => (/\b(freeze dried|gold|espresso|barista|crema|premium)\b/.test(f) ? 'P' : ''), exc: /\b(latte|cappuccino|mocha|flavou?r(ed)?|vanilla|caramel|hazelnut|sachets?|sticks?|mix|decaf|decaffeinated|machine|capsules?|pods?|beans|ground|cold brew|iced|protein|chicory|dandelion|sugar free|skinny|frothy|or)\b/ },
    { k: 'coffee_caps', re: /\bcoffee\b.*\b(?:capsules?|pods)\b|\b(?:capsules?|pods)\b.*\bcoffee\b/, basis: 'ea', fx: (f) => (/\bespressotoria\b/.test(f) ? 'E' : ''), exc: /\b(flavou?r(ed)?|vanilla|caramel|hazelnut|machine|descaler|holder|drawer|stand|rack|tea|chai|hot chocolate|milk|dolce gusto|tassimo|caddy|storage|or)\b/ },
];
// Things that change the price a lot whatever the product: both sides must be the same
// (fresh vs frozen — "From the Seafood Freezer" counts as frozen — free range, organic, long life, boneless)
function _cmpFlags(full) {
    return [
        /\bfrozen\b|\bfreezer\b/.test(full) ? 'F' : '',
        /\bfree[ -]range\b/.test(full) ? 'R' : '',
        /\borganic\b/.test(full) ? 'O' : '',
        /\blong life\b|\buht\b/.test(full) ? 'U' : '',
    ].join('');
}
// The kind of product ("eggs|R|"), or null when it is not compared; its price per kg / litre / item goes in item._cmpUp
function cmpTypeOf(item) {
    if (!item) return null;
    // keyed by the price fields too: a state's own price (regionize copies the object) must never reuse another state's figure
    const sig = `${item.title}|${item.price}|${item.price_display}|${item.unit_price}`;
    if (item._cmpType !== undefined && item._cmpTypeSig === sig) return item._cmpType;
    item._cmpTypeSig = sig;
    let r = null, p = null;
    const full = String(item.title || '').toLowerCase().replace(/['’]/g, '').replace(/[–—]/g, '-');
    // "– From the Deli / Meat Dept / Fridge" says where it's sold, not what it is (the freezer still counts, via the flags)
    const tl = full.replace(/-?\s*from the [a-z ]+$/, '');
    for (const ty of CMP_TYPES) {
        if (!ty.re.test(tl)) continue;
        if (ty.not && ty.not.test(tl)) continue;
        if (ty.exc && ty.exc.test(tl)) break;               // first matching type decides; an excluded one is not compared
        if (ty.exc2 && ty.exc2.test(tl)) break;
        if (ty.fz && !/\bfrozen\b|\bfreezer\b/.test(full) && item.category !== 'frozen') break;
        p = cmpPriceOf(item, ty.basis || 'kg');
        if (p) r = `${ty.k}|${_cmpFlags(ty.fz ? `${full} frozen` : full)}|${ty.fx ? ty.fx(full) : ''}`;
        break;
    }
    item._cmpType = r;
    item._cmpUp = r ? p : null;
    return r;
}
// The cheapest product of the same kind at each OTHER supermarket, same week (specials and everyday prices alike).
// verdict: this one is 'cheaper' / 'dearer' / about the 'same' (within 3%) vs the cheapest of them;
// lowest: nothing of this kind is cheaper this week, at any of the three (own store included).
function valueCompare(item, list) {
    if (!item || !list) return null;
    if (item._vc !== undefined && item._vcList === list) return item._vc;
    item._vcList = list;
    let res = null;
    const type = cmpTypeOf(item), mine = item._cmpUp;
    if (type) {
        if (!list._cmpIndex) {          // kind -> products, built once per list (a new list per state)
            list._cmpIndex = new Map();
            for (const o of list) {
                const k = cmpTypeOf(o);
                if (!k) continue;
                if (!list._cmpIndex.has(k)) list._cmpIndex.set(k, []);
                list._cmpIndex.get(k).push(o);
            }
        }
        const best = {};
        let lowest = true;
        for (const o of list._cmpIndex.get(type) || []) {
            if (o === item || (o.period || 'current') !== (item.period || 'current')) continue;
            const up = o._cmpUp;
            if (up.value < mine.value) lowest = false;
            if (o.store === item.store) continue;
            if (!best[o.store] || up.value < best[o.store].up.value) best[o.store] = { item: o, up };
        }
        const rows = Object.values(best).sort((a, b) => a.up.value - b.up.value);
        if (rows.length) {
            const cheapest = rows[0];
            const diff = Math.round((cheapest.up.value - mine.value) * 100) / 100;   // >0: this one is cheaper
            const rel = diff / mine.value;
            const verdict = rel >= 0.03 ? 'cheaper' : (rel <= -0.03 ? 'dearer' : 'same');
            res = { mine, rows, cheapest, diff: Math.abs(diff), verdict, basis: mine.basis, lowest };
        }
    }
    item._vc = res;
    return res;
}
if (typeof module !== 'undefined') module.exports = { unitPriceOf, eachPriceOf, sheetPriceOf, cmpPriceOf, cmpTypeOf, valueCompare, CMP_TYPES };
