param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$TargetPath = 'scripts/remediation/Remediate-DDDA-0.1.1-Closeout.ps1'
$SelfPath = 'scripts/remediation/Fix-DDDA-0.1.1-Closeout-Pytest.ps1'

Set-Location -LiteralPath $RepositoryRoot
$actualHead = (git rev-parse HEAD).Trim()
$authorizedHead = [string]$env:AUTHORIZED_HEAD_SHA
if ([string]::IsNullOrWhiteSpace($authorizedHead) -or $actualHead -ne $authorizedHead) {
    throw "Pytest bootstrap correction exact-SHA mismatch. Authorized='$authorizedHead', actual='$actualHead'."
}
if ((git status --porcelain)) { throw 'Pytest bootstrap correction requires a clean working tree.' }

$target = Join-Path $RepositoryRoot $TargetPath
$text = Get-Content -LiteralPath $target -Raw -Encoding UTF8
$old = @'
python -m pytest -q `
  runtime/platform/tests/test_merge_release_eligibility_collector.py `
  runtime/platform/tests/test_project_backlog_delivery_governance.py
'@
$new = @'
python -m pip install --disable-pip-version-check --quiet "pytest>=8,<9"
if ($LASTEXITCODE -ne 0) { throw "Failed to provision pytest for focused closeout validation: $LASTEXITCODE" }

python -m pytest -q `
  runtime/platform/tests/test_merge_release_eligibility_collector.py `
  runtime/platform/tests/test_project_backlog_delivery_governance.py
'@
$count = ([regex]::Matches($text, [regex]::Escape($old))).Count
if ($count -ne 1) { throw "Expected one focused pytest block to bootstrap, found $count." }
$text = $text.Replace($old, $new)
Set-Content -LiteralPath $target -Value $text -Encoding UTF8 -NoNewline

$changed = @(git diff --name-only)
if (($changed.Count -ne 1) -or ($changed[0] -ne $TargetPath)) {
    throw "Unexpected pytest-bootstrap diff: $($changed -join ', ')"
}

git rm -- $SelfPath
if ($LASTEXITCODE -ne 0) { throw 'Failed to self-remove pytest bootstrap correction.' }
git add -- $TargetPath
if ($LASTEXITCODE -ne 0) { throw 'Failed to stage pytest-bootstrap correction.' }
git diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Pytest-bootstrap correction failed git diff --check.' }

git commit -m 'fix(release): bootstrap closeout regression runner'
if ($LASTEXITCODE -ne 0) { throw 'Failed to commit pytest-bootstrap correction.' }
if ((git status --porcelain)) { throw 'Pytest-bootstrap correction did not leave a clean working tree.' }
if (-not $NoPush) { throw 'This correction must run through the DDDA remote broker with -NoPush.' }
