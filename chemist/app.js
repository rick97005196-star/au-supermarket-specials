// 小黃屋特價查詢 — data/products.json is made by scripts/build_chemist.py
'use strict';
const DEPTS = [
  ['vitamins', '維他命保健'], ['medicine', '藥品'], ['health', '健康用品'], ['baby', '孕期母嬰'],
  ['skin', '護膚防曬'], ['makeup', '彩妝美甲'], ['hair', '頭髮護理'], ['fragrance', '香水'], ['oral', '口腔'],
  ['sports', '運動營養'], ['appliance', '電器'], ['pet', '寵物'], ['other', '其他'],
];
const DEPT_NAME = Object.fromEntries(DEPTS);
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
const PAGE = 60;
const $ = (id) => document.getElementById(id);
let ALL = [], SPECIALS = [];
const state = { scope: 'special', dept: '', q: '', sort: 'pop', shown: PAGE };

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

// "Thu 12 Nov 2026 - Wed 25 Nov 2026" -> "11月12日 – 11月25日"
function heroDate(r) {
  const M = { Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6, Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12 };
  const p = [...String(r || '').matchAll(/(\d{1,2})\s+([A-Za-z]{3})/g)].slice(0, 2);
  return p.length === 2 ? p.map((m) => `${M[m[2]]}月${m[1]}日`).join(' – ') : (r || '');
}
function ago(d) {
  const min = Math.max(0, Math.round((Date.now() - d.getTime()) / 60000));
  if (min < 60) return `${min} 分鐘前更新`;
  if (min < 48 * 60) return `${Math.round(min / 60)} 小時前更新`;
  return `${Math.round(min / 1440)} 天前更新`;
}

function terms(q) {
  // every word must match; a Chinese word may match any of its English words
  const out = [];
  let rest = norm(q).trim();
  for (const k of Object.keys(ZH).sort((a, b) => b.length - a.length)) {
    if (rest.includes(k)) { out.push(ZH[k].split('|').map(norm)); rest = rest.split(k).join(' '); }
  }
  for (const w of rest.split(/\s+/)) if (w) out.push([w]);
  return out;
}
function matches(it, groups) {
  return groups.every((alts) => alts.some((a) => it._s.includes(a)));
}

function render() {
  const groups = state.q ? terms(state.q) : [];
  const base = state.scope === 'special' ? SPECIALS : ALL;
  const hit = base.filter((it) => (!groups.length || matches(it, groups)));
  // department counts for what the search found
  const byDept = {};
  for (const it of hit) byDept[it.dept] = (byDept[it.dept] || 0) + 1;
  let list = state.dept ? hit.filter((it) => it.dept === state.dept) : hit;
  const s = state.sort;
  list = list.slice().sort((a, b) => {
    if (!!b.special !== !!a.special) return b.special ? 1 : -1;      // specials first
    if (!a.special) return a._i - b._i;                                 // already in name order
    if (s === 'save') return (b.save_amount || 0) - (a.save_amount || 0) || (b.pop || 0) - (a.pop || 0);
    if (s === 'low') return (a.price || 0) - (b.price || 0);
    if (s === 'name') return (a.zh || a.title).localeCompare(b.zh || b.title, 'zh-Hant');
    return (b.pop || 0) - (a.pop || 0) || (b.save_amount || 0) - (a.save_amount || 0);
  });

  $('chips').innerHTML = [`<button type="button" class="chip" data-dept="" aria-pressed="${!state.dept}">全部<small>${hit.length}</small></button>`]
    .concat(DEPTS.filter(([k]) => byDept[k] || state.dept === k)
      .map(([k, n]) => `<button type="button" class="chip" data-dept="${k}" aria-pressed="${state.dept === k}">${n}<small>${byDept[k] || 0}</small></button>`)).join('');

  const nSp = list.filter((x) => x.special).length;
  $('count').textContent = list.length ? (state.scope === 'all' ? `${list.length.toLocaleString()} 件商品，其中 ${nSp} 件有型錄特價` : `${list.length} 件型錄特價`) : '';
  $('grid').innerHTML = list.slice(0, state.shown).map(card).join('');
  $('more').hidden = list.length <= state.shown;
  $('more').textContent = `顯示更多（還有 ${(list.length - state.shown).toLocaleString()} 件）`;
  const empty = $('empty');
  empty.hidden = list.length > 0;
  if (!list.length && state.scope === 'special' && groups.length) {
    const n = ALL.filter((it) => !it.special && matches(it, groups)).length;
    empty.innerHTML = n ? `這次型錄沒有符合的特價。<br><button type="button" class="linkbtn" id="toAll">看全部商品裡的 ${n} 件 ›</button>` : '找不到符合的商品，試試英文品牌名。';
  } else if (!list.length) empty.textContent = '找不到符合的商品，試試英文品牌名。';
}

function priceHTML(display, price) {
  // "$5.50" -> <sup>$</sup>5<sup>.50</sup> like the supermarket site; "2 for $36.99" / "From $9.99" kept in words
  const txt = display || money(price);
  const m = txt.match(/^(From\s+)?\$(\d+)(?:\.(\d{2}))?$/i);
  if (m) return `<sup>$</sup>${m[2]}${m[3] ? `<sup>.${m[3]}</sup>` : ''}${m[1] ? '<small>起</small>' : ''}`;
  const two = txt.match(/^(\d+)\s*for\s*\$([\d.]+)$/i);
  if (two) return `<sup>$</sup>${esc(two[2])}<small>${esc(two[1])} 件</small>`;
  return esc(txt);
}

function card(it) {
  const url = safeUrl(it.url);
  const open = (cls) => (url ? `<a class="card ${cls}" href="${esc(url)}" target="_blank" rel="noopener">` : `<div class="card ${cls}">`);
  const close = url ? '</a>' : '</div>';
  const dept = `<div class="dept">${esc(DEPT_NAME[it.dept] || '')}</div>`;
  if (!it.special) {
    // the shop's own product photo (same address pattern as its product pages); hidden if there is none
    const thumb = /^\d+$/.test(it.pid) ? `<span class="thumb"><img src="https://static.chemistwarehouse.com.au/ams/media/pi/${it.pid}/2DF_200.jpg" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.parentNode.remove()"></span>` : '';
    return `${open('row')}${thumb}<div class="info">${dept}<div class="zh">${esc(it.title)}</div></div><span class="go">官網看價 ↗</span>${close}`;
  }
  const img = safeUrl(it.image_url, true);
  const pic = `<div class="pic">${img ? `<img src="${esc(img)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">` : ''}</div>`;
  const half = /1\/2 price/i.test(it.discount_desc);
  const badge = half ? '<span class="badge half">半價</span>' : (it.period === 'next' ? '<span class="badge">下一檔型錄</span>' : '');
  const title = it.zh ? `<div class="zh">${esc(it.zh)}</div><div class="en">${esc(it.title)}</div>` : `<div class="zh">${esc(it.title)}</div>`;
  let extra = '<span class="special-note">型錄特價</span>';
  if (it.was_price > 0 && it.save_amount > 0) {
    const lab = /off RRP/i.test(it.discount_desc) ? '建議售價' : '原價';
    extra = `<span class="was">${lab} <s>${money(it.was_price)}</s></span><span class="save">省 ${money(it.save_amount)}</span>`;
  }
  return `${open('')}${pic}${badge}${dept}${title}<div class="price"><div class="now">${priceHTML(it.price_display, it.price)}</div>${extra}</div>${close}`;
}

function setScope(scope) {
  state.scope = scope; state.dept = ''; state.shown = PAGE;
  document.querySelectorAll('.seg-btn').forEach((b) => { const on = b.dataset.scope === scope; b.setAttribute('aria-selected', String(on)); b.classList.toggle('is-active', on); });
  render();
}

async function main() {
  let data;
  try {
    const r = await fetch('data/products.json', { cache: 'no-cache' });
    data = await r.json();
  } catch (e) {
    $('heroDate').textContent = '資料載入失敗，請重新整理';
    return;
  }
  SPECIALS = (data.specials || []).map((x) => Object.assign(x, { special: true }));
  // other products come compact: [product number, link text, department]
  const depts = data.depts || [];
  const listed = (data.products || []).map((r, i) => ({
    pid: r[0], title: nameFromSlug(r[1]), url: `https://www.chemistwarehouse.com.au/buy/${r[0]}/${r[1]}`,
    dept: depts[r[2]] || 'other', _i: i,
  }));
  ALL = SPECIALS.concat(listed);
  for (const it of ALL) it._s = norm(`${it.title} ${it.zh || ''} ${DEPT_NAME[it.dept] || ''}`);
  $('heroDate').textContent = (data.date_ranges || []).map(heroDate).join('、') || '小黃屋特價';
  $('statSpecial').textContent = SPECIALS.length;
  $('statSave').textContent = SPECIALS.filter((x) => x.save_amount > 0).length;
  $('statHalf').textContent = SPECIALS.filter((x) => /1\/2 price/i.test(x.discount_desc)).length;
  $('statAll').textContent = ALL.length.toLocaleString();
  $('nSpecial').textContent = SPECIALS.length;
  $('nAll').textContent = ALL.length.toLocaleString();
  if (!(data.products || []).length) $('nAll').textContent = SPECIALS.length;
  const d = data.updated ? new Date(data.updated) : null;
  if (d && !isNaN(d)) $('updatedAgo').textContent = ago(d);
  if (d && !isNaN(d)) $('updated').textContent = `資料更新：${d.toLocaleString('zh-TW', { timeZone: 'Australia/Sydney', dateStyle: 'medium', timeStyle: 'short' })}（雪梨時間）`;
  render();
}

let timer;
$('q').addEventListener('input', (e) => {
  clearTimeout(timer);
  $('clear').hidden = !e.target.value;
  timer = setTimeout(() => { state.q = e.target.value; state.dept = ''; state.shown = PAGE; render(); }, 150);
});
$('clear').addEventListener('click', () => { $('q').value = ''; $('clear').hidden = true; state.q = ''; state.shown = PAGE; render(); $('q').focus(); });
$('sort').addEventListener('change', (e) => { state.sort = e.target.value; state.shown = PAGE; render(); });
document.querySelector('.seg').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) setScope(b.dataset.scope); });
['魚油', '維他命', '益生菌', '膠原蛋白', '防曬', '止痛', '感冒', '牙膏', '香水', 'Swisse'].forEach((w) => {
  const b = document.createElement('button'); b.type = 'button'; b.textContent = w;
  b.addEventListener('click', () => { $('q').value = w; $('clear').hidden = false; state.q = w; state.dept = ''; state.shown = PAGE; render(); });
  $('hot').appendChild(b);
});
$('chips').addEventListener('click', (e) => { const b = e.target.closest('.chip'); if (b) { state.dept = b.dataset.dept; state.shown = PAGE; render(); } });
$('more').addEventListener('click', () => { state.shown += PAGE; render(); });
$('empty').addEventListener('click', (e) => { if (e.target.id === 'toAll') setScope('all'); });
main();
