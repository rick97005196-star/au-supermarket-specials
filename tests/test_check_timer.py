"""Checks for scripts/check_timer.py (the "Cloudflare timer stopped" alarm, and whether GitHub's
backup schedule may skip an update the timer already started)."""
import datetime
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from check_timer import covered, is_timer_slot, verdict  # noqa: E402

UTC = datetime.timezone.utc


def bne(y, mo, d, h, mi):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=UTC) - datetime.timedelta(hours=10)


def run(created, title='定時更新（Cloudflare 定時器）', event='workflow_dispatch', conclusion='success'):
    return {'created_at': created.strftime('%Y-%m-%dT%H:%M:%SZ'), 'display_title': title, 'event': event,
            'conclusion': conclusion}


CASES = [
    # (description, runs, now, expected state)
    ('never set up: no alarm', [run(bne(2026, 10, 6, 9, 0), title='手動更新')], bne(2026, 10, 6, 12, 0), 'not set up'),
    ('Tuesday, started 40 min ago', [run(bne(2026, 10, 6, 11, 17))], bne(2026, 10, 6, 11, 57), 'ok'),
    ('Tuesday, nothing for 4 hours', [run(bne(2026, 10, 6, 7, 47))], bne(2026, 10, 6, 11, 57), 'stopped'),
    ('Monday 00:05 after the quiet weekend', [run(bne(2026, 10, 4, 22, 17))], bne(2026, 10, 5, 0, 5), 'ok'),
    ('Friday, 11 hours since the last one', [run(bne(2026, 10, 9, 10, 17))], bne(2026, 10, 9, 21, 30), 'ok'),
    ('Saturday, one start skipped (queue busy)', [run(bne(2026, 10, 9, 22, 17))], bne(2026, 10, 10, 23, 0), 'ok'),
    ('Sunday, nothing for 2 days', [run(bne(2026, 10, 9, 22, 17))], bne(2026, 10, 11, 23, 0), 'stopped'),
    ('manual runs do not count as the timer',
     [run(bne(2026, 10, 6, 6, 0)), run(bne(2026, 10, 6, 11, 0), title='手動更新')], bne(2026, 10, 6, 11, 30), 'stopped'),
    ('the newest timer start counts',
     [run(bne(2026, 10, 6, 1, 17)), run(bne(2026, 10, 6, 11, 17))], bne(2026, 10, 6, 11, 30), 'ok'),
]

COVERED_CASES = [
    # (description, runs, now, may the backup skip?)  2026-10-06 = Tuesday, 10-08 = Thursday
    ('Tuesday: the timer started the 11:17 update', [run(bne(2026, 10, 6, 11, 17))], bne(2026, 10, 6, 11, 25), True),
    ('Tuesday: the 11:47 start is missing', [run(bne(2026, 10, 6, 11, 17))], bne(2026, 10, 6, 11, 51), False),
    ('a start one minute early still counts', [run(bne(2026, 10, 6, 11, 16))], bne(2026, 10, 6, 11, 25), True),
    ('Thursday: the timer started the 10:17 update', [run(bne(2026, 10, 8, 10, 17))], bne(2026, 10, 8, 10, 40), True),
    ('Thursday: the 10:17 one was cancelled (replaced in the queue)',
     [run(bne(2026, 10, 8, 10, 17), conclusion='cancelled')], bne(2026, 10, 8, 10, 40), False),
    ('Thursday: the 10:17 one failed', [run(bne(2026, 10, 8, 10, 17), conclusion='failure')], bne(2026, 10, 8, 10, 40), False),
    ('Thursday: the 10:17 one is still waiting', [run(bne(2026, 10, 8, 10, 17), conclusion=None)], bne(2026, 10, 8, 10, 40), True),
    ('Wednesday 00:01 switch-over started', [run(bne(2026, 10, 7, 0, 1))], bne(2026, 10, 7, 0, 5), True),
    ('Wednesday 00:05: only the 23:47 one ran', [run(bne(2026, 10, 6, 23, 47))], bne(2026, 10, 7, 0, 5), False),
    ('the timer never started anything', [], bne(2026, 10, 6, 11, 25), False),
    ('a manual run does not count', [run(bne(2026, 10, 6, 11, 20), title='手動更新')], bne(2026, 10, 6, 11, 25), False),
    ('Sunday 22:17 started', [run(bne(2026, 10, 11, 22, 17))], bne(2026, 10, 11, 22, 30), True),
    ('Monday 00:10: the last planned start was Sunday 22:17', [run(bne(2026, 10, 11, 22, 17))], bne(2026, 10, 12, 0, 10), True),
]

NODE_PLAN = """
import { pathToFileURL } from 'node:url';
const { shouldRun } = await import(pathToFileURL(process.argv[1]).href);
const monday = Date.UTC(2026, 9, 5) - 10 * 3600 * 1000;     // Mon 5 Oct 2026 00:00 Brisbane
const picked = [];
for (let i = 0; i < 7 * 24 * 60; i++) if (shouldRun(monday + i * 60000)) picked.push(i);
console.log(JSON.stringify(picked));
"""


def same_plan_as_cloudflare():
    """Do is_timer_slot() and the Cloudflare timer's shouldRun() pick the same minutes of a week?"""
    node = shutil.which('node')
    if not node:
        return None
    timer = os.path.join(ROOT, 'cloudflare', 'update-timer', 'src', 'timer.js')
    out = subprocess.run([node, '--input-type=module', '-e', NODE_PLAN, timer],
                         capture_output=True, text=True, check=True).stdout
    monday = datetime.datetime(2026, 10, 5)
    ours = [i for i in range(7 * 24 * 60) if is_timer_slot(monday + datetime.timedelta(minutes=i))]
    return ours == json.loads(out)


def main():
    bad = 0
    for desc, runs, now, want in CASES:
        got, msg = verdict(runs, now)
        ok = got == want
        bad += not ok
        print(('ok   ' if ok else 'FAIL ') + f'{desc}: {got} ({msg})')
    for desc, runs, now, want in COVERED_CASES:
        got = covered(runs, now)
        ok = got == want
        bad += not ok
        print(('ok   ' if ok else 'FAIL ') + f'skip? {desc}: {got}')
    same = same_plan_as_cloudflare()
    if same is None:
        print('skip the plan comparison: node not found')
    else:
        bad += not same
        print(('ok   ' if same else 'FAIL ') + 'the same plan as the Cloudflare timer (shouldRun)')
    total = len(CASES) + len(COVERED_CASES) + (same is not None)
    print(f'{total - bad}/{total} timer checks passed')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
