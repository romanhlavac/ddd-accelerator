#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$RepositoryRoot,

    [Parameter(Mandatory)]
    [ValidatePattern('^[0-9a-f]{40}$')]
    [string]$ExpectedSha,

    [Parameter(Mandatory)]
    [string]$Branch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path -LiteralPath $RepositoryRoot).Path
Set-Location $root

$actualBranch = (git branch --show-current).Trim()
$actualSha = (git rev-parse HEAD).Trim()
$remoteSha = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()

if ($actualBranch -ne $Branch) {
    throw "Unexpected branch '$actualBranch'; expected '$Branch'."
}
if ($actualSha -ne $ExpectedSha) {
    throw "Unexpected HEAD '$actualSha'; expected '$ExpectedSha'."
}
if ($remoteSha -ne $ExpectedSha) {
    throw "Remote branch changed to '$remoteSha'; expected '$ExpectedSha'."
}
if (-not [string]::IsNullOrWhiteSpace((git status --porcelain | Out-String))) {
    throw 'Repository is not clean before remediation.'
}

$workflowPath = Join-Path $root '.github\workflows\platform-ci.yml'
$text = [IO.File]::ReadAllText($workflowPath, [Text.UTF8Encoding]::new($false))

$old = @'
          .\scripts\platform\Invoke-DDDAMiroAcceptanceEvidence.ps1 `
            -PlatformPath $PWD.Path `
            -Suite project-steering `
            -Full `
            -KeepReviewBoard `
            -MiroTeamId $env:MIRO_TEAM_ID `
            -NonInteractive
'@

$new = @'
          $packageRoot = Join-Path $env:RUNNER_TEMP 'online-miro-package'
          if (Test-Path -LiteralPath $packageRoot) {
            Remove-Item -LiteralPath $packageRoot -Recurse -Force
          }
          Expand-Archive -LiteralPath $candidate[0].FullName -DestinationPath $packageRoot -Force

          $manifestPath = Join-Path $packageRoot 'ddda-package.json'
          if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
            throw "Expanded candidate package is missing ddda-package.json: $manifestPath"
          }
          $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
          if ([string]$manifest.source_commit -ne $env:SOURCE_SHA -or [string]$manifest.kind -ne 'candidate') {
            throw "Expanded candidate package provenance does not match exact SHA '$env:SOURCE_SHA'."
          }

          & (Join-Path $packageRoot 'scripts\platform\Invoke-DDDAMiroAcceptanceEvidence.ps1') `
            -PlatformPath $packageRoot `
            -Suite project-steering `
            -Full `
            -KeepReviewBoard `
            -MiroTeamId $env:MIRO_TEAM_ID `
            -NonInteractive
'@

$count = ([regex]::Matches($text, [regex]::Escape($old))).Count
if ($count -ne 1) {
    throw "Expected exactly one source-root online acceptance block, found $count."
}

$updated = $text.Replace($old, $new)
if ($updated -notmatch [regex]::Escape("Join-Path `$packageRoot 'scripts\platform\Invoke-DDDAMiroAcceptanceEvidence.ps1'")) {
    throw 'Package-root acceptance invocation was not created.'
}
if ($updated -notmatch "-PlatformPath \$packageRoot") {
    throw 'Package-root PlatformPath binding was not created.'
}
if ($updated -match "Invoke-DDDAMiroAcceptanceEvidence\.ps1 `\r?\n\s+-PlatformPath \$PWD\.Path") {
    throw 'Source-root acceptance invocation remains present.'
}

[IO.File]::WriteAllText($workflowPath, $updated, [Text.UTF8Encoding]::new($false))

# The bootstrap payload is one-shot and must not remain in the product branch.
Remove-Item -LiteralPath $PSCommandPath -Force

$changes = @(git status --porcelain)
$expectedChange = ' M .github/workflows/platform-ci.yml'
$expectedDelete = 'D  scripts/remediation/Invoke-DDDAPR8Rem004MiroResilience.ps1'

# Stage first so deletion status is deterministic.
git add -- '.github/workflows/platform-ci.yml' 'scripts/remediation/Invoke-DDDAPR8Rem004MiroResilience.ps1'
$staged = @(git diff --cached --name-status)
if ($staged.Count -ne 2) {
    throw "Unexpected staged file count: $($staged.Count)."
}
$stagedNames = @($staged | ForEach-Object { ($_ -split "`t")[-1] })
$expectedNames = @('.github/workflows/platform-ci.yml', 'scripts/remediation/Invoke-DDDAPR8Rem004MiroResilience.ps1')
if (@($stagedNames | Where-Object { $_ -notin $expectedNames }).Count -ne 0) {
    throw "Unexpected staged paths: $($staged -join ', ')."
}

# Fast contract checks before the full exact-SHA CI starts after push.
$workflowCheck = [IO.File]::ReadAllText($workflowPath, [Text.UTF8Encoding]::new($false))
foreach ($marker in @(
    "Expand-Archive -LiteralPath `$candidate[0].FullName -DestinationPath `$packageRoot -Force",
    "`$manifestPath = Join-Path `$packageRoot 'ddda-package.json'",
    "-PlatformPath `$packageRoot"
)) {
    if (-not $workflowCheck.Contains($marker)) {
        throw "Workflow contract marker missing: $marker"
    }
}

& (Join-Path $root 'ddda.ps1') test -Suite lint -NonInteractive
if ($LASTEXITCODE -ne 0) {
    throw "Lint suite failed with exit code $LASTEXITCODE."
}

$commitMessage = 'ci: run online Miro acceptance from expanded candidate package'
git commit -m $commitMessage
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to create remediation commit.'
}

$newSha = (git rev-parse HEAD).Trim()
$parentSha = (git rev-parse HEAD^).Trim()
if ($parentSha -ne $ExpectedSha) {
    throw "Remediation commit parent '$parentSha' does not match authorized SHA '$ExpectedSha'."
}

$committedPaths = @(git diff-tree --no-commit-id --name-only -r HEAD)
if ($committedPaths.Count -ne 2 -or @($committedPaths | Where-Object { $_ -notin $expectedNames }).Count -ne 0) {
    throw "Unexpected committed paths: $($committedPaths -join ', ')."
}

$remoteBeforePush = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()
if ($remoteBeforePush -ne $ExpectedSha) {
    throw "Remote branch changed before push: '$remoteBeforePush'."
}

git push origin "HEAD:refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to push remediation commit.'
}

$remoteAfterPush = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()
if ($remoteAfterPush -ne $newSha) {
    throw "Remote branch '$remoteAfterPush' does not match remediation SHA '$newSha'."
}
if (-not [string]::IsNullOrWhiteSpace((git status --porcelain | Out-String))) {
    throw 'Repository is not clean after remediation.'
}

Write-Host "REM-PR8-HVA-CC-004 workflow repair pushed: $newSha"
