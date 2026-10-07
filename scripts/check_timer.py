"""
Is the Cloudflare update timer still starting the updates?

Runs at the end of every update that GitHub's own (backup) schedule started. The Cloudflare timer
marks the updates it starts with "Cloudflare" in their title. If the timer has worked before but has
not started anything for too long (for example its GitHub key expired), this check fails, and GitHub
emails the owner. Before the timer has ever run, it only prints a note.

    python scripts/check_timer.py          (needs GH_TOKEN and GITHUB_REPOSITORY, set by GitHub Actions)
"""
import datetime
import json
import os
import sys
import urllib.request

TIMER_MARK = 'Cloudflare'
# longest normal gap between two timer starts, plus room for an update that was already queued
MAX_GAP_BUSY_DAYS = datetime.timedelta(hours=3)     # Mon-Wed: every 30 minutes
MAX_GAP_QUIET_DAYS = datetime.timedelta(hours=25)   # Thu-Sun: twice a day


def latest_timer_start(runs):
    """Newest creation time of an update started by the Cloudflare timer, or None."""
    times = [r['created_at'] for r in runs
             if r.get('event') == 'workflow_dispatch' and TIMER_MARK in (r.get('display_title') or '')]
    if not times:
        return None
    return max(datetime.datetime.fromisoformat(t.replace('Z', '+00:00')) for t in times)


def verdict(runs, now):
    """('ok' | 'not set up' | 'stopped', message)"""
    last = latest_timer_start(runs)
    if last is None:
        return 'not set up', 'Cloudflare 定時器尚未啟用（目前只靠 GitHub 排程）'
    brisbane = now + datetime.timedelta(hours=10)
    limit = MAX_GAP_BUSY_DAYS if brisbane.weekday() in (0, 1, 2) else MAX_GAP_QUIET_DAYS
    gap = now - last
    hours = gap.total_seconds() / 3600
    if gap > limit:
        return 'stopped', (f'Cloudflare 定時器已經 {hours:.1f} 小時沒有啟動更新（金鑰可能過期了），'
                           f'目前只靠不準時的 GitHub 排程。請照說明換一把新的金鑰。')
    return 'ok', f'Cloudflare 定時器正常：上次啟動更新是 {hours:.1f} 小時前'


def fetch_runs():
    repo = os.environ['GITHUB_REPOSITORY']
    req = urllib.request.Request(
        f'https://api.github.com/repos/{repo}/actions/workflows/auto_update.yml/runs'
        f'?event=workflow_dispatch&per_page=50',
        headers={'Authorization': f"Bearer {os.environ['GH_TOKEN']}",
                 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get('workflow_runs') or []


def main():
    try:
        runs = fetch_runs()
    except Exception as e:                         # cannot check: never fail the update because of it
        print(f'::notice::無法檢查 Cloudflare 定時器（{e}）')
        return 0
    state, msg = verdict(runs, datetime.datetime.now(datetime.timezone.utc))
    if state == 'stopped':
        print(f'::error::{msg}')
        return 1
    print(f'::notice::{msg}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
