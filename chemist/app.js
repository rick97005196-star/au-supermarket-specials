// 小黃屋特價查詢 — data/products.json and data/names-<lang>.json are made by scripts/build_chemist.py; words in i18n.js
'use strict';
const DEPT_KEYS = ['vitamins', 'medicine', 'health', 'baby', 'skin', 'makeup', 'hair', 'fragrance', 'oral', 'sports', 'appliance', 'pet', 'other'];
// Chinese words people type -> words in the English product names
const ZH = {
  '維他命': 'vitamin', '維生素': 'vitamin', '綜合維他命': 'multivitamin', '魚油': 'fish oil|omega', '磷蝦油': 'krill',
  '益生菌': 'probiotic', '膠原蛋白': 'collagen', '鎂': 'magnesium', '鈣': 'calcium', '鋅': 'zinc', '鐵': 'iron',
  '葡萄糖胺': 'glucosamine', '關節': 'joint|glucosamine', '薑黃': 'turmeric|curcumin', '睡眠': 'sleep|melatonin',
  '褪黑激素': 'melatonin', '助眠': 'sleep', '睡': 'sleep', '維他命c': 'vitamin c', '維他命d': 'vitamin d',
  '葉酸': 'folate|folic', '孕婦': 'pregnancy|elevit', '懷孕': 'pregnancy', '哺乳': 'breastfeeding', '嬰兒': 'baby|infant',
  '奶粉': 'formula', '尿布': 'nappies|nappy', '寶寶': 'baby|kids', '兒童': 'kids|children', '小孩': 'kids|children',
  '防曬': 'spf|sunscreen|sun', '乳液': 'lotion|moisturis', '保濕': 'moisturis|hydra', '面霜': 'cream', '精華': 'serum',
  '洗面乳': 'cleanser|face wash', '卸妝': 'makeup remover|micellar|micellaire', '身體乳': 'body lotion',
  '洗髮': 'shampoo', '洗髮精': 'shampoo', '潤髮': 'conditioner', '護髮': 'hair', '染髮': 'hair colour|hair color', '頭髮': 'hair',
  '香水': 'edp|edt|parfum|perfume', '口紅': 'lipstick|lip', '睫毛膏': 'mascara', '粉底': 'foundation', '指甲油': 'nail',
  '牙膏': 'toothpaste|sensodyne|colgate', '牙刷': 'toothbrush', '漱口水': 'mouthwash', '牙線': 'floss',
  '感冒': 'cold|flu', '咳嗽': 'cough', '喉嚨': 'throat', '止痛': 'pain|panadol|nurofen|paracetamol|ibuprofen|voltaren', '頭痛': 'pain|headache|panadol|nurofen', '退燒': 'paracetamol|ibuprofen|fever|panadol|nurofen|childrens panadol',
  '過敏': 'allergy|hayfever|antihistamine', '花粉': 'hayfever', '鼻塞': 'nasal|decongestant', '腹瀉': 'diarrhoea', '便秘': 'constipation|laxative',
  '胃酸': 'heartburn|reflux|antacid', '戒菸': 'nicotine|nicotinell|nicorette', 'ok蹦': 'bandage|plaster', '繃帶': 'bandage',
  '蛋白粉': 'protein|whey', '乳清': 'whey', '肌酸': 'creatine', '刮鬍刀': 'shaver|razor', '電動牙刷': 'electric toothbrush|oral-b io',
  '體溫計': 'thermometer', '血壓計': 'blood pressure', '隱形眼鏡': 'contact lens', '眼藥水': 'eye drops', '保險套': 'condom',
  '驗孕': 'pregnancy test', '寵物': 'dog|cat|pet', '狗': 'dog', '貓': 'cat', '除臭': 'deodorant|antiperspirant', '護唇': 'lip balm',
  '跳蚤': 'flea|bravecto|nexgard|simparica|frontline|advocate|revolution', '驅蟲': 'worm|flea|bravecto|nexgard|simparica|drontal|milbemax', '衛生棉': 'pads|libra|kotex|u by kotex', '棉條': 'tampon', '護膝': 'knee', '護腕': 'wrist',
  '護踝': 'ankle', '壓力襪': 'compression', '血糖': 'glucose|glucometer|accu chek', '口罩': 'mask', '乾洗手': 'sanitiser|sanitizer',
  '紗布': 'gauze', '眼睛': 'eye', '眼藥': 'eye drops', '鼻噴劑': 'nasal spray', '曼努卡': 'manuka', '蜂蜜': 'honey', '刮鬍': 'razor|shav',
  '面膜': 'mask', '洗手': 'hand wash', '沐浴乳': 'body wash|shower gel', '香皂': 'soap', '濕紙巾': 'wipes', '指甲': 'nail',
  '眼影': 'eyeshadow|shadow', '眉': 'brow', '髮蠟': 'wax|pomade|styl', '吹風機': 'dryer', '離子夾': 'straightener',
};
Object.assign(ZH, SYN);
const PAGE = 60;
const LANGS = { zh: 'zh-Hant-TW', en: 'en', ja: 'ja', ko: 'ko' };
const $ = (id) => document.getElementById(id);
let ALL = [], SPECIALS = [], LISTED = [], DATA = null;
let lang = (Object.keys(LANGS).find((k) => LANGS[k] === document.documentElement.lang)) || 'zh';
const names = {};          // lang -> {product number: name}
const state = { scope: 'special', dept: '', q: '', sort: 'pop', shown: PAGE };
const T = () => I18N[lang];
const deptName = (k) => T().depts[k] || k;

function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
function safeUrl(u, img) {
  if (typeof u !== 'string') return '';
  if (img) return /^https:\/\/[^\s"'<>]+$/i.test(u) ? u : '';
  return /^https:\/\/www\.chemistwarehouse\.com\.au\/[^\s"'<>]*$/i.test(u) ? u : '';
}
function norm(s) { return String(s || '').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/['’`]/g, '').replace(/\s+/g, ' '); }
function money(n) { return '$' + Number(n).toFixed(2); }
// 'cerave-moisturising-cream-454g' -> 'Cerave Moisturising Cream 454g' (same as scrapers/chemist_all.py)
function nameFromSlug(slug) {
  return String(slug || '').split('-').filter(Boolean).map((w) => (/^\d/.test(w) ? w : w[0].toUpperCase() + w.slice(1))).join(' ');
}
// the name in the chosen language (English when there is none yet)
function localName(it) {
  if (lang === 'en') return '';
  if (it.special) return it[lang] || '';
  return (names[lang] && names[lang][it.pid]) || '';
}
// "Thu 12 Nov 2026 - Wed 25 Nov 2026" -> "11月12日 – 11月25日" / "12 Nov – 25 Nov"
function heroDate(r) {
  const M = { Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6, Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12 };
  const p = [...String(r || '').matchAll(/(\d{1,2})\s+([A-Za-z]{3})/g)].slice(0, 2);
  return p.length === 2 ? p.map((m) => T().date(M[m[2]], +m[1])).join(' – ') : (r || '');
}
function ago(d) {
  const min = Math.max(0, Math.round((Date.now() - d.getTime()) / 60000));
  if (min < 60) return T().ago(min, 'm');
  if (min < 48 * 60) return T().ago(Math.round(min / 60), 'h');
  return T().ago(Math.round(min / 1440), 'd');
}

function terms(q) {
  // every word must match; a Chinese / Japanese / Korean word may match any of its English words
  const out = [];
  let rest = norm(q).trim();
  for (const k of Object.keys(ZH).sort((a, b) => b.length - a.length)) {
    const nk = norm(k);
    if (rest.includes(nk)) { out.push(ZH[k].split('|').map(norm).concat([nk])); rest = rest.split(nk).join(' '); }
  }
  for (const w of rest.split(/\s+/)) if (w) out.push([w]);
  return out;
}
function matches(it, groups) { return groups.every((alts) => alts.some((a) => it._s.includes(a))); }
function index() {
  // searchable text: English + Chinese always (Chinese search works in every language) + the chosen language
  for (const it of ALL) {
    const zh = it.special ? it.zh : (names.zh && names.zh[it.pid]) || '';
    const own = lang !== 'zh' && lang !== 'en' ? localName(it) : '';
    it._s = norm(`${it.title} ${zh} ${own} ${I18N.zh.depts[it.dept] || ''} ${deptName(it.dept)}`);
  }
}

function render() {
  const t = T();
  const groups = state.q ? terms(state.q) : [];
  const base = state.scope === 'special' ? SPECIALS : ALL;
  const hit = base.filter((it) => (!groups.length || matches(it, groups)));
  const byDept = {};
  for (const it of hit) byDept[it.dept] = (byDept[it.dept] || 0) + 1;
  let list = state.dept ? hit.filter((it) => it.dept === state.dept) : hit;
  const s = state.sort;
  list = list.slice().sort((a, b) => {
    if (!!b.special !== !!a.special) return b.special ? 1 : -1;      // specials first
    if (!a.special) return a._i - b._i;                                 // already in name order
    if (s === 'save') return (b.save_amount || 0) - (a.save_amount || 0) || (b.pop || 0) - (a.pop || 0);
    if (s === 'low') return (a.price || 0) - (b.price || 0);
    if (s === 'name') return (localName(a) || a.title).localeCompare(localName(b) || b.title, LANGS[lang]);
    return (b.pop || 0) - (a.pop || 0) || (b.save_amount || 0) - (a.save_amount || 0);
  });

  $('chips').innerHTML = [`<button type="button" class="chip" data-dept="" aria-pressed="${!state.dept}">${esc(t.all)}<small>${hit.length.toLocaleString()}</small></button>`]
    .concat(DEPT_KEYS.filter((k) => byDept[k] || state.dept === k)
      .map((k) => `<button type="button" class="chip" data-dept="${k}" aria-pressed="${state.dept === k}">${esc(deptName(k))}<small>${(byDept[k] || 0).toLocaleString()}</small></button>`)).join('');

  const nSp = list.filter((x) => x.special).length;
  $('count').textContent = list.length ? (state.scope === 'all' ? t.countAll(list.length.toLocaleString(), nSp) : t.countSp(list.length)) : '';
  $('grid').innerHTML = list.slice(0, state.shown).map(card).join('');
  $('more').hidden = list.length <= state.shown;
  $('more').textContent = t.more((list.length - state.shown).toLocaleString());
  const empty = $('empty');
  empty.hidden = list.length > 0;
  if (!list.length && state.scope === 'special' && groups.length) {
    const n = ALL.filter((it) => !it.special && matches(it, groups)).length;
    empty.innerHTML = n ? `${esc(t.noneSp)}<br><button type="button" class="linkbtn" id="toAll">${esc(t.seeAll(n.toLocaleString()))}</button>` : esc(t.none);
  } else if (!list.length) empty.textContent = t.none;
}

function priceHTML(display, price) {
  // "$5.50" -> <sup>$</sup>5<sup>.50</sup> like the supermarket site; "2 for $36.99" / "From $9.99" kept in words
  const t = T();
  const txt = display || money(price);
  const m = txt.match(/^(From\s+)?\$(\d+)(?:\.(\d{2}))?$/i);
  if (m) return `<sup>$</sup>${m[2]}${m[3] ? `<sup>.${m[3]}</sup>` : ''}${m[1] ? `<small>${esc(t.from)}</small>` : ''}`;
  const two = txt.match(/^(\d+)\s*for\s*\$([\d.]+)$/i);
  if (two) return `<sup>$</sup>${esc(two[2])}<small>${esc(t.pcs(two[1]))}</small>`;
  return esc(txt);
}

function card(it) {
  const t = T();
  const url = safeUrl(it.url);
  const open = (cls) => (url ? `<a class="card ${cls}" href="${esc(url)}" target="_blank" rel="noopener">` : `<div class="card ${cls}">`);
  const close = url ? '</a>' : '</div>';
  const dept = `<div class="dept">${esc(deptName(it.dept))}</div>`;
  const own = localName(it);
  const title = own ? `<div class="zh">${esc(own)}</div><div class="en">${esc(it.title)}</div>` : `<div class="zh">${esc(it.title)}</div>`;
  if (!it.special) {
    // the shop's own product photo (same address pattern as its product pages); hidden if there is none
    const thumb = /^\d+$/.test(it.pid) ? `<span class="thumb"><img src="https://static.chemistwarehouse.com.au/ams/media/pi/${it.pid}/2DF_200.jpg" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.parentNode.remove()"></span>` : '';
    return `${open('row')}${thumb}<div class="info">${dept}${title}</div><span class="go">${esc(t.go)}</span>${close}`;
  }
  const img = safeUrl(it.image_url, true);
  const pic = `<div class="pic">${img ? `<img src="${esc(img)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">` : ''}</div>`;
  const half = /1\/2 price/i.test(it.discount_desc);
  const badge = half ? `<span class="badge half">${esc(t.half)}</span>` : (it.period === 'next' ? `<span class="badge">${esc(t.next)}</span>` : '');
  let extra = `<span class="special-note">${esc(t.sp)}</span>`;
  if (it.was_price > 0 && it.save_amount > 0) {
    const lab = /off RRP/i.test(it.discount_desc) ? t.rrp : t.was;
    extra = `<span class="was">${esc(lab)} <s>${money(it.was_price)}</s></span><span class="save">${esc(t.save(money(it.save_amount)))}</span>`;
  }
  return `${open('')}${pic}${badge}${dept}${title}<div class="price"><div class="now">${priceHTML(it.price_display, it.price)}</div>${extra}</div>${close}`;
}

function setScope(scope) {
  state.scope = scope; state.dept = ''; state.shown = PAGE;
  document.querySelectorAll('.seg-btn').forEach((b) => { const on = b.dataset.scope === scope; b.setAttribute('aria-selected', String(on)); b.classList.toggle('is-active', on); });
  render();
}

// ---------- language ----------
async function loadNames(l) {
  if (l === 'en' || names[l]) return;
  try { names[l] = await (await fetch(`data/names-${l}.json`, { cache: 'no-cache' })).json(); } catch (e) { names[l] = {}; }
}
function texts() {
  const t = T();
  document.documentElement.lang = LANGS[lang];
  document.title = t.title;
  document.querySelectorAll('[data-i18n]').forEach((el) => { const v = t[el.dataset.i18n]; if (typeof v === 'string') el.textContent = v; });
  document.querySelectorAll('[data-i18n-html]').forEach((el) => { el.innerHTML = t[el.dataset.i18nHtml]; });   // our own words only
  document.querySelectorAll('[data-i18n-ph]').forEach((el) => { el.placeholder = t[el.dataset.i18nPh]; });
  document.querySelectorAll('.lang-btn').forEach((b) => b.classList.toggle('is-active', b.dataset.lang === lang));
  $('langSelect').value = lang;
  $('themeBtn').setAttribute('aria-label', t.dark);
  const hot = $('hot');
  hot.querySelectorAll('button').forEach((b) => b.remove());
  t.hotWords.forEach((w) => {
    const b = document.createElement('button'); b.type = 'button'; b.textContent = w;
    b.addEventListener('click', () => { $('q').value = w; $('clear').hidden = false; state.q = w; state.dept = ''; state.shown = PAGE; render(); });
    hot.appendChild(b);
  });
  if (DATA) {
    $('heroDate').textContent = (DATA.date_ranges || []).map(heroDate).join(', ') || t.title;
    const d = DATA.updated ? new Date(DATA.updated) : null;
    if (d && !isNaN(d)) {
      $('updatedAgo').textContent = ago(d);
      $('updated').textContent = t.updated(d.toLocaleString(LANGS[lang], { timeZone: 'Australia/Sydney', dateStyle: 'medium', timeStyle: 'short' }));
    }
  }
}
async function setLang(l) {
  if (!LANGS[l]) return;
  lang = l;
  try { localStorage.setItem('cw-lang', l); } catch (e) {}
  texts();
  await loadNames(l);
  index();
  render();
}

async function main() {
  texts();
  try {
    DATA = await (await fetch('data/products.json', { cache: 'no-cache' })).json();
  } catch (e) {
    $('heroDate').textContent = T().failed;
    return;
  }
  SPECIALS = (DATA.specials || []).map((x) => Object.assign(x, { special: true }));
  // other products come compact: [product number, link text, department]
  const depts = DATA.depts || [];
  LISTED = (DATA.products || []).map((r, i) => ({
    pid: r[0], title: nameFromSlug(r[1]), url: `https://www.chemistwarehouse.com.au/buy/${r[0]}/${r[1]}`,
    dept: depts[r[2]] || 'other', _i: i,
  }));
  ALL = SPECIALS.concat(LISTED);
  $('statSpecial').textContent = SPECIALS.length;
  $('statSave').textContent = SPECIALS.filter((x) => x.save_amount > 0).length;
  $('statHalf').textContent = SPECIALS.filter((x) => /1\/2 price/i.test(x.discount_desc)).length;
  $('statAll').textContent = ALL.length.toLocaleString();
  $('nSpecial').textContent = SPECIALS.length;
  $('nAll').textContent = ALL.length.toLocaleString();
  texts();
  index();
  render();
  // Chinese names are searched in every language; the chosen language's names show on the cards
  await Promise.all([loadNames('zh'), loadNames(lang)]);
  index();
  render();
}

// ---------- light / dark (same switch and storage as the other sites) ----------
(function () {
  const root = document.documentElement, btn = $('themeBtn');
  function apply(th) {
    root.classList.toggle('dark', th === 'dark');
    if (th === 'dark') root.setAttribute('data-theme', 'dark'); else root.removeAttribute('data-theme');
    btn.setAttribute('aria-pressed', String(th === 'dark'));
    document.querySelector('meta[name="theme-color"]').content = getComputedStyle(root).getPropertyValue('--bg').trim();
  }
  apply(root.classList.contains('dark') ? 'dark' : 'light');
  btn.addEventListener('click', () => {
    const th = root.classList.contains('dark') ? 'light' : 'dark';
    apply(th);
    try { localStorage.setItem('ozwh-theme', th); } catch (e) {}
  });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    let saved; try { saved = localStorage.getItem('ozwh-theme'); } catch (x) {}
    if (!saved) apply(e.matches ? 'dark' : 'light');
  });
})();

let timer;
$('q').addEventListener('input', (e) => {
  clearTimeout(timer);
  $('clear').hidden = !e.target.value;
  timer = setTimeout(() => { state.q = e.target.value; state.dept = ''; state.shown = PAGE; render(); }, 150);
});
$('clear').addEventListener('click', () => { $('q').value = ''; $('clear').hidden = true; state.q = ''; state.shown = PAGE; render(); $('q').focus(); });
$('sort').addEventListener('change', (e) => { state.sort = e.target.value; state.shown = PAGE; render(); });
document.querySelector('.seg').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) setScope(b.dataset.scope); });
$('chips').addEventListener('click', (e) => { const b = e.target.closest('.chip'); if (b) { state.dept = b.dataset.dept; state.shown = PAGE; render(); } });
$('more').addEventListener('click', () => { state.shown += PAGE; render(); });
$('empty').addEventListener('click', (e) => { if (e.target.id === 'toAll') setScope('all'); });
document.querySelector('.lang-group').addEventListener('click', (e) => { const b = e.target.closest('.lang-btn'); if (b) setLang(b.dataset.lang); });
$('langSelect').addEventListener('change', (e) => setLang(e.target.value));
main();
