# -*- coding: utf-8 -*-
"""
Safety checks for the automatic update (run by GitHub Actions).

  python scripts/check_data.py pre     -> before saving/deploying the new data
  python scripts/check_data.py post    -> after deploying: is the live site really updated?

pre  writes these outputs for the workflow:
  changed=true|false   the specials really changed (otherwise: no commit, no deploy)
  block=true|false     the new data looks broken -> keep the site as it is
  alert=<text>         something needs the owner's attention (the run is marked failed -> email)
"""
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'static', 'data')
LIVE = 'https://au-supermarket-specials.pages.dev'
STORES = ('Woolworths', 'Coles', 'ALDI')


def out(key, value):
    path = os.environ.get('GITHUB_OUTPUT')
    line = f"{key}={value}"
    if path:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(line.replace('\n', ' ') + '\n')
    print(f"[output] {line}")


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def previous(rel):
    """The version that is currently live (last commit), or None."""
    try:
        raw = subprocess.run(['git', 'show', f'HEAD:{rel}'], cwd=ROOT, capture_output=True, check=True).stdout
        return json.loads(raw.decode('utf-8'))
    except Exception:
        return None


def counts(items):
    c = {}
    for it in items or []:
        if it.get('store') != 'ALDI' and not (it.get('save_amount') or 0) > 0:
            continue
        key = (it.get('store'), it.get('period'))
        c[key] = c.get(key, 0) + 1
    return c


def ranges(items):
    r = {}
    for it in items or []:
        r.setdefault((it.get('store'), it.get('period')), it.get('date_range') or '')
    return r


def fingerprint(items, stats, translations):
    """Content hash that ignores values which change on every run (ids, timestamps)."""
    rows = sorted(
        json.dumps({k: v for k, v in it.items() if k not in ('id',)}, ensure_ascii=False, sort_keys=True)
        for it in items or []
    )
    st = {k: v for k, v in (stats or {}).items() if k not in ('last_updated', 'data_updated_at')}
    h = hashlib.sha256()
    h.update('\n'.join(rows).encode('utf-8'))
    h.update(json.dumps(st, ensure_ascii=False, sort_keys=True).encode('utf-8'))
    h.update(json.dumps(translations or {}, ensure_ascii=False, sort_keys=True).encode('utf-8'))
    return h.hexdigest()


def range_end(date_range):
    m = re.findall(r'(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s*(\d{4})?', date_range or '')
    if len(m) >= 2:
        d, mon, yr = m[1]
        try:
            return dt.datetime.strptime(f"{d} {mon} {yr or dt.date.today().year}", "%d %b %Y").date()
        except ValueError:
            return None
    m = re.findall(r'(\d{1,2})/(\d{1,2})', date_range or '')  # ALDI "(09/23 - 09/29)"
    if len(m) >= 2:
        mo, d = int(m[1][0]), int(m[1][1])
        today = dt.date.today()
        try:
            end = dt.date(today.year, mo, d)
            return end if (end - today).days < 200 else dt.date(today.year - 1, mo, d)
        except ValueError:
            return None
    return None


def today_au():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo('Australia/Sydney')).date()
    except Exception:
        return (dt.datetime.utcnow() + dt.timedelta(hours=10)).date()


GUESS_ALERT = 25        # more guessed products than this in one week -> email the owner
TRANSLATION_ALERT = 30  # more products with translation problems than this -> email the owner


def pre():
    items = load(os.path.join(DATA, 'specials.json'))
    stats = load(os.path.join(DATA, 'stats.json'))
    trans = load(os.path.join(DATA, 'translations.json'))
    prev_items = previous('static/data/specials.json')
    prev_stats = previous('static/data/stats.json')
    prev_trans = previous('static/data/translations.json')

    now_c, prev_c = counts(items), counts(prev_items)
    now_r, prev_r = ranges(items), ranges(prev_items)
    problems, block = [], False

    # Layer 2: never publish data that looks broken
    for store in STORES:
        key = (store, 'current')
        n, p = now_c.get(key, 0), prev_c.get(key, 0)
        if p >= 20 and n == 0:
            block = True
            problems.append(f"{store} 本週特價變成 0 件（原本 {p} 件），已停止上線，網站維持原本資料")
        elif store == 'ALDI' and prev_items and not any(x.get('sf') for x in prev_items if x.get('store') == 'ALDI'):
            pass   # one-time switch to ALDI's own sale dates (older Special Buys no longer listed by ALDI drop out)
        elif p >= 20 and now_r.get(key) == prev_r.get(key) and n < p * 0.5:
            block = True
            problems.append(f"{store} 本週特價從 {p} 件驟減到 {n} 件（同一檔期），已停止上線")

    # Layer 3: data that is getting old = the scraper is probably broken
    today = today_au()
    for store in STORES:
        rng = now_r.get((store, 'current'))
        end = range_end(rng)
        if end and (today - end).days >= 2:   # a day of grace for the Wednesday switch-over
            problems.append(f"{store} 本週特價的檔期已過期（{rng}），可能是超市網站改版導致抓不到新資料")
    # Coles website half-price list: after the Wednesday reset it should be refilled by noon.
    # Fewer than 800 Coles specials outside that window = the website list is not coming back
    # (blocked, or the updates are not running) -> email the owner. Never blocks the update.
    try:
        from zoneinfo import ZoneInfo
        bne = dt.datetime.now(ZoneInfo('Australia/Brisbane'))
    except Exception:
        bne = dt.datetime.utcnow() + dt.timedelta(hours=10)
    refill_window = (bne.weekday() == 2 and bne.hour < 12) or (bne.weekday() == 1 and bne.hour >= 23)
    coles_now = now_c.get(('Coles', 'current'), 0)
    if not refill_window and 0 < coles_now < 800:
        problems.append(f"Coles 本週只有 {coles_now} 件（正常約 1,300 件），Coles 官網半價清單可能被擋或沒有更新")

    if not any(now_c.get((s, 'current')) for s in STORES):
        block = True
        problems.append("三家超市都沒有本週特價資料")

    # Category health. Products no rule recognises are placed by the AI's answer or the supermarket's
    # own aisle (written by export_static_data.py to data/category_report.json). Only products that
    # had to be GUESSED (no rule, no AI answer, no aisle) can be misplaced: many of them email the owner.
    # Never blocks the update.
    try:
        rep = load(os.path.join(ROOT, 'data', 'category_report.json'))
        if isinstance(rep, dict):
            # both weeks are on the site (this week and the next-week preview)
            n_ai, n_aisle = len(rep.get('ai') or []), len(rep.get('aisle') or [])
            guessed = rep.get('guessed') or []
            msg = f"規則認不出的商品（本週＋下週）：AI 判斷 {n_ai} 件、依超市分區 {n_aisle} 件、只能用猜的 {len(guessed)} 件"
            if guessed:
                msg += '，例如：' + '；'.join(f"{r['title'][:35]}→{r['category']}" for r in guessed[:8])
            print(f"::notice::{msg}")
            if len(guessed) > GUESS_ALERT:
                problems.append(f"{len(guessed)} 件新商品的分類只能用猜的（AI 和超市分區都無法判斷），可能放錯分類；"
                                f"通常是 AI 暫時無法使用，下次更新會自動重試")
    except Exception as e:
        print(f"[WARN] category check skipped: {e}")

    # Translation health: every product on the site should have a clean zh / ja / ko name. A few
    # leftovers are normal (the AI retries each one twice); many at once means translating broke.
    try:
        sys.path.insert(0, os.path.join(ROOT, 'scripts'))
        from translation_check import problems as tr_problems
        cur_items = [it for it in items if it.get('period') == 'current']
        bad_tr = [it['title'] for it in cur_items if tr_problems(it.get('title') or '', it.get('translations'))]
        print(f"::notice::翻譯檢查：本週 {len(cur_items)} 件中 {len(bad_tr)} 件有問題"
              + ('，例如：' + '；'.join(t[:35] for t in bad_tr[:5]) if bad_tr else ''))
        if len(bad_tr) > TRANSLATION_ALERT:
            problems.append(f"{len(bad_tr)} 件商品的翻譯有問題或沒有翻譯（AI 翻譯可能暫時無法使用）")
    except Exception as e:
        print(f"[WARN] translation check skipped: {e}")

    # Quick searches (熱門搜尋): how many products each one shows this week, with a few examples,
    # so an odd result can be spotted on the run page. Never blocks the update.
    try:
        js = ("const r=require(process.argv[1]);const a=JSON.parse(require('fs').readFileSync(0,'utf8'));"
              "const o={};for(const k in r.QUICK_SEARCH){const m=a.filter(i=>r.quickSearchMatch(i,k));"
              "o[k]=[m.length,m.slice(0,3).map(i=>i.title.slice(0,30))]}process.stdout.write(JSON.stringify(o))")
        cur = [{'title': it.get('title') or '', 'category': it.get('category') or ''} for it in items
               if it.get('period') == 'current' and (it.get('store') == 'ALDI' or (it.get('save_amount') or 0) > 0)]
        res = subprocess.run(['node', '-e', js, os.path.join(ROOT, 'static', 'category-rules.js')],
                             input=json.dumps(cur), capture_output=True, text=True, timeout=60, check=True)
        summary = json.loads(res.stdout)
        print("::notice::熱門搜尋本週結果：" + '，'.join(f"{k} {v[0]} 件" for k, v in summary.items()))
        for k, (n, ex) in summary.items():
            print(f"  {k}: {n} -> {' / '.join(ex)}")
    except Exception as e:
        print(f"[WARN] quick-search summary skipped: {e}")

    changed = prev_items is None or fingerprint(items, stats, trans) != fingerprint(prev_items, prev_stats, prev_trans)
    print("本週件數:", {f"{s}/{p}": n for (s, p), n in sorted(now_c.items())})
    out('changed', 'true' if changed and not block else 'false')
    out('block', 'true' if block else 'false')
    out('alert', ' | '.join(problems))
    for p in problems:
        print(f"::warning::{p}")


def post():
    """Layer 4: the live site must now serve exactly what we just deployed."""
    local = load(os.path.join(DATA, 'stats.json'))
    want = (local.get('current', {}).get('total'), local.get('data_updated_at') or local.get('last_updated'))
    got = None
    for attempt in range(8):
        try:
            req = urllib.request.Request(f"{LIVE}/data/stats.json?check={int(time.time())}",
                                         headers={'Cache-Control': 'no-cache', 'User-Agent': 'update-check'})
            with urllib.request.urlopen(req, timeout=20) as r:
                live = json.loads(r.read().decode('utf-8'))
            got = (live.get('current', {}).get('total'), live.get('data_updated_at') or live.get('last_updated'))
            if got == want:
                print(f"網站已更新：本週 {want[0]} 件，更新時間 {want[1]}")
                return 0
        except Exception as e:
            got = str(e)
        time.sleep(15)
    print(f"::error::部署後網站資料不一致：預期 {want}，網站上是 {got}")
    return 1


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'pre'
    sys.exit(post() if mode == 'post' else (pre() or 0))
