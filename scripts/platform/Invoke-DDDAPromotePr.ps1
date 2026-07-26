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
    [switch]$NonInteractive,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")

Assert-DDDAPlatformSemanticVersion -Version $Version
$platformRoot = Get-DDDAPlatformGitRoot -Path $PlatformPath
if ($platformRoot -ne [System.IO.Path]::GetFullPath($PlatformPath).TrimEnd('\', '/')) {
    throw "PlatformPath musí být Git root DDDA platformy."
}
Assert-DDDAPlatformCleanGit -Repository $platformRoot

if (-not (Get-Command "gh" -ErrorAction SilentlyContinue)) {
    throw "promote-pr vyžaduje GitHub CLI 'gh' s aktivní autentizací."
}

$originUrl = Get-DDDAPlatformRepositoryUrl -Repository $platformRoot
$repositorySlug = Get-DDDAPlatformRepositorySlug -RepositoryUrl $originUrl
$policyPath = Join-Path $platformRoot "config/platform/development-policy.yaml"
if (-not (Test-Path -LiteralPath $policyPath -PathType Leaf)) {
    throw "Chybí platform development policy: $policyPath"
}
$policy = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($policy.schema_version -ne 1) {
    throw "Nepodporovaná platform development policy."
}

$prText = Invoke-DDDAPlatformNative -Command "gh" -Arguments @(
    "pr", "view", [string]$Pr,
    "--repo", $repositorySlug,
    "--json", "number,state,isDraft,headRefName,headRefOid,baseRefName,mergeStateStatus,reviewDecision"
)
$prInfo = $prText | ConvertFrom-Json
if ($prInfo.state -ne "OPEN") { throw "PR #$Pr není otevřený." }
if ($prInfo.isDraft) { throw "PR #$Pr je stále draft. Nejprve jej označ jako ready for review." }
if ($prInfo.baseRefName -ne [string]$policy.base_branch) {
    throw "PR #$Pr míří do '$($prInfo.baseRefName)', očekáváno '$($policy.base_branch)'."
}
if ($prInfo.mergeStateStatus -notin @("CLEAN", "HAS_HOOKS", "UNSTABLE")) {
    throw "PR #$Pr není připraven k merge. mergeStateStatus=$($prInfo.mergeStateStatus)"
}
$headSha = [string]$prInfo.headRefOid
if ($headSha -notmatch '^[0-9a-f]{40}$') {
    throw "GitHub nevrátil platný PR head SHA."
}

$checksOutput = $null
try {
    $checksOutput = Invoke-DDDAPlatformNative -Command "gh" -Arguments @("pr", "checks", [string]$Pr, "--repo", $repositorySlug)
}
catch {
    throw "CI kontroly PR #$Pr nejsou všechny PASS:`n$($_.Exception.Message)"
}

$minimumApprovals = [int]$policy.minimum_approvals
if ($minimumApprovals -gt 0) {
    $reviewsText = Invoke-DDDAPlatformNative -Command "gh" -Arguments @("api", "repos/$repositorySlug/pulls/$Pr/reviews", "--paginate")
    $reviews = @($reviewsText | ConvertFrom-Json)
    $approvedUsers = @(
        $reviews |
            Where-Object { $_.state -eq "APPROVED" } |
            ForEach-Object { $_.user.login } |
            Sort-Object -Unique
    )
    if ($approvedUsers.Count -lt $minimumApprovals) {
        throw "PR #$Pr nemá požadovaný počet approvals. Požadováno: $minimumApprovals; nalezeno: $($approvedUsers.Count)."
    }
}

$validationRoot = Join-Path (Get-DDDAPlatformStateRoot) ("validation-reports/pr-$Pr-$headSha")
$validationReports = @()
if (Test-Path -LiteralPath $validationRoot) {
    $validationReports = @(
        Get-ChildItem -LiteralPath $validationRoot -Filter "result.json" -File -Recurse -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTimeUtc -Descending
    )
}
if ($validationReports.Count -eq 0) {
    throw "Nenalezen PASS validate-pr report pro PR #$Pr a SHA $headSha. Spusť .\ddda.ps1 validate-pr -Pr $Pr."
}
$validationReportPath = $null
$validationReport = $null
foreach ($candidate in $validationReports) {
    $candidateReport = Get-Content -LiteralPath $candidate.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($candidateReport.status -eq "PASS" -and $candidateReport.source.commit -eq $headSha -and $candidateReport.source.pr -eq $Pr) {
        $validationReportPath = $candidate.FullName
        $validationReport = $candidateReport
        break
    }
}
if ($null -eq $validationReport) {
    throw "Žádný validation report nemá PASS pro aktuální PR head SHA $headSha."
}
if (-not (Test-Path -LiteralPath $validationReport.package.path -PathType Leaf)) {
    throw "Candidate package z validation reportu neexistuje: $($validationReport.package.path)"
}
$actualCandidateHash = Get-DDDAPlatformFileHash -Path $validationReport.package.path
if ($actualCandidateHash -ne [string]$validationReport.package.sha256) {
    throw "Candidate package hash neodpovídá validation reportu."
}

$stateRoot = Get-DDDAPlatformStateRoot
$timestamp = Get-DDDAPlatformTimestamp
$promotionId = "release-$Version-pr-$Pr-$timestamp"
$promotionRoot = Join-Path $stateRoot ("promotion/" + $promotionId)
$reviewRoot = Join-Path $promotionRoot "review"
New-Item -ItemType Directory -Path $promotionRoot -Force | Out-Null

$null = Invoke-DDDAPlatformNative -Command "git" -Arguments @("clone", "--no-checkout", $originUrl, $reviewRoot)
$null = Invoke-DDDAPlatformGit -Repository $reviewRoot -Arguments @("fetch", "origin", "refs/pull/$Pr/head")
$null = Invoke-DDDAPlatformGit -Repository $reviewRoot -Arguments @("checkout", "--detach", $headSha)
foreach ($relative in @($policy.required_documents)) {
    if (-not (Test-Path -LiteralPath (Join-Path $reviewRoot ([string]$relative)) -PathType Leaf)) {
        throw "PR #$Pr neobsahuje povinný governance dokument: $relative"
    }
}

Write-Host "=== DDDA promote-pr preflight ==="
Write-Host "Repository:        $repositorySlug"
Write-Host "PR:                $Pr"
Write-Host "Branch:            $($prInfo.headRefName)"
Write-Host "Head SHA:          $headSha"
Write-Host "Version:           $Version"
Write-Host "Validation report: $validationReportPath"
Write-Host "Candidate hash:    $actualCandidateHash"
Write-Host "CI checks:         PASS"
Write-Host "Approvals policy:  PASS"

if ($DryRun) {
    Write-Host ""
    Write-Host "DDDA promote-pr dry-run: PASS"
    Write-Host "Nebyl proveden merge, release ani tag."
    if (-not $KeepArtifacts -and (Test-Path -LiteralPath $promotionRoot)) {
        Remove-Item -LiteralPath $promotionRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    exit 0
}

if ([bool]$policy.require_explicit_confirmation -and -not $ConfirmMerge) {
    throw "Promotion vyžaduje explicitní -ConfirmMerge."
}

$mergeMethod = [string]$policy.merge_method
$mergeArguments = @("pr", "merge", [string]$Pr, "--repo", $repositorySlug, "--match-head-commit", $headSha, "--delete-branch")
switch ($mergeMethod) {
    "squash" { $mergeArguments += "--squash" }
    "merge" { $mergeArguments += "--merge" }
    "rebase" { $mergeArguments += "--rebase" }
    default { throw "Nepodporovaná merge_method v policy: $mergeMethod" }
}
$null = Invoke-DDDAPlatformNative -Command "gh" -Arguments $mergeArguments

$postMergeText = Invoke-DDDAPlatformNative -Command "gh" -Arguments @("pr", "view", [string]$Pr, "--repo", $repositorySlug, "--json", "state,mergedAt,mergeCommit")
$postMerge = $postMergeText | ConvertFrom-Json
if ($postMerge.state -ne "MERGED" -or $null -eq $postMerge.mergeCommit) {
    throw "GitHub nepotvrdil merge PR #$Pr."
}
$mergeCommit = [string]$postMerge.mergeCommit.oid

$releaseSource = Join-Path $promotionRoot "release-source"
$releasePackageRoot = Join-Path $promotionRoot "release-package"
$releaseWorkspace = Join-Path $promotionRoot "release-workspace"
$releaseReports = Join-Path $stateRoot ("release-reports/$Version/$timestamp")
$releasePackagePath = Join-Path $stateRoot ("packages/ddda-release-$Version-$($mergeCommit.Substring(0,12)).zip")
$releaseSuitesPath = Join-Path $promotionRoot "release-suites.json"
$releaseSuites = [System.Collections.Generic.List[object]]::new()
$releasePassed = $false

try {
    $null = Invoke-DDDAPlatformNative -Command "git" -Arguments @("clone", "--branch", [string]$policy.base_branch, "--single-branch", $originUrl, $releaseSource)
    $releaseHead = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("rev-parse", "HEAD")
    if ($releaseHead -ne $mergeCommit) {
        throw "Aktuální main HEAD '$releaseHead' neodpovídá merge commit '$mergeCommit'."
    }
    Assert-DDDAPlatformCleanGit -Repository $releaseSource -Label "Release source"

    $releasePackageText = & (Join-Path $releaseSource "scripts/platform/New-DDDAPlatformPackage.ps1") -PlatformPath $releaseSource -Kind release -Version $Version -SourceRef $mergeCommit -OutputPath $releasePackagePath -Json | Out-String
    if ($LASTEXITCODE -ne 0) { throw "Vytvoření release package selhalo." }
    $releasePackage = $releasePackageText.Trim() | ConvertFrom-Json
    & (Join-Path $releaseSource "scripts/platform/Test-DDDAPlatformPackage.ps1") -PackagePath $releasePackagePath -ExpectedCommit $mergeCommit -ExpectedKind release
    if ($LASTEXITCODE -ne 0) { throw "Release package validation selhala." }

    New-Item -ItemType Directory -Path $releasePackageRoot -Force | Out-Null
    Expand-Archive -LiteralPath $releasePackagePath -DestinationPath $releasePackageRoot -Force
    $null = Invoke-DDDAPlatformNative -Command "git" -Arguments @("-C", $releasePackageRoot, "init", "-b", "main")
    $null = Invoke-DDDAPlatformGit -Repository $releasePackageRoot -Arguments @("config", "user.name", "DDDA Release Validation")
    $null = Invoke-DDDAPlatformGit -Repository $releasePackageRoot -Arguments @("config", "user.email", "ddda-release@example.invalid")
    $null = Invoke-DDDAPlatformGit -Repository $releasePackageRoot -Arguments @("add", ".")
    $null = Invoke-DDDAPlatformGit -Repository $releasePackageRoot -Arguments @("commit", "-m", "chore: release package baseline")

    $releaseWorkspaceText = & (Join-Path $releasePackageRoot "scripts/platform/New-DDDAValidationWorkspace.ps1") -PlatformPath $releasePackageRoot -WorkspaceRoot $releaseWorkspace -Json | Out-String
    if ($LASTEXITCODE -ne 0) { throw "Release validation workspace selhal." }
    $null = $releaseWorkspaceText.Trim() | ConvertFrom-Json

    foreach ($suiteName in @("security", "smoke", "e2e", "acceptance")) {
        $watch = [System.Diagnostics.Stopwatch]::StartNew()
        $arguments = @("-PlatformPath", $releasePackageRoot, "-Suite", $suiteName, "-PackagePath", $releasePackagePath)
        if ($suiteName -eq "acceptance") {
            $arguments = @("-PlatformPath", $releasePackageRoot, "-Suite", "acceptance", "-CleanupOnFailure", "-NonInteractive")
        }
        try {
            Invoke-DDDAPlatformChildPowerShell -ScriptPath (Join-Path $releasePackageRoot "scripts/platform/Invoke-DDDAPlatformTest.ps1") -Arguments $arguments
            $suiteStatus = "PASS"
            $suiteDetails = $null
        }
        catch {
            $suiteStatus = "FAIL"
            $suiteDetails = $_.Exception.Message
            throw
        }
        finally {
            $watch.Stop()
            $releaseSuites.Add([ordered]@{ name = $suiteName; status = $suiteStatus; duration_ms = [int64]$watch.ElapsedMilliseconds; details = $suiteDetails })
        }
    }

    if ($WithMiro) {
        $watch = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $miroArguments = @("-PlatformPath", $releasePackageRoot, "-Suite", "acceptance", "-WithMiro", "-CleanupOnFailure")
            if ($Full) { $miroArguments += "-Full" }
            if ($NonInteractive) { $miroArguments += "-NonInteractive" }
            Invoke-DDDAPlatformChildPowerShell -ScriptPath (Join-Path $releasePackageRoot "scripts/platform/Invoke-DDDAPlatformTest.ps1") -Arguments $miroArguments
            $suiteStatus = "PASS"
            $suiteDetails = $null
        }
        catch {
            $suiteStatus = "FAIL"
            $suiteDetails = $_.Exception.Message
            throw
        }
        finally {
            $watch.Stop()
            $releaseSuites.Add([ordered]@{ name = "miro"; status = $suiteStatus; duration_ms = [int64]$watch.ElapsedMilliseconds; details = $suiteDetails })
        }
    }

    $releasePassed = $true
}
finally {
    Write-DDDAPlatformJson -Value @($releaseSuites) -Path $releaseSuitesPath
    $releaseStatus = if ($releasePassed) { "PASS" } else { "FAIL" }
    & (Join-Path $releaseSource "scripts/platform/New-DDDAValidationReport.ps1") -ValidationId $promotionId -Status $releaseStatus -SourceKind release -Repository $repositorySlug -Commit $mergeCommit -Branch ([string]$policy.base_branch) -PackagePath $releasePackagePath -Workspace $releaseWorkspace -SuitesJsonPath $releaseSuitesPath -OutputRoot $releaseReports
}

if (-not $releasePassed) {
    throw "PR byl mergován, ale release validation selhala. Release tag nebyl vytvořen. Report: $releaseReports"
}

$tag = "v$Version"
$existingTag = Invoke-DDDAPlatformNative -Command "git" -Arguments @("ls-remote", "--tags", $originUrl, "refs/tags/$tag")
if (-not [string]::IsNullOrWhiteSpace($existingTag)) {
    throw "Release tag již existuje: $tag"
}
$null = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("tag", "-a", $tag, $mergeCommit, "-m", "DDDA $Version")
$null = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("push", "origin", $tag)

if (-not $KeepArtifacts -and (Test-Path -LiteralPath $promotionRoot)) {
    Remove-Item -LiteralPath $promotionRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "========================================"
Write-Host "DDDA PR promotion: PASS"
Write-Host "PR:              $Pr"
Write-Host "Merge commit:    $mergeCommit"
Write-Host "Release version: $Version"
Write-Host "Release package: $releasePackagePath"
Write-Host "Release report:  $releaseReports"
Write-Host "Tag:             $tag"
Write-Host "========================================"
