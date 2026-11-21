"""Checks for scripts/item_rules.py (逐筆防呆): broken products never reach the site."""
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from item_rules import problems  # noqa: E402
from check_data import range_end  # noqa: E402

OK = {'store': 'Woolworths', 'period': 'current', 'title': 'Arnott\'s Tim Tam 200g', 'price': 2.5,
      'price_display': '$2.50 ea', 'was_price': 5.0, 'save_amount': 2.5, 'discount_desc': '1/2 PRICE',
      'product_url': 'https://www.woolworths.com.au/shop/productdetails/1/x', 'date_range': 'Wed 18 Nov 2026 - Tue 24 Nov 2026'}
TODAY = datetime.date(2026, 11, 21)


def bad(**kw):
    return problems(dict(OK, **kw), TODAY, range_end)


assert problems(OK, TODAY, range_end) == [], problems(OK, TODAY, range_end)
assert bad(price=0)
assert bad(price=1500)
assert bad(was_price=2.0, save_amount=0.5)             # 原價低於特價
assert bad(save_amount=1.0)                              # 省下金額算錯
assert bad(price=3.5, save_amount=1.5)                   # 標半價但不是半價
assert bad(discount_desc='Save $3.00')                   # Save 金額和資料不一致
assert bad(title='Trampoline - Everyday Market')         # 網路限定
assert bad(product_url='https://www.amazon.com.au/x')    # 不是超市官網
assert bad(product_url='')
assert bad(date_range='Wed 4 Nov 2026 - Tue 10 Nov 2026')   # 已過期
assert bad(price_display='2 for $6.00', price=2.5)        # 多件優惠和價格不一致
assert not bad(store='ALDI', price=1299.0, was_price=0, save_amount=0, discount_desc='Special Buys',
               product_url='https://www.aldi.com.au/product/x', date_range='Special Buys (11/18 - 11/24)')
assert not bad(product_url='https://www.salefinder.com.au/1/x', discount_desc='Save $2.50')
assert not bad(was_price=0, save_amount=0, discount_desc='Everyday Low Price')
print('item rules OK')

# Woolworths 目錄裡的 Everyday Market 網路商品（2026-11-21 抽查發現：彈跳床、吧台冰箱、升降桌）
SF = dict(OK, product_url='https://www.salefinder.com.au/68975/food-and-beverage/groceries/home-and-outdoor/x/1/',
          discount_desc='Save $350.00', price=624.0, was_price=974.0, save_amount=350.0)
assert bad(**{k: v for k, v in SF.items() if k != 'title'}, title='VULY Ultra 2 Medium 11ft Trampoline')
assert bad(**{k: v for k, v in SF.items() if k != 'title'}, title='Some Brand Stand Mixer')          # 家居類 $60 以上
assert not bad(**dict(SF, price=12.0, was_price=24.0, save_amount=12.0, discount_desc='1/2 PRICE', title='Sistema Container'))
print('marketplace rules OK')
