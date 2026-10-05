# -*- coding: utf-8 -*-
"""
Category regression test: every product in tests/category_cases.json must land in its expected
place on the website (department from categories.py + shortcut from static/category-rules.js).

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


def main():
    with open(os.path.join(ROOT, 'tests', 'category_cases.json'), encoding='utf-8') as f:
        cases = json.load(f)
    items = [{'title': c['title'], 'category': classify_product(c['title'])} for c in cases]
    got = display_categories(items)
    bad = [(c['title'], c['expect'], g) for c, g in zip(cases, got) if g != c['expect']]
    print(f"{len(cases) - len(bad)}/{len(cases)} category checks passed")
    for t, want, g in bad:
        print(f"  WRONG: {t[:90]}  -> {g} (should be {want})")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
