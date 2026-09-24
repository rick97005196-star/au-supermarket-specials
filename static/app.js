// State
var currentLang = (typeof window !== 'undefined' && window.currentLang) || (typeof localStorage !== 'undefined' && localStorage.getItem('lang')) || 'zh';
let currentPeriod = 'current'; // 'current' or 'next'
let currentStore = 'All';
let currentCategory = 'all';
let currentSearch = '';
let searchTimeout = null;
let isUpdating = false;
let globalStats = null;
let isStaticMode = false;
let staticSpecials = [];
const DEFAULT_FALLBACK_IMG = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 300' width='300' height='300'%3E%3Crect width='300' height='300' fill='%23f8fafc'/%3E%3Cpath d='M100 110 h100 v12 h-100 z M90 135 h120 v90 c0 10 -8 18 -18 18 h-84 c-10 0 -18 -8 -18 -18 z' fill='%23e2e8f0'/%3E%3Cpath d='M130 110 v-20 c0 -11 9 -20 20 -20 s20 9 20 20 v20' fill='none' stroke='%2394a3b8' stroke-width='8' stroke-linecap='round'/%3E%3Ctext x='150' y='270' font-family='system-ui, -apple-system, sans-serif' font-size='13' font-weight='600' fill='%2394a3b8' text-anchor='middle'%3EAU Specials%3C/text%3E%3C/svg%3E";

// Categories definition (Aligned with Australian Supermarket Departments)
const CATEGORY_KEYS = [
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
];

// Scroll & Back to Top Management
function initScrollListeners() {
    const backToTopBtn = document.getElementById('backToTopBtn');
    if (!backToTopBtn) return;

    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            backToTopBtn.classList.remove('translate-y-16', 'opacity-0', 'pointer-events-none');
            backToTopBtn.classList.add('translate-y-0', 'opacity-100', 'pointer-events-auto');
        } else {
            backToTopBtn.classList.add('translate-y-16', 'opacity-0', 'pointer-events-none');
            backToTopBtn.classList.remove('translate-y-0', 'opacity-100', 'pointer-events-auto');
        }
    }, { passive: true });
}

function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Language Management
function initLanguage() {
    currentLang = localStorage.getItem('lang') || 'zh';
    applyLanguage(currentLang);
}

function setLanguage(lang) {
    if (currentLang === lang) return;
    currentLang = lang;
    localStorage.setItem('lang', lang);
    applyLanguage(lang);
    renderCategoryBar();
    updateStatsDisplay();
    renderAnnouncement();
    renderProductsCurrent();
    loadShoppingList();
    if (currentModalItem) {
        openProductModal(currentModalItem);
    }
}

function applyLanguage(lang) {
    // Update language switcher active styles
    document.querySelectorAll('.lang-btn').forEach(btn => {
        if (btn.dataset.lang === lang) {
            btn.className = "lang-btn px-2.5 py-1 rounded-lg transition bg-white dark:bg-zinc-700 text-slate-900 dark:text-white shadow-2xs font-bold";
        } else {
            btn.className = "lang-btn px-2.5 py-1 rounded-lg transition text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white";
        }
    });

    // Update text content of all elements with data-i18n
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        el.textContent = t(key);
    });

    // Update placeholders
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.placeholder = t('search_placeholder');
    }
    const emailInput = document.getElementById('shoppingEmailInput');
    if (emailInput) {
        emailInput.placeholder = t('email_placeholder');
    }

    // Update dynamic tooltips & period badges
    const backToTopBtn = document.getElementById('backToTopBtn');
    if (backToTopBtn) {
        backToTopBtn.title = t('back_to_top');
    }
    const drawerClearBtn = document.querySelector('button[onclick="clearShoppingList()"]');
    if (drawerClearBtn) {
        drawerClearBtn.title = t('clear_manifest');
    }

    updatePeriodBadges();
}

function updatePeriodBadges() {
    const key = currentPeriod === 'current' ? 'current_cycle' : 'next_cycle';
    const headerBadge = document.getElementById('headerPeriodBadge');
    if (headerBadge) {
        headerBadge.textContent = t(key);
    }
    const periodIndicator = document.getElementById('periodIndicatorBadge');
    if (periodIndicator) {
        const activeInfo = globalStats ? (currentPeriod === 'current' ? globalStats.current : globalStats.next) : null;
        const activeRangeText = (activeInfo && activeInfo.date_range) ? activeInfo.date_range : '';
        periodIndicator.textContent = activeRangeText ? `${t(key)} (${activeRangeText})` : t(key);
    }
}

const CATEGORY_STYLES = {
    'all': {
        emoji: '✨',
        iconBg: 'bg-emerald-50 dark:bg-emerald-950/80 border-emerald-200/80 dark:border-emerald-800/80 text-emerald-700 dark:text-emerald-300'
    },
    'produce': {
        emoji: '🥦',
        iconBg: 'bg-emerald-50 dark:bg-emerald-950/80 border-emerald-200/80 dark:border-emerald-800/80 text-emerald-700 dark:text-emerald-300'
    },
    'meat': {
        emoji: '🥩',
        iconBg: 'bg-rose-50 dark:bg-rose-950/80 border-rose-200/80 dark:border-rose-800/80 text-rose-700 dark:text-rose-300'
    },
    'seafood': {
        emoji: '🦐',
        iconBg: 'bg-cyan-50 dark:bg-cyan-950/80 border-cyan-200/80 dark:border-cyan-800/80 text-cyan-700 dark:text-cyan-300'
    },
    'dairy_eggs': {
        emoji: '🥛',
        iconBg: 'bg-amber-50 dark:bg-amber-950/80 border-amber-200/80 dark:border-amber-800/80 text-amber-700 dark:text-amber-300'
    },
    'bakery': {
        emoji: '🥖',
        iconBg: 'bg-amber-50 dark:bg-amber-950/80 border-amber-200/80 dark:border-amber-800/80 text-amber-800 dark:text-amber-300'
    },
    'frozen': {
        emoji: '🧊',
        iconBg: 'bg-blue-50 dark:bg-blue-950/80 border-blue-200/80 dark:border-blue-800/80 text-blue-700 dark:text-blue-300'
    },
    'pantry': {
        emoji: '🍚',
        iconBg: 'bg-orange-50 dark:bg-orange-950/80 border-orange-200/80 dark:border-orange-800/80 text-orange-700 dark:text-orange-300'
    },
    'snacks': {
        emoji: '🍫',
        iconBg: 'bg-purple-50 dark:bg-purple-950/80 border-purple-200/80 dark:border-purple-800/80 text-purple-700 dark:text-purple-300'
    },
    'drinks': {
        emoji: '🥤',
        iconBg: 'bg-teal-50 dark:bg-teal-950/80 border-teal-200/80 dark:border-teal-800/80 text-teal-700 dark:text-teal-300'
    },
    'liquor': {
        emoji: '🍺',
        iconBg: 'bg-yellow-50 dark:bg-yellow-950/80 border-yellow-200/80 dark:border-yellow-800/80 text-yellow-800 dark:text-yellow-300'
    },
    'health_vitamins': {
        emoji: '💊',
        iconBg: 'bg-pink-50 dark:bg-pink-950/80 border-pink-200/80 dark:border-pink-800/80 text-pink-700 dark:text-pink-300'
    },
    'household': {
        emoji: '🧺',
        iconBg: 'bg-indigo-50 dark:bg-indigo-950/80 border-indigo-200/80 dark:border-indigo-800/80 text-indigo-700 dark:text-indigo-300'
    },
    'pet': {
        emoji: '🐾',
        iconBg: 'bg-lime-50 dark:bg-lime-950/80 border-lime-200/80 dark:border-lime-800/80 text-lime-800 dark:text-lime-300'
    }
};

function getCleanCategoryLabel(catKey) {
    const raw = getCategoryName(catKey);
    return raw.replace(/^[\p{Emoji}\p{Extended_Pictographic}\u200d\uFE0F\s]+/u, '').trim() || raw;
}

// Render Categories Bar (2 Rows: Row 1 Fresh & Perishables, Row 2 Pantry, Drinks, Liquor, Home & Pet)
function renderCategoryBar() {
    const bar = document.getElementById('categoryBar');
    if (!bar) return;

    const activeClasses = "flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-1.5 rounded-2xl text-[11px] sm:text-xs font-bold bg-gradient-to-r from-emerald-600 via-emerald-600 to-teal-600 text-white shadow-[0_4px_16px_-2px_rgba(16,185,129,0.35)] ring-2 ring-emerald-400/50 border border-emerald-500/80 shrink-0 transition-all duration-200 active:scale-95 whitespace-nowrap scale-[1.03]";
    const inactiveClasses = "flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-1.5 rounded-2xl text-[11px] sm:text-xs font-semibold bg-white/90 dark:bg-[#15171a] hover:bg-slate-50 dark:hover:bg-zinc-800/90 text-slate-700 dark:text-zinc-200 border border-slate-200/80 dark:border-white/[0.08] hover:border-slate-300 dark:hover:border-zinc-700 shrink-0 transition-all duration-200 active:scale-95 whitespace-nowrap shadow-[0_1px_3px_rgba(0,0,0,0.03)]";

    const renderBtnContent = (btn, catKey, isActive) => {
        const style = CATEGORY_STYLES[catKey] || { emoji: '🏷️', iconBg: 'bg-slate-50 border-slate-200 text-slate-700' };
        const label = getCleanCategoryLabel(catKey);
        const iconClasses = isActive
            ? 'w-5 h-5 sm:w-6 sm:h-6 rounded-xl bg-white/20 border border-white/30 text-white flex items-center justify-center text-xs sm:text-sm shrink-0 shadow-2xs backdrop-blur-xs'
            : `w-5 h-5 sm:w-6 sm:h-6 rounded-xl border flex items-center justify-center text-xs sm:text-sm shrink-0 shadow-2xs ${style.iconBg}`;

        btn.innerHTML = `
            <span class="${iconClasses}">
                ${style.emoji}
            </span>
            <span class="truncate tracking-tight font-medium">${label}</span>
        `;
    };

    const existingBtns = bar.querySelectorAll('button');
    if (existingBtns.length === CATEGORY_KEYS.length) {
        existingBtns.forEach(btn => {
            const catKey = btn.dataset.cat;
            const isActive = currentCategory === catKey;
            btn.className = isActive ? activeClasses : inactiveClasses;
            renderBtnContent(btn, catKey, isActive);
        });
        return;
    }

    bar.innerHTML = '';
    
    // Arrange into 2 rows: Row 1: All -> 蔬菜水果 -> 肉品 -> 海鮮水產 -> 蛋奶製品 -> 麵包烘焙 -> 冷凍食品 (7 items)
    // Row 2: 糧油調味 -> 休閒零食 -> 飲料 -> 酒類 -> 美妝保健 -> 日用清潔 -> 寵物用品 (7 items)
    const row1Keys = ['all', 'produce', 'meat', 'seafood', 'dairy_eggs', 'bakery', 'frozen'];
    const row2Keys = ['pantry', 'snacks', 'drinks', 'liquor', 'health_vitamins', 'household', 'pet'];
    
    const orderedKeys = [];
    for (let i = 0; i < row1Keys.length; i++) {
        orderedKeys.push(row1Keys[i]);
        if (i < row2Keys.length) {
            orderedKeys.push(row2Keys[i]);
        }
    }

    orderedKeys.forEach(catKey => {
        const btn = document.createElement('button');
        const isActive = currentCategory === catKey;

        btn.dataset.cat = catKey;
        btn.className = isActive ? activeClasses : inactiveClasses;
        renderBtnContent(btn, catKey, isActive);
        btn.onclick = () => selectCategory(catKey);
        bar.appendChild(btn);
    });
}

function selectCategory(catKey) {
    currentCategory = catKey;
    renderCategoryBar();

    // Smooth scroll the categoryBar HORIZONTALLY only - NEVER scroll the page window!
    const bar = document.getElementById('categoryBar');
    if (bar) {
        const activeBtn = bar.querySelector(`[data-cat="${catKey}"]`);
        if (activeBtn) {
            const scrollLeft = activeBtn.offsetLeft - (bar.clientWidth / 2) + (activeBtn.clientWidth / 2);
            bar.scrollTo({ left: scrollLeft, behavior: 'smooth' });
        }
    }

    loadSpecials();
}

// Theme Management (Dark / Light Mode)
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        applyTheme('dark');
    } else {
        applyTheme('light');
    }
}

function toggleDarkMode() {
    const isDark = document.documentElement.classList.contains('dark');
    applyTheme(isDark ? 'light' : 'dark');
}

function applyTheme(theme) {
    const icon = document.getElementById('themeIcon');
    if (theme === 'dark') {
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
        localStorage.setItem('theme', 'dark');
        if (icon) icon.className = 'fa-solid fa-sun text-amber-400 text-xs';
    } else {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
        localStorage.setItem('theme', 'light');
        if (icon) icon.className = 'fa-solid fa-moon text-slate-600 text-xs';
    }
}

// Toast notification
function showToast(message, icon = 'fa-circle-check', isError = false) {
    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toastMessage');
    const toastIcon = document.getElementById('toastIcon');

    toastMsg.textContent = message;
    toastIcon.className = `fa-solid ${icon} ${isError ? 'text-rose-400' : 'text-emerald-400 dark:text-emerald-500'}`;
    
    toast.classList.remove('hidden');
    toast.classList.add('flex');
    
    setTimeout(() => {
        toast.classList.add('hidden');
        toast.classList.remove('flex');
    }, 2500);
}

// Client-side Multilingual Dictionary for Cloudflare Pages Static Mode
const CLIENT_MULTILINGUAL = {
    '牛奶': 'milk', '鮮奶': 'milk', '蛋': 'egg', '雞蛋': 'egg', '雞肉': 'chicken', '牛肉': 'beef', '豬肉': 'pork', '羊肉': 'lamb', '魚': 'fish', '鮭魚': 'salmon',
    '咖啡': 'coffee', '茶': 'tea', '麵包': 'bread', '奶油': 'butter', '起司': 'cheese', '冰淇淋': 'ice cream', '洋芋片': 'chips', '巧克力': 'chocolate',
    '衛生紙': 'toilet paper', '洗衣精': 'laundry', '洗碗精': 'dishwash', '洗髮精': 'shampoo', '沐浴乳': 'body wash', '牙膏': 'toothpaste',
    '牛乳': 'milk', '卵': 'egg', '鶏肉': 'chicken', 'サーモン': 'salmon', '豚肉': 'pork', 'お茶': 'tea', 'パン': 'bread', 'チーズ': 'cheese',
    '우유': 'milk', '계란': 'egg', '닭고기': 'chicken', '치킨': 'chicken', '소고기': 'beef', '연어': 'salmon', '커피': 'coffee', '라면': 'noodles'
};

function translateQueryClient(q) {
    if (!q) return '';
    let res = q.trim().toLowerCase();
    for (const [term, en] of Object.entries(CLIENT_MULTILINGUAL)) {
        if (res.includes(term)) {
            res = res.replace(term, ` ${en} `);
        }
    }
    return res.trim();
}

// In-memory high-speed cache for static JSON files
const staticJsonCache = new Map();

// Helper to fetch static JSON that works seamlessly on both local server and Cloudflare Pages
async function fetchStaticJson(filename) {
    if (staticJsonCache.has(filename)) {
        return staticJsonCache.get(filename);
    }
    const candidates = [
        `/data/${filename}`,
        `/static/data/${filename}`,
        `data/${filename}`
    ];
    for (const url of candidates) {
        try {
            const res = await fetch(url);
            const contentType = res.headers.get('content-type') || '';
            // Prevent parsing HTML 404 fallback as JSON
            if (res.ok && !contentType.includes('text/html')) {
                const data = await res.json();
                staticJsonCache.set(filename, data);
                return data;
            }
        } catch (e) {}
    }
    return null;
}

// Translations Management
let productTranslations = {};

async function loadTranslations() {
    try {
        const data = await fetchStaticJson('translations.json');
        if (data) {
            productTranslations = data;
        }
    } catch (e) {
        console.log('Failed to load translations.json', e);
    }
}

function getProductTranslation(item, lang) {
    if (!item || !lang || lang === 'en') return null;
    let t = item.translations;
    if (typeof t === 'string') {
        try { t = JSON.parse(t); } catch (e) {}
    }
    if (t && typeof t === 'object' && t[lang]) {
        return t[lang];
    }
    if (productTranslations && productTranslations[item.title]) {
        return productTranslations[item.title][lang] || null;
    }
    return null;
}

// Stats & Metadata
async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) throw new Error('API not available');
        globalStats = await res.json();
        updateStatsDisplay();
    } catch (e) {
        console.log('API /api/stats unavailable, falling back to static stats.json');
        isStaticMode = true;
        try {
            const data = await fetchStaticJson('stats.json');
            if (data) {
                globalStats = data;
                updateStatsDisplay();
            }
        } catch (err) {
            console.error('Failed to load static stats', err);
        }
    }
}

function updateStatsDisplay() {
    if (!globalStats) return;

    const currentData = globalStats.current || {};
    const nextData = globalStats.next || {};

    const currDateStr = currentData.date_range || '';
    const nextDateStr = nextData.date_range || '';

    if (currDateStr) {
        document.getElementById('periodDateCurrentBadge').textContent = `(${currDateStr.replace(' 2026', '')})`;
    }
    const nextBadgeEl = document.getElementById('periodDateNextBadge');
    if (nextBadgeEl) {
        if (nextData.total > 0 && nextDateStr && !nextDateStr.includes('尚未') && !nextDateStr.includes('公佈')) {
            nextBadgeEl.textContent = `(${nextDateStr.replace(' 2026', '')})`;
        } else {
            nextBadgeEl.textContent = t('not_released_yet');
        }
    }

    const activeInfo = currentPeriod === 'current' ? currentData : nextData;
    let activeRangeText = activeInfo.date_range || (currentPeriod === 'current' ? t('current_cycle') : t('next_cycle'));
    if (currentPeriod === 'next' && (!activeInfo.total || activeInfo.total === 0)) {
        activeRangeText = currentLang === 'zh' ? '尚未公佈（預計週二釋出）' : (currentLang === 'ja' ? '未公開（火曜公開予定）' : (currentLang === 'ko' ? '미공개 (화요일 공개 예정)' : 'Not Released Yet'));
    }
    document.getElementById('activeDateRange').textContent = activeRangeText;

    const headerBadge = document.getElementById('headerPeriodBadge');
    const headerBadgeContainer = headerBadge ? headerBadge.parentElement : null;
    const periodIndicator = document.getElementById('periodIndicatorBadge');
    if (currentPeriod === 'current') {
        if (headerBadgeContainer) {
            headerBadgeContainer.className = "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-[10px] font-bold border border-emerald-500/20 shrink-0";
            const dot = headerBadgeContainer.querySelector('.rounded-full');
            if (dot) dot.className = "w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse";
        }
        if (headerBadge) headerBadge.textContent = t('current_cycle');
        if (periodIndicator) {
            periodIndicator.className = "text-[10px] sm:text-[11px] px-2.5 py-0.5 rounded-full font-bold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200/60 dark:border-emerald-800/60";
            periodIndicator.textContent = activeRangeText ? `${t('current_cycle')} (${activeRangeText})` : t('current_cycle');
        }
    } else {
        if (headerBadgeContainer) {
            headerBadgeContainer.className = "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-500/10 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400 text-[10px] font-bold border border-amber-500/20 shrink-0";
            const dot = headerBadgeContainer.querySelector('.rounded-full');
            if (dot) dot.className = "w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse";
        }
        if (headerBadge) headerBadge.textContent = t('next_cycle');
        if (periodIndicator) {
            periodIndicator.className = "text-[10px] sm:text-[11px] px-2.5 py-0.5 rounded-full font-bold bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200/60 dark:border-amber-800/60";
            periodIndicator.textContent = activeRangeText ? `${t('next_cycle')} (${activeRangeText})` : t('next_cycle');
        }
    }

    document.getElementById('statTotal').textContent = activeInfo.total || 0;
    document.getElementById('statHalfPrice').textContent = activeInfo.half_price_count || 0;
    
    const byStore = activeInfo.by_store || {};
    document.getElementById('statWoolies').textContent = byStore['Woolworths'] || 0;
    document.getElementById('statColes').textContent = byStore['Coles'] || 0;
    document.getElementById('statAldi').textContent = byStore['ALDI'] || 0;
}

// Period / Week Switcher
function selectPeriod(period) {
    if (currentPeriod === period) return;
    currentPeriod = period;

    const btnCurr = document.getElementById('tabPeriodCurrent');
    const btnNext = document.getElementById('tabPeriodNext');

    if (period === 'current') {
        btnCurr.className = "flex items-center justify-center gap-2 py-2 sm:py-2.5 px-3 sm:px-5 rounded-xl text-xs sm:text-sm font-black bg-emerald-600 dark:bg-emerald-600 text-white shadow-md ring-2 ring-emerald-400/50 border border-emerald-500 scale-[1.02] transition-all";
        const iconC = btnCurr.querySelector('i');
        if (iconC) iconC.className = "fa-regular fa-calendar-check text-white text-sm";

        btnNext.className = "flex items-center justify-center gap-2 py-2 sm:py-2.5 px-3 sm:px-5 rounded-xl text-xs sm:text-sm font-semibold text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/70 dark:hover:bg-zinc-700/70 transition-all opacity-80 hover:opacity-100";
        const iconN = btnNext.querySelector('i');
        if (iconN) iconN.className = "fa-solid fa-wand-magic-sparkles text-amber-500 text-sm";
    } else {
        btnNext.className = "flex items-center justify-center gap-2 py-2 sm:py-2.5 px-3 sm:px-5 rounded-xl text-xs sm:text-sm font-black bg-amber-500 dark:bg-amber-500 text-slate-950 shadow-md ring-2 ring-amber-300 border border-amber-400 scale-[1.02] transition-all";
        const iconN = btnNext.querySelector('i');
        if (iconN) iconN.className = "fa-solid fa-wand-magic-sparkles text-slate-950 text-sm";

        btnCurr.className = "flex items-center justify-center gap-2 py-2 sm:py-2.5 px-3 sm:px-5 rounded-xl text-xs sm:text-sm font-semibold text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/70 dark:hover:bg-zinc-700/70 transition-all opacity-80 hover:opacity-100";
        const iconC = btnCurr.querySelector('i');
        if (iconC) iconC.className = "fa-regular fa-calendar-check text-emerald-600 dark:text-emerald-400 text-sm";
    }

    updateStatsDisplay();
    loadSpecials();
}

// 1/2 Price Pill Toggle
function toggleHalfPricePill() {
    const checkbox = document.getElementById('halfPriceOnly');
    if (!checkbox) return;
    checkbox.checked = !checkbox.checked;
    updateHalfPricePillStyle();
    loadSpecials();
}

function updateHalfPricePillStyle() {
    const checkbox = document.getElementById('halfPriceOnly');
    const pill = document.getElementById('halfPricePill');
    if (!checkbox || !pill) return;
    if (checkbox.checked) {
        pill.className = "flex items-center gap-1.5 px-3 py-1 sm:py-1.5 rounded-xl font-black text-xs transition border border-rose-500 bg-rose-500 text-white shadow-xs active:scale-95";
    } else {
        pill.className = "flex items-center gap-1.5 px-3 py-1 sm:py-1.5 rounded-xl font-bold text-xs transition border border-slate-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 active:scale-95 shadow-2xs";
    }
}

// Hardware / Kitchenware Appliance Guard (Strictly exclude from grocery bestsellers)
const APPLIANCE_HARDWARE_REGEX = /\b(kettle\s*\d|electric\s*toothbrush|toothbrush\s*handle|saucepan|frypan|cookware|knife\s*block|toaster|air\s*fryer|steam\s*iron|vacuum|pillow|quilt|bedsheet|blanket|storage\s*box|clothes\s*airer|pressure\s*cooker|slow\s*cooker|blender|mixer|armor\s*all|car\s*wash|motor\s*oil|windscreen|protectant\s*spray|tyre\s*shine)\b/i;

// Tier 1: Australia's #1 National Consumer Superstars (Highest weekly supermarket grocery unit volume)
const SUPERSTAR_REGEX = /\b(shapes|red\s*rock\s*deli|coca-cola|coke|doritos|smith'?s|tim\s*tam|cadbury|magnum|drumstick|connoisseur|moccona|omo|cold\s*power|weet-bix|milo|vegemite|chobani|bega|western\s*star|dare|up\s*&\s*go|quilton|sorbent|morning\s*fresh|primo\s*(?:rindless|bacon|ham)|heinz\s*(?:ketchup|baked|beans|soup)|natural\s*confectionery|sour\s*patch|birds\s*eye|mccain|twinings|la\s*famiglia|helga'?s|tip\s*top|barilla|cobram\s*estate)\b|\bfinish\s*(?:quantum|powerball|ultimate|all\s*in\s*1|dishwasher|rinse\s*aid|tablets?|capsules?)\b|\bfairy\s*(?:platinum|dish|clean|laundry|capsules?|tablets?|wash)\b/i;

// Comprehensive Australian Supermarket Best-Sellers & Consumer Favorites Index
const POPULAR_REGEX = /\b(tim\s*tam|arnott'?s|shapes|jatz|clix|teevee|wagon\s*wheels?|cadbury|favourites|roses|twirl|flake|marvellous|red\s*rock(\s*deli)?|smith'?s|doritos|kettle\s*(?:chips?|potato|brand|sea\s*salt|honey)|cheezels|grain\s*waves|twisties|burger\s*rings|pods|maltesers|m&m'?s|skittles|allen'?s|lindt|ferrero|kinder|nutella|biscoff|oreo|kit\s*kat|mars|snickers|twix|pringles|weet-bix|sanitarium|corn\s*flakes|nutri-grain|coco\s*pops|special\s*k|sultana\s*bran|froot\s*loops|milo|nesquik|vegemite|promite|moccona|nescafe|vittoria|lavazza|grinders|l'or|starbucks|twinings|lipton|dilmah|tetley|bushells|carman'?s|uncle\s*tobys|barilla|san\s*remo|leggo'?s|dolmio|heinz|masterfoods|praise|hellmann'?s|sirena|john\s*west|greenseas|cobram\s*estate|moro|bertolli|crisco|campbell'?s|spam|old\s*el\s*paso|coca-cola|coke|pepsi|solo|sunkist|mountain\s*dew|7up|sprite|fanta|schweppes|bundaberg|mount\s*franklin|pump|cool\s*ridge|san\s*pellegrino|kirks|golden\s*circle|daily\s*juice|v\s*energy|red\s*bull|monster|dare|farmers\s*union\s*iced\s*coffee|oak\s*milk|ice\s*break|up\s*&\s*go|bega|mainland|cheer|cracker\s*barrel|mersey\s*valley|chobani|gippsland|dairy\s*farmers|jalna|western\s*star|lurpak|devondale|flora|nuttelex|philadelphia|perfect\s*italiano|d'orsogna|primo|don|magnum|cornetto|golden\s*gaytime|paddle\s*pop|blue\s*ribbon|connoisseur|peters|drumstick|maxibon|ben\s*&\s*jerry'?s|h[aä]agen-dazs|bulla|weis|birds\s*eye|ingham'?s|steggles|four'?n\s*twenty|patties|sara\s*lee|mccain|tip\s*top|helga|abbott|la\s*famiglia|wonder\s*white|mighty\s*soft|mr\s*kipling|finish\s*(?:quantum|powerball|ultimate|all\s*in\s*1|dishwasher|rinse)|fairy\s*(?:platinum|dish|clean|laundry|capsules?|tablets?)|omo|dynamo|cold\s*power|radiant|biozet|comfort|fluffy|cuddly|morning\s*fresh|dawn|palmolive|pine\s*o\s*cleen|dettol|domestos|harpic|duck|bref|ajax|glen\s*20|quilton|sorbent|kleenex|viva|handee|glad|swisse|blackmores|nature'?s\s*own|cenovis|centrum|berocca|colgate|oral-b|sensodyne|listerine|rexona|nivea|dove|lynx|gillette|schick|head\s*&\s*shoulders|pantene|l'or[eé]al|garnier|sunsilk|tresemme|radox|aveeno|cetaphil|qv|cancer\s*council|banana\s*boat|huggies|babylove|curash|bananas?|hass\s*avocados?|pink\s*lady\s*apples?|strawberries|blueberries|carrots?|potatoes?|broccoli|chicken\s*breast|beef\s*mince|rump\s*steak|rib\s*eye|atlantic\s*salmon|tiger\s*prawns?)\b/i;

function isItemPopular(it) {
    if (!it) return false;
    const title = it.title || '';
    if (APPLIANCE_HARDWARE_REGEX.test(title)) return false;
    if (/fairy\s*floss/i.test(title)) return false;
    if (it.is_popular === true) return true;
    return POPULAR_REGEX.test(title);
}

function calculatePopularityScore(it) {
    if (!it) return -999;
    if (typeof it.popularity_score === 'number' && it.popularity_score !== 0) {
        return it.popularity_score;
    }
    const title = it.title || '';
    if (APPLIANCE_HARDWARE_REGEX.test(title)) return -999;
    const isFairyFloss = /fairy\s*floss/i.test(title);
    
    let score = 0;
    if (SUPERSTAR_REGEX.test(title) && !isFairyFloss) {
        score += 200;
    } else if (POPULAR_REGEX.test(title) && !isFairyFloss) {
        score += 120;
    } else if (it.is_popular && !isFairyFloss) {
        score += 60;
    } else {
        return 0;
    }

    const price = typeof it.price === 'number' ? it.price : parseFloat(it.price) || 0;
    const was = typeof it.was_price === 'number' ? it.was_price : parseFloat(it.was_price) || 0;
    const save = typeof it.save_amount === 'number' ? it.save_amount : parseFloat(it.save_amount) || 0;
    const isHalf = isItemHalfPrice(it);

    if (isHalf) {
        score += 60;
    } else if (save > 0 && was > 0 && (save / was) >= 0.3) {
        score += 30;
    }

    if (price >= 1 && price <= 6) {
        score += 50;
    } else if (price > 6 && price <= 15) {
        score += 35;
    } else if (price > 15 && price <= 30) {
        score += 15;
    } else if (price > 30) {
        score -= 20;
    }

    if (was > 0 && save > 0) {
        score += Math.round((save / was) * 10);
    }

    // Category weighting for balanced supermarket popularity
    const cat = it.category || '';
    if (['bakery', 'produce', 'meat', 'dairy_eggs', 'seafood'].includes(cat)) {
        score += 25;
    } else if (['snacks', 'drinks', 'frozen', 'pantry'].includes(cat)) {
        score += 15;
    } else if (['household', 'health_vitamins'].includes(cat)) {
        score -= 10;
    }

    return score;
}

const KNOWN_SUPERMARKET_BRANDS = [
    'cadbury', 'arnott', 'shapes', 'tim tam', 'smith', 'red rock deli', 'doritos', 'kettle',
    'coca-cola', 'coke', 'pepsi', 'up&go', 'dare', 'chobani', 'bega', 'western star',
    'connoisseur', 'magnum', 'drumstick', 'peters', 'bulla', 'weis', 'ben & jerry',
    'birds eye', 'mccain', 'lavazza', 'moccona', 'nescafe', 'starbucks', 'vittoria', "l'or",
    'twinings', 'dilmah', 'tetley', 'omo', 'cold power', 'finish', 'fairy', 'morning fresh',
    'quilton', 'sorbent', 'kleenex', 'viva', 'ajax', 'harpic', 'bref', 'duck', 'cuddly', 'fluffy',
    'comfort', 'radiant', 'palmolive', 'colgate', 'oral-b', 'sensodyne', 'gillette', 'schick',
    'dettol', 'rexona', 'lynx', 'nivea', 'dove', 'garnier', 'mcobeauty', 'swisse', 'blackmores',
    "nature's own", 'cenovis', 'berocca', 'primo', 'don', "d'orsogna", 'weet-bix', 'sanitarium',
    'milo', 'vegemite', 'barilla', 'san remo', 'leggo', 'dolmio', 'cobram estate', 'moro',
    'la famiglia', 'helga', 'tip top', 'abbott', 'wonder white', 'sirena', 'john west',
    'greenseas', "four'n twenty", 'patties', 'carman', 'uncle tobys', 'kellogg',
    'kraft', 'philadelphia', 'lurpak', 'devondale', 'mainland', 'meredith dairy',
    'jalna', 'gippsland', 'danone', 'yoplait', 'nudie', 'daily juice', 'bundaberg',
    'red bull', 'monster', 'v energy', 'gatorade', 'powerade', 'schweppes', 'kirks',
    'mount franklin', 'pump', 'armor all', 'pine o cleen', 'bushman', 'aerogard'
];

function getProductFamilyKey(title) {
    const t = (title || '').toLowerCase();
    for (const b of KNOWN_SUPERMARKET_BRANDS) {
        if (t.includes(b)) return b;
    }
    const words = t.replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(Boolean);
    return words[0] || 'generic';
}

function createDiverseBestSellers(items) {
    if (!items || items.length <= 1) return items;

    // Strictly filter to genuine popular items ("不熱門就不用列入")
    const popularOnly = items.filter(it => isItemPopular(it) && calculatePopularityScore(it) > 0);
    if (popularOnly.length <= 1) return popularOnly;

    const brandCounts = new Map();
    const result = [];
    const isMultiCategory = new Set(popularOnly.map(x => x.category)).size > 2;

    if (isMultiCategory) {
        const CATEGORY_TARGETS = {
            'snacks': 16,
            'drinks': 16,
            'pantry': 12,
            'dairy_eggs': 10,
            'frozen': 10,
            'household': 8,
            'meat': 8,
            'bakery': 6,
            'health_vitamins': 6,
            'produce': 5,
            'seafood': 3
        };

        const byCat = {};
        for (const it of popularOnly) {
            const cat = it.category || 'other';
            if (!byCat[cat]) byCat[cat] = [];
            byCat[cat].push(it);
        }

        // Pass 1: Select up to category targets with max 2 per brand
        for (const [cat, target] of Object.entries(CATEGORY_TARGETS)) {
            const catList = byCat[cat] || [];
            let picked = 0;
            for (const it of catList) {
                if (picked >= target) break;
                const fam = getProductFamilyKey(it.title);
                const count = brandCounts.get(fam) || 0;
                if (count < 2) {
                    result.push(it);
                    brandCounts.set(fam, count + 1);
                    picked++;
                }
            }
        }

        // Pass 2: Fill remaining popular items (strictly max 2 per brand)
        const pickedSet = new Set(result);
        for (const it of popularOnly) {
            if (pickedSet.has(it)) continue;
            const fam = getProductFamilyKey(it.title);
            const count = brandCounts.get(fam) || 0;
            if (count < 2) {
                result.push(it);
                brandCounts.set(fam, count + 1);
                pickedSet.add(it);
            }
        }

        // Strictly sort by popularity score descending! ("越熱門的越上面 以此類推")
        result.sort((a, b) => {
            const scoreA = calculatePopularityScore(a);
            const scoreB = calculatePopularityScore(b);
            if (scoreB !== scoreA) return scoreB - scoreA;
            return (b.save_amount || 0) - (a.save_amount || 0);
        });

        return result;
    } else {
        // Single category view: max 2 per brand family
        for (const it of popularOnly) {
            const fam = getProductFamilyKey(it.title);
            const count = brandCounts.get(fam) || 0;
            if (count < 2) {
                result.push(it);
                brandCounts.set(fam, count + 1);
            }
        }

        result.sort((a, b) => {
            const scoreA = calculatePopularityScore(a);
            const scoreB = calculatePopularityScore(b);
            if (scoreB !== scoreA) return scoreB - scoreA;
            return (b.save_amount || 0) - (a.save_amount || 0);
        });

        return result;
    }
}

// Product Series Clustering (Groups identical product lines with different flavors/variants together)
function getProductSeriesKey(item) {
    if (!item) return '';
    let title = (item.title || '').toLowerCase()
        .replace(/['’]/g, '')
        .replace(/\b\d+([.-]\d+)?\s*(g|kg|ml|l|litre|liter|pack|pk|s|pieces|tablets|capsules|sheets|wipes)\b/gi, ' ')
        .replace(/\b\d+\s*[-–]\s*\d+\s*(g|kg|ml|l|litre|liter|pack|pk|s)?\b/gi, ' ')
        .replace(/\bpk\s*\d+([.-]\d+)?\b/gi, ' ')
        .replace(/\b\d+\s*pk\b/gi, ' ')
        .replace(/[^\w\s]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();

    if (title.includes('cadbury')) {
        if (title.includes('favourites')) return 'cadbury_favourites';
        if (title.includes('roses')) return 'cadbury_roses';
        if (title.includes('chocolate block') || title.includes('block')) return 'cadbury_blocks';
        if (title.includes('bar') || item.price <= 2.0) return 'cadbury_chocolate_bars';
        return 'cadbury_general';
    }
    if (title.includes('smith')) {
        if (title.includes('chips') || title.includes('crinkle')) return 'smiths_chips';
        return 'smiths_general';
    }
    if (title.includes('red rock deli')) {
        if (title.includes('chips')) return 'red_rock_deli_chips';
        if (title.includes('dip')) return 'red_rock_deli_dip';
        if (title.includes('crackers')) return 'red_rock_deli_crackers';
        return 'red_rock_deli_general';
    }
    if (title.includes('connoisseur')) return 'connoisseur_ice_cream';
    if (title.includes('magnum')) return 'magnum_ice_cream';
    if (title.includes('twinings')) return 'twinings_tea';
    if (title.includes('rexona')) return 'rexona_deodorant';
    if (title.includes('dove')) return 'dove_personal_care';
    if (title.includes('nivea')) return 'nivea_personal_care';
    if (title.includes('head & shoulders') || title.includes('head shoulders')) return 'head_shoulders_haircare';
    if (title.includes('pantene')) return 'pantene_haircare';
    if (title.includes('colgate')) return 'colgate_oralcare';
    if (title.includes('oral b') || title.includes('oral-b')) return 'oralb_oralcare';
    if (title.includes('morning fresh')) return 'morning_fresh_dish';
    if (title.includes('fairy')) return 'fairy_dish';
    if (title.includes('finish')) return 'finish_dish';
    if (title.includes('omo')) return 'omo_laundry';
    if (title.includes('cold power')) return 'cold_power_laundry';
    if (title.includes('dynamo')) return 'dynamo_laundry';
    if (title.includes('earthwise')) return 'earthwise_household';
    if (title.includes('quilton')) return 'quilton_paper';
    if (title.includes('sorbent')) return 'sorbent_paper';
    if (title.includes('kleenex')) return 'kleenex_paper';
    if (title.includes('gippsland')) return 'gippsland_dairy';
    if (title.includes('chobani')) return 'chobani_yoghurt';
    if (title.includes('dare')) return 'dare_iced_coffee';
    if (title.includes('ocean blue')) return 'ocean_blue_seafood';
    if (title.includes('doritos')) return 'doritos_chips';
    if (title.includes('tim tam')) return 'tim_tam';
    if (title.includes('shapes')) return 'arnotts_shapes';
    if (title.includes('vita gummies') || (title.includes('natures way') && title.includes('gummies'))) return 'natures_way_vita_gummies';
    if (title.includes('swisse')) return 'swisse_vitamins';
    if (title.includes('blackmores')) return 'blackmores_vitamins';
    if (title.includes('cenovis')) return 'cenovis_vitamins';
    if (title.includes('milo')) return 'milo_products';
    if (title.includes('moccona')) return 'moccona_coffee';
    if (title.includes('kewpie')) return 'kewpie_condiments';

    const variants = [
        'salt & vinegar', 'salt and vinegar', 'cheese & onion', 'cheese and onion',
        'sour cream & chives', 'sweet chilli & sour cream', 'sour cream', 'sweet chilli',
        'original', 'bbq', 'barbecue', 'lightly salted', 'sea salt', 'cracked pepper',
        'honey soy chicken', 'honey soy & chicken', 'supreme', 'cheese supreme', 'nacho cheese',
        'milk chocolate', 'dark chocolate', 'white chocolate', 'caramilk', 'hazelnut',
        'fruit & nut', 'roast almond', 'peppermint', 'caramello', 'caramel',
        'strawberry', 'vanilla', 'raspberry', 'cookies & cream', 'honeycomb', 'almond',
        'double dipped', 'classic clean', 'smooth & silky', 'apple fresh', 'citrus breeze',
        'lemon', 'lime', 'eucalyptus', 'antibacterial', 'sensitive', 'whitening',
        'deep clean', 'total clean', 'extra fresh', 'cool mint', 'fresh mint',
        'english breakfast', 'earl grey', 'green tea', 'peppermint tea', 'chamomile'
    ];
    let genericTitle = title;
    for (const v of variants) {
        genericTitle = genericTitle.replace(new RegExp('\\b' + v + '\\b', 'gi'), ' ');
    }
    const words = genericTitle.replace(/\s+/g, ' ').trim().split(' ').filter(w => w.length > 1);
    return words.slice(0, 3).join('_');
}

// Cluster items by product series (keeps same product with different types together)
function clusterItemsBySeries(items) {
    if (!items || items.length <= 1) return items;
    const groups = new Map();
    items.forEach(item => {
        const key = getProductSeriesKey(item);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(item);
    });

    for (const [k, groupItems] of groups.entries()) {
        groupItems.sort((a, b) => {
            const titleA = (a.title || '').toLowerCase();
            const titleB = (b.title || '').toLowerCase();
            if (titleA < titleB) return -1;
            if (titleA > titleB) return 1;
            return (a.store || '').localeCompare(b.store || '');
        });
    }

    const sortedGroupKeys = Array.from(groups.keys()).sort((k1, k2) => {
        const g1 = groups.get(k1);
        const g2 = groups.get(k2);
        const maxScore1 = Math.max(...g1.map(x => x.popularity_score || 0));
        const maxScore2 = Math.max(...g2.map(x => x.popularity_score || 0));
        if (maxScore2 !== maxScore1) return maxScore2 - maxScore1;
        const maxSave1 = Math.max(...g1.map(x => x.save_amount || 0));
        const maxSave2 = Math.max(...g2.map(x => x.save_amount || 0));
        return maxSave2 - maxSave1;
    });

    const result = [];
    sortedGroupKeys.forEach(k => {
        result.push(...groups.get(k));
    });
    return result;
}

// Sort items by comparator while clustering identical product lines together
function sortAndClusterBySeries(items, comparator) {
    if (!items || items.length <= 1) return items;
    const groups = new Map();
    items.forEach(item => {
        const key = getProductSeriesKey(item);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(item);
    });

    for (const [k, groupItems] of groups.entries()) {
        groupItems.sort((a, b) => {
            const comp = comparator(a, b);
            if (comp !== 0) return comp;
            return (a.title || '').localeCompare(b.title || '');
        });
    }

    const sortedKeys = Array.from(groups.keys()).sort((k1, k2) => {
        const item1 = groups.get(k1)[0];
        const item2 = groups.get(k2)[0];
        return comparator(item1, item2);
    });

    const result = [];
    sortedKeys.forEach(k => result.push(...groups.get(k)));
    return result;
}

// Cross-Supermarket Comparison Core Key
function getCoreProductKey(item) {
    if (!item || !item.title) return '';
    return item.title.toLowerCase()
        .replace(/['’]/g, '')
        .replace(/\b\d+([.-]\d+)?\s*(g|kg|ml|l|litre|liter|pack|pk|s|pieces|tablets|capsules|sheets|wipes)\b/gi, ' ')
        .replace(/\b\d+\s*[-–]\s*\d+\s*(g|kg|ml|l|litre|liter|pack|pk|s)?\b/gi, ' ')
        .replace(/\bpk\s*\d+([.-]\d+)?\b/gi, ' ')
        .replace(/\b\d+\s*pk\b/gi, ' ')
        .replace(/\b(or|and|&)\b/gi, ' ')
        .replace(/[^\w\s]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

// Enriches list with cross-store comparison metadata
function enrichCrossStoreComparisons(list) {
    if (!list || list.length === 0) return;
    const keyMap = new Map();
    list.forEach(it => {
        const k = getCoreProductKey(it);
        if (!keyMap.has(k)) keyMap.set(k, []);
        keyMap.get(k).push(it);
    });

    list.forEach(it => {
        const k = getCoreProductKey(it);
        const matches = (keyMap.get(k) || []).filter(other => other.store !== it.store);
        if (matches.length > 0) {
            it.cross_store_matches = matches.map(other => ({
                id: other.id,
                store: other.store,
                title: other.title,
                price: (typeof other.price === 'number') ? other.price : (parseFloat(other.price) || 0),
                was_price: (typeof other.was_price === 'number') ? other.was_price : (parseFloat(other.was_price) || 0),
                save_amount: (typeof other.save_amount === 'number') ? other.save_amount : (parseFloat(other.save_amount) || 0),
                price_display: other.price_display || '',
                unit_price: other.unit_price || '',
                image_url: other.image_url || '',
                product_url: other.product_url || '',
                category: other.category || 'other'
            }));
            const other = it.cross_store_matches[0];
            const priceDiff = Math.round((it.price - other.price) * 100) / 100;
            if (priceDiff < -0.05) {
                it.cross_store_cheaper = true;
                it.cross_store_diff = Math.abs(priceDiff);
            } else if (priceDiff > 0.05) {
                it.cross_store_cheaper = false;
                it.cross_store_diff = priceDiff;
            } else {
                it.cross_store_cheaper = false;
                it.cross_store_diff = 0;
            }
        } else {
            it.cross_store_matches = [];
        }
    });
}

function getCrossStoreBadgeText(item) {
    if (!item.cross_store_matches || item.cross_store_matches.length === 0) return '';
    const other = item.cross_store_matches[0];
    if (item.cross_store_cheaper && item.cross_store_diff > 0) {
        return t('cross_store_badge_cheaper', { store: other.store, amount: item.cross_store_diff.toFixed(2) });
    } else if (item.cross_store_diff > 0) {
        return t('cross_store_badge_other', { store: other.store, price: other.price.toFixed(2) });
    } else {
        return t('cross_store_badge_both', { price: item.price.toFixed(2) });
    }
}


// Robust Australian Supermarket 1/2 Price (Half Price) Detection
function isItemHalfPrice(it) {
    if (!it) return false;
    const desc = (it.discount_desc || '').toLowerCase();
    if (desc.includes('1/2') || desc.includes('half price') || desc.includes('50%')) return true;

    const price = typeof it.price === 'number' ? it.price : parseFloat(it.price) || 0;
    const was = typeof it.was_price === 'number' ? it.was_price : parseFloat(it.was_price) || 0;
    const save = typeof it.save_amount === 'number' ? it.save_amount : parseFloat(it.save_amount) || 0;

    const effectiveWas = was > 0 ? was : (save > 0 ? price + save : 0);
    if (effectiveWas > 0 && price > 0) {
        // Strictly at least 49.5% discount (accounting for odd cent rounding such as $3.15 -> $1.57 save $1.58)
        const discountRatio = (effectiveWas - price) / effectiveWas;
        if (discountRatio >= 0.495) return true;
    }

    // Exact equal save and price: e.g. price $2.00, save $2.00
    if (save > 0 && price > 0 && (save >= price - 0.05)) {
        const total = price + save;
        if (total > 0 && (save / total) >= 0.495) return true;
    }

    return false;
}

// Search & Filtering
function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        const val = document.getElementById('searchInput').value.trim();
        currentSearch = val;
        
        const clearBtn = document.getElementById('clearSearchBtn');
        if (val) {
            clearBtn.classList.remove('hidden');
        } else {
            clearBtn.classList.add('hidden');
        }
        loadSpecials();
    }, 300);
}

function setSearch(term) {
    document.getElementById('searchInput').value = term;
    currentSearch = term;
    document.getElementById('clearSearchBtn').classList.remove('hidden');
    loadSpecials();
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    currentSearch = '';
    document.getElementById('clearSearchBtn').classList.add('hidden');
    loadSpecials();
}

function selectStore(store) {
    currentStore = store;
    document.querySelectorAll('.store-tab').forEach(tab => {
        const s = tab.dataset.store;
        const dot = tab.querySelector('.store-dot');
        const isActive = (s === store);

        if (isActive) {
            if (s === 'All') {
                tab.className = 'store-tab active px-3 py-1.5 rounded-xl transition bg-slate-900 dark:bg-zinc-100 text-white dark:text-slate-900 shadow-xs font-bold scale-[1.02] shrink-0';
            } else if (s === 'Woolworths') {
                tab.className = 'store-tab active px-3 py-1.5 rounded-xl transition bg-[#007a3d] text-white shadow-xs font-bold scale-[1.02] shrink-0';
                if (dot) dot.className = 'store-dot inline-block w-2 h-2 rounded-full bg-white mr-1 shadow-2xs';
            } else if (s === 'Coles') {
                tab.className = 'store-tab active px-3 py-1.5 rounded-xl transition bg-[#e01a22] text-white shadow-xs font-bold scale-[1.02] shrink-0';
                if (dot) dot.className = 'store-dot inline-block w-2 h-2 rounded-full bg-white mr-1 shadow-2xs';
            } else if (s === 'ALDI') {
                tab.className = 'store-tab active px-3 py-1.5 rounded-xl transition bg-[#00205b] text-white shadow-xs font-bold scale-[1.02] shrink-0';
                if (dot) dot.className = 'store-dot inline-block w-2 h-2 rounded-full bg-white mr-1 shadow-2xs';
            }
        } else {
            if (s === 'All') {
                tab.className = 'store-tab px-3 py-1.5 rounded-xl transition font-semibold text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-zinc-700/60 shrink-0';
            } else if (s === 'Woolworths') {
                tab.className = 'store-tab px-3 py-1.5 rounded-xl transition font-semibold text-emerald-700 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 shrink-0';
                if (dot) dot.className = 'store-dot inline-block w-2 h-2 rounded-full bg-emerald-600 mr-1';
            } else if (s === 'Coles') {
                tab.className = 'store-tab px-3 py-1.5 rounded-xl transition font-semibold text-rose-700 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 shrink-0';
                if (dot) dot.className = 'store-dot inline-block w-2 h-2 rounded-full bg-rose-600 mr-1';
            } else if (s === 'ALDI') {
                tab.className = 'store-tab px-3 py-1.5 rounded-xl transition font-semibold text-blue-700 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/40 shrink-0';
                if (dot) dot.className = 'store-dot inline-block w-2 h-2 rounded-full bg-blue-600 mr-1';
            }
        }
    });
    loadSpecials();
}

let currentLoadedItems = [];

// Load Specials
async function loadSpecials() {
    const grid = document.getElementById('productsGrid');
    const loading = document.getElementById('loadingState');
    const empty = document.getElementById('emptyState');
    const resultsCountText = document.getElementById('resultsCountText');
    const sentinel = document.getElementById('infiniteScrollSentinel');

    // Immediately stop and disconnect any active infinite scroll observer
    if (infiniteScrollObserver) {
        infiniteScrollObserver.disconnect();
        infiniteScrollObserver = null;
    }
    currentDisplayItems = [];
    renderedCount = 0;
    if (sentinel) sentinel.classList.add('hidden');

    grid.innerHTML = '';
    loading.classList.remove('hidden');
    empty.classList.add('hidden');

    const discountOnly = document.getElementById('halfPriceOnly').checked;
    const sortBy = document.getElementById('sortSelect').value;

    if (!isStaticMode) {
        const params = new URLSearchParams({
            store: currentStore,
            period: currentPeriod,
            category: currentCategory,
            discount_only: discountOnly,
            sort_by: sortBy,
            limit: 150
        });
        if (currentSearch) {
            params.set('q', currentSearch);
        }

        try {
            const res = await fetch(`/api/specials?${params.toString()}`);
            if (!res.ok) throw new Error('API specials unavailable');
            const data = await res.json();
            
            loading.classList.add('hidden');
            currentLoadedItems = data.items || [];
            resultsCountText.textContent = t('found_targets', { n: data.total || 0 });

            if (!currentLoadedItems || currentLoadedItems.length === 0) {
                empty.classList.remove('hidden');
                return;
            }

            if (sortBy === 'popular') {
                currentLoadedItems = currentLoadedItems.filter(it => isItemPopular(it) && calculatePopularityScore(it) > 0);
            }

            renderProducts(currentLoadedItems);
            return;
        } catch (e) {
            console.log('API specials unavailable, falling back to static specials.json');
            isStaticMode = true;
        }
    }

    // Static Mode execution (Cloudflare Pages fallback)
    try {
        if (!staticSpecials || staticSpecials.length === 0) {
            staticSpecials = (await fetchStaticJson('specials.json')) || [];
        }

        let filtered = staticSpecials.filter(it => {
            if (it.period !== currentPeriod) return false;
            if (currentStore !== 'All' && it.store !== currentStore) return false;
            if (currentCategory !== 'all' && it.category !== currentCategory) {
                return false;
            }
            // Strictly only show items with genuine discounts (or ALDI Super Savers & Special Buys)
            if (it.store !== 'ALDI' && (!it.save_amount || it.save_amount <= 0)) return false;
            if (discountOnly) {
                if (!isItemHalfPrice(it)) return false;
            }
            if (currentSearch) {
                const translated = translateQueryClient(currentSearch);
                const titleLower = it.title.toLowerCase();
                const words = translated.split(/\s+/).filter(Boolean);
                const match = words.every(w => titleLower.includes(w) || (it.category && it.category.includes(w)));
                if (!match) return false;
            }
            return true;
        });

        // Enrich with cross-supermarket comparison info
        enrichCrossStoreComparisons(staticSpecials);

        // Sorting & Series Clustering
        if (sortBy === 'popular') {
            filtered = filtered.filter(it => isItemPopular(it) && calculatePopularityScore(it) > 0);
            filtered = createDiverseBestSellers(filtered);
        } else if (sortBy === 'save_desc') {
            filtered = sortAndClusterBySeries(filtered, (a, b) => (b.save_amount || 0) - (a.save_amount || 0));
        } else if (sortBy === 'price_asc') {
            filtered = sortAndClusterBySeries(filtered, (a, b) => (a.price || 0) - (b.price || 0));
        } else if (sortBy === 'price_desc') {
            filtered = sortAndClusterBySeries(filtered, (a, b) => (b.price || 0) - (a.price || 0));
        } else {
            // Default & relevance: Group identical products with different types together
            filtered = clusterItemsBySeries(filtered);
        }

        loading.classList.add('hidden');
        currentLoadedItems = filtered;
        resultsCountText.textContent = t('found_targets', { n: filtered.length });

        if (filtered.length === 0) {
            loading.classList.add('hidden');
            grid.innerHTML = '';
            currentLoadedItems = [];
            currentDisplayItems = [];
            renderedCount = 0;
            if (sentinel) sentinel.classList.add('hidden');
            if (infiniteScrollObserver) {
                infiniteScrollObserver.disconnect();
                infiniteScrollObserver = null;
            }

            const emptyTitle = document.getElementById('emptyStateTitle');
            const emptySub = document.getElementById('emptyStateSub');
            const emptyAction = document.getElementById('emptyStateAction');
            if (currentPeriod === 'next') {
                if (emptyTitle) {
                    emptyTitle.textContent = currentLang === 'zh' ? '下週特價型錄尚未公佈' : (currentLang === 'ja' ? '来週のチラシはまだ公開されていません' : (currentLang === 'ko' ? '다음 주 세일 카탈로그가 아직 공개되지 않았습니다' : 'Next Week Specials Not Released Yet'));
                }
                if (emptySub) {
                    emptySub.textContent = currentLang === 'zh' ? '澳洲超商（Coles / Woolies）每週三換檔，通常於週一或週二提前釋出下週預告，目前請先查看「本週特價」！' : (currentLang === 'ja' ? '豪州スーパーは通常月曜・火曜に来週のチラシを先行公開します。まずは今週の特売をご覧ください！' : (currentLang === 'ko' ? '호주 대형마트는 보통 월/화요일에 다음 주 카탈로그를 선공개합니다. 이번 주 특가를 먼저 확인하세요!' : 'Supermarkets typically preview next week specials on Mon/Tue. Please check This Week specials for now!'));
                }
                if (emptyAction) emptyAction.classList.remove('hidden');
            } else {
                if (emptyTitle) {
                    emptyTitle.textContent = currentLang === 'zh' ? '沒有找到符合的特價商品' : (currentLang === 'ja' ? '該当する商品が見つかりませんでした' : (currentLang === 'ko' ? '조건에 맞는 특가 상품이 없습니다' : 'No matching specials found'));
                }
                if (emptySub) {
                    emptySub.textContent = currentLang === 'zh' ? '試試切換其他分類或調整搜尋關鍵字' : (currentLang === 'ja' ? '他のカテゴリーを選択するか検索条件を変更してください' : (currentLang === 'ko' ? '다른 카테고리를 선택하거나 검색어를 변경해보세요' : 'Try selecting another category or adjusting your search filters'));
                }
                if (emptyAction) emptyAction.classList.add('hidden');
            }
            empty.classList.remove('hidden');
            return;
        }

        renderProducts(filtered);
    } catch (err) {
        loading.classList.add('hidden');
        empty.classList.remove('hidden');
        console.error('Static specials load error', err);
    }
}

function renderProductsCurrent() {
    if (currentLoadedItems && currentLoadedItems.length > 0) {
        renderProducts(currentLoadedItems);
    }
}

// Authentic Australian Supermarket (Woolworths & Coles online) Price Formatting
function parseSupermarketPrice(priceDisplay, price) {
    let num = (typeof price === 'number' && !isNaN(price)) ? price : 0;
    let unit = 'ea';

    if (priceDisplay && typeof priceDisplay === 'string') {
        const text = priceDisplay.toLowerCase().trim();
        if (text.includes('/kg') || text.includes('per kg') || text.includes(' kg')) {
            unit = '/kg';
        } else if (text.includes('pk') || text.includes('pack')) {
            unit = 'pk';
        } else if (text.includes('bunch')) {
            unit = 'bunch';
        } else if (text.includes('each') || text.includes(' ea')) {
            unit = 'ea';
        }

        if (!num) {
            const m = priceDisplay.match(/\$?(\d+(?:\.\d{1,2})?)/);
            if (m) num = parseFloat(m[1]);
        }
    }

    const fixed = num.toFixed(2);
    const [dollars, cents] = fixed.split('.');

    return {
        dollars,
        cents,
        unit,
        formatted: `$${fixed}`,
        displayWithUnit: `$${fixed} ${unit}`
    };
}

function formatSupermarketUnitPrice(unitPrice) {
    if (!unitPrice || typeof unitPrice !== 'string') return '';
    return unitPrice.replace(/A\$/gi, '$').trim();
}

// High-Performance Batch Rendering & Infinite Scrolling State
let currentDisplayItems = [];
let renderedCount = 0;
const BATCH_SIZE = 40;
let infiniteScrollObserver = null;

// Render Products Grid with Instant 40-Card First Paint & Infinite Scroll
function renderProducts(items) {
    const grid = document.getElementById('productsGrid');
    const sentinel = document.getElementById('infiniteScrollSentinel');
    
    // Disconnect any active observer
    if (infiniteScrollObserver) {
        infiniteScrollObserver.disconnect();
        infiniteScrollObserver = null;
    }
    
    grid.innerHTML = '';
    currentDisplayItems = items || [];
    renderedCount = 0;

    if (currentDisplayItems.length === 0) {
        if (sentinel) sentinel.classList.add('hidden');
        return;
    }

    // Render the initial 40 items instantly (<15ms)
    renderNextBatch();

    // Set up IntersectionObserver to automatically load more on scroll
    if (sentinel && renderedCount < currentDisplayItems.length) {
        sentinel.classList.remove('hidden');
        if (typeof IntersectionObserver !== 'undefined') {
            infiniteScrollObserver = new IntersectionObserver((entries) => {
                if (entries[0] && entries[0].isIntersecting) {
                    renderNextBatch();
                }
            }, {
                root: null,
                rootMargin: '500px', // Pre-load 500px before user reaches bottom for zero perceived wait
                threshold: 0.05
            });
            infiniteScrollObserver.observe(sentinel);
        } else {
            renderNextBatch();
        }
    } else if (sentinel) {
        sentinel.classList.add('hidden');
    }
}

let isRenderingBatch = false;

function renderNextBatch() {
    if (isRenderingBatch) return;
    if (renderedCount >= currentDisplayItems.length) {
        const sentinel = document.getElementById('infiniteScrollSentinel');
        if (sentinel) sentinel.classList.add('hidden');
        if (infiniteScrollObserver) {
            infiniteScrollObserver.disconnect();
            infiniteScrollObserver = null;
        }
        return;
    }

    isRenderingBatch = true;
    try {
        const grid = document.getElementById('productsGrid');
        const nextSlice = currentDisplayItems.slice(renderedCount, renderedCount + BATCH_SIZE);
        const fragment = document.createDocumentFragment();

        nextSlice.forEach(item => {
            try {
                const card = createProductCardElement(item);
                if (card) fragment.appendChild(card);
            } catch (cardErr) {
                console.error('Failed to create product card:', item, cardErr);
            }
        });

        grid.appendChild(fragment);
        renderedCount += nextSlice.length;

        const sentinel = document.getElementById('infiniteScrollSentinel');
        if (sentinel) {
            if (renderedCount >= currentDisplayItems.length) {
                sentinel.classList.add('hidden');
                if (infiniteScrollObserver) {
                    infiniteScrollObserver.disconnect();
                    infiniteScrollObserver = null;
                }
            } else {
                sentinel.classList.remove('hidden');
            }
        }
    } finally {
        isRenderingBatch = false;
    }
}

function createProductCardElement(item) {
    const card = document.createElement('div');
    card.className = 'bg-white dark:bg-[#121316] rounded-2xl sm:rounded-3xl border border-slate-200/80 dark:border-white/[0.07] overflow-hidden shadow-[0_2px_10px_-2px_rgba(0,0,0,0.04)] hover:shadow-[0_16px_36px_-6px_rgba(0,0,0,0.12)] dark:hover:shadow-[0_16px_36px_-6px_rgba(0,0,0,0.5)] hover:-translate-y-1 hover:border-emerald-500/40 dark:hover:border-emerald-500/40 transition-all duration-300 flex flex-col justify-between group cursor-pointer relative';
    card.onclick = () => openProductModal(item);

    let storeBadgeClass = 'bg-[#007a3d] text-white';
    let storeIcon = '<i class="fa-solid fa-leaf text-[9px] text-emerald-200"></i>';
    if (item.store === 'Coles') {
        storeBadgeClass = 'bg-[#e01a22] text-white';
        storeIcon = '<i class="fa-solid fa-cart-shopping text-[9px] text-red-200"></i>';
    } else if (item.store === 'ALDI') {
        storeBadgeClass = 'bg-[#00205b] text-white';
        storeIcon = '<i class="fa-solid fa-store text-[9px] text-sky-200"></i>';
    }

    const isHalfPrice = isItemHalfPrice(item);
    const hasCatalogueBadge = !!(item.image_url && item.image_url.includes('cloudfront.net'));
    const fallbackImg = DEFAULT_FALLBACK_IMG;

    const effectivePrice = (typeof item.price === 'number') ? item.price : (parseFloat(item.price) || 0);
    let effectiveSave = (typeof item.save_amount === 'number') ? item.save_amount : (parseFloat(item.save_amount) || 0);
    let effectiveWas = (typeof item.was_price === 'number') ? item.was_price : (parseFloat(item.was_price) || 0);

    if (effectiveSave <= 0 && effectiveWas > effectivePrice && effectivePrice > 0) {
        effectiveSave = Math.round((effectiveWas - effectivePrice) * 100) / 100;
    } else if (effectiveWas <= 0 && effectiveSave > 0 && effectivePrice > 0) {
        effectiveWas = Math.round((effectivePrice + effectiveSave) * 100) / 100;
    }

    let cleanDiscountDesc = item.discount_desc || '';
    const lowerDesc = cleanDiscountDesc.toLowerCase();
    if (lowerDesc.startsWith('offers apply') || lowerDesc.includes('while stocks last') || lowerDesc.includes('specials not available')) {
        cleanDiscountDesc = effectiveSave > 0 ? `Save $${effectiveSave.toFixed(2)}` : '';
    } else if (!cleanDiscountDesc && effectiveSave > 0) {
        cleanDiscountDesc = `Save $${effectiveSave.toFixed(2)}`;
    }

    const p = parseSupermarketPrice(item.price_display, item.price);
    const unitPriceClean = formatSupermarketUnitPrice(item.unit_price);
    const translated = getProductTranslation(item, currentLang);
    const catStyle = CATEGORY_STYLES[item.category] || { emoji: '🏷️' };
    const crossStoreBadgeText = getCrossStoreBadgeText(item);

    const cartPayload = {
        id: item.id,
        store: item.store,
        title: item.title,
        price: effectivePrice,
        was_price: effectiveWas,
        save_amount: effectiveSave,
        price_display: item.price_display || `$${effectivePrice.toFixed(2)}`,
        unit_price: item.unit_price || '',
        image_url: item.image_url || '',
        category: item.category || 'other',
        period: item.period || 'current'
    };

    card.innerHTML = `
        <div class="p-3 sm:p-3.5 space-y-2.5">
            <!-- Product Image Stage with Floating Badges -->
            <div class="relative w-full aspect-square rounded-xl sm:rounded-2xl bg-gradient-to-b from-slate-50/90 to-slate-100/50 dark:from-zinc-800/40 dark:to-zinc-850/60 p-2.5 sm:p-3 flex items-center justify-center overflow-hidden ring-1 ring-black/[0.04] dark:ring-white/[0.05]">
                <!-- Top-Left Store Tag -->
                <div class="absolute top-2 left-2 z-10">
                    <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-[10px] sm:text-[11px] font-bold ${storeBadgeClass} shadow-xs">
                        ${storeIcon}
                        <span>${item.store}</span>
                    </span>
                </div>

                <!-- Woolworths 1/2 Price Circular Badge Overlay -->
                ${(isHalfPrice && item.store === 'Woolworths' && !hasCatalogueBadge) ? `
                    <div class="absolute top-8 left-2 sm:top-8.5 sm:left-2.5 z-10 pointer-events-none drop-shadow-sm select-none transition-transform group-hover:scale-105">
                        <img src="./woolworths_half_price_badge.png" alt="1/2 Price" class="w-10 h-10 sm:w-11 sm:h-11 object-contain" />
                    </div>
                ` : ''}

                <!-- Top-Right Discount Badge (Only shown for 1/2 Price items to avoid duplication with bottom-right save badge) -->
                <div class="absolute top-2 right-2 z-10">
                    ${isHalfPrice ? `
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] sm:text-[11px] font-black bg-gradient-to-r from-rose-500 via-rose-600 to-red-600 text-white shadow-md shadow-rose-500/25 tracking-tight">
                            <i class="fa-solid fa-fire text-[9px] text-amber-200"></i>
                            <span>${t('half_price_badge')}</span>
                        </span>
                    ` : ''}
                </div>

                <!-- Product Image with Zoom -->
                <img 
                    src="${item.image_url || fallbackImg}" 
                    alt="${item.title}" 
                    loading="lazy" 
                    decoding="async"
                    class="max-h-full max-w-full object-contain group-hover:scale-108 transition-transform duration-500 ease-out"
                    onerror="this.src='${fallbackImg}'"
                />
            </div>

            <!-- Category, Unit Price & Comparison Meta Row -->
            <div class="flex items-center justify-between gap-1 text-[10px] text-slate-500 dark:text-zinc-400">
                <div class="flex items-center gap-1.5 flex-wrap min-w-0">
                    <span class="inline-flex items-center gap-1 font-medium bg-slate-100/90 dark:bg-zinc-800/70 px-1.5 py-0.5 rounded-md text-[9px] sm:text-[10px]">
                        <span>${catStyle.emoji}</span>
                        <span>${getCleanCategoryLabel(item.category)}</span>
                    </span>
                    ${crossStoreBadgeText ? `
                        <span class="inline-flex items-center gap-1 font-bold text-[9px] sm:text-[10px] px-1.5 py-0.5 rounded-md ${item.cross_store_cheaper ? 'bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300/60' : 'bg-blue-100 dark:bg-blue-950/80 text-blue-800 dark:text-blue-300 border border-blue-200/60'} shrink-0 shadow-2xs" title="${crossStoreBadgeText}">
                            <i class="fa-solid fa-scale-balanced text-[8px]"></i>
                            <span>${crossStoreBadgeText}</span>
                        </span>
                    ` : ''}
                    ${isItemPopular(item) ? `
                        <span class="inline-flex items-center gap-1 font-black text-[9px] sm:text-[10px] px-1.5 py-0.5 rounded-md bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border border-amber-300/50 shrink-0">
                            <i class="fa-solid fa-star text-[8px] text-amber-500"></i>
                            <span>${t('popular_badge')}</span>
                        </span>
                    ` : ''}
                </div>
                ${unitPriceClean ? `
                    <span class="font-mono text-slate-500 dark:text-zinc-400 text-[10px] font-medium truncate max-w-[110px]" title="${unitPriceClean}">
                        ${unitPriceClean}
                    </span>
                ` : ''}
            </div>

            <!-- Product Title & Multilingual Subtitle -->
            <div class="space-y-1">
                <h3 class="text-xs sm:text-sm font-bold text-slate-900 dark:text-zinc-100 line-clamp-2 leading-snug group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors" title="${item.title}">
                    ${item.title}
                </h3>
                ${translated ? `
                    <div class="text-[11px] sm:text-xs font-semibold text-emerald-800 dark:text-emerald-300 bg-emerald-50/80 dark:bg-emerald-950/50 border border-emerald-200/50 dark:border-emerald-800/50 px-2 py-0.5 rounded-lg line-clamp-1 leading-normal" title="${translated}">
                        ${translated}
                    </div>
                ` : ''}
            </div>
        </div>

        <!-- Price & Action Footer -->
        <div class="p-3 sm:p-3.5 pt-0 space-y-2 sm:space-y-2.5">
            <!-- Price Display Row -->
            <div class="pt-2 border-t border-slate-100 dark:border-zinc-800/80 flex items-baseline justify-between gap-1">
                <div class="flex items-baseline gap-0.5 leading-none">
                    <span class="text-xs sm:text-sm font-extrabold text-slate-900 dark:text-white self-start mt-0.5 font-mono">$</span>
                    <span class="text-xl sm:text-3xl font-black tracking-tight text-slate-900 dark:text-white font-mono">${p.dollars}</span>
                    <span class="text-xs sm:text-sm font-extrabold text-slate-900 dark:text-white self-start mt-0.5 font-mono">${p.cents}</span>
                    <span class="text-[10px] sm:text-xs font-semibold text-slate-500 dark:text-zinc-400 ml-0.5 self-baseline">${p.unit}</span>
                </div>

                <div class="text-right leading-none space-y-0.5">
                    ${effectiveWas > 0 ? `
                        <div class="text-[10px] sm:text-[11px] text-slate-400 line-through font-medium">
                            ${t('was_price')} $${effectiveWas.toFixed(2)}
                        </div>
                    ` : ''}
                    ${effectiveSave > 0 ? `
                        <span class="inline-block px-1.5 py-0.2 rounded text-[9px] sm:text-[10px] font-black bg-amber-400 text-slate-950">
                            ${t('save_badge', { amount: effectiveSave.toFixed(2) })}
                        </span>
                    ` : ''}
                </div>
            </div>

            <!-- Add to Shopping List Button -->
            <button 
                onclick='event.stopPropagation(); addToShoppingList(${JSON.stringify(cartPayload).replace(/'/g, "&#39;")})'
                class="w-full py-2 px-3 rounded-xl sm:rounded-2xl text-[11px] sm:text-xs font-bold bg-slate-100 hover:bg-emerald-600 text-slate-700 hover:text-white dark:bg-zinc-800 dark:hover:bg-emerald-600 dark:text-zinc-200 dark:hover:text-white border border-slate-200/60 dark:border-zinc-700/60 hover:border-emerald-600 dark:hover:border-emerald-600 transition-all duration-200 flex items-center justify-center gap-1.5 active:scale-95 shadow-2xs group/btn"
            >
                <i class="fa-solid fa-plus text-[10px] sm:text-xs transition-transform duration-200 group-hover/btn:rotate-90"></i>
                <span data-i18n="add_to_list">${t('add_to_list')}</span>
            </button>
        </div>
    `;

    return card;
}

// Product Details Modal
let currentModalItem = null;

function sanitizeKeyword(text) {
    if (!text) return '';
    let t = text;
    // Remove department and exclusions
    t = t.replace(/[\u2013\u2014\-–]\s*(From the Deli|From the Meat Dept|Excludes.*)/gi, '');
    // Remove weight and volume ranges
    t = t.replace(/\b\d+(\.\d+)?\s*(g|kg|ml|l|pack|pk)\s*[\-–]\s*\d+(\.\d+)?\s*(g|kg|ml|l|pack|pk)\b/gi, '');
    t = t.replace(/\b\d+\s*x\s*\d+(\.\d+)?\s*(ml|g|l)\b/gi, '');
    t = t.replace(/\b\d+(\.\d+)?\s*x\s*\d+(\.\d+)?\s*(ml|g|l)\b/gi, '');
    t = t.replace(/\b\d+(\.\d+)?\s*(g|kg|ml|l|litre|punnet|pack|pk)\b/gi, '');
    t = t.replace(/\b\d+\s*(pack|pk)\b/gi, '');
    // Strip apostrophes completely (Arnott's -> Arnotts, Smith's -> Smiths, M&M's -> MMs)
    t = t.replace(/['’]/g, '');
    // Replace '&' with space
    t = t.replace(/&/g, ' ');
    // Remove fluff words
    t = t.replace(/\b(biscuits|varieties|selected|regular|bulk)\b/gi, ' ');
    // Remove all non-alphanumeric except spaces
    t = t.replace(/[^a-zA-Z0-9\s]/g, ' ');
    return t.replace(/\s+/g, ' ').trim();
}

function buildStoreSearchUrl(store, queryTerm, fallbackUrl = '') {
    const cleanTerm = sanitizeKeyword(queryTerm);
    const q = encodeURIComponent(cleanTerm);
    if (store === 'Coles') {
        return `https://www.coles.com.au/search?q=${q}`;
    } else if (store === 'Woolworths') {
        return `https://www.woolworths.com.au/shop/search/products?searchTerm=${q}`;
    } else if (store === 'ALDI') {
        if (fallbackUrl && fallbackUrl.includes('aldi.com.au')) {
            return fallbackUrl;
        }
        return `https://www.aldi.com.au/groceries/super-savers/`;
    }
    return fallbackUrl || '#';
}

function extractSubProducts(title) {
    if (!title) return [];
    let t = title
        .replace(/[\u2013\u2014\-–]\s*(From the Deli|From the Meat Dept|Excludes.*)/gi, '')
        .replace(/\b\d+(\.\d+)?\s*(g|kg|ml|l|pack|pk)\s*[\-–]\s*\d+(\.\d+)?\s*(g|kg|ml|l|pack|pk)\b/gi, '')
        .replace(/\b\d+\s*x\s*\d+(\.\d+)?\s*(ml|g|l)\b/gi, '')
        .replace(/\b\d+(\.\d+)?\s*x\s*\d+(\.\d+)?\s*(ml|g|l)\b/gi, '')
        .replace(/\b\d+(\.\d+)?\s*(g|kg|ml|l|litre|punnet|pack|pk)\b/gi, '');

    let items = [];
    if (t.includes(' or ') || t.includes(',')) {
        let rawParts = t.split(/\s+or\s+|,/i);
        for (let p of rawParts) {
            let cleanP = sanitizeKeyword(p);
            if (cleanP.length >= 2 && !items.includes(cleanP)) {
                items.push(cleanP);
            }
        }
    }
    return items;
}

function cleanTitleForSearch(title) {
    if (!title) return '';
    let t = title;
    if (t.includes(' or ') || t.includes(',')) {
        const subs = extractSubProducts(title);
        if (subs.length > 0) return subs[0];
    }
    return sanitizeKeyword(title);
}

function getOfficialStoreUrl(item) {
    if (!item) return '#';

    // If it's already a direct official supermarket link
    if (item.product_url) {
        if (item.product_url.includes('aldi.com.au') || 
            item.product_url.includes('coles.com.au/product') || 
            item.product_url.includes('woolworths.com.au/shop/productdetails')) {
            return item.product_url;
        }
    }

    const cleanTitle = cleanTitleForSearch(item.title) || item.title;

    if (item.store === 'Coles') {
        return `https://duckduckgo.com/?q=!ducky+site:coles.com.au+${encodeURIComponent(cleanTitle)}`;
    } else if (item.store === 'Woolworths') {
        return `https://duckduckgo.com/?q=!ducky+site:woolworths.com.au+${encodeURIComponent(cleanTitle)}`;
    } else if (item.store === 'ALDI') {
        if (item.product_url && item.product_url.includes('aldi.com.au')) {
            return item.product_url;
        }
        return `https://www.aldi.com.au/groceries/super-savers/`;
    }
    return item.product_url || '#';
}

function openProductModal(item) {
    currentModalItem = item;
    const modal = document.getElementById('productModal');
    const backdrop = document.getElementById('productModalBackdrop');

    let storeColor = 'bg-emerald-600 text-white';
    if (item.store === 'Coles') storeColor = 'bg-rose-600 text-white';
    if (item.store === 'ALDI') storeColor = 'bg-blue-600 text-white';

    const isHalfPrice = isItemHalfPrice(item);
    const fallbackImg = DEFAULT_FALLBACK_IMG;

    // Badges
    const storeBadge = document.getElementById('modalStoreBadge');
    storeBadge.className = `px-2.5 py-0.5 rounded-lg text-xs font-bold ${storeColor}`;
    storeBadge.textContent = item.store;

    document.getElementById('modalCategoryBadge').textContent = getCategoryName(item.category);
    
    const halfBadge = document.getElementById('modalHalfPriceBadge');
    if (isHalfPrice) {
        halfBadge.textContent = t('half_price_badge');
        halfBadge.classList.remove('hidden');
    } else {
        halfBadge.classList.add('hidden');
    }

    const popularBadge = document.getElementById('modalPopularBadge');
    if (popularBadge) {
        if (isItemPopular(item)) {
            popularBadge.classList.remove('hidden');
            const spanText = popularBadge.querySelector('span');
            if (spanText) spanText.textContent = t('popular_modal_tag');
        } else {
            popularBadge.classList.add('hidden');
        }
    }

    // Image & Title
    const imgElem = document.getElementById('modalProductImg');
    imgElem.src = item.image_url || fallbackImg;
    imgElem.onerror = () => { imgElem.src = fallbackImg; };
    document.getElementById('modalProductTitle').textContent = item.title;

    const modalWooliesBadge = document.getElementById('modalWooliesHalfPriceBadge');
    if (modalWooliesBadge) {
        const hasCatalogueBadge = !!(item.image_url && item.image_url.includes('cloudfront.net'));
        if (isHalfPrice && item.store === 'Woolworths' && !hasCatalogueBadge) {
            modalWooliesBadge.classList.remove('hidden');
        } else {
            modalWooliesBadge.classList.add('hidden');
        }
    }

    const translated = getProductTranslation(item, currentLang);
    const transElem = document.getElementById('modalProductTranslated');
    if (transElem) {
        if (translated && currentLang !== 'en') {
            transElem.textContent = translated;
            transElem.classList.remove('hidden');
        } else {
            transElem.textContent = '';
            transElem.classList.add('hidden');
        }
    }

    // Dates
    document.getElementById('modalDateRange').textContent = item.date_range || 'Active Specials';

    // Supermarket Price Lockup in Modal
    const p = parseSupermarketPrice(item.price_display, item.price);
    document.getElementById('modalDollars').textContent = p.dollars;
    document.getElementById('modalCents').textContent = p.cents;
    document.getElementById('modalUnit').textContent = p.unit;
    
    const effectivePrice = (typeof item.price === 'number') ? item.price : (parseFloat(item.price) || 0);
    let effectiveSave = (typeof item.save_amount === 'number') ? item.save_amount : (parseFloat(item.save_amount) || 0);
    let effectiveWas = (typeof item.was_price === 'number') ? item.was_price : (parseFloat(item.was_price) || 0);

    if (effectiveSave <= 0 && effectiveWas > effectivePrice && effectivePrice > 0) {
        effectiveSave = Math.round((effectiveWas - effectivePrice) * 100) / 100;
    } else if (effectiveWas <= 0 && effectiveSave > 0 && effectivePrice > 0) {
        effectiveWas = Math.round((effectivePrice + effectiveSave) * 100) / 100;
    }

    const wasElem = document.getElementById('modalWasPrice');
    if (effectiveWas > 0) {
        wasElem.textContent = `${t('was_price')} $${effectiveWas.toFixed(2)}`;
        wasElem.classList.remove('hidden');
    } else {
        wasElem.classList.add('hidden');
    }

    const saveBadge = document.getElementById('modalSaveBadge');
    if (effectiveSave > 0) {
        saveBadge.textContent = t('save_badge', { amount: effectiveSave.toFixed(2) });
        saveBadge.classList.remove('hidden');
    } else {
        saveBadge.classList.add('hidden');
    }

    // Unit price
    const unitPriceBox = document.getElementById('modalUnitPriceBox');
    const unitPriceElem = document.getElementById('modalUnitPrice');
    if (item.unit_price) {
        unitPriceElem.textContent = formatSupermarketUnitPrice(item.unit_price);
        unitPriceBox.classList.remove('hidden');
    } else {
        unitPriceElem.textContent = '--';
        unitPriceBox.classList.add('hidden');
    }

    // Cross-store comparison in modal (各大超市現場同款比價)
    const crossStoreBox = document.getElementById('modalCrossStoreBox');
    const crossStoreList = document.getElementById('modalCrossStoreList');
    const crossStoreBadge = document.getElementById('modalCrossStoreBadge');

    if (crossStoreBox && crossStoreList) {
        if (item.cross_store_matches && item.cross_store_matches.length > 0) {
            crossStoreList.innerHTML = '';
            
            // Render this store's price row
            const thisStoreRow = document.createElement('div');
            thisStoreRow.className = "p-2.5 rounded-xl bg-white dark:bg-zinc-900 border border-slate-200/80 dark:border-zinc-800 flex items-center justify-between gap-2 shadow-2xs";
            thisStoreRow.innerHTML = `
                <div class="flex items-center gap-2">
                    <span class="px-2 py-0.5 rounded-lg text-[10px] font-bold ${item.store === 'Coles' ? 'bg-[#e01a22]' : (item.store === 'ALDI' ? 'bg-[#00205b]' : 'bg-[#007a3d]')} text-white">
                        ${item.store} (${currentLang === 'zh' ? '當前' : (currentLang === 'ja' ? '現在' : (currentLang === 'ko' ? '현재' : 'Current'))})
                    </span>
                    <span class="text-xs font-semibold text-slate-800 dark:text-zinc-200 truncate max-w-[180px] sm:max-w-xs" title="${item.title}">
                        ${item.title}
                    </span>
                </div>
                <div class="text-right leading-tight">
                    <span class="font-mono font-black text-sm text-slate-900 dark:text-white">$${effectivePrice.toFixed(2)}</span>
                    ${effectiveSave > 0 ? `<span class="block text-[10px] text-amber-600 dark:text-amber-400 font-bold">${t('save_badge', { amount: effectiveSave.toFixed(2) })}</span>` : ''}
                </div>
            `;
            crossStoreList.appendChild(thisStoreRow);

            // Render other matching stores
            item.cross_store_matches.forEach(other => {
                const otherPrice = (typeof other.price === 'number') ? other.price : (parseFloat(other.price) || 0);
                const otherSave = (typeof other.save_amount === 'number') ? other.save_amount : (parseFloat(other.save_amount) || 0);
                const diff = Math.round((otherPrice - effectivePrice) * 100) / 100;
                
                let diffBadge = '';
                if (diff > 0.05) {
                    diffBadge = `<span class="text-[10px] font-bold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/60 px-1.5 py-0.5 rounded">${currentLang === 'zh' ? '貴' : '+$'}${diff.toFixed(2)}</span>`;
                } else if (diff < -0.05) {
                    diffBadge = `<span class="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-1.5 py-0.5 rounded">${currentLang === 'zh' ? '平' : '-$'}${Math.abs(diff).toFixed(2)}</span>`;
                } else {
                    diffBadge = `<span class="text-[10px] font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/60 px-1.5 py-0.5 rounded">${t('cross_store_same_price')}</span>`;
                }

                const otherRow = document.createElement('div');
                otherRow.className = "p-2.5 rounded-xl bg-white dark:bg-zinc-900 border border-slate-200/80 dark:border-zinc-800 flex items-center justify-between gap-2 shadow-2xs hover:border-blue-400 transition cursor-pointer";
                otherRow.onclick = (e) => {
                    e.stopPropagation();
                    openProductModal(other);
                };
                otherRow.innerHTML = `
                    <div class="flex items-center gap-2">
                        <span class="px-2 py-0.5 rounded-lg text-[10px] font-bold ${other.store === 'Coles' ? 'bg-[#e01a22]' : (other.store === 'ALDI' ? 'bg-[#00205b]' : 'bg-[#007a3d]')} text-white">
                            ${other.store}
                        </span>
                        <div class="space-y-0.5">
                            <span class="text-xs font-semibold text-slate-800 dark:text-zinc-200 truncate max-w-[180px] sm:max-w-xs block" title="${other.title}">
                                ${other.title}
                            </span>
                            <span class="text-[10px] text-blue-600 dark:text-blue-400 font-medium">
                                <i class="fa-solid fa-arrow-right text-[8px]"></i> ${t('cross_store_view_other', { store: other.store })}
                            </span>
                        </div>
                    </div>
                    <div class="text-right leading-tight">
                        <div class="flex items-center gap-1 justify-end">
                            <span class="font-mono font-black text-sm text-slate-900 dark:text-white">$${otherPrice.toFixed(2)}</span>
                            ${diffBadge}
                        </div>
                        ${otherSave > 0 ? `<span class="block text-[10px] text-amber-600 dark:text-amber-400 font-bold">${t('save_badge', { amount: otherSave.toFixed(2) })}</span>` : ''}
                    </div>
                `;
                crossStoreList.appendChild(otherRow);
            });

            if (crossStoreBadge) {
                crossStoreBadge.textContent = t('cross_store_title');
            }
            crossStoreBox.classList.remove('hidden');
        } else {
            crossStoreBox.classList.add('hidden');
        }
    }

    // WHV Advice
    document.getElementById('modalWhvAdvice').textContent = generateWhvAdvice(item);

    // Next Week Notice
    const nextNotice = document.getElementById('modalNextWeekNotice');
    if (nextNotice) {
        if (item.period === 'next') {
            nextNotice.classList.remove('hidden');
        } else {
            nextNotice.classList.add('hidden');
        }
    }

    // Official store link (Direct to real supermarket official website)
    const linkElem = document.getElementById('modalOfficialLink');
    const cleanPrimary = cleanTitleForSearch(item.title) || item.title;
    const officialUrl = getOfficialStoreUrl(item);

    linkElem.href = officialUrl;
    const linkSpan = linkElem.querySelector('span');
    if (linkSpan) {
        linkSpan.textContent = t('open_official_store', { store: item.store });
    }
    document.getElementById('modalOfficialLinkBox').classList.remove('hidden');

    // Sub-item quick links (if title groups multiple items, e.g. Red Rock Deli, Smith's, Doritos)
    const subItems = extractSubProducts(item.title);
    const subItemsBox = document.getElementById('modalSubItemsBox');
    const subItemsList = document.getElementById('modalSubItemsList');
    if (subItemsBox && subItemsList) {
        if (subItems.length > 1) {
            subItemsList.innerHTML = '';
            subItems.forEach(sub => {
                const subLink = document.createElement('a');
                let targetUrl = '';
                if (item.store === 'Coles') {
                    targetUrl = `https://duckduckgo.com/?q=!ducky+site:coles.com.au+${encodeURIComponent(sub)}`;
                } else if (item.store === 'Woolworths') {
                    targetUrl = `https://duckduckgo.com/?q=!ducky+site:woolworths.com.au+${encodeURIComponent(sub)}`;
                } else {
                    targetUrl = `https://www.aldi.com.au/groceries/super-savers/`;
                }
                subLink.href = targetUrl;
                subLink.target = '_blank';
                subLink.rel = 'noopener noreferrer';
                subLink.className = "px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-zinc-800 hover:bg-emerald-50 hover:text-emerald-700 dark:hover:bg-zinc-700 text-slate-700 dark:text-zinc-300 font-medium transition flex items-center gap-1 shadow-2xs";
                subLink.innerHTML = `<span>${sub}</span><i class="fa-solid fa-arrow-up-right-from-square text-[9px] opacity-70"></i>`;
                subItemsList.appendChild(subLink);
            });
            subItemsBox.classList.remove('hidden');
        } else {
            subItemsBox.classList.add('hidden');
        }
    }

    modal.classList.remove('hidden');
    backdrop.classList.remove('hidden');
}

function closeProductModal() {
    document.getElementById('productModal').classList.add('hidden');
    document.getElementById('productModalBackdrop').classList.add('hidden');
    currentModalItem = null;
}

function modalAddCurrentToShoppingList() {
    if (currentModalItem) {
        addToShoppingList(currentModalItem);
        closeProductModal();
    }
}

function generateWhvAdvice(item) {
    const isHalf = item.discount_desc && (item.discount_desc.includes('1/2') || item.discount_desc.toLowerCase().includes('half'));
    const cat = item.category;
    const store = item.store;

    if (currentLang === 'zh') {
        if (isHalf) return "🔥 50% OFF 半價極限折扣！非易腐生活用品（如洗劑、衛生紙、罐頭、零食）建議趁特價大量囤貨，省下整週生活費。";
        if (cat === 'meat') return "🥩 澳洲肉品性價比判斷重點：注意每公斤單價 ($/kg)。雞肉/肉末低於 $11/kg、牛排低於 $25/kg 即為打工度假高性價比蛋白質首選！";
        if (cat === 'seafood') return "🦐 超市每週輪流特價鮭魚與蝦子，建議自備保冷袋採買，回家可分裝冷凍保鮮。";
        if (cat === 'health_vitamins') return "💊 澳洲保健品（Swisse、Blackmores）通常每 2-3 週輪流推出 50% 半價，切勿在非特價時購買原價！";
        if (cat === 'dairy_eggs') return "🥛 鮮奶與雞蛋常態建議比價 ALDI。若 Coles / Woolies 特價起司或大包裝優格有折扣，可列入備餐優質蛋白質清單。";
        if (cat === 'produce') return "🥦 蔬菜水果看每公斤價格與產季。週二下午至傍晚有機會在生鮮區遇到即期黃標（Quick Sale）出清！";
        if (store === 'ALDI') return "⚡ ALDI 自有品牌日常定價已非常平價，適合固定採買米、油、蛋、麵包等每週必備主食基底。";
        return "💡 採買前請核對卡片上的單位價格（$/100g 或 $/kg），確認大包裝是否真的比單件更划算！";
    } else if (currentLang === 'en') {
        if (isHalf) return "🔥 50% OFF Half Price Deal! Great time to stock up on non-perishables (laundry, toiletries, pantry staples) to save big on your weekly budget.";
        if (cat === 'meat') return "🥩 Working holiday tip: Always check unit price ($/kg). Chicken breast/mince under $11/kg and beef steaks under $25/kg offer the best value.";
        if (cat === 'seafood') return "🦐 Supermarkets alternate weekly specials on salmon and tiger prawns. Bring a cooler bag and portion into freezer bags at home.";
        if (cat === 'health_vitamins') return "💊 Vitamins & supplements (Blackmores, Swisse) go on 50% OFF every 2-3 weeks. Never pay full price!";
        if (cat === 'dairy_eggs') return "🥛 Everyday milk and eggs are often cheapest at ALDI. Grab branded cheese/yogurt when discounted at Coles or Woolies.";
        if (cat === 'produce') return "🥦 Check $/kg across seasonal produce. Look for yellow clearance stickers on Tuesday afternoons!";
        if (store === 'ALDI') return "⚡ ALDI's private labels are already everyday low-priced—ideal for staples like rice, flour, oil, and bread.";
        return "💡 Always check the unit price ($/100g or $/kg) to confirm whether bulk packs offer genuine savings.";
    } else if (currentLang === 'ja') {
        if (isHalf) return "🔥 50% OFF 半額セール！洗剤・トイレットペーパー・保存食など日持ちするものは、このタイミングでの買いだめが一番節約になります。";
        if (cat === 'meat') return "🥩 ワーホリ自炊のコツ：必ず「$/kg（1kgあたり）」を確認！鶏むね肉やひき肉が$11/kg以下、牛肉ステーキが$25/kg以下なら買い時です。";
        if (cat === 'seafood') return "🦐 サーモンやエビはColes/Wooliesで交互に半額になります。保冷バッグを持参し、小分けにして冷凍保存がおすすめ。";
        if (cat === 'health_vitamins') return "💊 サプリメント（SwisseやBlackmores）は2〜3週間おきに50%オフになります。定価では買わないのがオーストラリアの常識！";
        if (cat === 'dairy_eggs') return "🥛 普段の牛乳や卵はALDIが最安。チーズやヨーグルトはColes/Wooliesの特売日を狙いましょう。";
        if (cat === 'produce') return "🥦 野菜・果物は1kgあたりの価格に注目。火曜日の夕方は賞味期限間近の黄色い割引シール（Quick Sale）が見つかりやすいです！";
        if (store === 'ALDI') return "⚡ ALDIはPB商品が普段から格安。お米、油、食パンなどの基本食料の買い出しに最適です。";
        return "💡 大容量パックが本当にお得かどうか、「単位価格（$/100gまたは$/kg）」で確認しましょう。";
    } else { // ko
        if (isHalf) return "🔥 50% OFF 반값 특가! 세제, 화장지, 통조림 등 유통기한이 긴 생필품은 반값 세일 때 쟁여두면 주간 생활비를 대폭 아낄 수 있습니다.";
        if (cat === 'meat') return "🥩 워홀러 장보기 팁: 반드시 '$/kg' 단위 가격을 확인하세요! 닭가슴살/다진육은 $11/kg 이하, 스테이크는 $25/kg 이하일 때가 가성비 최고입니다.";
        if (cat === 'seafood') return "🦐 연어와 타이거 새우는 울월스와 콜스에서 번갈아 반값 행사를 진행합니다. 보랭백을 챙겨가 소분 냉동 보관하세요.";
        if (cat === 'health_vitamins') return "💊 영양제(Swisse, Blackmores)는 2~3주마다 정기적으로 50% 반값 세일을 하니 정가에 구매하지 마세요!";
        if (cat === 'dairy_eggs') return "🥛 기본 우유와 계란은 ALDI가 가장 저렴하며, 요거트나 치즈는 콜스/울월스 특가 때 구매하는 것이 좋습니다.";
        if (cat === 'produce') return "🥦 신선 채소/과일은 kg당 가격과 제철 여부를 체크하세요. 화요일 오후~저녁에는 마감 임박 노란색 할인 스티커가 자주 붙습니다!";
        if (store === 'ALDI') return "⚡ ALDI 자체 브랜드(PB)는 평소에도 최저가 수준이므로 쌀, 식용유, 식빵 등 기본 식자재 구매에 최적입니다.";
        return "💡 대용량이 항상 저렴한 것은 아닙니다. 카드에 표기된 단위 가격($/100g 또는 $/kg)을 반드시 비교하세요.";
    }
}

// Shopping Drawer Operations
function toggleShoppingDrawer() {
    const drawer = document.getElementById('shoppingDrawer');
    const backdrop = document.getElementById('shoppingDrawerBackdrop');
    const isOpen = !drawer.classList.contains('translate-x-full');

    if (isOpen) {
        drawer.classList.add('translate-x-full');
        backdrop.classList.add('hidden');
    } else {
        drawer.classList.remove('translate-x-full');
        backdrop.classList.remove('hidden');
        loadShoppingList();
    }
}

// LocalStorage helpers for Shopping List in Static / Cloudflare Pages mode
function getLocalShoppingList() {
    try {
        return JSON.parse(localStorage.getItem('whv_shopping_items') || '[]');
    } catch (e) {
        return [];
    }
}

function saveLocalShoppingList(items) {
    localStorage.setItem('whv_shopping_items', JSON.stringify(items));
}

function repairLocalShoppingItems() {
    try {
        const items = getLocalShoppingList();
        if (!items || items.length === 0) return;
        let changed = false;
        const pool = window.staticSpecials || allSpecials || [];
        items.forEach(it => {
            const price = (typeof it.price === 'number') ? it.price : (parseFloat(it.price) || 0);
            let was = (typeof it.was_price === 'number') ? it.was_price : (parseFloat(it.was_price) || 0);
            let save = (typeof it.save_amount === 'number') ? it.save_amount : (parseFloat(it.save_amount) || 0);

            // Match against staticSpecials pool if available
            if ((save <= 0 || was <= 0) && pool.length > 0) {
                const match = pool.find(s => (it.product_id && s.id === it.product_id) || (s.title === it.title && s.store === it.store));
                if (match) {
                    const matchPrice = (typeof match.price === 'number') ? match.price : (parseFloat(match.price) || 0);
                    const matchWas = (typeof match.was_price === 'number') ? match.was_price : (parseFloat(match.was_price) || 0);
                    let matchSave = (typeof match.save_amount === 'number') ? match.save_amount : (parseFloat(match.save_amount) || 0);
                    if (matchSave <= 0 && matchWas > matchPrice && matchPrice > 0) {
                        matchSave = Math.round((matchWas - matchPrice) * 100) / 100;
                    }
                    if (matchSave > 0 && save <= 0) {
                        save = matchSave;
                        it.save_amount = save;
                        changed = true;
                    }
                    if (matchWas > 0 && was <= 0) {
                        was = matchWas;
                        it.was_price = was;
                        changed = true;
                    }
                }
            }

            // Derive save from was - price
            if (save <= 0 && was > price && price > 0) {
                save = Math.round((was - price) * 100) / 100;
                it.save_amount = save;
                changed = true;
            }
            // Derive was from price + save
            if (was <= 0 && save > 0 && price > 0) {
                was = Math.round((price + save) * 100) / 100;
                it.was_price = was;
                changed = true;
            }
        });
        if (changed) {
            saveLocalShoppingList(items);
        }
    } catch (e) {
        console.error('Error repairing shopping list items:', e);
    }
}

function getLocalShoppingData() {
    const items = getLocalShoppingList();
    const grouped = {'Woolworths': [], 'Coles': [], 'ALDI': [], 'Other': []};
    let total_cost = 0;
    let total_saved = 0;
    let total_original = 0;
    items.forEach(it => {
        const st = it.store || 'Other';
        if (!grouped[st]) grouped[st] = [];
        grouped[st].push(it);
        const price = (typeof it.price === 'number') ? it.price : (parseFloat(it.price) || 0);
        const qty = it.quantity || 1;
        total_cost += price * qty;

        let save = (typeof it.save_amount === 'number') ? it.save_amount : (parseFloat(it.save_amount) || 0);
        const was = (typeof it.was_price === 'number') ? it.was_price : (parseFloat(it.was_price) || 0);
        if (save <= 0 && was > price && price > 0) {
            save = Math.round((was - price) * 100) / 100;
        }
        total_saved += save * qty;

        const origPrice = (was > price) ? was : (save > 0 ? (price + save) : price);
        total_original += origPrice * qty;
    });

    const calculatedOriginal = Math.round((total_cost + total_saved) * 100) / 100;
    const finalOriginal = Math.max(Math.round(total_original * 100) / 100, calculatedOriginal);

    return {
        items,
        grouped,
        total_items: items.length,
        total_original: finalOriginal,
        total_saved: Math.round(total_saved * 100) / 100,
        total_cost: Math.round(total_cost * 100) / 100
    };
}

async function loadShoppingList() {
    repairLocalShoppingItems();
    let data = null;
    try {
        const res = await fetch('/api/shopping-list');
        if (res.ok) {
            data = await res.json();
        } else {
            data = getLocalShoppingData();
        }
    } catch (e) {
        data = getLocalShoppingData();
    }

    try {
        const originalTotal = data.total_original !== undefined ? data.total_original : (data.total_cost + (data.total_saved || 0));
        const discountTotal = data.total_saved || 0;
        const checkoutTotal = data.total_cost || 0;

        const elCartBadge = document.getElementById('cartCountBadge');
        if (elCartBadge) elCartBadge.textContent = data.total_items || 0;

        const elOriginal = document.getElementById('drawerOriginalTotal');
        if (elOriginal) elOriginal.textContent = `$${originalTotal.toFixed(2)}`;

        const elDiscount = document.getElementById('drawerDiscountTotal');
        if (elDiscount) elDiscount.textContent = `- $${discountTotal.toFixed(2)}`;

        const elCheckout = document.getElementById('drawerCheckoutTotal');
        if (elCheckout) elCheckout.textContent = `$${checkoutTotal.toFixed(2)}`;

        const elTotalCost = document.getElementById('drawerTotalCost');
        if (elTotalCost) elTotalCost.textContent = `$${checkoutTotal.toFixed(2)}`;

        const elTotalSaved = document.getElementById('drawerTotalSaved');
        if (elTotalSaved) elTotalSaved.textContent = `$${discountTotal.toFixed(2)}`;

        const container = document.getElementById('shoppingListContainer');
        container.innerHTML = '';

        if (!data.items || data.items.length === 0) {
            container.innerHTML = `
                <div class="py-20 text-center text-slate-400 dark:text-zinc-500">
                    <i class="fa-solid fa-basket-shopping text-4xl mb-3 text-slate-300 dark:text-zinc-700"></i>
                    <p class="text-xs font-bold text-slate-600 dark:text-zinc-400">${t('empty_manifest')}</p>
                    <p class="text-[11px] text-slate-400 dark:text-zinc-500 mt-1">${t('empty_manifest_sub')}</p>
                </div>
            `;
            return;
        }

        const stores = ['Woolworths', 'Coles', 'ALDI', 'Other'];
        stores.forEach(store => {
            const items = data.grouped[store];
            if (!items || items.length === 0) return;

            let badgeClass = 'bg-emerald-600 text-white';
            if (store === 'Coles') badgeClass = 'bg-rose-600 text-white';
            if (store === 'ALDI') badgeClass = 'bg-blue-600 text-white';

            let storeSubtotal = items.reduce((acc, cur) => acc + (cur.price * cur.quantity), 0);

            const section = document.createElement('div');
            section.className = 'bg-slate-50 dark:bg-zinc-800/40 p-3.5 rounded-2xl border border-slate-200/80 dark:border-zinc-800 space-y-2.5';
            section.innerHTML = `
                <div class="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-zinc-700/80 text-xs">
                    <span class="px-2 py-0.5 rounded-md font-bold ${badgeClass}">
                        ${store} (${items.length})
                    </span>
                    <span class="font-bold text-slate-700 dark:text-zinc-300">
                        ${t('subtotal')} $${storeSubtotal.toFixed(2)}
                    </span>
                </div>
                <div class="space-y-1.5">
                    ${items.map(it => {
                        const itPrice = parseSupermarketPrice(it.price_display, it.price);
                        const itPriceNum = (typeof it.price === 'number') ? it.price : (parseFloat(it.price) || 0);
                        let itSave = (typeof it.save_amount === 'number') ? it.save_amount : (parseFloat(it.save_amount) || 0);
                        let itWas = (typeof it.was_price === 'number') ? it.was_price : (parseFloat(it.was_price) || 0);
                        if (itSave <= 0 && itWas > itPriceNum && itPriceNum > 0) {
                            itSave = Math.round((itWas - itPriceNum) * 100) / 100;
                        } else if (itWas <= 0 && itSave > 0 && itPriceNum > 0) {
                            itWas = Math.round((itPriceNum + itSave) * 100) / 100;
                        }
                        const fallbackImg = DEFAULT_FALLBACK_IMG;
                        return `
                        <div class="flex items-center justify-between gap-2.5 p-2.5 rounded-xl bg-white dark:bg-zinc-800 border border-slate-200/80 dark:border-zinc-700/70 shadow-2xs ${it.is_bought ? 'opacity-40' : ''}">
                            <div class="flex items-center gap-2.5 flex-1 min-w-0">
                                <input 
                                    type="checkbox" 
                                    ${it.is_bought ? 'checked' : ''} 
                                    onchange="toggleShoppingItem(${it.id}, this.checked)"
                                    class="w-4 h-4 text-emerald-600 rounded border-slate-300 dark:border-zinc-600 focus:ring-emerald-500 cursor-pointer shrink-0"
                                />
                                <!-- Product Image Thumbnail -->
                                <div class="w-12 h-12 rounded-lg bg-slate-50 dark:bg-zinc-900/60 p-1 flex items-center justify-center shrink-0 border border-slate-100 dark:border-zinc-700/60 overflow-hidden">
                                    <img 
                                        src="${it.image_url || fallbackImg}" 
                                        alt="${it.title}" 
                                        loading="lazy" 
                                        class="max-h-full max-w-full object-contain"
                                        onerror="this.src='${fallbackImg}'"
                                    />
                                </div>
                                <div class="min-w-0 flex-1">
                                    <div class="flex items-center gap-1.5">
                                        <h4 class="text-xs font-semibold text-slate-900 dark:text-zinc-100 truncate ${it.is_bought ? 'line-through text-slate-400' : ''}" title="${it.title}">
                                             ${it.title}
                                        </h4>
                                        <span class="text-[9px] sm:text-[10px] px-1 py-0.2 rounded font-medium shrink-0 ${it.period === 'next' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300' : 'bg-slate-100 dark:bg-zinc-700 text-slate-600 dark:text-zinc-300'}">
                                            ${it.period === 'next' ? t('next_cycle') : t('current_cycle')}
                                        </span>
                                    </div>
                                    ${(() => {
                                        const itTrans = getProductTranslation(it, currentLang);
                                        return (itTrans && currentLang !== 'en') ? `<div class="text-[11px] font-medium text-emerald-700 dark:text-emerald-300 truncate mt-0.5" title="${itTrans}">${itTrans}</div>` : '';
                                    })()}
                                    <div class="text-[11px] text-slate-500 dark:text-zinc-400 flex items-center gap-2 mt-0.5 font-medium flex-wrap">
                                        <span class="font-bold text-slate-900 dark:text-white">${itPrice.displayWithUnit}</span>
                                        ${itSave > 0 ? `<span class="px-1 py-0.2 rounded text-[10px] font-black bg-amber-400 text-slate-950">${t('save_badge', { amount: itSave.toFixed(2) })}</span>` : ''}
                                        ${itWas > 0 ? `<span class="text-slate-400 line-through text-[10px]">${t('was_price')} $${itWas.toFixed(2)}</span>` : ''}
                                    </div>
                                </div>
                            </div>
                            <button onclick="deleteShoppingItem(${it.id})" class="text-slate-400 hover:text-rose-500 p-1.5 transition shrink-0" title="${t('delete')}">
                                <i class="fa-solid fa-xmark text-xs"></i>
                            </button>
                        </div>
                    `;}).join('')}
                </div>
            `;
            container.appendChild(section);
        });

    } catch (e) {
        console.error('Failed to load shopping list', e);
    }
}

async function addToShoppingList(item) {
    const price = (typeof item.price === 'number') ? item.price : (parseFloat(item.price) || 0);
    let save = (typeof item.save_amount === 'number') ? item.save_amount : (parseFloat(item.save_amount) || 0);
    let was = (typeof item.was_price === 'number') ? item.was_price : (parseFloat(item.was_price) || 0);

    if (save <= 0 && was > price && price > 0) {
        save = Math.round((was - price) * 100) / 100;
    } else if (was <= 0 && save > 0 && price > 0) {
        was = Math.round((price + save) * 100) / 100;
    }

    const payload = {
        product_id: item.id,
        store: item.store,
        period: item.period || currentPeriod,
        date_range: item.date_range || '',
        title: item.title,
        price: price,
        price_display: item.price_display,
        quantity: 1,
        image_url: item.image_url,
        save_amount: save,
        was_price: was
    };

    try {
        const res = await fetch('/api/shopping-list', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast(`${t('added')}: ${item.title.substring(0, 18)}...`);
            loadShoppingList();
            return;
        }
    } catch (e) {}

    // Fallback to localStorage
    const items = getLocalShoppingList();
    payload.id = Date.now();
    payload.is_bought = false;
    items.push(payload);
    saveLocalShoppingList(items);
    showToast(`${t('added')}: ${item.title.substring(0, 18)}...`);
    loadShoppingList();
}

async function toggleShoppingItem(id, isBought) {
    try {
        const res = await fetch(`/api/shopping-list/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_bought: isBought })
        });
        if (res.ok) {
            loadShoppingList();
            return;
        }
    } catch (e) {}

    const items = getLocalShoppingList();
    const target = items.find(it => it.id === id);
    if (target) target.is_bought = isBought;
    saveLocalShoppingList(items);
    loadShoppingList();
}

async function deleteShoppingItem(id) {
    try {
        const res = await fetch(`/api/shopping-list/${id}`, { method: 'DELETE' });
        if (res.ok) {
            loadShoppingList();
            return;
        }
    } catch (e) {}

    let items = getLocalShoppingList();
    items = items.filter(it => it.id !== id);
    saveLocalShoppingList(items);
    loadShoppingList();
}

async function clearShoppingList() {
    if (!confirm(t('clear_manifest') + '?')) return;
    try {
        const res = await fetch('/api/shopping-list', { method: 'DELETE' });
        if (res.ok) {
            showToast(t('clear_manifest'));
            loadShoppingList();
            return;
        }
    } catch (e) {}

    saveLocalShoppingList([]);
    showToast(t('clear_manifest'));
    loadShoppingList();
}

async function copyShoppingList() {
    try {
        let data = null;
        try {
            const res = await fetch('/api/shopping-list');
            if (res.ok) data = await res.json();
            else data = getLocalShoppingData();
        } catch (err) {
            data = getLocalShoppingData();
        }

        if (!data.items || data.items.length === 0) {
            showToast(t('empty_manifest'), 'fa-circle-exclamation', true);
            return;
        }

        let text = `🛒 ${t('shopping_manifest')} (${new Date().toLocaleDateString()})\n`;
        text += `🇦🇺 All prices in AUD ($)\n\n`;
        const stores = ['Woolworths', 'Coles', 'ALDI', 'Other'];
        stores.forEach(st => {
            const items = data.grouped[st];
            if (items && items.length > 0) {
                text += `【${st}】\n`;
                items.forEach((it, idx) => {
                    const tag = it.period === 'next' ? `[${t('next_cycle')}]` : `[${t('current_cycle')}]`;
                    const itPrice = parseSupermarketPrice(it.price_display, it.price);
                    const itTrans = getProductTranslation(it, currentLang);
                    const titleDisplay = (itTrans && currentLang !== 'en') ? `${it.title} (${itTrans})` : it.title;
                    text += `  ${idx + 1}. ${tag} ${titleDisplay} - ${itPrice.displayWithUnit}\n`;
                });
                text += `\n`;
            }
        });

        const origTotal = data.total_original !== undefined ? data.total_original : (data.total_cost + (data.total_saved || 0));
        text += `💰 ${t('original_total')} $${origTotal.toFixed(2)}\n`;
        text += `🏷️ ${t('discount_total')} - $${data.total_saved.toFixed(2)}\n`;
        text += `🧾 ${t('checkout_total')} $${data.total_cost.toFixed(2)}`;

        await navigator.clipboard.writeText(text);
        showToast(t('copied'));
    } catch (e) {
        showToast('Copy failed', 'fa-circle-xmark', true);
    }
}

async function sendShoppingListEmail() {
    const emailInput = document.getElementById('shoppingEmailInput');
    const email = (emailInput ? emailInput.value : '').trim();

    // Validate Email
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showToast(t('email_invalid'), 'fa-circle-exclamation', true);
        if (emailInput) emailInput.focus();
        return;
    }

    // Get current shopping list data
    let data = null;
    try {
        const res = await fetch('/api/shopping-list');
        if (res.ok) data = await res.json();
        else data = getLocalShoppingData();
    } catch (err) {
        data = getLocalShoppingData();
    }

    if (!data.items || data.items.length === 0) {
        showToast(t('empty_cart_error'), 'fa-circle-exclamation', true);
        return;
    }

    const btn = document.getElementById('sendEmailBtn');
    const icon = document.getElementById('sendEmailIcon');
    const btnText = document.getElementById('sendEmailBtnText');
    const origIcon = icon ? icon.className : 'fa-solid fa-paper-plane text-xs';
    const origText = btnText ? btnText.textContent : t('email_send_btn');

    if (btn) btn.disabled = true;
    if (icon) icon.className = 'fa-solid fa-spinner fa-spin text-xs';
    if (btnText) btnText.textContent = t('sending_email');

    // Build plain text version
    let text = `🛒 ${t('shopping_manifest')} (${new Date().toLocaleDateString()})\n`;
    text += `🇦🇺 All prices in AUD ($)\n\n`;
    const stores = ['Woolworths', 'Coles', 'ALDI', 'Other'];
    stores.forEach(st => {
        const items = data.grouped[st];
        if (items && items.length > 0) {
            text += `【${st}】\n`;
            items.forEach((it, idx) => {
                const tag = it.period === 'next' ? `[${t('next_cycle')}]` : `[${t('current_cycle')}]`;
                const itPrice = parseSupermarketPrice(it.price_display, it.price);
                const itTrans = getProductTranslation(it, currentLang);
                const titleDisplay = (itTrans && currentLang !== 'en') ? `${it.title} (${itTrans})` : it.title;
                text += `  ${idx + 1}. ${tag} ${titleDisplay} - ${itPrice.displayWithUnit}`;
                if (it.quantity > 1) text += ` x${it.quantity}`;
                if (it.save_amount > 0) text += ` (Save $${(it.save_amount * it.quantity).toFixed(2)})`;
                text += `\n`;
            });
            text += `\n`;
        }
    });
    text += `💰 ${t('total_budget')} $${data.total_cost.toFixed(2)} (${t('total_saved')} $${data.total_saved.toFixed(2)})\n\n`;
    text += `來自：澳洲三大超市特價比價站 (AU Supermarket Specials)\n`;
    text += `💡 任何建議與反饋，歡迎來信至：rick97005109@gmail.com`;

    // Build responsive HTML version for email
    let html = `
    <div style="max-width: 600px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #059669, #0d9488); padding: 24px; text-align: center; color: #ffffff;">
            <h1 style="margin: 0; font-size: 20px; font-weight: bold;">🛒 澳洲三大超市特價採買清單</h1>
            <p style="margin: 6px 0 0 0; font-size: 12px; opacity: 0.9;">Woolworths · Coles · ALDI 每週省錢比價清單 (${new Date().toLocaleDateString()})</p>
        </div>
        <div style="padding: 20px;">
    `;

    stores.forEach(st => {
        const items = data.grouped[st];
        if (items && items.length > 0) {
            let badgeBg = '#059669';
            if (st === 'Coles') badgeBg = '#e11d48';
            if (st === 'ALDI') badgeBg = '#2563eb';

            html += `
                <div style="margin-bottom: 20px; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
                    <div style="background-color: #f8fafc; padding: 10px 14px; border-bottom: 1px solid #e2e8f0;">
                        <span style="background-color: ${badgeBg}; color: #ffffff; padding: 3px 8px; border-radius: 6px; font-size: 12px; font-weight: bold;">${st} (${items.length})</span>
                    </div>
                    <ul style="list-style: none; margin: 0; padding: 10px 14px;">
            `;
            items.forEach(it => {
                const itPrice = parseSupermarketPrice(it.price_display, it.price);
                const tag = it.period === 'next' ? `[${t('next_cycle')}] ` : '';
                const itTrans = getProductTranslation(it, currentLang);
                html += `
                    <li style="padding: 10px 0; border-bottom: 1px dashed #f1f5f9; display: flex; align-items: center; justify-content: space-between; font-size: 13px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            ${it.image_url ? `<img src="${it.image_url}" alt="${it.title}" style="width: 44px; height: 44px; object-fit: contain; border-radius: 8px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 2px; flex-shrink: 0;" />` : ''}
                            <div>
                                <strong style="color: #0f172a;">${tag}${it.title}</strong>
                                ${itTrans && currentLang !== 'en' ? `<div style="color: #059669; font-size: 11px; font-weight: 600; margin-top: 2px;">${itTrans}</div>` : ''}
                                <div style="color: #64748b; font-size: 11px; margin-top: 2px;">數量: ${it.quantity} | 單價: ${itPrice.displayWithUnit}</div>
                            </div>
                        </div>
                        <div style="text-align: right; flex-shrink: 0;">
                            <span style="font-weight: bold; color: #059669;">$${(it.price * it.quantity).toFixed(2)}</span>
                            ${it.save_amount > 0 ? `<div style="color: #e11d48; font-size: 11px;">省 $${(it.save_amount * it.quantity).toFixed(2)}</div>` : ''}
                        </div>
                    </li>
                `;
            });
            html += `
                    </ul>
                </div>
            `;
        }
    });

    html += `
            <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 14px; margin-top: 15px;">
                <div style="display: flex; justify-content: space-between; font-size: 14px; font-weight: bold; color: #0f172a;">
                    <span>預估總花費：</span>
                    <span>$${data.total_cost.toFixed(2)} AUD</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: bold; color: #e11d48; margin-top: 4px;">
                    <span>本週預計節省：</span>
                    <span>$${data.total_saved.toFixed(2)} AUD</span>
                </div>
            </div>
            <div style="text-align: center; margin-top: 24px; font-size: 11px; color: #94a3b8;">
                <p style="margin: 0;">此郵件由 <strong>澳洲超市特價優惠</strong> 系統自動產生</p>
                <p style="margin: 4px 0 0 0;">祝您在澳洲採買省心省荷包！🦘✨</p>
                <p style="margin: 8px 0 0 0; color: #64748b;">💡 任何建議或反饋，歡迎來信：<a href="mailto:rick97005109@gmail.com" style="color: #059669; text-decoration: underline; font-weight: bold;">rick97005109@gmail.com</a></p>
            </div>
        </div>
    </div>
    `;

    try {
        const res = await fetch('/api/send-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: email,
                items: data.items,
                grouped: data.grouped,
                total_cost: data.total_cost,
                total_saved: data.total_saved,
                text_content: text,
                html_content: html
            })
        });

        const result = await res.json().catch(() => ({}));
        if (res.ok && result.ok) {
            showToast(t('email_sent_success'), 'fa-circle-check');
            if (emailInput) emailInput.value = '';
        } else {
            if (result.error && result.error.message) {
                console.warn('Resend notice:', result.error.message);
                showToast(result.error.message, 'fa-triangle-exclamation', true);
            }
            // Backend signaled fallback or key not configured -> open mail client
            openMailtoFallback(email, text);
        }
    } catch (e) {
        // Pure static deployment without /api/send-email -> open mail client
        openMailtoFallback(email, text);
    } finally {
        if (btn) btn.disabled = false;
        if (icon) icon.className = origIcon;
        if (btnText) btnText.textContent = origText;
    }
}

function openMailtoFallback(email, text) {
    const subject = encodeURIComponent(`🛒 我的澳洲超市採買清單 (${new Date().toLocaleDateString()})`);
    const body = encodeURIComponent(text);
    const mailtoUrl = `mailto:${email}?subject=${subject}&body=${body}`;
    window.location.href = mailtoUrl;
    showToast(t('email_mailto_opened'), 'fa-envelope');
}

// Background Updater
async function triggerUpdate() {
    if (isUpdating) return;
    if (!confirm(t('update_feed') + '?')) return;

    try {
        const res = await fetch('/api/update?pages=10', { method: 'POST' });
        const data = await res.json();
        showToast(t('updating'));
        checkUpdateStatus();
    } catch (e) {
        showToast('Update failed', 'fa-circle-xmark', true);
    }
}

async function checkUpdateStatus() {
    const updateBtn = document.getElementById('updateBtn');
    const updateIcon = document.getElementById('updateIcon');
    const updateText = document.getElementById('updateBtnText');

    try {
        const res = await fetch('/api/update-status');
        const data = await res.json();

        if (data.is_updating) {
            isUpdating = true;
            if (updateBtn) updateBtn.disabled = true;
            if (updateIcon) updateIcon.classList.add('fa-spin');
            if (updateText) updateText.textContent = t('updating');
            setTimeout(checkUpdateStatus, 3000);
        } else {
            if (isUpdating) {
                showToast(t('update_done'));
                loadStats();
                loadSpecials();
            }
            isUpdating = false;
            if (updateBtn) updateBtn.disabled = false;
            if (updateIcon) updateIcon.classList.remove('fa-spin');
            if (updateText) updateText.textContent = t('update_feed');
        }
    } catch (e) {
        // Background update status check optional
    }
}

// Creator Announcement / 站長的話 (多語系同步切換)
let cachedAnnouncement = null;

async function loadAnnouncement() {
    try {
        cachedAnnouncement = await fetchStaticJson('announcement.json');
        if (cachedAnnouncement) {
            renderAnnouncement();
        }
    } catch (e) {
        console.log('No announcement available');
    }
}

function renderAnnouncement() {
    const box = document.getElementById('announcementBox');
    if (!box || !cachedAnnouncement) return;

    if (!cachedAnnouncement.enabled) {
        box.classList.add('hidden');
        return;
    }

    const isDismissed = localStorage.getItem('dismiss_announcement_date');
    if (isDismissed === cachedAnnouncement.date) {
        box.classList.add('hidden');
        return;
    }

    // Read language specific announcement
    const langData = cachedAnnouncement[currentLang] || cachedAnnouncement['zh'] || cachedAnnouncement;

    document.getElementById('announcementTitle').textContent = langData.title || cachedAnnouncement.title || '📢 站長的話';
    document.getElementById('announcementAuthor').textContent = langData.author || cachedAnnouncement.author || '站長';
    document.getElementById('announcementDate').textContent = cachedAnnouncement.date || '';
    document.getElementById('announcementBadge').textContent = langData.badge || cachedAnnouncement.badge || '最新公告';
    document.getElementById('announcementContent').textContent = langData.content || cachedAnnouncement.content || '';

    const linkElem = document.getElementById('announcementLink');
    const linkText = document.getElementById('announcementLinkText');
    const linkUrl = cachedAnnouncement.link_url || langData.link_url;
    if (linkUrl && linkUrl.trim()) {
        linkElem.href = linkUrl;
        linkText.textContent = langData.link_text || '了解更多';
        linkElem.classList.remove('hidden');
    } else {
        linkElem.classList.add('hidden');
    }

    box.classList.remove('hidden');
}

function dismissAnnouncement() {
    const box = document.getElementById('announcementBox');
    if (box) {
        box.classList.add('hidden');
        const dateText = document.getElementById('announcementDate').textContent;
        if (dateText) {
            localStorage.setItem('dismiss_announcement_date', dateText);
        }
    }
}

// App Initialization (Runs after all constants, models, and UI functions are defined)
function initApp() {
    isStaticMode = window.location.hostname.includes('pages.dev') ||
                   window.location.hostname.includes('github.io') ||
                   window.location.protocol === 'file:' ||
                   window.location.hostname === 'localhost' ||
                   window.location.hostname === '127.0.0.1' ||
                   !window.location.port;

    initTheme();
    initLanguage();
    renderCategoryBar();
    initScrollListeners();
    loadStats();
    loadAnnouncement();
    loadSpecials();
    loadShoppingList();
    checkUpdateStatus();
    setTimeout(loadTranslations, 4000);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}


