// 搜尋：中文／日文／韓文打字要和英文一樣找得到 (2026-11-28 「咖哩」找不到、curry 才有)
//   node tests/test_search_words.cjs
// Loads the real search code (static/app.js + category-rules.js) with a few made-up products and checks:
//  - other writings of a word (咖喱, 简体, hiragana) find the same products;
//  - a product with an English name only (the regular-price lists) is found by the Chinese / Japanese / Korean word;
//  - Korean 커리 (curry) does not rank 베이커리 (bakery) first.
const fs = require('fs'), path = require('path'), vm = require('vm');
const ROOT = path.join(__dirname, '..');
const stub = new Proxy(function () {}, { get: (t, k) => (k === Symbol.toPrimitive ? () => '' : stub), apply: () => stub, construct: () => stub });
const ctx = { console, setTimeout, clearTimeout, URLSearchParams, Date, Math, JSON, Intl, Promise,
    document: stub, navigator: stub, localStorage: stub, sessionStorage: stub, history: stub, fetch: () => Promise.reject(new Error('no network')),
    location: { search: '', hostname: 'localhost', pathname: '/', href: 'http://localhost/' } };
ctx.window = ctx; ctx.self = ctx; ctx.globalThis = ctx;
ctx.addEventListener = () => {}; ctx.matchMedia = () => ({ matches: false, addEventListener() {} }); ctx.innerWidth = 1200;
vm.createContext(ctx);
for (const f of ['i18n.js', 'category-rules.js', 'app.js']) {
    try { vm.runInContext(fs.readFileSync(path.join(ROOT, 'static', f), 'utf8'), ctx, { filename: f }); }
    catch (e) { if (f !== 'app.js') throw e; /* page start-up code needs a real browser; the search functions are defined by then */ }
}
const P = (title, zh, ja, ko, category) => ({ title, category, period: 'current', translations: zh ? { zh, ja, ko } : undefined });
const specials = [];
// translated products (this week's specials): enough of them for the page to learn 咖哩 = curry
['Red', 'Green', 'Yellow', 'Panang', 'Massaman', 'Korma'].forEach((k, i) => specials.push(
    P(`Ayam ${k} Curry Paste ${180 + i}g`, `Ayam ${k} 咖哩醬 ${180 + i}克`, `Ayam ${k} カレーペースト ${180 + i}g`, `Ayam ${k} 커리 페이스트 ${180 + i}g`, 'pantry')));
['Plain', 'Sesame', 'Fruit', 'Rye'].forEach((k, i) => specials.push(
    P(`Coles Bakery ${k} Loaf ${500 + i}g`, `Coles 烘焙坊 ${k} 麵包 ${500 + i}克`, `Coles ベーカリー ${k} パン ${500 + i}g`, `Coles 베이커리 ${k} 빵 ${500 + i}g`, 'bakery')));
['Manuka', 'Yellow Box', 'Raw', 'Squeeze'].forEach((k, i) => specials.push(
    P(`Capilano ${k} Honey ${250 + i}g`, `Capilano ${k} 蜂蜜 ${250 + i}克`, `Capilano ${k} はちみつ ${250 + i}g`, `Capilano ${k} 꿀 ${250 + i}g`, 'pantry')));
['Original', 'Light', 'Lactose Free'].forEach((k, i) => specials.push(
    P(`Bulla ${k} Thickened Cream ${300 + i}mL`, `Bulla ${k} 鮮奶油 ${300 + i}毫升`, `Bulla ${k} 生クリーム ${300 + i}ml`, `Bulla ${k} 생크림 ${300 + i}ml`, 'dairy_eggs')));
specials.push(P('Dairy Farmers Full Cream Milk 2L', 'Dairy Farmers 全脂鮮奶 2公升', 'Dairy Farmers 牛乳 2L', 'Dairy Farmers 우유 2L', 'dairy_eggs'));
vm.runInContext('staticSpecials = __s', Object.assign(ctx, { __s: specials }));
// English names only, like the regular-price lists
const sb = P('S&B Golden Curry Sauce Mix Medium 220g', '', '', '', 'pantry');
const honey = P("Beechworth Bee Cause Honey 500g", '', '', '', 'pantry');
const jam = P('Cottees Strawberry Jam 500g', '', '', '', 'pantry');
const bakery = specials.find(p => /Bakery Plain/.test(p.title));
const curry = specials[0], cream = specials.find(p => /Thickened/.test(p.title)), milk = specials[specials.length - 1];
const score = (it, q) => ctx.scoreSearchMatch(it, q);
const checks = [
    ['咖哩 finds the translated curry paste', score(curry, '咖哩') > 0],
    ['咖喱 (other writing) finds it too', score(curry, '咖喱') > 0],
    ['咖哩 finds the English-only S&B curry', score(sb, '咖哩') > 0],
    ['咖喱 finds the English-only S&B curry', score(sb, '咖喱') > 0],
    ['カレー finds the English-only S&B curry', score(sb, 'カレー') > 0],
    ['커리 finds the English-only S&B curry', score(sb, '커리') > 0],
    ['咖哩 does not show jam', score(jam, '咖哩') === 0],
    ['蜂蜜 finds the English-only honey', score(honey, '蜂蜜') > 0],
    ['ハチミツ (katakana) finds はちみつ', score(specials.find(p => /Honey/.test(p.title)), 'ハチミツ') > 0],
    ['蜂蜜 does not show curry', score(sb, '蜂蜜') === 0],
    ['커리: curry ranks above 베이커리 (bakery)', score(curry, '커리') > score(bakery, '커리')],
    ['简体 鸡蛋 = 雞蛋 (dictionary word)', !!ctx._groupOf('鸡蛋') && ctx._groupOf('鸡蛋') === ctx._groupOf('雞蛋')],
    ['简体 蓝莓 = 藍莓 (dictionary word)', !!ctx._groupOf('蓝莓') && ctx._groupOf('蓝莓') === ctx._groupOf('藍莓')],
    ['鮮奶油 finds cream', score(cream, '鮮奶油') > 0],
    ['鮮奶油 does not show milk', score(milk, '鮮奶油') === 0],
    ['curry (English) still finds both', score(curry, 'curry') > 0 && score(sb, 'curry') > 0],
];
const bad = checks.filter(c => !c[1]);
console.log(`${checks.length - bad.length}/${checks.length} search-word checks passed`);
bad.forEach(c => console.log('  WRONG: ' + c[0]));
process.exit(bad.length ? 1 : 0);
