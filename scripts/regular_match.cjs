// Woolworths regular (not on special) prices for the price compare: which products to look up, and which
// looked-up prices to keep. "The same product" is decided by static/compare.js, exactly as on the website.
//   node scripts/regular_match.cjs targets <specials.json>                 -> [{id, store, title}]
//   node scripts/regular_match.cjs keep <specials.json> < candidates.json  -> the candidates some target matches
// Targets: this week's Coles / ALDI products with a brand + size, of a brand Woolworths has on special this
// week (so it sells it), and no Woolworths price yet.
const fs = require('fs'), path = require('path'), vm = require('vm');
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'static', 'compare.js'), 'utf8'), ctx);

const [mode, specialsFile] = process.argv.slice(2);
const all = JSON.parse(fs.readFileSync(specialsFile, 'utf8'));
const cur = all.filter(x => (x.period || 'current') === 'current');
const brand = (x) => x._sp.key.split('|')[1];
const wBrands = new Set(cur.filter(x => x.store === 'Woolworths' && ctx._sameInfo(x)).map(brand));
// ALDI writes every brand in capitals, its own brands too: its brand is the leading run of capital words,
// kept only when a Woolworths name starts with it (so ALDI's own brands are not looked up)
const wTitles = cur.filter(x => x.store === 'Woolworths').map(x => x.title.toLowerCase());
const aldiBrand = (t) => (t.match(/^(?:[A-Z0-9'&.,!-]+\s+)*?[A-Z0-9'&.,!-]+(?=\s+[A-Z][a-z]|\s*$)/) || [t.split(' ')[0]])[0].toLowerCase();
const targets = cur.filter(x => (x.store === 'Coles' || x.store === 'ALDI') && ctx._sameInfo(x) && wBrands.has(brand(x))
    && (x.store !== 'ALDI' || wTitles.some(w => w.startsWith(aldiBrand(x.title) + ' ')))
    && !ctx.findSameProducts(x, cur).Woolworths);

let out;
if (mode === 'targets') {
    out = targets.map(x => ({ id: x.id, store: x.store, title: x.title }));
} else if (mode === 'keep') {
    const cands = JSON.parse(fs.readFileSync(0, 'utf8'));
    const pool = cur.concat(cands.map(c => Object.assign({}, c, { period: 'current' })));
    const kept = new Set();
    for (const t of targets) {
        const w = ctx.findSameProducts(t, pool).Woolworths;
        // as on the website: only when both point at each other, and a Woolworths special always wins
        if (w && !cur.includes(w) && ctx.findSameProducts(w, pool)[t.store] === t) kept.add(w.id);
    }
    out = cands.filter(c => kept.has(c.id));
} else {
    console.error('usage: node scripts/regular_match.cjs targets|keep <specials.json> [< candidates.json]');
    process.exit(2);
}
process.stdout.write(JSON.stringify(out));
