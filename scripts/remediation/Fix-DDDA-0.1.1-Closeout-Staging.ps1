param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$TargetPath = 'scripts/remediation/Remediate-DDDA-0.1.1-Closeout.ps1'
$SelfPath = 'scripts/remediation/Fix-DDDA-0.1.1-Closeout-Staging.ps1'

Set-Location -LiteralPath $RepositoryRoot
$actualHead = (git rev-parse HEAD).Trim()
$authorizedHead = [string]$env:AUTHORIZED_HEAD_SHA
if ([string]::IsNullOrWhiteSpace($authorizedHead) -or $actualHead -ne $authorizedHead) {
    throw "Staging correction exact-SHA mismatch. Authorized='$authorizedHead', actual='$actualHead'."
}
if ((git status --porcelain)) { throw 'Staging correction requires a clean working tree.' }

$target = Join-Path $RepositoryRoot $TargetPath
$text = Get-Content -LiteralPath $target -Raw -Encoding UTF8
$old = @'
collector = exactly_once(
    collector,
    "POLICY_ACTIVE_MILESTONE_RE",
    "POLICY_MARKED_MILESTONE_RE",
    collector_path,
)
'@
$new = @'
collector = collector.replace(
    "POLICY_ACTIVE_MILESTONE_RE",
    "POLICY_MARKED_MILESTONE_RE",
)
'@
$count = ([regex]::Matches($text, [regex]::Escape($old))).Count
if ($count -ne 1) { throw "Expected one staging block to correct, found $count." }
$text = $text.Replace($old, $new)
Set-Content -LiteralPath $target -Value $text -Encoding UTF8 -NoNewline

$changed = @(git diff --name-only)
if (($changed.Count -ne 1) -or ($changed[0] -ne $TargetPath)) {
    throw "Unexpected staging-correction diff: $($changed -join ', ')"
}

git rm -- $SelfPath
if ($LASTEXITCODE -ne 0) { throw 'Failed to self-remove staging correction script.' }
git add -- $TargetPath
if ($LASTEXITCODE -ne 0) { throw 'Failed to stage corrected closeout remediation.' }
git diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Corrected closeout staging diff failed git diff --check.' }

git commit -m 'fix(release): correct 0.1.1 closeout staging transform'
if ($LASTEXITCODE -ne 0) { throw 'Failed to commit corrected closeout staging transform.' }
if ((git status --porcelain)) { throw 'Staging correction did not leave a clean working tree.' }
if (-not $NoPush) { throw 'This staging correction must run through the DDDA remote broker with -NoPush.' }
