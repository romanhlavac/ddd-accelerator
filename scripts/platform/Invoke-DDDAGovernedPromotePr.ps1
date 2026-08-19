[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [Parameter(Mandatory = $true)][ValidateRange(1, 2147483647)][int]$Pr,
    [Parameter(Mandatory = $true)][string]$Version,
    [switch]$ConfirmMerge,
    [switch]$WithMiro,
    [switch]$Full,
    [switch]$CleanupOnFailure,
    [switch]$KeepArtifacts,
    [switch]$KeepReviewBoard,
    [string]$MiroTeamId,
    [switch]$NonInteractive,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAGitHubSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAReleaseGovernanceSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAPromotionResultSupport.ps1")

Assert-DDDAPlatformSemanticVersion -Version $Version
$platformRoot = Get-DDDAPlatformGitRoot -Path $PlatformPath
Assert-DDDAPlatformCleanGit -Repository $platformRoot
$originUrl = Get-DDDAPlatformRepositoryUrl -Repository $platformRoot
$repositorySlug = Get-DDDAPlatformRepositorySlug -RepositoryUrl $originUrl
$githubAuth = Get-DDDAGitHubAuthentication

$prInfo = Get-DDDAGitHubPullRequest -RepositorySlug $repositorySlug -Pr $Pr -Token $githubAuth.Token
if ([string]$prInfo.state -ne "open") {
    throw "PR #$Pr není otevřený."
}
if ([bool]$prInfo.draft) {
    throw "PR #$Pr je draft; Release Scope Gate nelze použít pro promotion."
}
$headSha = [string]$prInfo.head.sha
if ($headSha -notmatch '^[0-9a-f]{40}$') {
    throw "GitHub nevrátil platný PR head SHA."
}

$validation = Get-DDDACandidateValidationEvidence -Pr $Pr -HeadSha $headSha

$comments = @(Get-DDDAHrdrComments -RepositorySlug $repositorySlug -Pr $Pr -Token $githubAuth.Token)
if ($comments.Count -ne 1) {
    throw "Promotion vyžaduje právě jeden authoritativní HRDR comment marker. Nalezeno: $($comments.Count)."
}
$comment = $comments[0]
$commentAuthor = [string]$comment.user.login
$commentAuthorType = [string]$comment.user.type
if (
    [string]::IsNullOrWhiteSpace($commentAuthor) -or
    $commentAuthorType -eq "Bot" -or
    $commentAuthor -match '\[bot\]$'
) {
    throw "Authoritativní HRDR decision musí mít lidskou GitHub provenance."
}
$hrdr = ConvertFrom-DDDAHrdrComment -Comment $comment
if ([string]$hrdr.decision_owner -ne $commentAuthor) {
    throw "HRDR decision owner '$([string]$hrdr.decision_owner)' neodpovídá human comment authorovi '$commentAuthor'."
}

$gateRoot = Join-Path (Get-DDDAPlatformStateRoot) ("release-scope-gates/pr-$Pr-$headSha")
New-Item -ItemType Directory -Path $gateRoot -Force | Out-Null
$hrdrPath = Join-Path $gateRoot "human-release-decision.json"
$gatePath = Join-Path $gateRoot "release-scope-gate.json"
Write-DDDAPlatformJson -Value $hrdr -Path $hrdrPath -Depth 30

if ([string]::IsNullOrWhiteSpace($env:DDDA_GITHUB_PROJECT_TOKEN)) {
    throw "Release Scope Gate vyžaduje DDDA_GITHUB_PROJECT_TOKEN pro autoritativní Project V2 read-back."
}

$python = Get-DDDAPlatformPythonCommand
$collector = Join-Path $platformRoot "scripts/platform/Test-DDDAReleaseScope.py"
if (-not (Test-Path -LiteralPath $collector -PathType Leaf)) {
    throw "Release Scope Gate collector neexistuje: $collector"
}

$previousGhToken = $env:GH_TOKEN
$previousGithubToken = $env:GITHUB_TOKEN
try {
    $env:GH_TOKEN = $githubAuth.Token
    $collectorOutput = Invoke-DDDAPlatformNative -Command $python -Arguments @(
        $collector,
        "--repository", $repositorySlug,
        "--pr", [string]$Pr,
        "--source-sha", $headSha,
        "--candidate-sha256", [string]$validation.PackageSha256,
        "--version", $Version,
        "--hrdr", $hrdrPath,
        "--output", $gatePath
    ) -WorkingDirectory $platformRoot
}
finally {
    $env:GH_TOKEN = $previousGhToken
    $env:GITHUB_TOKEN = $previousGithubToken
}

if (-not (Test-Path -LiteralPath $gatePath -PathType Leaf)) {
    throw "Release Scope Gate nevytvořil evidence report."
}
$gate = Get-Content -LiteralPath $gatePath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([string]$gate.release_scope_gate_status -ne "PASS" -or -not [bool]$gate.side_effects_allowed) {
    $failures = @($gate.failing_invariants | ForEach-Object { [string]$_ })
    throw "Release Scope Gate FAIL:`n$($failures -join "`n")"
}

Write-Host "=== DDDA governed promotion preflight ==="
Write-Host "Repository:          $repositorySlug"
Write-Host "PR:                  $Pr"
Write-Host "Head SHA:            $headSha"
Write-Host "Candidate SHA-256:   $($validation.PackageSha256)"
Write-Host "Version:             $Version"
Write-Host "HRDR decision:       $([string]$hrdr.decision)"
Write-Host "Decision owner:      $([string]$hrdr.decision_owner)"
Write-Host "Release Scope Gate:  PASS"
Write-Host "Gate evidence:       $gatePath"

$arguments = @(
    "-PlatformPath", $platformRoot,
    "-Pr", [string]$Pr,
    "-Version", $Version
)
if ($ConfirmMerge) { $arguments += "-ConfirmMerge" }
if ($WithMiro) { $arguments += "-WithMiro" }
if ($Full) { $arguments += "-Full" }
if ($CleanupOnFailure) { $arguments += "-CleanupOnFailure" }
if ($KeepArtifacts) { $arguments += "-KeepArtifacts" }
if ($KeepReviewBoard) { $arguments += "-KeepReviewBoard" }
if (-not [string]::IsNullOrWhiteSpace($MiroTeamId)) { $arguments += @("-MiroTeamId", $MiroTeamId) }
if ($NonInteractive) { $arguments += "-NonInteractive" }
if ($DryRun) { $arguments += "-DryRun" }

# This is the only call into the legacy release executor. No merge/release/tag
# code is reachable until the read-only Release Scope Gate returned PASS.
$executorPath = Join-Path $PSScriptRoot "Invoke-DDDAPromotePr.ps1"
if (-not $DryRun) {
    Invoke-DDDAPlatformChildPowerShell -ScriptPath $executorPath -Arguments $arguments
    return
}

# Issue #67: promotion dry-run result is operation-local and machine-readable.
# Expected 404 responses for absent tag/GitHub Release are classified as successful
# absence assertions; auth/network/5xx failures remain FAIL without ambient process state.
$resultRoot = Join-Path (Get-DDDAPlatformStateRoot) ("promotion/pr-$Pr-$headSha/$Version")
New-Item -ItemType Directory -Path $resultRoot -Force | Out-Null
$resultPath = Join-Path $resultRoot "dry-run-result.json"
$tag = "v$Version"
$beforeSnapshot = $null
$afterSnapshot = $null
$sideEffectResult = $null
$promotionPreflightStatus = "NOT_RUN"
$sideEffectAssertionsStatus = "NOT_RUN"
$wrapperStatus = "FAIL"
$errorMessage = $null

try {
    $beforeSnapshot = Get-DDDAPromotionDryRunSnapshot -RepositorySlug $repositorySlug -Pr $Pr -Tag $tag -Token $githubAuth.Token
    if ([bool]$beforeSnapshot.pr_merged) {
        throw "Dry-run precondition failed: PR #$Pr is already merged."
    }
    if ([string]$beforeSnapshot.head_sha -ne $headSha) {
        throw "Dry-run precondition failed: PR head changed before executor invocation."
    }
    if ([string]$beforeSnapshot.tag_status -ne "ABSENT") {
        throw "Dry-run precondition failed: canonical tag $tag already exists."
    }
    if ([string]$beforeSnapshot.github_release_status -ne "ABSENT") {
        throw "Dry-run precondition failed: GitHub Release for $tag already exists."
    }

    try {
        Invoke-DDDAPlatformChildPowerShell -ScriptPath $executorPath -Arguments $arguments
        $promotionPreflightStatus = "PASS"
    }
    catch {
        $promotionPreflightStatus = "FAIL"
        throw
    }

    $afterSnapshot = Get-DDDAPromotionDryRunSnapshot -RepositorySlug $repositorySlug -Pr $Pr -Tag $tag -Token $githubAuth.Token
    $sideEffectResult = Test-DDDAPromotionDryRunSideEffects -Before $beforeSnapshot -After $afterSnapshot -ExpectedHeadSha $headSha
    $sideEffectAssertionsStatus = [string]$sideEffectResult.status
    if ($sideEffectAssertionsStatus -ne "PASS") {
        throw "Promotion dry-run side-effect assertions failed: $(@($sideEffectResult.failures) -join ', ')"
    }
    $wrapperStatus = "PASS"
}
catch {
    $errorMessage = $_.Exception.Message
    if ($promotionPreflightStatus -eq "PASS" -and $sideEffectAssertionsStatus -eq "NOT_RUN") {
        $sideEffectAssertionsStatus = "FAIL"
    }
}
finally {
    $result = [ordered]@{
        schema_version = 1
        repository = $repositorySlug
        pr = $Pr
        source_sha = $headSha
        candidate_package_sha256 = [string]$validation.PackageSha256
        version = $Version
        release_scope_gate_status = [string]$gate.release_scope_gate_status
        promotion_preflight_status = $promotionPreflightStatus
        side_effect_assertions_status = $sideEffectAssertionsStatus
        wrapper_status = $wrapperStatus
        assertions = if ($null -eq $sideEffectResult) { $null } else { $sideEffectResult.assertions }
        failing_assertions = if ($null -eq $sideEffectResult) { @() } else { @($sideEffectResult.failures) }
        before = $beforeSnapshot
        after = $afterSnapshot
        error = $errorMessage
        evidence_path = $resultPath
    }
    Write-DDDAPlatformJson -Value $result -Path $resultPath -Depth 30
    Write-Host "Promotion dry-run evidence: $resultPath"
}

if ($wrapperStatus -ne "PASS") {
    throw "Governed promotion dry-run FAIL. Evidence: $resultPath. $errorMessage"
}
Write-Host "DDDA governed promotion dry-run: PASS"
Write-Host "Promotion preflight:       $promotionPreflightStatus"
Write-Host "Side-effect assertions:    $sideEffectAssertionsStatus"
Write-Host "Wrapper status:            $wrapperStatus"
