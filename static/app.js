// State
let currentPeriod = 'current'; // 'current' or 'next'
let currentStore = 'All';
let currentCategory = 'all';
let currentSearch = '';
let searchTimeout = null;
let isUpdating = false;
let globalStats = null;

// Categories definition (Aligned with Australian Supermarket Departments)
const CATEGORY_KEYS = [
    'all',
    'produce',
    'meat',
    'seafood',
    'dairy_eggs',
    'bakery',
    'pantry',
    'snacks',
    'drinks',
    'frozen',
    'health_vitamins',
    'household'
];

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initLanguage();
    renderCategoryBar();
    initScrollListeners();
    loadTranslations();
    loadStats();
    loadAnnouncement();
    loadSpecials();
    loadShoppingList();
    checkUpdateStatus();
});

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
}

// Render Categories Bar (2 Rows: Row 1 Fresh/Daily, Row 2 Pantry/Snacks/Home)
function renderCategoryBar() {
    const bar = document.getElementById('categoryBar');
    if (!bar) return;

    bar.innerHTML = '';
    
    // Arrange into 2 rows: 6 columns with 2 items per column for grid-flow-col
    // Row 1: Fresh & Perishables (Produce -> Meat -> Seafood -> Dairy & Eggs -> Bakery)
    // Row 2: Grocery, Drinks & Home (Pantry -> Snacks -> Drinks -> Freezer -> Health & Beauty -> Household)
    const row1Keys = ['all', 'produce', 'meat', 'seafood', 'dairy_eggs', 'bakery'];
    const row2Keys = ['pantry', 'snacks', 'drinks', 'frozen', 'health_vitamins', 'household'];
    
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
        const name = getCategoryName(catKey);

        btn.dataset.cat = catKey;
        btn.className = isActive
            ? "px-2.5 sm:px-3 py-1 rounded-lg sm:rounded-xl text-[11px] sm:text-xs font-bold bg-slate-900 dark:bg-emerald-600 text-white shadow-xs shrink-0 transition active:scale-95 whitespace-nowrap text-center"
            : "px-2.5 sm:px-3 py-1 rounded-lg sm:rounded-xl text-[11px] sm:text-xs font-semibold bg-slate-100 dark:bg-zinc-800/80 hover:bg-slate-200 dark:hover:bg-zinc-700 text-slate-700 dark:text-zinc-300 shrink-0 transition active:scale-95 whitespace-nowrap text-center";

        btn.textContent = name;
        btn.onclick = () => selectCategory(catKey);
        bar.appendChild(btn);
    });
}

function selectCategory(catKey) {
    currentCategory = catKey;
    renderCategoryBar();

    // Auto smooth scroll the active button into center view horizontally
    const bar = document.getElementById('categoryBar');
    if (bar) {
        const activeBtn = bar.querySelector(`[data-cat="${catKey}"]`);
        if (activeBtn) {
            activeBtn.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
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

let isStaticMode = false;
let staticSpecials = [];

// Helper to fetch static JSON that works seamlessly on both local server and Cloudflare Pages
async function fetchStaticJson(filename) {
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
                return await res.json();
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
    if (nextDateStr) {
        document.getElementById('periodDateNextBadge').textContent = `(${nextDateStr.replace(' 2026', '')})`;
    }

    const activeInfo = currentPeriod === 'current' ? currentData : nextData;
    const activeRangeText = activeInfo.date_range || (currentPeriod === 'current' ? t('current_cycle') : t('next_cycle'));
    document.getElementById('activeDateRange').textContent = activeRangeText;

    const headerBadge = document.getElementById('headerPeriodBadge');
    const periodIndicator = document.getElementById('periodIndicatorBadge');
    if (currentPeriod === 'current') {
        headerBadge.className = "text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300";
        headerBadge.textContent = t('current_cycle');
        periodIndicator.className = "text-[11px] px-2 py-0.5 rounded-md font-semibold bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/60";
        periodIndicator.textContent = `${t('current_cycle')} (${activeRangeText})`;
    } else {
        headerBadge.className = "text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 dark:bg-amber-950/70 dark:text-amber-300 border border-amber-300 dark:border-amber-700";
        headerBadge.textContent = t('next_cycle');
        periodIndicator.className = "text-[11px] px-2 py-0.5 rounded-md font-bold bg-amber-100 text-amber-900 dark:bg-amber-950/70 dark:text-amber-300 border border-amber-300 dark:border-amber-700";
        periodIndicator.textContent = `${t('next_cycle')} (${activeRangeText})`;
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
        btnCurr.className = "flex items-center justify-center gap-1.5 py-1.5 sm:py-2 px-3 rounded-lg text-xs sm:text-sm font-bold bg-white dark:bg-zinc-700 text-slate-900 dark:text-white shadow-2xs transition";
        btnNext.className = "flex items-center justify-center gap-1.5 py-1.5 sm:py-2 px-3 rounded-lg text-xs sm:text-sm font-semibold text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white transition";
    } else {
        btnNext.className = "flex items-center justify-center gap-1.5 py-1.5 sm:py-2 px-3 rounded-lg text-xs sm:text-sm font-bold bg-white dark:bg-zinc-700 text-slate-900 dark:text-white shadow-2xs transition";
        btnCurr.className = "flex items-center justify-center gap-1.5 py-1.5 sm:py-2 px-3 rounded-lg text-xs sm:text-sm font-semibold text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white transition";
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
        if (tab.dataset.store === store) {
            tab.className = 'store-tab active px-3 py-1.5 rounded-lg transition bg-white dark:bg-zinc-700 text-slate-900 dark:text-white shadow-2xs font-bold';
        } else {
            let textColor = 'text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white';
            if (tab.dataset.store === 'Woolworths') textColor = 'text-slate-600 dark:text-zinc-400 hover:text-emerald-600 dark:hover:text-emerald-400';
            if (tab.dataset.store === 'Coles') textColor = 'text-slate-600 dark:text-zinc-400 hover:text-rose-600 dark:hover:text-rose-400';
            if (tab.dataset.store === 'ALDI') textColor = 'text-slate-600 dark:text-zinc-400 hover:text-blue-600 dark:hover:text-blue-400';
            tab.className = `store-tab px-3 py-1.5 rounded-lg transition font-semibold ${textColor}`;
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
            if (currentCategory !== 'all' && it.category !== currentCategory) return false;
            if (discountOnly) {
                const desc = (it.discount_desc || '').toLowerCase();
                const isHalf = desc.includes('1/2') || desc.includes('half') || (it.was_price > 0 && it.price <= it.was_price * 0.55);
                if (!isHalf) return false;
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

        // Sorting
        if (sortBy === 'save_desc') {
            filtered.sort((a, b) => (b.save_amount || 0) - (a.save_amount || 0));
        } else if (sortBy === 'price_asc') {
            filtered.sort((a, b) => (a.price || 0) - (b.price || 0));
        } else if (sortBy === 'price_desc') {
            filtered.sort((a, b) => (b.price || 0) - (a.price || 0));
        }

        loading.classList.add('hidden');
        currentLoadedItems = filtered;
        resultsCountText.textContent = t('found_targets', { n: filtered.length });

        if (filtered.length === 0) {
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

// Render Products Grid (Authentic Australian Supermarket Design)
function renderProducts(items) {
    const grid = document.getElementById('productsGrid');
    grid.innerHTML = '';

    items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'bg-white dark:bg-zinc-900 rounded-2xl border border-slate-200/90 dark:border-zinc-800 overflow-hidden shadow-2xs hover:shadow-md hover:border-slate-300 dark:hover:border-zinc-700 transition duration-200 flex flex-col justify-between group cursor-pointer active:scale-[0.98]';
        card.onclick = () => openProductModal(item);

        let storeColor = 'bg-emerald-600 text-white';
        if (item.store === 'Coles') storeColor = 'bg-rose-600 text-white';
        if (item.store === 'ALDI') storeColor = 'bg-blue-600 text-white';

        const isHalfPrice = item.discount_desc && (item.discount_desc.includes('1/2') || item.discount_desc.toLowerCase().includes('half'));
        const fallbackImg = "https://images.unsplash.com/photo-1542838132-92c53300491e?w=300&auto=format&fit=crop&q=60";

        const p = parseSupermarketPrice(item.price_display, item.price);
        const unitPriceClean = formatSupermarketUnitPrice(item.unit_price);
        const translated = getProductTranslation(item, currentLang);

        card.innerHTML = `
            <div class="p-2.5 sm:p-3.5 space-y-2 sm:space-y-2.5">
                <!-- Top Tags: Store, Category & 1/2 Price Badge -->
                <div class="flex items-center justify-between gap-1 flex-wrap">
                    <div class="flex items-center gap-1">
                        <span class="px-1.5 sm:px-2 py-0.5 rounded-md text-[10px] sm:text-[11px] font-bold ${storeColor}">
                            ${item.store}
                        </span>
                        <span class="px-1 sm:px-1.5 py-0.5 rounded-md text-[9px] sm:text-[10px] font-medium bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400">
                            ${getCategoryName(item.category)}
                        </span>
                    </div>
                    ${isHalfPrice ? `
                        <span class="px-1.5 sm:px-2 py-0.5 rounded-md text-[10px] sm:text-[11px] font-black bg-rose-500 text-white shadow-2xs">
                            1/2
                        </span>
                    ` : (item.discount_desc ? `
                        <span class="px-1.5 py-0.5 rounded-md text-[9px] sm:text-[10px] font-semibold bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200/60 dark:border-amber-800/60 truncate max-w-[90px] sm:max-w-[110px]">
                            ${item.discount_desc}
                        </span>
                    ` : '')}
                </div>

                <!-- Product Image -->
                <div class="w-full h-28 sm:h-36 rounded-xl bg-slate-50 dark:bg-zinc-800/50 flex items-center justify-center p-2 sm:p-2.5 relative overflow-hidden group-hover:bg-slate-100/70 dark:group-hover:bg-zinc-800 transition">
                    <img 
                        src="${item.image_url || fallbackImg}" 
                        alt="${item.title}" 
                        loading="lazy" 
                        class="max-h-full max-w-full object-contain group-hover:scale-105 transition-transform duration-200"
                        onerror="this.src='${fallbackImg}'"
                    />
                </div>

                <!-- Date Range Tag -->
                ${item.date_range ? `
                    <div class="text-[9px] sm:text-[10px] text-slate-400 dark:text-zinc-500 flex items-center gap-1 font-medium truncate" title="${item.date_range}">
                        <i class="fa-regular fa-calendar text-[8px] sm:text-[9px]"></i>
                        <span class="truncate">${item.date_range}</span>
                    </div>
                ` : ''}

                <!-- Product Title & Translation -->
                <div class="space-y-1">
                    <h3 class="text-xs sm:text-sm font-semibold text-slate-900 dark:text-zinc-100 line-clamp-2 leading-snug" title="${item.title}">
                        ${item.title}
                    </h3>
                    ${translated ? `
                        <div class="text-[11px] sm:text-xs font-medium text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/70 border border-emerald-200/60 dark:border-emerald-800/60 px-2 py-0.5 rounded-lg line-clamp-2 leading-tight" title="${translated}">
                            ${translated}
                        </div>
                    ` : ''}
                    <!-- Supermarket Unit Price (e.g. $1.25 / 100g) -->
                    ${unitPriceClean ? `
                        <div class="inline-flex items-center gap-1 text-[10px] sm:text-[11px] font-mono font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200/60 dark:border-emerald-800/60 px-1.5 py-0.5 rounded">
                            <span class="text-[9px]">⚖️</span>
                            <span>${unitPriceClean}</span>
                        </div>
                    ` : ''}
                </div>
            </div>

            <!-- Price & Add Button Footer (Australian Supermarket Lockup: $ 4 25 ea | Save $4.25 | Was $8.50) -->
            <div class="p-2.5 sm:p-3.5 pt-0 space-y-2 sm:space-y-2.5">
                <div class="space-y-1">
                    <!-- Coles / Woolies Big Price Lockup -->
                    <div class="flex items-baseline gap-0.5 leading-none">
                        <span class="text-xs sm:text-sm font-extrabold text-slate-900 dark:text-white self-start mt-0.5">$</span>
                        <span class="text-xl sm:text-3xl font-black tracking-tight text-slate-900 dark:text-white">${p.dollars}</span>
                        <span class="text-xs sm:text-sm font-extrabold text-slate-900 dark:text-white self-start mt-0.5">${p.cents}</span>
                        <span class="text-[10px] sm:text-xs font-semibold text-slate-500 dark:text-zinc-400 ml-1 self-baseline">${p.unit}</span>
                    </div>

                    <!-- Was & Save Badges Row -->
                    <div class="flex items-center gap-1.5 flex-wrap min-h-[1.2rem]">
                        ${item.save_amount > 0 ? `
                            <span class="px-1.5 py-0.5 rounded text-[10px] sm:text-[11px] font-black bg-amber-400 text-slate-950 dark:bg-amber-400 dark:text-slate-950 shadow-2xs leading-none">
                                Save $${item.save_amount.toFixed(2)}
                            </span>
                        ` : ''}
                        ${item.was_price > 0 ? `
                            <span class="text-[10px] sm:text-[11px] text-slate-400 line-through font-medium">
                                Was $${item.was_price.toFixed(2)}
                            </span>
                        ` : ''}
                    </div>
                </div>

                <div class="flex items-center justify-between text-[9px] sm:text-[10px] text-slate-400 dark:text-zinc-500 pt-1 border-t border-slate-100 dark:border-zinc-800/60">
                    <span class="group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition flex items-center gap-1">
                        <i class="fa-solid fa-circle-info text-[8px] sm:text-[9px]"></i>
                        <span>${t('view_details')}</span>
                    </span>
                    <span class="text-slate-300 dark:text-zinc-600">→</span>
                </div>

                <button 
                    onclick='event.stopPropagation(); addToShoppingList(${JSON.stringify(item).replace(/'/g, "&#39;")})'
                    class="w-full py-1.5 sm:py-2 px-2 sm:px-3 rounded-xl text-[11px] sm:text-xs font-bold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-600 hover:text-white dark:hover:bg-emerald-600 dark:hover:text-white border border-emerald-200/80 dark:border-emerald-800/80 transition flex items-center justify-center gap-1 active:scale-95 shadow-2xs"
                >
                    <i class="fa-solid fa-plus text-[10px] sm:text-xs"></i>
                    <span>${t('add_to_list')}</span>
                </button>
            </div>
        `;
        grid.appendChild(card);
    });
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

    const isHalfPrice = item.discount_desc && (item.discount_desc.includes('1/2') || item.discount_desc.toLowerCase().includes('half'));
    const fallbackImg = "https://images.unsplash.com/photo-1542838132-92c53300491e?w=300&auto=format&fit=crop&q=60";

    // Badges
    const storeBadge = document.getElementById('modalStoreBadge');
    storeBadge.className = `px-2.5 py-0.5 rounded-lg text-xs font-bold ${storeColor}`;
    storeBadge.textContent = item.store;

    document.getElementById('modalCategoryBadge').textContent = getCategoryName(item.category);
    
    const halfBadge = document.getElementById('modalHalfPriceBadge');
    if (isHalfPrice) {
        halfBadge.textContent = "1/2 PRICE";
        halfBadge.classList.remove('hidden');
    } else {
        halfBadge.classList.add('hidden');
    }

    // Image & Title
    const imgElem = document.getElementById('modalProductImg');
    imgElem.src = item.image_url || fallbackImg;
    imgElem.onerror = () => { imgElem.src = fallbackImg; };
    document.getElementById('modalProductTitle').textContent = item.title;

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
    
    const wasElem = document.getElementById('modalWasPrice');
    if (item.was_price > 0) {
        wasElem.textContent = `Was $${item.was_price.toFixed(2)}`;
        wasElem.classList.remove('hidden');
    } else {
        wasElem.classList.add('hidden');
    }

    const saveBadge = document.getElementById('modalSaveBadge');
    if (item.save_amount > 0) {
        saveBadge.textContent = `Save $${item.save_amount.toFixed(2)}`;
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
        linkSpan.textContent = `前往 ${item.store} 官方商品頁`;
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

function getLocalShoppingData() {
    const items = getLocalShoppingList();
    const grouped = {'Woolworths': [], 'Coles': [], 'ALDI': [], 'Other': []};
    let total_cost = 0;
    let total_saved = 0;
    items.forEach(it => {
        const st = it.store || 'Other';
        if (!grouped[st]) grouped[st] = [];
        grouped[st].push(it);
        total_cost += (it.price || 0) * (it.quantity || 1);
        total_saved += (it.save_amount || 0) * (it.quantity || 1);
    });
    return {
        items,
        grouped,
        total_items: items.length,
        total_cost: Math.round(total_cost * 100) / 100,
        total_saved: Math.round(total_saved * 100) / 100
    };
}

async function loadShoppingList() {
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
        document.getElementById('cartCountBadge').textContent = data.total_items || 0;
        document.getElementById('drawerTotalCost').textContent = `$${data.total_cost.toFixed(2)}`;
        document.getElementById('drawerTotalSaved').textContent = `$${data.total_saved.toFixed(2)}`;

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
                        const fallbackImg = "https://images.unsplash.com/photo-1542838132-92c53300491e?w=300&auto=format&fit=crop&q=60";
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
                                        ${it.save_amount > 0 ? `<span class="px-1 py-0.2 rounded text-[10px] font-black bg-amber-400 text-slate-950">Save $${it.save_amount.toFixed(2)}</span>` : ''}
                                        ${it.was_price > 0 ? `<span class="text-slate-400 line-through text-[10px]">Was $${it.was_price.toFixed(2)}</span>` : ''}
                                    </div>
                                </div>
                            </div>
                            <button onclick="deleteShoppingItem(${it.id})" class="text-slate-400 hover:text-rose-500 p-1.5 transition shrink-0" title="刪除">
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
    const payload = {
        product_id: item.id,
        store: item.store,
        period: item.period || currentPeriod,
        date_range: item.date_range || '',
        title: item.title,
        price: item.price,
        price_display: item.price_display,
        quantity: 1,
        image_url: item.image_url,
        save_amount: item.save_amount
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
        text += `💰 ${t('total_budget')} $${data.total_cost.toFixed(2)} (${t('total_saved')} $${data.total_saved.toFixed(2)})`;

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

