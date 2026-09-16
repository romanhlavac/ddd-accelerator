[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [Parameter(Mandatory = $true)][ValidateRange(1, 2147483647)][int]$Pr,
    [Parameter(Mandatory = $true)][string]$Version,
    [string]$Reviewer,
    [string]$DecisionOwner,
    [string]$ValidationReportPath,
    [string]$CandidatePackagePath,
    [switch]$PublishScaffold,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAGitHubSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAReleaseGovernanceSupport.ps1")

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
$headSha = [string]$prInfo.head.sha
if ($headSha -notmatch '^[0-9a-f]{40}$') {
    throw "GitHub nevrátil platný PR head SHA."
}

$validation = Get-DDDACandidateValidationEvidence `
    -Pr $Pr `
    -HeadSha $headSha `
    -ValidationReportPath $ValidationReportPath `
    -PackagePath $CandidatePackagePath
$scope = Get-DDDAReleaseMilestoneScope -RepositorySlug $repositorySlug -Version $Version -Token $githubAuth.Token

$record = [ordered]@{
    schema_version = 1
    repository = $repositorySlug
    pr = $Pr
    branch = [string]$prInfo.head.ref
    source_sha = $headSha
    candidate_package_sha256 = [string]$validation.PackageSha256
    version = $Version
    reviewer = if ([string]::IsNullOrWhiteSpace($Reviewer)) { "" } else { $Reviewer }
    decision_owner = if ([string]::IsNullOrWhiteSpace($DecisionOwner)) { "" } else { $DecisionOwner }
    decision = "pending"
    decided_at = $null
    scope_issues = @($scope.Issues)
    findings = @()
    accepted_risks = @()
    evidence = [ordered]@{
        validation_report = [string]$validation.ReportPath
        candidate_package = [string]$validation.PackagePath
        milestone = [string]$scope.Title
    }
}

$reviewRoot = Join-Path (Get-DDDAPlatformStateRoot) ("human-reviews/pr-$Pr-$headSha")
New-Item -ItemType Directory -Path $reviewRoot -Force | Out-Null
$jsonPath = Join-Path $reviewRoot "human-release-decision.json"
$markdownPath = Join-Path $reviewRoot "human-release-decision.md"
Write-DDDAPlatformJson -Value $record -Path $jsonPath -Depth 30

$markdown = @"
# Human Release Decision Record — PR #$Pr

- Repository: $repositorySlug
- Branch: $([string]$prInfo.head.ref)
- Exact SHA: $headSha
- Candidate SHA-256: $([string]$validation.PackageSha256)
- Proposed version: $Version
- Milestone: $([string]$scope.Title)
- Scope Issues: $(@($scope.Issues | ForEach-Object { "#$_" }) -join ", ")
- Decision: **PENDING HUMAN DECISION**
- Reviewer: $(if ([string]::IsNullOrWhiteSpace($Reviewer)) { "<human fills>" } else { $Reviewer })
- Decision owner: $(if ([string]::IsNullOrWhiteSpace($DecisionOwner)) { "<human fills>" } else { $DecisionOwner })

Automation created only a scaffold. It did not issue a release decision and did not accept any risk.

Authoritative machine-readable working copy: $jsonPath
"@
Write-DDDAPlatformText -Value ($markdown + [Environment]::NewLine) -Path $markdownPath

$comment = $null
if ($PublishScaffold) {
    $comment = Set-DDDAHrdrComment -RepositorySlug $repositorySlug -Pr $Pr -Token $githubAuth.Token -Record $record
}

$result = [ordered]@{
    status = "PENDING_HUMAN_DECISION"
    repository = $repositorySlug
    pr = $Pr
    branch = [string]$prInfo.head.ref
    source_sha = $headSha
    candidate_package_sha256 = [string]$validation.PackageSha256
    version = $Version
    milestone = [string]$scope.Title
    scope_issues = @($scope.Issues)
    json_path = $jsonPath
    markdown_path = $markdownPath
    published_comment_id = if ($null -eq $comment) { $null } else { [int64]$comment.id }
}

if ($Json) {
    $result | ConvertTo-Json -Depth 20
}
else {
    Write-Host "DDDA review-pr scaffold: PASS"
    Write-Host "PR:                $Pr"
    Write-Host "Head SHA:          $headSha"
    Write-Host "Candidate hash:    $($validation.PackageSha256)"
    Write-Host "Version:           $Version"
    Write-Host "Milestone:         $($scope.Title)"
    Write-Host "Decision:          PENDING_HUMAN_DECISION"
    Write-Host "Working HRDR:      $jsonPath"
    if ($null -ne $comment) {
        Write-Host "Authoritative comment scaffold: $([int64]$comment.id)"
    }
}
