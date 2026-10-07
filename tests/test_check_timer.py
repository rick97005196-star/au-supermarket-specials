"""Checks for scripts/check_timer.py (the "Cloudflare timer stopped" alarm)."""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
from check_timer import verdict  # noqa: E402

UTC = datetime.timezone.utc


def bne(y, mo, d, h, mi):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=UTC) - datetime.timedelta(hours=10)


def run(created, title='定時更新（Cloudflare 定時器）', event='workflow_dispatch'):
    return {'created_at': created.strftime('%Y-%m-%dT%H:%M:%SZ'), 'display_title': title, 'event': event}


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


def main():
    bad = 0
    for desc, runs, now, want in CASES:
        got, msg = verdict(runs, now)
        ok = got == want
        bad += not ok
        print(('ok   ' if ok else 'FAIL ') + f'{desc}: {got} ({msg})')
    print(f'{len(CASES) - bad}/{len(CASES)} timer-alarm checks passed')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
