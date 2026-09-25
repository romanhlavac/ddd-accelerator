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

$baseText = git show "$BaseSha`:$TargetPath"
if ($LASTEXITCODE -ne 0) { throw "Failed to read $TargetPath from base $BaseSha." }
$baseText = ($baseText -join "`n") + "`n"
$old = @'
      "title": "DDDA 0.1.1",
      "state": "open",
'@
$new = @'
      "title": "DDDA 0.1.1",
      "state": "closed",
'@
$count = ([regex]::Matches($baseText, [regex]::Escape($old))).Count
if ($count -ne 1) { throw "Expected exactly one DDDA 0.1.1 milestone state block in base bootstrap, found $count." }
$corrected = $baseText.Replace($old, $new)
Set-Content -LiteralPath (Join-Path $RepositoryRoot $TargetPath) -Value $corrected -Encoding UTF8 -NoNewline

$changed = @(git diff --name-only)
if (($changed.Count -ne 1) -or ($changed[0] -ne $TargetPath)) {
    throw "Unexpected bootstrap-format diff: $($changed -join ', ')"
}
$stat = git diff --numstat -- $TargetPath
if ($LASTEXITCODE -ne 0) { throw 'Failed to inspect bootstrap-format diff.' }
if ($stat -notmatch '^1\s+1\s+') {
    throw "Bootstrap-format correction must be exactly one-line state replacement; numstat='$stat'."
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
