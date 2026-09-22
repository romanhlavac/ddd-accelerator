[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][string]$ReleaseSourceSha,
    [Parameter(Mandatory = $true)][string]$CandidatePackagePath,
    [Parameter(Mandatory = $true)][string]$CandidateValidationReportPath,
    [Parameter(Mandatory = $true)][string]$OutputRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")

if ($ReleaseSourceSha -notmatch '^[0-9a-f]{40}$') { throw "ReleaseSourceSha není plný SHA." }
Assert-DDDAPlatformSemanticVersion -Version $Version
$report = Get-Content -LiteralPath $CandidateValidationReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([string]$report.status -ne "PASS" -or [string]$report.source.kind -ne "pr" -or [string]$report.source.commit -ne $ReleaseSourceSha -or [int]$report.source.pr -le 0 -or [string]::IsNullOrWhiteSpace([string]$report.source.repository) -or [string]$report.package.sha256 -notmatch '^[0-9a-f]{64}$') {
    throw "Candidate validation report není exact PASS evidence pro controlled release source."
}
if (-not (Test-Path -LiteralPath $CandidatePackagePath -PathType Leaf)) { throw "Candidate package neexistuje: $CandidatePackagePath" }
$candidateHash = Get-DDDAPlatformFileHash -Path $CandidatePackagePath
if ($candidateHash -ne [string]$report.package.sha256) { throw "Candidate package SHA-256 neodpovídá exact validation reportu." }

$platformRoot = Get-DDDAPlatformGitRoot -Path $PlatformPath
Assert-DDDAPlatformCleanGit -Repository $platformRoot
$recoveryRoot = [System.IO.Path]::GetFullPath($OutputRoot)
if (Test-Path -LiteralPath $recoveryRoot) { throw "Recovery evidence output již existuje a nebude přepsán: $recoveryRoot" }
New-Item -ItemType Directory -Path $recoveryRoot -Force | Out-Null
$sourceRoot = Join-Path $recoveryRoot "release-source"
$packageRoot = Join-Path $recoveryRoot "package"
$reportRoot = Join-Path $recoveryRoot "report"
$suitesPath = Join-Path $recoveryRoot "release-suites.json"
$originUrl = Get-DDDAPlatformRepositoryUrl -Repository $platformRoot

$null = Invoke-DDDAPlatformNative -Command "git" -Arguments @("clone", "--no-checkout", $originUrl, $sourceRoot)
$null = Invoke-DDDAPlatformGit -Repository $sourceRoot -Arguments @("fetch", "origin", $ReleaseSourceSha)
$null = Invoke-DDDAPlatformGit -Repository $sourceRoot -Arguments @("checkout", "--detach", $ReleaseSourceSha)
$checkedOut = Invoke-DDDAPlatformGit -Repository $sourceRoot -Arguments @("rev-parse", "HEAD")
if ($checkedOut -ne $ReleaseSourceSha) { throw "Recovery checkout neodpovídá exact frozen release source SHA." }
Assert-DDDAPlatformCleanGit -Repository $sourceRoot -Label "Recovery release source"

New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
$releasePackagePath = Join-Path $packageRoot ("ddda-release-$Version-$($ReleaseSourceSha.Substring(0, 12)).zip")
$packageArguments = @{ PlatformPath = $sourceRoot; Kind = "release"; Version = $Version; SourceRef = $ReleaseSourceSha; OutputPath = $releasePackagePath }
& (Join-Path $sourceRoot "scripts/platform/New-DDDAPlatformPackage.ps1") @packageArguments | Out-Null
if (-not (Test-Path -LiteralPath $releasePackagePath -PathType Leaf)) { throw "Release package reconstruction nevytvořila canonical package." }

$suites = [System.Collections.Generic.List[object]]::new()
foreach ($suite in @("smoke", "e2e", "acceptance")) {
    $suiteStarted = Get-Date
    & (Join-Path $sourceRoot "ddda.ps1") test -Suite $suite -PackagePath $releasePackagePath -CleanupOnFailure -NonInteractive
    if ($LASTEXITCODE -ne 0) { throw "Release recovery suite '$suite' selhala." }
    $suites.Add([ordered]@{ name = $suite; status = "PASS"; duration_ms = [int64]((Get-Date) - $suiteStarted).TotalMilliseconds; details = "Revalidated during idempotent recovery from exact frozen source SHA." })
}
Write-DDDAPlatformJson -Value @($suites.ToArray()) -Path $suitesPath

# workflow_run_id was added to newer validation reports. Frozen controlled
# candidates can legitimately carry older schema-v1 reports without that
# optional property, so read it through the PSObject property bag under
# Set-StrictMode instead of dereferencing a missing member.
$workflowRunId = $null
$workflowRunProperty = $report.package.PSObject.Properties['workflow_run_id']
if ($null -ne $workflowRunProperty -and -not [string]::IsNullOrWhiteSpace([string]$workflowRunProperty.Value)) {
    $workflowRunId = [string]$workflowRunProperty.Value
}

$reportArguments = @{
    ValidationId = "release-recovery-$Version-$($ReleaseSourceSha.Substring(0, 12))"
    Status = "PASS"
    SourceKind = "release"
    Repository = [string]$report.source.repository
    Commit = $ReleaseSourceSha
    Pr = [int]$report.source.pr
    Branch = [string]$report.source.branch
    PackagePath = $releasePackagePath
    WorkflowRunId = $workflowRunId
    SuitesJsonPath = $suitesPath
    OutputRoot = $reportRoot
    Diagnostics = @("Reconstructed from exact candidate package SHA-256 $candidateHash and revalidated release suites.")
    PortablePaths = $true
    RedactedRoots = @($recoveryRoot)
}
# Release source code builds and exercises the frozen package, but portable report
# materialization is a trusted control-plane concern. Historical candidates may
# predate current report parameters such as PortablePaths/RedactedRoots.
& (Join-Path $platformRoot "scripts/platform/New-DDDAValidationReport.ps1") @reportArguments | Out-Null

$resultJson = Join-Path $reportRoot "result.json"
$resultMarkdown = Join-Path $reportRoot "result.md"
$releaseReport = Get-Content -LiteralPath $resultJson -Raw -Encoding UTF8 | ConvertFrom-Json
if ([string]$releaseReport.status -ne "PASS" -or [string]$releaseReport.source.kind -ne "release" -or [string]$releaseReport.source.commit -ne $ReleaseSourceSha -or [string]$releaseReport.package.sha256 -ne (Get-DDDAPlatformFileHash -Path $releasePackagePath)) {
    throw "Reconstructed release evidence není exact canonical PASS evidence."
}

[ordered]@{
    status = "PASS"
    version = $Version
    release_source_sha = $ReleaseSourceSha
    candidate_package_sha256 = $candidateHash
    release_package_path = $releasePackagePath
    release_package_sha256 = [string]$releaseReport.package.sha256
    release_report_json_path = $resultJson
    release_report_markdown_path = $resultMarkdown
} | ConvertTo-Json -Depth 10
