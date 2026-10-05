# -*- coding: utf-8 -*-
"""
Apply human-reviewed translation fixes to static/data/translations.json.

    python scripts/apply_reviewed_translations.py fixes1.jsonl [fixes2.jsonl ...]

Each line: {"title": "<exact English title>", "zh": "...", "ja": "...", "ko": "...", "why": "..."}
(only the languages that changed). A fix is accepted only when it does not add a new automatic
quality problem (missing numbers, wrong script, Simplified characters...). Accepted entries are
marked "reviewed": true, so the weekly automatic translation never overwrites them.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scripts.translation_check import problems  # noqa: E402
from scripts.auto_translate import polish_zh  # noqa: E402

TR_FILE = os.path.join(ROOT, 'static', 'data', 'translations.json')


def main(paths):
    with open(TR_FILE, encoding='utf-8') as f:
        tr = json.load(f)
    applied, rejected, unknown = 0, [], []
    for path in paths:
        with open(path, encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                fix = json.loads(line)
                t = fix.get('title', '')
                if t not in tr:
                    unknown.append(t)
                    continue
                old = dict(tr[t])
                new = dict(old)
                for lang in ('zh', 'ja', 'ko'):
                    v = (fix.get(lang) or '').strip()
                    if v:
                        new[lang] = polish_zh(v) if lang == 'zh' else v
                before = set(problems(t, old, style=True))
                after = set(problems(t, new, style=True))
                added = after - before
                if added:
                    rejected.append((t, sorted(added)))
                    continue
                new['reviewed'] = True
                new['src'] = 'reviewed'
                tr[t] = new
                applied += 1
    with open(TR_FILE, 'w', encoding='utf-8') as f:
        json.dump(tr, f, ensure_ascii=False, indent=2)
    print(f'applied {applied}, rejected {len(rejected)}, unknown titles {len(unknown)}')
    for t, p in rejected:
        print(f'  REJECTED {t[:70]}: {"; ".join(p)}')
    for t in unknown[:10]:
        print(f'  UNKNOWN {t[:70]}')


if __name__ == '__main__':
    main(sys.argv[1:])
