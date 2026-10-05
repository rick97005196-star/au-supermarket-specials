# -*- coding: utf-8 -*-
"""
Category regression test: every product in tests/category_cases.json must land in its expected
place on the website (department from categories.py + shortcut from static/category-rules.js),
and every quick search (熱門搜尋) shows exactly the right products (tests/search_cases.json).

    python tests/test_categories.py          -> exit code 1 and a list of problems if anything moved

The cases are real products that were once in the wrong place (found in the full review of
~6,000 products in Oct 2026 or reported by the site owner), so a rule change can never bring
those mistakes back.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from categories import classify_product  # noqa: E402

JS = r"""
const { subCategoryOf } = require(process.argv[1]);
const items = JSON.parse(require('fs').readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(items.map(it => subCategoryOf(it) || it.category)));
"""


def display_categories(items):
    """[{'title','category'}] -> what the website shows (shortcut key or department)."""
    res = subprocess.run(['node', '-e', JS, os.path.join(ROOT, 'static', 'category-rules.js')],
                         input=json.dumps(items), capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


JS_SEARCH = r"""
const r = require(process.argv[1]);
const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(cases.map(c => {
    const k = r.quickSearchKey(c.q);
    return k ? r.quickSearchMatch({ title: c.title, category: c.category }, k) : null;
})));
"""


def search_check():
    """Quick searches (熱門搜尋): every word must be a strict quick search, and known products must
    be in / out of its results (tests/search_cases.json)."""
    with open(os.path.join(ROOT, 'tests', 'search_cases.json'), encoding='utf-8') as f:
        cases = json.load(f)
    for c in cases:
        c['category'] = classify_product(c['title'])
    res = subprocess.run(['node', '-e', JS_SEARCH, os.path.join(ROOT, 'static', 'category-rules.js')],
                         input=json.dumps(cases), capture_output=True, text=True, check=True)
    got = json.loads(res.stdout)
    bad = [(c, g) for c, g in zip(cases, got) if g is None or g != c['expect']]
    print(f"{len(cases) - len(bad)}/{len(cases)} quick-search checks passed")
    for c, g in bad:
        what = 'is not a quick search word' if g is None else ('should NOT be shown' if g else 'should be shown')
        print(f"  WRONG: search 「{c['q']}」 / {c['title'][:70]}  -> {what}")
    return len(bad)


def main():
    with open(os.path.join(ROOT, 'tests', 'category_cases.json'), encoding='utf-8') as f:
        cases = json.load(f)
    items = [{'title': c['title'], 'category': classify_product(c['title'])} for c in cases]
    got = display_categories(items)
    bad = [(c['title'], c['expect'], g) for c, g in zip(cases, got) if g != c['expect']]
    print(f"{len(cases) - len(bad)}/{len(cases)} category checks passed")
    for t, want, g in bad:
        print(f"  WRONG: {t[:90]}  -> {g} (should be {want})")
    bad_search = search_check()
    return 1 if (bad or bad_search) else 0


if __name__ == '__main__':
    sys.exit(main())
