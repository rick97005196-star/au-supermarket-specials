"""
Coles regular prices, read on Rick's own computer.

On GitHub's servers Coles shows its bot check after 5 pages, so the cloud never finishes a week of Coles regular
prices. This runs the same reader (scrapers/coles_regular.py --local) on Rick's computer and puts what it read on
GitHub; a finished week's list goes online by itself (the quick-deploy workflow watches regular-coles.json).

    python tools/coles_local.py          the weekly read: any day; does nothing once this week is read
    python tools/coles_local.py --test   can this computer read Coles? 10 pages, nothing saved or sent

Set up once with tools/coles_local_setup.ps1 (Windows), which makes a small separate copy of the repository
(only the files the reader needs) and a daily scheduled task; see tools/COLES_LOCAL.md. A run takes up to about
80 minutes, a few seconds between pages, and stops at Coles' first bot check: it never tries to get past it.
Everything a run does is written to tools/coles_local.log (not on GitHub).
"""
import datetime
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, 'tools', 'coles_local.log')
FILES = ['data/coles_regular_progress.json', 'static/data/regular-coles.json']
LIST = 'static/data/regular-coles.json'


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M} {msg}"
    print(line)
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > 300_000:      # keep the last part only
            with open(LOG, encoding='utf-8', errors='replace') as f:
                keep = f.read()[-150_000:]
            with open(LOG, 'w', encoding='utf-8') as f:
                f.write(keep)
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except OSError:
        pass


def git(*args):
    r = subprocess.run(['git', '-C', ROOT, *args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout + r.stderr).strip()


def reader(*args):
    r = subprocess.run([sys.executable, os.path.join('scrapers', 'coles_regular.py'), *args], cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    for line in (r.stdout + r.stderr).splitlines():
        if line.strip():
            log('  ' + line.replace('::warning::', '').replace('::error::', ''))
    return r.returncode


def safe_clone():
    """Only a clean copy on main may push to main (never someone's work in progress)."""
    code, branch = git('rev-parse', '--abbrev-ref', 'HEAD')
    if code or branch != 'main':
        log(f"This copy is not on main ({branch}) - use the reader's own copy (tools/COLES_LOCAL.md)")
        return False
    code, status = git('status', '--porcelain', '--untracked-files=no')
    other = [ln for ln in status.splitlines() if ln[3:].strip() not in FILES]
    if code or other:
        log("This copy has other changes - use the reader's own copy (tools/COLES_LOCAL.md): " + '; '.join(other[:3]))
        return False
    return True


def send():
    """Commit the reader's two files and push; a file the cloud changed meanwhile is replaced by ours."""
    for f in FILES:
        if os.path.exists(os.path.join(ROOT, f)):
            git('add', '--', f)
    if git('diff', '--staged', '--quiet')[0] == 0:
        log('Nothing new to send')
        return True
    new_list = git('diff', '--staged', '--quiet', '--', LIST)[0] != 0
    msg = 'Coles regular prices (read on Rick\'s computer)' + ('' if new_list else ' [skip ci]')
    code, out = git('commit', '-q', '-m', msg)
    if code:
        log('git commit failed: ' + out[-300:])
        return False
    for attempt in range(3):
        code, out = git('pull', '-q', '--rebase', '-X', 'theirs', 'origin', 'main')
        if code:
            git('rebase', '--abort')
            log('git pull failed: ' + out[-300:])
            continue
        code, out = git('push', '-q', 'origin', 'HEAD:main')
        if code == 0:
            log('Sent to GitHub' + (' - the new list goes online in a few minutes' if new_list else ''))
            return True
        log('git push failed: ' + out[-300:])
    return False


def main(argv):
    if '--test' in argv:
        log('Test: can this computer read Coles?')
        return reader('--test')
    if not safe_clone():
        return 1
    code, out = git('pull', '-q', '--rebase', 'origin', 'main')
    if code:
        log('git pull failed (no internet, or GitHub sign-in needed?): ' + out[-300:])
        return 1
    log('Reading Coles regular prices')
    rc = reader('--local')
    return 0 if send() and rc == 0 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
