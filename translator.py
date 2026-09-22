# Multilingual keyword mapper to English for Australian Supermarket searching
MULTILINGUAL_KEYWORDS = {
    # Chinese (Traditional & Simplified)
    '牛奶': 'milk', '鮮奶': 'milk', '蛋': 'egg', '雞蛋': 'egg',
    '雞肉': 'chicken', '牛肉': 'beef', '豬肉': 'pork', '羊肉': 'lamb', '魚': 'fish', '鮭魚': 'salmon',
    '咖啡': 'coffee', '茶': 'tea', '麵包': 'bread', '吐司': 'bread', '奶油': 'butter', '起司': 'cheese', '乳酪': 'cheese',
    '冰淇淋': 'ice cream', '洋芋片': 'chips', '薯片': 'chips', '巧克力': 'chocolate', '餅乾': 'biscuit',
    '衛生紙': 'toilet paper', '紙巾': 'tissue', '洗衣精': 'laundry', '洗衣粉': 'laundry', '洗碗精': 'dishwash',
    '洗手乳': 'hand wash', '洗髮精': 'shampoo', '沐浴乳': 'body wash', '牙膏': 'toothpaste',
    '麥片': 'oats', '燕麥': 'oats', '優格': 'yogurt', '酸奶': 'yogurt', '可樂': 'coca-cola', '汽水': 'drink',
    '果汁': 'juice', '水': 'water', '礦泉水': 'water', '水果': 'fruit', '蘋果': 'apple', '香蕉': 'banana',
    '蔬菜': 'veg', '番茄': 'tomato', '蕃茄': 'tomato', '馬鈴薯': 'potato', '洋蔥': 'onion', '蒜': 'garlic',
    '義大利麵': 'pasta', '米': 'rice', '油': 'oil', '橄欖油': 'olive oil', '醬油': 'soy sauce', '泡麵': 'noodles',

    # Japanese (日本語)
    '牛乳': 'milk', 'ミルク': 'milk', '卵': 'egg', 'たまご': 'egg',
    '鶏肉': 'chicken', 'チキン': 'chicken', '牛肉': 'beef', '豚肉': 'pork', 'ラム': 'lamb', '魚': 'fish', 'サーモン': 'salmon',
    'コーヒー': 'coffee', 'お茶': 'tea', 'パン': 'bread', '食パン': 'bread', 'バター': 'butter', 'チーズ': 'cheese',
    'アイス': 'ice cream', 'アイスクリーム': 'ice cream', 'ポテチ': 'chips', 'ポテトチップス': 'chips',
    'チョコ': 'chocolate', 'チョコレート': 'chocolate', 'クッキー': 'biscuit', 'ビスケット': 'biscuit',
    'トイレットペーパー': 'toilet paper', 'ティッシュ': 'tissue', '洗剤': 'laundry', 'シャンプー': 'shampoo',
    'ボディソープ': 'body wash', '歯磨き粉': 'toothpaste', 'ヨーグルト': 'yogurt', 'コーラ': 'coca-cola',
    'ジュース': 'juice', '水': 'water', 'リンゴ': 'apple', 'バナナ': 'banana', 'トマト': 'tomato',
    'パスタ': 'pasta', '米': 'rice', 'オリーブオイル': 'olive oil',

    # Korean (한국어)
    '우유': 'milk', '계란': 'egg', '달걀': 'egg',
    '닭고기': 'chicken', '치킨': 'chicken', '소고기': 'beef', '돼지고기': 'pork', '양고기': 'lamb', '생선': 'fish', '연어': 'salmon',
    '커피': 'coffee', '차': 'tea', '빵': 'bread', '식빵': 'bread', '버터': 'butter', '치즈': 'cheese',
    '아이스크림': 'ice cream', '감자칩': 'chips', '과자': 'chips', '초콜릿': 'chocolate', '초코': 'chocolate',
    '비스킷': 'biscuit', '쿠키': 'biscuit', '화장지': 'toilet paper', '휴지': 'tissue', '세제': 'laundry',
    '샴푸': 'shampoo', '바디워시': 'body wash', '치약': 'toothpaste', '요거트': 'yogurt', '콜라': 'coca-cola',
    '주스': 'juice', '물': 'water', '생수': 'water', '사과': 'apple', '바나나': 'banana', '토마토': 'tomato',
    '파스타': 'pasta', '쌀': 'rice', '올리브유': 'olive oil', '라면': 'noodles'
}

def translate_query(q: str) -> str:
    """Translates Chinese, Japanese, or Korean grocery terms to English."""
    res = q.strip().lower()
    for term, en in MULTILINGUAL_KEYWORDS.items():
        if term in res:
            res = res.replace(term, f" {en} ")
    return " ".join(res.split())
