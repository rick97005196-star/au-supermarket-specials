# One-time setup: Coles regular prices read on this Windows computer (see tools/COLES_LOCAL.md).
# Paste into PowerShell:
#   irm https://raw.githubusercontent.com/rick97005196-star/au-supermarket-specials/main/tools/coles_local_setup.ps1 | iex
# Finds Python, then runs tools/coles_local_setup.py, which does the rest. Safe to run again.
& {
    $url = 'https://raw.githubusercontent.com/rick97005196-star/au-supermarket-specials/main/tools/coles_local_setup.py'
    $cands = @()
    $cands += @(Get-ChildItem "$env:LOCALAPPDATA\Python\pythoncore-3*\python.exe" -ErrorAction SilentlyContinue |
                Sort-Object FullName -Descending | ForEach-Object { $_.FullName })
    $cands += @(Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue |
                Sort-Object FullName -Descending | ForEach-Object { $_.FullName })
    foreach ($name in @('py', 'python', 'python3')) {
        $c = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($c -and $c.Path -and ($c.Path -notmatch 'WindowsApps')) { $cands += $c.Path }   # not the Microsoft Store stand-in
    }
    $py = $null
    foreach ($c in $cands) {
        $exe = & $c -c "import sys; print(sys.executable)" 2>$null
        if (($LASTEXITCODE -eq 0) -and $exe) { $py = ("$exe").Trim(); break }
    }
    if (-not $py) {
        Write-Host 'Python not found. Install it from https://www.python.org/downloads/ and paste the line again.'
        return
    }
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $file = Join-Path $env:TEMP 'coles_local_setup.py'
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $file
    & $py $file
}
