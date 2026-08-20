[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [Parameter(Mandatory = $true)][ValidateRange(1, 2147483647)][int]$Pr,
    [string]$PackagePath,
    [string]$ValidationReportPath,
    [ValidateSet("merge", "squash")][string]$MergeMethod,
    [switch]$ConfirmMerge,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAGitHubSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAReleaseGovernanceSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAMergeStrategySupport.ps1")

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
$baseSha = [string]$prInfo.base.sha
if ($baseSha -notmatch '^[0-9a-f]{40}$') {
    throw "GitHub nevrátil platný base SHA."
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
    $ignoredCheckRunNames = if ($DryRun -and -not [string]::IsNullOrWhiteSpace([string]$env:DDDA_CURRENT_CHECK_NAME)) {
        @([string]$env:DDDA_CURRENT_CHECK_NAME)
    }
    else {
        @()
    }
    $checkSummary = Assert-DDDAGitHubChecksPassed -RepositorySlug $repositorySlug -Commit $headSha -Token $githubAuth.Token -IgnoredCheckRunNames $ignoredCheckRunNames
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

$validationArguments = @{
    Pr = $Pr
    HeadSha = $headSha
}
if (-not [string]::IsNullOrWhiteSpace($PackagePath)) { $validationArguments["PackagePath"] = $PackagePath }
if (-not [string]::IsNullOrWhiteSpace($ValidationReportPath)) { $validationArguments["ValidationReportPath"] = $ValidationReportPath }
$validation = Get-DDDACandidateValidationEvidence @validationArguments
Invoke-DDDAPlatformChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/platform/Test-DDDAPlatformPackage.ps1") -Arguments @(
    "-PackagePath", [string]$validation.PackagePath,
    "-ExpectedCommit", $headSha,
    "-ExpectedKind", "candidate"
) -SuppressOutput

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

$impact = Get-DDDAChangeImpactFromPrBody -Body ([string]$prInfo.body)
$requestedMergeMethod = if ([string]::IsNullOrWhiteSpace($MergeMethod)) { "" } else { $MergeMethod }
$strategyDecision = Resolve-DDDAMergeStrategy `
    -Policy $policy `
    -Impact $impact `
    -RequestedMethod $requestedMergeMethod `
    -Pr $Pr `
    -BaseSha $baseSha `
    -PrBody ([string]$prInfo.body)
$effectiveMergeMethod = [string]$strategyDecision.merge_method

$squashException = $null
if ([bool]$strategyDecision.human_squash_exception_required) {
    $exceptionComments = [System.Collections.Generic.List[object]]::new()
    for ($page = 1; ; $page++) {
        $batch = @(Invoke-DDDAGitHubApi -Method GET -Path "repos/$repositorySlug/issues/$Pr/comments?per_page=100&page=$page" -Token $githubAuth.Token)
        foreach ($comment in $batch) {
            if ([string]$comment.body -like "*$script:DDDASquashExceptionMarker*") {
                $exceptionComments.Add($comment)
            }
        }
        if ($batch.Count -lt 100) { break }
    }
    if ($exceptionComments.Count -ne 1) {
        throw "LOW/MEDIUM squash vyžaduje právě jeden authoritativní human squash exception marker. Nalezeno: $($exceptionComments.Count)."
    }
    $exceptionComment = $exceptionComments[0]
    $squashException = ConvertFrom-DDDASquashExceptionComment -Comment $exceptionComment
    Assert-DDDASquashExceptionRecord `
        -Record $squashException `
        -CommentAuthor ([string]$exceptionComment.user.login) `
        -CommentAuthorType ([string]$exceptionComment.user.type) `
        -Repository $repositorySlug `
        -Pr $Pr `
        -HeadSha $headSha `
        -CandidatePackageSha256 ([string]$validation.PackageSha256) `
        -Impact $impact
}

Write-Host "=== DDDA governed implementation merge preflight ==="
Write-Host "Repository:        $repositorySlug"
Write-Host "PR:                $Pr"
Write-Host "Head SHA:          $headSha"
Write-Host "Base SHA:          $baseSha"
Write-Host "Candidate SHA-256: $($validation.PackageSha256)"
Write-Host "CI checks:         PASS ($($checkSummary.CheckRunCount) check runs)"
Write-Host "Human Review:      PASS ($commentAuthor)"
Write-Host "Impact:            $impact"
Write-Host "Merge method:      $effectiveMergeMethod"
Write-Host "Bootstrap transition: $([bool]$strategyDecision.bootstrap_transition)"
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
    -MergeMethod $effectiveMergeMethod `
    -Token $githubAuth.Token

$mergeCommit = [string]$mergeResult.sha
if ($mergeCommit -notmatch '^[0-9a-f]{40}$') {
    throw "GitHub nevrátil platný merge commit SHA."
}

$postMerge = Get-DDDAGitHubPullRequest -RepositorySlug $repositorySlug -Pr $Pr -Token $githubAuth.Token
if (-not [bool]$postMerge.merged) {
    throw "GitHub nepotvrdil merge PR #$Pr."
}

$sourceToResultRelation = $null
$ancestryVerified = $false
if ($effectiveMergeMethod -eq "merge") {
    $mergeCommitInfo = Invoke-DDDAGitHubApi -Method GET -Path "repos/$repositorySlug/commits/$mergeCommit" -Token $githubAuth.Token
    $parentShas = @($mergeCommitInfo.parents | ForEach-Object { [string]$_.sha })
    if ($headSha -notin $parentShas) {
        throw "Post-merge ancestry read-back selhal: validated PR HEAD $headSha není parent výsledného merge commit $mergeCommit."
    }
    $compare = Invoke-DDDAGitHubApi -Method GET -Path "repos/$repositorySlug/compare/$headSha...$mergeCommit" -Token $githubAuth.Token
    if ([string]$compare.merge_base_commit.sha -ne $headSha) {
        throw "Post-merge ancestry read-back selhal: validated PR HEAD není ancestor výsledného main state."
    }
    $sourceToResultRelation = "ancestor"
    $ancestryVerified = $true
}
elseif ($effectiveMergeMethod -eq "squash") {
    $sourceToResultRelation = "explicit_squash_mapping"
}
else {
    throw "Neočekávaný merge method po merge: $effectiveMergeMethod"
}

$exceptionEvidence = $null
if ($null -ne $squashException) {
    $exceptionEvidence = [ordered]@{
        type = "human_low_medium_exception"
        reason = [string]$squashException.reason
        reviewer = [string]$squashException.reviewer
        approved_at = [string]$squashException.approved_at
    }
}
elseif ([bool]$strategyDecision.bootstrap_transition) {
    $transition = $policy.merge_strategy.bootstrap_transition
    $exceptionEvidence = [ordered]@{
        type = "prospective_policy_bootstrap"
        change_issue = [int]$transition.change_issue
        legacy_base_sha = [string]$transition.legacy_base_sha
        reason = [string]$transition.reason
    }
}

$evidenceRoot = Join-Path (Get-DDDAPlatformStateRoot) ("merge-reports/pr-$Pr-$headSha")
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$evidencePath = Join-Path $evidenceRoot "result.json"
Write-DDDAPlatformJson -Path $evidencePath -Depth 30 -Value ([ordered]@{
    schema_version = 2
    repository = $repositorySlug
    pr = $Pr
    impact = $impact
    validated_source_head_sha = $headSha
    candidate_package_sha256 = [string]$validation.PackageSha256
    human_review = [ordered]@{
        reviewer = $commentAuthor
        reviewed_at = [string]$review.reviewed_at
        verdict = "pass"
    }
    merge_method = $effectiveMergeMethod
    resulting_merge_sha = $mergeCommit
    source_to_result_relation = $sourceToResultRelation
    ancestry_verified = $ancestryVerified
    squash_exception = $exceptionEvidence
    merged = $true
    release_scope_gate = "NOT_APPLICABLE"
    release_side_effects = $false
    tag_side_effects = $false
    completed_at = (Get-Date).ToUniversalTime().ToString("o")
})

Write-Host ""
Write-Host "DDDA merge-pr: PASS"
Write-Host "PR #$Pr merged as $mergeCommit."
Write-Host "Source→result: $sourceToResultRelation"
Write-Host "Evidence: $evidencePath"
Write-Host "Nebyl vytvořen release package, release validation ani tag."
