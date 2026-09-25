param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$BaseSha = '2a3d52a8239bcc788b6f0aef35a6b57a6f01fb7f'
$TargetPath = 'config/governance/github-bootstrap.json'
$SelfPath = 'scripts/remediation/Fix-DDDA-0.1.1-Closeout-BootstrapFormatting.ps1'

Set-Location -LiteralPath $RepositoryRoot
$actualHead = (git rev-parse HEAD).Trim()
$authorizedHead = [string]$env:AUTHORIZED_HEAD_SHA
if ([string]::IsNullOrWhiteSpace($authorizedHead) -or $actualHead -ne $authorizedHead) {
    throw "Bootstrap-format correction exact-SHA mismatch. Authorized='$authorizedHead', actual='$actualHead'."
}
if ((git status --porcelain)) { throw 'Bootstrap-format correction requires a clean working tree.' }

git cat-file -e "$BaseSha^{commit}"
if ($LASTEXITCODE -ne 0) { throw "Base commit $BaseSha is unavailable." }

$python = @'
from pathlib import Path
import re
import subprocess

BASE_SHA = "2a3d52a8239bcc788b6f0aef35a6b57a6f01fb7f"
TARGET = "config/governance/github-bootstrap.json"
raw = subprocess.check_output(["git", "show", f"{BASE_SHA}:{TARGET}"])
text = raw.decode("utf-8")
pattern = re.compile(r'("title"\s*:\s*"DDDA 0\.1\.1"\s*,\s*"state"\s*:\s*)"open"', re.MULTILINE)
matches = list(pattern.finditer(text))
if len(matches) != 1:
    raise RuntimeError(f"Expected exactly one DDDA 0.1.1 milestone state in base bootstrap, found {len(matches)}")
corrected = pattern.sub(r'\1"closed"', text, count=1)
Path(TARGET).write_bytes(corrected.encode("utf-8"))
if Path(TARGET).read_bytes() != corrected.encode("utf-8"):
    raise RuntimeError("Bootstrap-format correction write/read-back mismatch")
'@
$tempPy = Join-Path $env:RUNNER_TEMP 'ddda-011-minimize-bootstrap.py'
Set-Content -LiteralPath $tempPy -Value $python -Encoding UTF8
python $tempPy
if ($LASTEXITCODE -ne 0) { throw "Bootstrap-format correction failed: $LASTEXITCODE" }

$changed = @(git diff --name-only)
if (($changed.Count -ne 1) -or ($changed[0] -ne $TargetPath)) {
    throw "Unexpected bootstrap-format diff: $($changed -join ', ')"
}
$stat = (git diff --numstat -- $TargetPath | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Failed to inspect bootstrap-format diff.' }
if ($stat -notmatch '^1\s+1\s+config/governance/github-bootstrap\.json$') {
    throw "Bootstrap-format correction must be exactly one-line state replacement; numstat='$stat'."
}
$diff = (git diff -- $TargetPath | Out-String)
if (($diff -notmatch '^-\s+"state": "open",') -or ($diff -notmatch '^\+\s+"state": "closed",')) {
    throw "Bootstrap-format diff does not contain the expected state-only replacement.`n$diff"
}
if (($diff -match 'DDDA 0\.1\.2') -or ($diff -match 'DDDA 0\.2\.0')) {
    throw 'Bootstrap-format correction unexpectedly touched a future milestone.'
}

git rm -- $SelfPath
if ($LASTEXITCODE -ne 0) { throw 'Failed to self-remove bootstrap-format correction.' }
git add -- $TargetPath
if ($LASTEXITCODE -ne 0) { throw 'Failed to stage bootstrap-format correction.' }
git diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Bootstrap-format correction failed git diff --check.' }

git commit -m 'fix(release): minimize 0.1.1 bootstrap closeout diff'
if ($LASTEXITCODE -ne 0) { throw 'Failed to commit bootstrap-format correction.' }
if ((git status --porcelain)) { throw 'Bootstrap-format correction did not leave a clean working tree.' }
if (-not $NoPush) { throw 'This correction must run through the DDDA remote broker with -NoPush.' }
