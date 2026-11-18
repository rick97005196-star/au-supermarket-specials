"""
One-time setup on Rick's computer: Coles regular prices read here instead of on GitHub's servers.

Run by tools/coles_local_setup.ps1 (one line in PowerShell, see tools/COLES_LOCAL.md), or directly:
    python coles_local_setup.py

1. makes the reader's own small copy of the repository in %USERPROFILE%\\coles-reader (only the files the reader
   needs, about 5 MB; Rick's other copies are never touched), or brings it up to date
2. installs curl_cffi, the one extra Python package the reader uses
3. tests: can this computer read Coles? (10 pages; nothing saved or sent)
4. only if the test passes: checks GitHub lets this computer send (a browser sign-in may open), adds a daily
   Windows scheduled task (18:00, or as soon as the computer is on after a missed time) and starts the first read
Running it again is safe: it updates the copy and replaces the scheduled task.
"""
import datetime
import os
import subprocess
import sys
from xml.sax.saxutils import escape

REPO = 'https://github.com/rick97005196-star/au-supermarket-specials.git'
TASK = 'Coles regular prices'
SPARSE = ['/categories.py', '/scrapers/', '/tools/', '/data/ai_categories.json',
          '/data/coles_regular_progress.json', '/static/data/regular-coles.json']


def say(msg):
    print(msg, flush=True)


def run(cmd, cwd=None, quiet=False):
    r = subprocess.run(cmd, cwd=cwd, capture_output=quiet, text=True, encoding='utf-8', errors='replace')
    return r.returncode, ((r.stdout or '') + (r.stderr or '')).strip() if quiet else ''


def copy_of_repo(target, repo):
    if os.path.isdir(os.path.join(target, '.git')):
        say('1/4 更新讀取用的資料夾…')
        code, out = run(['git', '-C', target, 'pull', '-q', '--rebase', 'origin', 'main'], quiet=True)
        if code:
            say('    git pull 失敗：' + out[-300:])
            return False
    else:
        say(f'1/4 建立讀取用的資料夾：{target}')
        os.makedirs(os.path.dirname(target), exist_ok=True)
        code, _ = run(['git', 'clone', '-q', '--depth', '1', '--filter=blob:none', '--sparse', '--single-branch',
                       '--branch', 'main', repo, target])
        if code:
            say('    git clone 失敗（網路或 GitHub 登入？）')
            return False
    code, out = run(['git', '-C', target, 'sparse-checkout', 'set', '--no-cone', *SPARSE], quiet=True)
    if code:
        say('    git sparse-checkout 失敗：' + out[-300:])
        return False
    if run(['git', '-C', target, 'config', 'user.email'], quiet=True)[0]:       # no git name yet: one for this copy
        run(['git', '-C', target, 'config', 'user.email', 'rick97005196-star@users.noreply.github.com'])
        run(['git', '-C', target, 'config', 'user.name', "Rick's computer (Coles reader)"])
    return True


def task_xml(pyw, script, workdir):
    start = datetime.date.today().isoformat() + 'T18:00:00'
    user = escape(f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}".lstrip('\\'))
    return f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Reads Coles regular prices for au-supermarket-specials (tools/coles_local.py); log in tools\\coles_local.log</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{start}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{user}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(pyw)}</Command>
      <Arguments>{escape(chr(34) + script + chr(34))}</Arguments>
      <WorkingDirectory>{escape(workdir)}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
'''


def schedule(target):
    script = os.path.join(target, 'tools', 'coles_local.py')
    pyw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')     # no black window while it reads
    if not os.path.exists(pyw):
        pyw = sys.executable
    xml = os.path.join(target, 'tools', 'coles_local_task.xml')
    with open(xml, 'w', encoding='utf-16') as f:
        f.write(task_xml(pyw, script, target))
    code, out = run(['schtasks', '/Create', '/TN', TASK, '/XML', xml, '/F'], quiet=True)
    if code:                                            # simpler form: daily at 18:00 (a missed time is skipped)
        code, out = run(['schtasks', '/Create', '/TN', TASK, '/SC', 'DAILY', '/ST', '18:00', '/F',
                         '/TR', f'"{pyw}" "{script}"'], quiet=True)
    if code:
        say('    排程建立失敗：' + out[-300:])
        return False
    run(['schtasks', '/Run', '/TN', TASK], quiet=True)
    return True


def main(argv):
    repo = argv[argv.index('--repo') + 1] if '--repo' in argv else REPO
    target = argv[argv.index('--dir') + 1] if '--dir' in argv else os.path.join(os.path.expanduser('~'), 'coles-reader',
                                                                                 'au-supermarket-specials')
    if run(['git', '--version'], quiet=True)[0]:
        say('找不到 git：請先安裝 https://git-scm.com/download/win ，再執行一次')
        return 1
    if not copy_of_repo(target, repo):
        return 1

    say('2/4 安裝 curl_cffi…')
    code, out = run([sys.executable, '-m', 'pip', 'install', '--user', '--upgrade', '--quiet', 'curl_cffi'], quiet=True)
    if code:
        say('    安裝失敗：' + out[-300:])
        return 1

    say('3/4 測試：這台電腦能不能讀 Coles（10 頁，約 1 分鐘）…')
    code, _ = run([sys.executable, os.path.join(target, 'tools', 'coles_local.py'), '--test'])
    if code:
        say('\n結果：Coles 也擋這台電腦，所以不建立排程（什麼都沒改）。')
        return 1

    if '--no-schedule' in argv:
        say('4/4 測試通過（--no-schedule：不建立排程）')
        return 0
    say('4/4 確認可以上傳到 GitHub（可能會跳出瀏覽器登入，請登入）…')
    code, out = run(['git', '-C', target, 'push', '--dry-run', '-q', 'origin', 'HEAD:main'], quiet=True)
    if code:
        say('    GitHub 上傳權限確認失敗：' + out[-300:])
        return 1
    if os.name != 'nt':
        say(f'    不是 Windows：請自行用 cron 每天執行一次  "{sys.executable}" "{os.path.join(target, "tools", "coles_local.py")}"')
        return 0
    if not schedule(target):
        return 1
    say('\n完成！每天 18:00（或之後電腦一開）會自動讀 Coles 一般價，讀完一週就會自動上線。')
    say('第一次讀取已經在背景開始（約 1 小時，電腦請保持開機、連網）。')
    say(f'紀錄檔：{os.path.join(target, "tools", "coles_local.log")}')
    return 0


if __name__ == '__main__':
    code = main(sys.argv[1:])
    if os.name == 'nt' and sys.stdin and sys.stdin.isatty():
        input('\n按 Enter 關閉…')
    sys.exit(code)
