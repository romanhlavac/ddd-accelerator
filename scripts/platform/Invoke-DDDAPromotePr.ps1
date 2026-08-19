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

Assert-DDDAPlatformSemanticVersion -Version $Version
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
    throw "PR #$Pr je stále draft. Nejprve jej označ jako ready for review."
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
$headRefName = [string]$prInfo.head.ref
$headRepository = if ($null -ne $prInfo.head.repo) { [string]$prInfo.head.repo.full_name } else { $null }
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
    if (
        $candidateReport.status -eq "PASS" -and
        $candidateReport.source.commit -eq $headSha -and
        $candidateReport.source.pr -eq $Pr -and
        $null -ne $candidateReport.package
    ) {
        $validationReportPath = $candidate.FullName
        $validationReport = $candidateReport
        break
    }
}
if ($null -eq $validationReport) {
    throw "Žádný validation report nemá PASS pro aktuální PR head SHA $headSha a existující candidate package."
}
if ($WithMiro) {
    $miroProperty = $validationReport.PSObject.Properties["miro"]
    if ($null -eq $miroProperty -or [string]$miroProperty.Value.status -ne "PASS") {
        throw "Promotion s -WithMiro vyžaduje PASS strukturovanou Miro evidence ve validate-pr reportu pro exact SHA."
    }
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
$logRoot = Join-Path $promotionRoot "logs"
New-Item -ItemType Directory -Path $promotionRoot, $logRoot -Force | Out-Null

$null = Invoke-DDDAPlatformNative -Command "git" -Arguments @("clone", "--no-checkout", $originUrl, $reviewRoot)
$null = Invoke-DDDAPlatformGit -Repository $reviewRoot -Arguments @("fetch", "origin", "refs/pull/$Pr/head")
$null = Invoke-DDDAPlatformGit -Repository $reviewRoot -Arguments @("checkout", "--detach", $headSha)
$reviewHead = Invoke-DDDAPlatformGit -Repository $reviewRoot -Arguments @("rev-parse", "HEAD")
if ($reviewHead -ne $headSha) {
    throw "Promotion review checkout neodpovídá exact PR head SHA."
}
Assert-DDDAPlatformCleanGit -Repository $reviewRoot -Label "Promotion review"

foreach ($relative in @($policy.required_documents)) {
    if (-not (Test-Path -LiteralPath (Join-Path $reviewRoot ([string]$relative)) -PathType Leaf)) {
        throw "PR #$Pr neobsahuje povinný governance dokument: $relative"
    }
}

$changelogRelease = Assert-DDDAPlatformChangelogRelease -Path (Join-Path $reviewRoot "CHANGELOG.md") -Version $Version
$tag = [string]$changelogRelease.Tag
$existingTag = Invoke-DDDAPlatformNative -Command "git" -Arguments @("ls-remote", "--tags", $originUrl, "refs/tags/$tag")
if (-not [string]::IsNullOrWhiteSpace($existingTag)) {
    throw "Release tag již existuje: $tag"
}

Write-Host "=== DDDA promote-pr preflight ==="
Write-Host "Repository:        $repositorySlug"
Write-Host "PR:                $Pr"
Write-Host "Branch:            $headRefName"
Write-Host "Head SHA:          $headSha"
Write-Host "Version:           $Version"
Write-Host "GitHub auth:       $($githubAuth.Source)"
Write-Host "Validation report: $validationReportPath"
Write-Host "Candidate hash:    $actualCandidateHash"
Write-Host "CI checks:         PASS ($($checkSummary.CheckRunCount) check runs)"
Write-Host "Approvals policy:  PASS"
Write-Host "Governance docs:   PASS"
Write-Host "Changelog release: PASS ($($changelogRelease.Version), $($changelogRelease.Date))"
Write-Host "Release tag free:  PASS ($tag)"

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
if ($mergeMethod -notin @("squash", "merge", "rebase")) {
    throw "Nepodporovaná merge_method v policy: $mergeMethod"
}
$mergeResult = Merge-DDDAGitHubPullRequest -RepositorySlug $repositorySlug -Pr $Pr -HeadSha $headSha -MergeMethod $mergeMethod -Token $githubAuth.Token
$mergeCommit = [string]$mergeResult.sha
if ($mergeCommit -notmatch '^[0-9a-f]{40}$') {
    throw "GitHub nevrátil platný merge commit SHA."
}

$postMerge = Get-DDDAGitHubPullRequest -RepositorySlug $repositorySlug -Pr $Pr -Token $githubAuth.Token
if (-not [bool]$postMerge.merged) {
    throw "GitHub nepotvrdil merge PR #$Pr."
}

if (-not [string]::IsNullOrWhiteSpace($headRefName) -and $headRepository -eq $repositorySlug) {
    try {
        $null = Invoke-DDDAPlatformNative -Command "git" -Arguments @("push", "origin", "--delete", $headRefName) -WorkingDirectory $platformRoot
    }
    catch {
        Write-Warning "PR byl mergován, ale zdrojovou větev se nepodařilo odstranit: $($_.Exception.Message)"
    }
}

$releaseSource = Join-Path $promotionRoot "release-source"
$releasePackageRoot = Join-Path $promotionRoot "release-package"
$releaseWorkspace = Join-Path $promotionRoot "release-workspace"
$releaseReports = Join-Path $stateRoot ("release-reports/$Version/$timestamp")
$releasePackagePath = Join-Path $stateRoot ("packages/ddda-release-$Version-$($mergeCommit.Substring(0,12)).zip")
$releaseSuitesPath = Join-Path $promotionRoot "release-suites.json"
$releaseMiroEvidencePath = Join-Path $promotionRoot "release-miro-acceptance-evidence.json"
$releaseSuites = [System.Collections.Generic.List[object]]::new()
$releaseDiagnostics = [System.Collections.Generic.List[string]]::new()
$releasePassed = $false
$releaseReportCreated = $false
$releaseFailure = $null
$releaseStartedAt = (Get-Date).ToUniversalTime()

function Invoke-ReleaseSuite {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $logPath = Join-Path $logRoot ("release-$Name.log")
    $hostExe = (Get-Process -Id $PID).Path
    $hostArguments = @("-NoProfile")
    if (Test-DDDAPlatformIsWindows) {
        $hostArguments += @("-ExecutionPolicy", "Bypass")
    }
    $hostArguments += @(
        "-File", (Join-Path $releasePackageRoot "scripts/platform/Invoke-DDDAPlatformTest.ps1"),
        "-PlatformPath", $releasePackageRoot,
        "-Suite", $Arguments[0]
    )
    if ($Arguments.Count -gt 1) {
        $hostArguments += $Arguments[1..($Arguments.Count - 1)]
    }

    $previousPreference = $ErrorActionPreference
    $exitCode = 1
    try {
        $ErrorActionPreference = "Continue"
        & $hostExe @hostArguments *> $logPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
        $watch.Stop()
    }

    $logTail = ""
    if (Test-Path -LiteralPath $logPath) {
        $logTail = ((Get-Content -LiteralPath $logPath -Tail 40 -ErrorAction SilentlyContinue) -join [Environment]::NewLine).Trim()
    }
    $suiteStatus = if ($exitCode -eq 0) { "PASS" } else { "FAIL" }
    $releaseSuites.Add([ordered]@{
        name = $Name
        status = $suiteStatus
        duration_ms = [int64]$watch.ElapsedMilliseconds
        details = if ($exitCode -eq 0) { "Log: $logPath" } else { $logTail }
    })
    $releaseDiagnostics.Add($logPath)

    if ($exitCode -ne 0) {
        throw "Release suite '$Name' selhala. Log: $logPath`n$logTail"
    }
}

try {
    $null = Invoke-DDDAPlatformNative -Command "git" -Arguments @(
        "clone", "--branch", [string]$policy.base_branch, "--single-branch", $originUrl, $releaseSource
    )

    # Release tags are annotated objects and require a tagger identity. Configure it
    # only in the isolated release-source clone so clean runners never depend on
    # ambient/global Git identity and no user-specific metadata leaks into the tag.
    $releaseTaggerName = "DDDA Release Tagger"
    $releaseTaggerEmail = "ddda-release-tagger@example.invalid"
    $null = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("config", "user.name", $releaseTaggerName)
    $null = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("config", "user.email", $releaseTaggerEmail)
    $configuredTaggerName = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("config", "--get", "user.name")
    $configuredTaggerEmail = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("config", "--get", "user.email")
    if ($configuredTaggerName -ne $releaseTaggerName -or $configuredTaggerEmail -ne $releaseTaggerEmail) {
        throw "Release-source Git tagger identity could not be configured deterministically."
    }

    $releaseHead = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("rev-parse", "HEAD")
    if ($releaseHead -ne $mergeCommit) {
        throw "Aktuální main HEAD '$releaseHead' neodpovídá merge commit '$mergeCommit'."
    }
    Assert-DDDAPlatformCleanGit -Repository $releaseSource -Label "Release source"

    $releasePackageText = & (Join-Path $releaseSource "scripts/platform/New-DDDAPlatformPackage.ps1") -PlatformPath $releaseSource -Kind release -Version $Version -SourceRef $mergeCommit -OutputPath $releasePackagePath -Json | Out-String
    if ([string]::IsNullOrWhiteSpace($releasePackageText)) {
        throw "Vytvoření release package nevrátilo JSON."
    }
    $releasePackage = $releasePackageText.Trim() | ConvertFrom-Json
    if ($releasePackage.source_commit -ne $mergeCommit) {
        throw "Release package není svázán s merge commit SHA."
    }

    Invoke-DDDAPlatformChildPowerShell -ScriptPath (Join-Path $releaseSource "scripts/platform/Test-DDDAPlatformPackage.ps1") -Arguments @(
        "-PackagePath", $releasePackagePath,
        "-ExpectedCommit", $mergeCommit,
        "-ExpectedKind", "release"
    ) -SuppressOutput

    New-Item -ItemType Directory -Path $releasePackageRoot -Force | Out-Null
    Expand-Archive -LiteralPath $releasePackagePath -DestinationPath $releasePackageRoot -Force
    $null = Invoke-DDDAPlatformNative -Command "git" -Arguments @("-C", $releasePackageRoot, "init", "-b", "main")
    $null = Invoke-DDDAPlatformGit -Repository $releasePackageRoot -Arguments @("config", "user.name", "DDDA Release Validation")
    $null = Invoke-DDDAPlatformGit -Repository $releasePackageRoot -Arguments @("config", "user.email", "ddda-release@example.invalid")
    $null = Invoke-DDDAPlatformGit -Repository $releasePackageRoot -Arguments @("add", ".")
    $null = Invoke-DDDAPlatformGit -Repository $releasePackageRoot -Arguments @("commit", "-m", "chore: release package baseline")
    Assert-DDDAPlatformCleanGit -Repository $releasePackageRoot -Label "Rozbalený release package"

    $releaseWorkspaceText = & (Join-Path $releasePackageRoot "scripts/platform/New-DDDAValidationWorkspace.ps1") -PlatformPath $releasePackageRoot -WorkspaceRoot $releaseWorkspace -Json | Out-String
    if ([string]::IsNullOrWhiteSpace($releaseWorkspaceText)) {
        throw "Release validation workspace nevrátil JSON."
    }
    $releaseWorkspaceResult = $releaseWorkspaceText.Trim() | ConvertFrom-Json
    if ($releaseWorkspaceResult.status -ne "PASS") {
        throw "Release validation workspace nevrátil PASS."
    }

    Invoke-ReleaseSuite -Name "security" -Arguments @("security", "-PackagePath", $releasePackagePath)
    Invoke-ReleaseSuite -Name "smoke" -Arguments @("smoke", "-PackagePath", $releasePackagePath)
    Invoke-ReleaseSuite -Name "e2e" -Arguments @("e2e", "-PackagePath", $releasePackagePath)
    Invoke-ReleaseSuite -Name "acceptance" -Arguments @("acceptance", "-PackagePath", $releasePackagePath, "-CleanupOnFailure", "-NonInteractive")

    if ($WithMiro) {
        $miroArguments = @(
            "acceptance",
            "-PackagePath", $releasePackagePath,
            "-WithMiro",
            "-CleanupOnFailure",
            "-MiroEvidenceOutputPath", $releaseMiroEvidencePath
        )
        if ($Full) { $miroArguments += "-Full" }
        if ($KeepReviewBoard) { $miroArguments += "-KeepReviewBoard" }
        if (-not [string]::IsNullOrWhiteSpace($MiroTeamId)) { $miroArguments += @("-MiroTeamId", $MiroTeamId) }
        if ($NonInteractive) { $miroArguments += "-NonInteractive" }
        Invoke-ReleaseSuite -Name "miro" -Arguments $miroArguments
        if (-not (Test-Path -LiteralPath $releaseMiroEvidencePath -PathType Leaf)) {
            throw "Release Miro acceptance nevytvořila strukturovanou evidence."
        }
    }

    $releasePassed = $true
}
catch {
    $releaseFailure = $_.Exception.Message
    $releaseDiagnostics.Add($releaseFailure)
    Write-Host "DDDA release validation: FAIL" -ForegroundColor Red
    Write-Host $releaseFailure -ForegroundColor Red
}
finally {
    Write-DDDAPlatformJson -Value @($releaseSuites) -Path $releaseSuitesPath
    $releaseStatus = if ($releasePassed) { "PASS" } else { "FAIL" }
    $reportScriptRoot = if (Test-Path -LiteralPath (Join-Path $releaseSource "scripts/platform/New-DDDAValidationReport.ps1")) {
        $releaseSource
    }
    elseif (Test-Path -LiteralPath (Join-Path $reviewRoot "scripts/platform/New-DDDAValidationReport.ps1")) {
        $reviewRoot
    }
    else {
        $platformRoot
    }

    $releaseReportArguments = @{
        ValidationId = $promotionId
        Status = $releaseStatus
        SourceKind = "release"
        Repository = $repositorySlug
        Commit = $mergeCommit
        Branch = [string]$policy.base_branch
        SuitesJsonPath = $releaseSuitesPath
        OutputRoot = $releaseReports
        Diagnostics = @($releaseDiagnostics)
        StartedAt = $releaseStartedAt
        CompletedAt = (Get-Date).ToUniversalTime()
    }
    if (Test-Path -LiteralPath $releasePackagePath -PathType Leaf) {
        $releaseReportArguments["PackagePath"] = $releasePackagePath
    }
    if (Test-Path -LiteralPath $releaseWorkspace -PathType Container) {
        $releaseReportArguments["Workspace"] = $releaseWorkspace
    }
    if (Test-Path -LiteralPath $releaseMiroEvidencePath -PathType Leaf) {
        $releaseReportArguments["MiroEvidencePath"] = $releaseMiroEvidencePath
    }

    try {
        & (Join-Path $reportScriptRoot "scripts/platform/New-DDDAValidationReport.ps1") @releaseReportArguments | Out-Null
        $releaseReportJson = Join-Path $releaseReports "result.json"
        $releaseReportMarkdown = Join-Path $releaseReports "result.md"
        if (-not (Test-Path -LiteralPath $releaseReportJson -PathType Leaf) -or -not (Test-Path -LiteralPath $releaseReportMarkdown -PathType Leaf)) {
            throw "Release report generator nevytvořil result.json a result.md."
        }
        $releaseReportCreated = $true
    }
    catch {
        $releaseReportCreated = $false
        $releasePassed = $false
        $releaseFailure = "Release report generation failed: $($_.Exception.Message)"
        Write-Warning $releaseFailure
    }
}

if (-not $releasePassed -or -not $releaseReportCreated) {
    throw "PR byl mergován, ale release validation selhala. Release tag nebyl vytvořen. Důvod: $releaseFailure Report: $releaseReports"
}

$existingTagAfterValidation = Invoke-DDDAPlatformNative -Command "git" -Arguments @("ls-remote", "--tags", $originUrl, "refs/tags/$tag")
if (-not [string]::IsNullOrWhiteSpace($existingTagAfterValidation)) {
    throw "Release tag vznikl souběžně během validace a nebude přepsán: $tag"
}
$null = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("tag", "-a", $tag, $mergeCommit, "-m", "DDDA $Version")
$null = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("push", "origin", $tag)

if (-not $KeepArtifacts -and -not $KeepReviewBoard -and (Test-Path -LiteralPath $promotionRoot)) {
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
