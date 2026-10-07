# -*- coding: utf-8 -*-
"""
Quality checks for product-name translations (zh = Taiwan Traditional Chinese, ja, ko).

Used by scripts/auto_translate.py on every weekly update: a translation that fails a check is
re-translated with the problem explained to the AI, so mistakes like "Whiting -> 鮭魚" or a
missing pack size never reach the website again.

    python scripts/translation_check.py        -> report on the current data
"""
import json
import os
import re

# ---- Simplified characters must not appear in Taiwan Chinese ----
# A character counts as Simplified when the Simplified->Traditional converter changes it,
# except for characters Taiwan itself also writes this way (唇, 里, 群, 游, 台 ...).
try:
    from opencc import OpenCC
    _S2T = OpenCC('s2t')
except Exception:          # converter not installed: fall back to a short list of common ones
    _S2T = None
VARIANT_OK = set('皂唇郁胜里床群采游托栗台干岩面着松谷只系制余卷斗向注布占咸酸才克并借准舍')
COMMON_SIMPLIFIED = set('黄强麦螨鸡鱼虾猪饼条这为发买卖们个来时对长东车门问间关头声体觉观见样热电话语说请让认计记读写书儿过还进边运远选钱铁银锅饭馆汤饮酱鲜鲑鳕鸭鹅肠脏药剂护肤洁净纸湿装听两处专业产员价质优择饰卫厨厅红绿蓝杂粮枣荞萝苹赠减满额')


def simplified_chars(text):
    out = set()
    for c in text or '':
        if not ('\u4e00' <= c <= '\u9fff') or c in VARIANT_OK:
            continue
        if (_S2T and _S2T.convert(c) != c) or (_S2T is None and c in COMMON_SIMPLIFIED):
            out.add(c)
    return out


MAINLAND_WORDS = {
    '薯片': '洋芋片', '酸奶': '優格', '芝士': '起司', '牛油果': '酪梨', '三文魚': '鮭魚', '士多啤梨': '草莓',
    '方便麵': '泡麵', '土豆': '馬鈴薯', '西紅柿': '番茄', '洗髮水': '洗髮精', '沐浴露': '沐浴乳',
    '護髮素': '潤髮乳', '紙巾': '面紙/紙巾', '質量': '品質', '視頻': '影片', '菠蘿': '鳳梨', '奇異果': None,
}
MAINLAND_WORDS = {k: v for k, v in MAINLAND_WORDS.items() if v}
# (紙巾 is fine in Taiwan too - only flag the clear ones)
MAINLAND_WORDS.pop('紙巾', None)

# ---- Food words: if the English name says X, the Chinese name must say one of these ----
# (english regex, accepted Chinese words, Chinese words that would be WRONG for this food)
FOOD_TERMS = [
    (r'\bsalmon\b', ['鮭']),
    (r'\bwhiting\b', ['鱚', '沙鮻', '白魚', '鱈']),
    (r'\bhoki\b', ['鱈', 'Hoki', '霍氏', '白肉魚']),
    (r'\bbarramundi\b', ['尖吻鱸', '金目鱸', 'Barramundi', '鱸']),
    (r'\btuna\b', ['鮪', '金槍魚']),
    (r'\bprawns?\b', ['蝦']),
    (r'\bsquid\b|\bcalamari\b', ['魷', '花枝', '透抽', '中卷', '小卷']),
    (r'\bchicken\b', ['雞']),
    (r'\bbeef\b', ['牛']),
    (r'\bpork\b', ['豬']),
    (r'\blamb\b', ['羊']),
    (r'\bbacon\b', ['培根']),
    (r'\bham\b', ['火腿']),
    (r'\bsausages?\b', ['香腸', '臘腸', '熱狗', '腸']),
    (r'\bcheese\b', ['起司', '乳酪', '起士', '奶酪']),
    (r'(?<!shea )(?<!cocoa )(?<!peanut )(?<!body )(?<!lip )\bbutter\b(?!\s*(?:chicken|me up|balm))', ['奶油', '牛油', '黃油', '酥']),
    (r'\by[o]?gh?urt\b', ['優格', '優酪', '乳']),
    (r'(?<!soy )(?<!oat )(?<!almond )(?<!dairy )\bmilk\b(?!\s*(?:choc|to water|thistle))', ['奶', '乳']),
    (r'\beggs?\b', ['蛋']),
    (r'\brice\b', ['米', '飯', '河粉', '粿']),                     # rice noodles = 河粉 / 米粉 / 米線
    (r'\bnoodles?\b', ['麵', '粉絲', '米粉', '冬粉', '河粉', '米線', '粿條']),
    (r'\bbread\b', ['麵包', '吐司', '餅']),
    (r'\bcoffee\b', ['咖啡', '拿鐵', '濃縮']),
    # (a make-up shade such as "Chocolate Brown" is a colour, not an ingredient)
    (r'\bchocolate\b(?!\s*(?:brown|shade))|\bchoc\b', ['巧克力', '可可']),
    (r'\bshampoo\b', ['洗髮', '洗潤']),
    (r'\btoothpaste\b', ['牙膏']),
]
# Chinese ingredient words that must be backed by the English name (catches invented ingredients,
# e.g. "Whiting" translated as 鮭魚 / salmon)
REVERSE_TERMS = [
    ('鮭魚', r'salmon|trout'),
    ('鮪魚', r'tuna'),
    ('牛肉', r'beef|steak|wagyu|angus|brisket|mince|porterhouse|rump|scotch fillet|meatball|burger|bolognese|lasagne|pie|massaman|rendang|pho|jerky|stroganoff|kransky|bully'),
    ('豬肉', r'pork|ham|bacon|kransky|salami|chorizo|prosciutto|sausage|dumpling|gyoza|dim sim|bun|char siu|schnitzel|ribs|cocktail|frankfurt|mince|belly|knuckle'),
    ('羊肉', r'lamb|mutton|goat'),
    ('雞肉', r'chicken|poultry'),
    ('蝦', r'prawn|shrimp|seafood|tempura'),
    ('多利魚', r'dory'),
]

KANA = re.compile(r'[぀-ヿ一-鿿]')
HANGUL = re.compile(r'[가-힣]')
CJK = re.compile(r'[一-鿿]')


CN_NUM = {'一': '1', '二': '2', '兩': '2', '雙': '2', '三': '3', '四': '4', '五': '5', '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'}


def _numbers(text):
    """Size / count numbers of a title: '1.25L', '4 x 375mL', 'Pk 12' -> {'1.25', '4', '375', '12'}.
    Percentages, '2 in 1', '24/7' and brand numbers like '-196' are not sizes and are ignored."""
    t = text or ''
    for k, v in CN_NUM.items():
        t = t.replace(k, ' ' + v + ' ')
    t = re.sub(r'\d+(?:\.\d+)?\s*%', ' ', t)
    t = re.split(r'\b(?:excludes?|excluding|不含)\b', t, flags=re.I)[0]
    t = re.sub(r'\d+\s*-?\s*(?:in|合)\s*-?\s*(?:1|one)\b|\ball\s*in\s*(?:1|one)\b', ' ', t, flags=re.I)
    t = re.sub(r'\d+/\d+|(?<![\w.])-\d+|\bB\d+|Q\d+|\bG\d+\b|\b(?:pro|mach|retinol|t-inspire)\s*\d+|(?<![\d.])1\s*each\b|\d+\s*(?:hr|hour|h)\b|\d+\s*小時', ' ', t, flags=re.I)
    t = re.sub(r'\bSPF\s*(\d+)\+?', r' \1 ', t, flags=re.I)
    t = re.sub(r'(?<=\d),(?=\d{3})', '', t)
    nums = set(re.findall(r'\d+(?:\.\d+)?', t))
    # drop numbers that are part of model/percentage/years noise
    return {n for n in nums if not (len(n) == 4 and n.startswith(('19', '20')))}


def problems(title, tr, style=False):
    """List of human-readable problems with one product's translations (empty = fine)."""
    out = []
    if not tr or not isinstance(tr, dict):
        return ['沒有翻譯']
    if re.search(r'\b(?:telstra|optus|vodafone|lebara|dodo|boost|sim)\b', title.lower()):
        return []                        # phone plans / SIM cards keep their English names
    zh, ja, ko = (tr.get('zh') or '').strip(), (tr.get('ja') or '').strip(), (tr.get('ko') or '').strip()
    en = title.lower()
    if not zh or zh == title or not CJK.search(zh):
        out.append('中文沒有翻譯')
    if not ja or ja == title or not KANA.search(ja):
        out.append('日文沒有翻譯')
    if not ko or ko == title or not HANGUL.search(ko):
        out.append('韓文沒有翻譯')
    if zh:
        bad = sorted(simplified_chars(zh))
        if bad:
            out.append('中文含簡體字：' + ''.join(bad))
        for w, good in MAINLAND_WORDS.items():
            if w in zh.replace('酸奶油', ''):
                out.append(f'中文用了大陸/香港用語「{w}」（台灣說「{good}」）')
        for pat, need in FOOD_TERMS:
            m = re.search(pat, en)
            if m and not any(n in zh for n in need):
                out.append(f'中文漏了食材：英文有「{m.group(0)}」')
        zh_meat = zh.replace('火雞', '')          # 火雞肉 (turkey) is not 雞肉 (chicken)
        for zw, back in REVERSE_TERMS:
            if zw in zh_meat and not re.search(back, en):
                out.append(f'中文食材錯誤：寫了「{zw}」，但英文沒有這個食材')
        # the same word repeated again and again (AI glitch, e.g. "Nutella Nutella Nutella …")
        words = re.findall(r'[A-Za-z][A-Za-z\'’]+', zh)
        for w in set(words):
            if words.count(w) >= 3 and title.count(w) < 3:
                out.append(f'中文重複字詞：「{w}」出現 {words.count(w)} 次')
                break
    # sizes and pack counts must survive translation
    if re.search(r'\b(?:telstra|optus|vodafone|lebara|dodo|boost|sim)\b', en):
        return out                      # phone plans / SIM cards keep their English names
    want = {n for n in _numbers(title) if not re.search(rf'(?<![\d.]){re.escape(n)}\s*billion', en)}
    for lang, txt in (('中文', zh), ('日文', ja), ('韓文', ko)):
        if txt and want:
            have = _numbers(txt)
            missing = [n for n in want if n not in have]
            if lang == '日文' and re.search(r'size\s*\d', en):
                missing = [n for n in missing if not re.search(r'size\s*' + re.escape(n) + r'\b', en)]
            if missing:
                out.append(f'{lang}漏了數字/容量：{", ".join(sorted(missing))}')
    if zh and len(zh) > max(60, len(title) * 1.6):
        out.append('中文過長（可能加了多餘的說明）')

    # ---- added after the full human review of ~6,000 translations (Oct 2026) ----
    # each language field must be written in its own script (no Korean inside Japanese etc.)
    if zh and (KANA_ONLY.search(zh) or HANGUL.search(zh)):
        out.append('中文裡混入日文假名或韓文')
    if ja and HANGUL.search(ja):
        out.append('日文裡混入韓文')
    if ko and KANA_ONLY.search(ko):
        out.append('韓文裡混入日文假名')
    # a pack count written twice ("85克 x 12入 12入裝" reads like 144)
    for lang, txt in (('中文', zh), ('日文', ja), ('韓文', ko)):
        m = re.search(r'(?<![\d.])(\d+)\s*(?:入|個入|本入|袋入|개입)(?!\d).{0,12}?(?<![\d.])\1\s*(?:入|個入|本入|袋入|개입)', txt or '')
        if m:
            out.append(f'{lang}重複寫了包裝數量「{m.group(0)}」')
    # the brand (first word of the title, kept in English in zh) should also stay in English in ja / ko.
    # Only a style point: checked for NEW translations (style=True) and when a reviewer's fix is applied,
    # never a reason to re-translate an existing, otherwise correct translation.
    brand = _brand_word(title) if style else ''
    if brand and brand.lower() in zh.lower():
        for lang, txt in (('日文', ja), ('韓文', ko)):
            if txt and brand.lower() not in txt.lower():
                out.append(f'{lang}品牌沒有保留英文「{brand}」')
    return out


KANA_ONLY = re.compile(r'[ぁ-ゟ゠-ヿ]')
GENERIC_FIRST = {'australian', 'aussie', 'fresh', 'new', 'organic', 'frozen', 'free', 'classic', 'premium', 'natural',
                 'mini', 'large', 'small', 'family', 'the', 'tasmanian', 'whole', 'chicken', 'beef', 'pork', 'lamb',
                 'fruit', 'macro', 'woolworths', 'coles', 'aldi', 'grass', 'any', 'select', 'selected', 'assorted'}


def _brand_word(title):
    """First word of a title when it looks like a brand ('Cadbury', "Arnott's", 'OMO'), else ''."""
    m = re.match(r"\s*([A-Z][A-Za-z'’&.-]{2,})", title or '')
    if not m:
        return ''
    w = m.group(1).rstrip('.')
    return '' if w.lower().replace('’', "'") in GENERIC_FIRST else w


def load_current():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, 'static', 'data', 'translations.json'), encoding='utf-8') as f:
        tr = json.load(f)
    with open(os.path.join(root, 'static', 'data', 'specials.json'), encoding='utf-8') as f:
        items = json.load(f)
    return tr, sorted({x['title'] for x in items})


if __name__ == '__main__':
    import collections
    tr, titles = load_current()
    bad = {t: problems(t, tr.get(t)) for t in titles}
    bad = {t: p for t, p in bad.items() if p}
    kinds = collections.Counter(p.split('：')[0].split('「')[0] for ps in bad.values() for p in ps)
    print(f'{len(titles)} products, {len(bad)} with problems')
    for k, n in kinds.most_common():
        print(f'  {n:4d}  {k}')
