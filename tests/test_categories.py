# -*- coding: utf-8 -*-
"""
Category regression test: every product in tests/category_cases.json and tests/tag_cases.json
must land in its expected place on the website (department from categories.py + its ONE tag from
static/category-rules.js), every product gets exactly one tag that belongs to exactly one browse
group, and every quick search (熱門搜尋) shows exactly the right products (tests/search_cases.json).

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
const r = require(process.argv[1]);
const items = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const tags = r.TAG_GROUPS.flatMap(g => g.tags);
process.stdout.write(JSON.stringify({
    tags: items.map(it => r.tagOf(it)),
    all_tags: tags,
    dup_tags: tags.filter((t, i) => tags.indexOf(t) !== i),
    // every department's catch-all tag must be on the menu, or its products could not be browsed
    missing_defaults: Object.values(r.DEPT_DEFAULT_TAG).filter(t => !tags.includes(t)),
}));
"""

# The original shortcut chips. A case that expects a plain department (e.g. "snacks") means
# "this department, and NOT one of these chips" (e.g. a cookie that must not be under 巧克力).
SHORTCUTS = {'sub_icecream', 'sub_chocolate', 'sub_chips', 'sub_coffee', 'sub_quickmeals',
             'sub_noodles', 'sub_soda', 'sub_laundry', 'sub_vitamins'}


def website_tags(items):
    """[{'title','category'}] -> {'tags': [the one tag each product is listed under], ...menu checks}."""
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
    cases = []
    for name in ('category_cases.json', 'tag_cases.json'):
        path = os.path.join(ROOT, 'tests', name)
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                cases += json.load(f)
    items = [{'title': c['title'], 'category': classify_product(c['title'])} for c in cases]
    res = website_tags(items)
    tags = set(res['all_tags'])
    bad = []
    for c, it, tag in zip(cases, items, res['tags']):
        want = c['expect']
        if want in tags:                       # an exact tag (汽水, 餅乾, 肉品…)
            ok = tag == want
        else:                                  # a department, and none of the shortcut chips
            ok = it['category'] == want and tag not in SHORTCUTS
        if not ok:
            bad.append((c['title'], want, f"{tag} / {it['category']}"))
    print(f"{len(cases) - len(bad)}/{len(cases)} category checks passed")
    for t, want, g in bad:
        print(f"  WRONG: {t[:90]}  -> {g} (should be {want})")
    menu = res['dup_tags'] + res['missing_defaults']
    for t in res['dup_tags']:
        print(f"  WRONG: tag {t} is in two menu groups")
    for t in res['missing_defaults']:
        print(f"  WRONG: tag {t} is not on the menu")
    bad_search = search_check()
    return 1 if (bad or bad_search or menu) else 0


if __name__ == '__main__':
    sys.exit(main())
