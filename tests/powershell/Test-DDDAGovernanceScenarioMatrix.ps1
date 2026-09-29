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
    $script:checkPages = @($scenario.input.pages | ForEach-Object { ,@($_) })

    # Production pagination advances only after a full GitHub page. Keep the
    # fixture compact while exercising the real second-page behavior.
    if ([string]$scenario.dimensions.actions -eq "paginated") {
        $first = [System.Collections.Generic.List[object]]::new()
        foreach ($run in @($script:checkPages[0])) { $first.Add($run) }
        for ($index = $first.Count; $index -lt 100; $index++) {
            $first.Add([pscustomobject]@{
                name = "pagination-padding-$index"
                id = 10000 + $index
                started_at = "2026-09-01T07:00:00Z"
                status = "completed"
                conclusion = "success"
            })
        }
        $script:checkPages[0] = @($first)
    }

    $passed = $true
    try {
        Assert-DDDAGitHubChecksPassed `
            -RepositorySlug "romanhlavac/ddd-accelerator" `
            -Commit ("a" * 40) `
            -Token "test-only" | Out-Null
    }
    catch {
        $passed = $false
    }
    $actual = if ($passed) { "PASS" } else { "FAIL" }
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
