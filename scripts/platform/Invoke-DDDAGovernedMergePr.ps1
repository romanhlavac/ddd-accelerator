[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [Parameter(Mandatory = $true)][ValidateRange(1, 2147483647)][int]$Pr,
    [switch]$ConfirmMerge,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAGitHubSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAReleaseGovernanceSupport.ps1")

$platformRoot = Get-DDDAPlatformGitRoot -Path $PlatformPath
if ($platformRoot -ne [System.IO.Path]::GetFullPath($PlatformPath).TrimEnd('\', '/')) {
    throw "PlatformPath musí být Git root DDDA platformy."
}
Assert-DDDAPlatformCleanGit -Repository $platformRoot

$originUrl = Get-DDDAPlatformRepositoryUrl -Repository $platformRoot
$repositorySlug = Get-DDDAPlatformRepositorySlug -RepositoryUrl $originUrl
$githubAuth = Get-DDDAGitHubAuthentication
$policyPath = Join-Path $platformRoot "config/platform/development-policy.yaml"
if (-not (Test-Path -LiteralPath $policyPath -PathType Leaf)) {
    throw "Chybí platform development policy: $policyPath"
}
$policy = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($policy.schema_version -ne 1) {
    throw "Nepodporovaná platform development policy."
}

$prInfo = Get-DDDAGitHubPullRequest -RepositorySlug $repositorySlug -Pr $Pr -Token $githubAuth.Token
if ([string]$prInfo.state -ne "open") {
    throw "PR #$Pr není otevřený."
}
if ([bool]$prInfo.draft) {
    throw "PR #$Pr je draft. Governed implementation merge vyžaduje Ready for review."
}
$baseRefName = [string]$prInfo.base.ref
if ($baseRefName -ne [string]$policy.base_branch) {
    throw "PR #$Pr míří do '$baseRefName', očekáváno '$($policy.base_branch)'."
}
$mergeStateStatus = ([string]$prInfo.mergeable_state).ToUpperInvariant()
if ($mergeStateStatus -notin @("CLEAN", "HAS_HOOKS", "UNSTABLE")) {
    throw "PR #$Pr není připraven k merge. mergeable_state=$([string]$prInfo.mergeable_state)"
}
$headSha = [string]$prInfo.head.sha
if ($headSha -notmatch '^[0-9a-f]{40}$') {
    throw "GitHub nevrátil platný PR head SHA."
}

try {
    $checkSummary = Assert-DDDAGitHubChecksPassed -RepositorySlug $repositorySlug -Commit $headSha -Token $githubAuth.Token
}
catch {
    throw "CI kontroly PR #$Pr nejsou všechny PASS:`n$($_.Exception.Message)"
}

$minimumApprovals = [int]$policy.minimum_approvals
$approvedUsers = @()
if ($minimumApprovals -gt 0) {
    $approvedUsers = @(Get-DDDAGitHubApprovedUsers -RepositorySlug $repositorySlug -Pr $Pr -Token $githubAuth.Token)
    if ($approvedUsers.Count -lt $minimumApprovals) {
        throw "PR #$Pr nemá požadovaný počet GitHub approvals. Požadováno: $minimumApprovals; nalezeno: $($approvedUsers.Count)."
    }
}

$validation = Get-DDDACandidateValidationEvidence -Pr $Pr -HeadSha $headSha

$reviewComments = @(Get-DDDAHumanPrReviewComments -RepositorySlug $repositorySlug -Pr $Pr -Token $githubAuth.Token)
if ($reviewComments.Count -ne 1) {
    throw "Governed implementation merge vyžaduje právě jeden authoritativní Human Review marker. Nalezeno: $($reviewComments.Count)."
}
$reviewComment = $reviewComments[0]
$commentAuthor = [string]$reviewComment.user.login
$commentAuthorType = [string]$reviewComment.user.type
if (
    [string]::IsNullOrWhiteSpace($commentAuthor) -or
    $commentAuthorType -eq "Bot" -or
    $commentAuthor -match '\[bot\]$'
) {
    throw "Human Review musí mít lidskou GitHub provenance."
}
$review = ConvertFrom-DDDAHumanPrReviewComment -Comment $reviewComment
if ([int]$review.schema_version -ne 1 -or [string]$review.kind -ne "implementation_pr_review") {
    throw "Human Review má nepodporovaný contract."
}
if ([int]$review.pr -ne $Pr) {
    throw "Human Review PR identity neodpovídá PR #$Pr."
}
if ([string]$review.reviewed_sha -ne $headSha) {
    throw "Human Review SHA '$([string]$review.reviewed_sha)' neodpovídá current PR head '$headSha'."
}
if ([string]$review.candidate_package_sha256 -ne [string]$validation.PackageSha256) {
    throw "Human Review candidate package hash neodpovídá exact-SHA validate-pr evidence."
}
if ([string]$review.reviewer -ne $commentAuthor) {
    throw "Human Review reviewer '$([string]$review.reviewer)' neodpovídá human comment authorovi '$commentAuthor'."
}
if ([string]$review.verdict -ne "pass") {
    throw "Human Review není PASS. verdict=$([string]$review.verdict)"
}
if ([string]::IsNullOrWhiteSpace([string]$review.reviewed_at)) {
    throw "Human Review neobsahuje reviewed_at."
}
$reviewedAt = [DateTimeOffset]::MinValue
if (-not [DateTimeOffset]::TryParse([string]$review.reviewed_at, [ref]$reviewedAt)) {
    throw "Human Review reviewed_at není platný timestamp."
}

foreach ($relative in @($policy.required_documents)) {
    $contentsPath = "repos/$repositorySlug/contents/$relative?ref=$headSha"
    try {
        $null = Invoke-DDDAGitHubApi -Method GET -Path $contentsPath -Token $githubAuth.Token
    }
    catch {
        throw "PR #$Pr neobsahuje povinný governance dokument '$relative' na exact SHA $headSha."
    }
}

$mergeMethod = [string]$policy.merge_method
if ($mergeMethod -notin @("squash", "merge", "rebase")) {
    throw "Nepodporovaná merge_method v policy: $mergeMethod"
}

Write-Host "=== DDDA governed implementation merge preflight ==="
Write-Host "Repository:        $repositorySlug"
Write-Host "PR:                $Pr"
Write-Host "Head SHA:          $headSha"
Write-Host "Candidate SHA-256: $($validation.PackageSha256)"
Write-Host "CI checks:         PASS ($($checkSummary.CheckRunCount) check runs)"
Write-Host "Human Review:      PASS ($commentAuthor)"
Write-Host "Merge method:      $mergeMethod"
Write-Host "Release Scope Gate: NOT APPLICABLE (implementation merge)"
Write-Host "Release/tag side effects: DISABLED"

if ($DryRun) {
    Write-Host ""
    Write-Host "DDDA merge-pr dry-run: PASS"
    Write-Host "Nebyl proveden merge, release, promotion ani tag."
    exit 0
}

if ([bool]$policy.require_explicit_confirmation -and -not $ConfirmMerge) {
    throw "Implementation merge vyžaduje explicitní -ConfirmMerge."
}

# This command is intentionally merge-only. It does not call HRDR, Release Scope Gate,
# release package, release validation or tag execution paths.
$mergeResult = Merge-DDDAGitHubPullRequest `
    -RepositorySlug $repositorySlug `
    -Pr $Pr `
    -HeadSha $headSha `
    -MergeMethod $mergeMethod `
    -Token $githubAuth.Token

$mergeCommit = [string]$mergeResult.sha
if ($mergeCommit -notmatch '^[0-9a-f]{40}$') {
    throw "GitHub nevrátil platný merge commit SHA."
}

$postMerge = Get-DDDAGitHubPullRequest -RepositorySlug $repositorySlug -Pr $Pr -Token $githubAuth.Token
if (-not [bool]$postMerge.merged) {
    throw "GitHub nepotvrdil merge PR #$Pr."
}

$evidenceRoot = Join-Path (Get-DDDAPlatformStateRoot) ("merge-reports/pr-$Pr-$headSha")
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$evidencePath = Join-Path $evidenceRoot "result.json"
Write-DDDAPlatformJson -Path $evidencePath -Depth 20 -Value ([ordered]@{
    schema_version = 1
    repository = $repositorySlug
    pr = $Pr
    source_sha = $headSha
    candidate_package_sha256 = [string]$validation.PackageSha256
    human_review = [ordered]@{
        reviewer = $commentAuthor
        reviewed_at = [string]$review.reviewed_at
        verdict = "pass"
    }
    merge_method = $mergeMethod
    merge_sha = $mergeCommit
    merged = $true
    release_scope_gate = "NOT_APPLICABLE"
    release_side_effects = $false
    tag_side_effects = $false
    completed_at = (Get-Date).ToUniversalTime().ToString("o")
})

Write-Host ""
Write-Host "DDDA merge-pr: PASS"
Write-Host "PR #$Pr merged as $mergeCommit."
Write-Host "Evidence: $evidencePath"
Write-Host "Nebyl vytvořen release package, release validation ani tag."
