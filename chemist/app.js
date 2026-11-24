// 小黃屋特價查詢 — data/products.json is made by scripts/build_chemist.py
'use strict';
const DEPTS = [
  ['vitamins', '維他命保健'], ['medicine', '藥品'], ['baby', '孕期母嬰'], ['skin', '護膚防曬'],
  ['makeup', '彩妝'], ['hair', '頭髮護理'], ['fragrance', '香水'], ['oral', '口腔'],
  ['sports', '運動營養'], ['appliance', '電器'], ['other', '其他'],
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
function dateZh(r) {
  // "Thu 12 Nov 2026 - Wed 25 Nov 2026" -> "11/12（四）到 11/25（三）"
  const M = { Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6, Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12 };
  const W = { Mon: '一', Tue: '二', Wed: '三', Thu: '四', Fri: '五', Sat: '六', Sun: '日' };
  const p = String(r || '').split(/\s+-\s+/).map((s) => s.match(/^(\w{3})\s+(\d{1,2})\s+(\w{3})/));
  if (p.length !== 2 || !p[0] || !p[1]) return r || '';
  const f = (m) => `${M[m[3]] || m[3]}/${m[2]}（${W[m[1]] || m[1]}）`;
  return `${f(p[0])}到 ${f(p[1])}`;
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
    if (!a.special) return a.title.localeCompare(b.title);
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

function card(it) {
  const url = safeUrl(it.url);
  const tagOpen = url ? `<a class="card" href="${esc(url)}" target="_blank" rel="noopener">` : '<div class="card">';
  const tagClose = url ? '</a>' : '</div>';
  const img = safeUrl(it.image_url, true);
  const pic = img ? `<div class="pic"><img src="${esc(img)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer"></div>` : '';
  const zh = it.zh ? `<div class="zh">${esc(it.zh)}</div>` : '';
  const en = `<div class="${it.zh ? 'en' : 'zh'}">${esc(it.title)}</div>`;
  if (!it.special) {
    return `${tagOpen}<div class="info">${en}<div class="dept">${esc(DEPT_NAME[it.dept] || '')}</div><div class="go">目前沒有型錄特價・<b>到官網看價格</b> ↗</div></div>${tagClose}`;
  }
  let now = esc(it.price_display || money(it.price));
  if (/^From\s+/i.test(it.price_display || '')) now = esc(it.price_display.replace(/^From\s+/i, '')) + ' 起';
  let extra = '';
  if (it.was_price > 0 && it.save_amount > 0) {
    const lab = /off RRP/i.test(it.discount_desc) ? '建議售價' : '原價';
    const half = /1\/2 price/i.test(it.discount_desc) ? '半價・' : '';
    extra = `<span class="was">${lab} ${money(it.was_price)}</span><span class="save">${half}省 ${money(it.save_amount)}</span>`;
  }
  const tag = it.period === 'next' ? '下一檔型錄' : '型錄特價';
  return `${tagOpen}${pic}<div class="info"><span class="tag">${tag}</span>${zh}${en}<div class="price"><span class="now">${now}</span>${extra}</div></div>${tagClose}`;
}

function setScope(scope) {
  state.scope = scope; state.dept = ''; state.shown = PAGE;
  document.querySelectorAll('.seg button').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.scope === scope)));
  render();
}

async function main() {
  let data;
  try {
    const r = await fetch('data/products.json', { cache: 'no-cache' });
    data = await r.json();
  } catch (e) {
    $('sub').textContent = '資料載入失敗，請重新整理。';
    return;
  }
  SPECIALS = (data.specials || []).map((x) => Object.assign(x, { special: true }));
  ALL = SPECIALS.concat(data.products || []);
  for (const it of ALL) it._s = norm(`${it.title} ${it.zh || ''} ${DEPT_NAME[it.dept] || ''}`);
  const ranges = (data.date_ranges || []).map(dateZh).join('、');
  $('sub').textContent = `本期型錄 ${ranges}，${SPECIALS.length} 件特價`;
  $('nSpecial').textContent = SPECIALS.length;
  $('nAll').textContent = ALL.length.toLocaleString();
  if (!(data.products || []).length) $('nAll').textContent = SPECIALS.length;
  const d = data.updated ? new Date(data.updated) : null;
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
$('chips').addEventListener('click', (e) => { const b = e.target.closest('.chip'); if (b) { state.dept = b.dataset.dept; state.shown = PAGE; render(); } });
$('more').addEventListener('click', () => { state.shown += PAGE; render(); });
$('empty').addEventListener('click', (e) => { if (e.target.id === 'toAll') setScope('all'); });
main();
