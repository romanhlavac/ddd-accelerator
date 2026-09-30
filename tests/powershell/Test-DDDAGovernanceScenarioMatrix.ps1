[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PlatformPath "scripts/platform/DDDAPlatformSupport.ps1")
. (Join-Path $PlatformPath "scripts/platform/DDDAGitHubSupport.ps1")
. (Join-Path $PlatformPath "scripts/platform/DDDAReleaseGovernanceSupport.ps1")

function Assert-True {
    param([bool]$Condition, [Parameter(Mandatory = $true)][string]$Message)
    if (-not $Condition) { throw $Message }
}

$matrixPath = Join-Path $PlatformPath "tests/fixtures/governance/scenario-matrix-v1.json"
$matrix = Get-Content -LiteralPath $matrixPath -Raw -Encoding UTF8 | ConvertFrom-Json
$script:checkPages = @()
$script:reviewComments = @()

function Invoke-DDDAGitHubApi {
    param([string]$Method, [string]$Path, [string]$Token)

    if ($Path -like "*/check-runs*") {
        $page = 1
        if ($Path -match '[?&]page=(?<page>\d+)') { $page = [int]$Matches.page }
        $runs = if ($page -le $script:checkPages.Count) { @($script:checkPages[$page - 1]) } else { @() }
        return @{ check_runs = $runs }
    }
    if ($Path -like "*/status") { return @{ statuses = @(); state = "success" } }
    if ($Path -like "*/issues/*/comments*") { return @($script:reviewComments) }
    throw "Unexpected mocked GitHub path: $Path"
}

foreach ($scenario in @($matrix.scenarios | Where-Object { $_.adapter -eq "check_runs" })) {
    $runs = [System.Collections.Generic.List[object]]::new()
    foreach ($page in @($scenario.input.pages)) {
        foreach ($run in @($page)) { $runs.Add($run) }
    }
    $inputPath = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-check-matrix-input-" + [guid]::NewGuid().ToString("N") + ".json")
    $outputPath = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-check-matrix-output-" + [guid]::NewGuid().ToString("N") + ".json")
    Write-DDDAPlatformJson -Path $inputPath -Depth 30 -Value @{ check_runs = @($runs); statuses = @() }
    try {
        $python = Get-DDDAPlatformPythonCommand
        try {
            Invoke-DDDAPlatformNative -Command $python -Arguments @(
                (Join-Path $PlatformPath "scripts/platform/Evaluate-DDDACheckRuns.py"),
                "--input", $inputPath,
                "--output", $outputPath
            ) | Out-Null
        }
        catch {
        }
        $result = Get-Content -LiteralPath $outputPath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    finally {
        Remove-Item -LiteralPath $inputPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $outputPath -Force -ErrorAction SilentlyContinue
    }
    $actual = [string]$result.status
    Assert-True -Condition ($actual -eq [string]$scenario.expected.status) -Message "Scenario '$($scenario.id)' expected $($scenario.expected.status), got $actual."
}

foreach ($scenario in @($matrix.scenarios | Where-Object { $_.adapter -eq "human_review_contract" })) {
    $script:reviewComments = @()
    for ($index = 0; $index -lt [int]$scenario.input.marker_count; $index++) {
        $record = [ordered]@{
            schema_version = 1
            kind = "implementation_pr_review"
            repository = "romanhlavac/ddd-accelerator"
            pr = 174
            reviewed_sha = ("a" * 40)
            candidate_package_sha256 = ("b" * 64)
            verdict = [string]$scenario.input.verdict
            reviewer = "romanhlavac"
            reviewed_at = "2026-09-01T09:00:00Z"
        }
        $json = $record | ConvertTo-Json -Depth 10
        $script:reviewComments += [pscustomobject]@{
            body = "<!-- ddda:human-pr-review:v1 -->`n``````json`n$json`n``````"
            user = [pscustomobject]@{ login = "romanhlavac"; type = "User" }
        }
    }

    $failureMessage = ""
    try {
        Get-DDDAHumanPrReviewEvidence `
            -RepositorySlug "romanhlavac/ddd-accelerator" `
            -Pr 174 `
            -HeadSha ("a" * 40) `
            -CandidatePackageSha256 ("b" * 64) `
            -Token "test-only" | Out-Null
    }
    catch {
        $failureMessage = $_.Exception.Message
    }
    $actual = if ([string]::IsNullOrWhiteSpace($failureMessage)) { "PASS" } else { "FAIL" }
    Assert-True -Condition ($actual -eq [string]$scenario.expected.status) -Message "Scenario '$($scenario.id)' expected $($scenario.expected.status), got $actual."
    foreach ($expectedCode in @($scenario.expected.failure_codes)) {
        Assert-True -Condition ($failureMessage -match [regex]::Escape([string]$expectedCode)) -Message "Scenario '$($scenario.id)' is missing failure '$expectedCode'."
    }
}

Write-Host "DDDA governance scenario matrix v1: PASS"
