"""
Coles regular (not on special) prices, read once a week in parts.

Every week the food categories of coles.com.au are read page by page (48 products a page, the same browse pages
the website shows), and every product sold at its plain shelf price is kept. Output:
    static/data/regular-coles.json   {"updated_at", "store": "Coles", "items": [[<ROW fields>], ...]}
        every regular price; the website loads it only when someone asks for regular prices or searches

    python scrapers/coles_regular.py

Reads only Thursday to Sunday (Brisbane): Monday to Wednesday the specials update reads the Coles website
often, and the two are kept apart. One run reads for at most TIME_BUDGET and keeps its place in
data/coles_regular_progress.json, so the next run goes on where it stopped. The list is written only when every
category is read; until then last week's stays (the website drops lists older than 15 days). When Coles stops
answering or shows its bot check, what was read is kept and the run only warns (exit 0): the bot check is
common and a failure email each time is noise; the daily site report shows how far the week got. Delete the
progress file to read the whole week again. Requests go through scrapers/polite.py: several seconds apart, never around a refusal.

On GitHub's servers Coles shows its bot check after 5 pages, so a week is never finished there. Rick's own computer
can read it instead (tools/coles_local.py, which runs this with --local and puts the result on GitHub):
    python scrapers/coles_regular.py --local   any day, the whole week in one sitting (about 50 minutes)
    python scrapers/coles_regular.py --test    can this computer read Coles? 10 pages, nothing saved
A week begun on Rick's computer is left to it ("by": "local" in the progress file), so the two never write the
same file at once. Either way the reader stops at Coles' first bot check; it never tries to get past it.
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from categories import classify_product  # noqa: E402
from scrapers.coles_web import _get, _product  # noqa: E402
from scrapers.polite import summary  # noqa: E402
from scrapers.regions import _brisbane_today, REGULAR_DESC  # noqa: E402
from scrapers.woolies_regular import ROW, is_fresh, load_json, read_pages, save_json  # noqa: E402

LIST = os.path.join(ROOT, 'static', 'data', 'regular-coles.json')
PROGRESS = os.path.join(ROOT, 'data', 'coles_regular_progress.json')
BROWSE = 'https://www.coles.com.au/browse/{}?page={}'
FOOD = ['meat-seafood', 'fruit-vegetables', 'dairy-eggs-fridge', 'bakery', 'deli', 'pantry',
        'chips-chocolates-snacks', 'international-foods', 'health-dietary', 'drinks', 'frozen']
READ_DAYS = (3, 4, 5, 6)     # Thursday to Sunday
TIME_BUDGET = 30 * 60        # seconds a run reads; the whole week is about 390 pages, 50 minutes
MIN_ROWS = 5000              # a full week has about 10,000; fewer means the pages changed - keep last week's
LOCAL_BUDGET = 80 * 60       # on Rick's computer: the whole week in one sitting
TEST_PAGES = 10


def to_item(p):
    """One Coles product as a website item, or None unless it is sold at its plain shelf price."""
    base = _product(p)
    if not base:
        return None
    pr = p.get('pricing') or {}
    now, was = float(pr.get('now') or 0), float(pr.get('was') or 0)
    if now <= 0 or was > now + 0.004 or pr.get('promotionType') or pr.get('specialType') or pr.get('offerDescription'):
        return None                                       # on special: the specials lists carry it, with its saving
    return dict(base, price=now, price_display=f'${now:.2f}', was_price=0.0, save_amount=0.0,
                discount_desc=REGULAR_DESC)


def read_page(token, n):
    """Page n of one category as (rows, more pages?), or None when Coles stops answering."""
    data = _get(BROWSE.format(token, n))
    if data is None:
        print(f"::warning::Coles stopped answering at {token} page {n} (bot check?) - the next run goes on from here")
        return None
    results = data.get('results') or []
    rows = []
    for it in filter(None, map(to_item, results)):
        it['category'] = classify_product(it['title'], it.get('store_category') or token, it['product_url'])
        rows.append([it[k] for k in ROW])
    last = math.ceil(int(data.get('noOfResults') or 0) / max(int(data.get('pageSize') or 48), 1))
    return rows, bool(results) and n < last


def try_pages():
    """--test: the first pages of one category, to see whether Coles answers this computer. Saves nothing."""
    ok = 0
    while ok < TEST_PAGES and read_page('pantry', ok + 1) is not None:
        ok += 1
    if ok == TEST_PAGES:
        print(f"Coles answered all {TEST_PAGES} test pages on this computer - the weekly read can run here")
        return 0
    print(f"Coles answered {ok} of {TEST_PAGES} test pages on this computer, then showed its bot check -"
          " a week cannot be read here either")
    return 1


def main(argv=()):
    local = '--local' in argv           # on Rick's computer: any day, the whole week in one sitting
    if '--test' in argv:
        return try_pages()
    today = _brisbane_today()
    if not local and today.weekday() not in READ_DAYS:
        print("Coles regular prices are read Thursday to Sunday - nothing to do today")
        return 0
    prog = load_json(PROGRESS)
    if not is_fresh(prog.get('started'), today):        # a new week (specials change on Wednesday): start over
        prog = {'started': today.isoformat()}
    if prog.get('done'):
        print("This week's Coles regular prices are already read - nothing to do")
        return 0
    if prog.get('by') == 'local' and not local:
        print("This week's Coles regular prices are being read on Rick's computer - nothing to do here")
        return 0

    pages, _ = read_pages(prog, FOOD, read_page, LOCAL_BUDGET if local else TIME_BUDGET)
    if not pages:
        print("::warning::Coles answered no page - nothing changed")
        return 0
    if local:
        prog['by'] = 'local'                            # only once Coles answered: a refused computer takes nothing over
    if not prog['done']:
        save_json(PROGRESS, prog)
        print(f"Read {pages} pages, {len(prog['rows'])} regular prices so far; next run starts at "
              f"{prog['dep']} page {prog['page']} - requests {summary()}")
        return 0

    rows = sorted(prog['rows'], key=lambda row: row[0])
    if len(rows) < MIN_ROWS:
        print(f"::error::Only {len(rows)} regular prices in the whole week (a full week has about 10,000) -"
              " Coles may have changed its pages; last week's list is kept")
        return 1
    save_json(LIST, {'updated_at': today.isoformat(), 'store': 'Coles', 'items': rows})
    save_json(PROGRESS, {'started': prog['started'], 'done': True, **({'by': 'local'} if local else {})})
    print(f"Saved {len(rows)} Coles regular prices - requests {summary()}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
