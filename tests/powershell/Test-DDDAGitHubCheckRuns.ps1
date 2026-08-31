[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PlatformPath "scripts/platform/DDDAGitHubSupport.ps1")

function Assert-True {
    param([bool]$Condition, [Parameter(Mandatory = $true)][string]$Message)
    if (-not $Condition) { throw $Message }
}
function Assert-Throws {
    param([Parameter(Mandatory = $true)][scriptblock]$Action, [Parameter(Mandatory = $true)][string]$Message)
    $thrown = $false
    try { & $Action } catch { $thrown = $true }
    if (-not $thrown) { throw $Message }
}

$script:checkRuns = @(
    [pscustomobject]@{ name = "reconcile"; id = 101; started_at = "2026-08-31T08:00:00Z"; status = "completed"; conclusion = "failure" },
    [pscustomobject]@{ name = "reconcile"; id = 102; started_at = "2026-08-31T08:05:00Z"; status = "completed"; conclusion = "success" },
    [pscustomobject]@{ name = "Platform validation"; id = 103; started_at = "2026-08-31T08:06:00Z"; status = "completed"; conclusion = "success" }
)

$latest = @(Get-DDDALatestCheckRunsByName -CheckRuns $script:checkRuns)
Assert-True -Condition ($latest.Count -eq 2) -Message "Exactly one newest check run per name must be evaluated."
$reconcile = @($latest | Where-Object { $_.name -eq "reconcile" })
Assert-True -Condition ($reconcile.Count -eq 1 -and [Int64]$reconcile[0].id -eq 102) -Message "A newer successful retry must supersede the historical failed attempt."

function Invoke-DDDAGitHubApi {
    param([string]$Method, [string]$Path, [string]$Token)
    if ($Path -like "*/check-runs*") { return @{ check_runs = $script:checkRuns } }
    if ($Path -like "*/status") { return @{ statuses = @(); state = "success" } }
    throw "Unexpected mocked GitHub path: $Path"
}

$result = Assert-DDDAGitHubChecksPassed -RepositorySlug "romanhlavac/ddd-accelerator" -Commit ("a" * 40) -Token "test"
Assert-True -Condition ($result.CheckRunCount -eq 3 -and $result.EvaluatedCheckRunCount -eq 2) -Message "Check evidence must retain observed and evaluated counts."

$script:checkRuns[1].conclusion = "failure"
Assert-Throws -Action {
    Assert-DDDAGitHubChecksPassed -RepositorySlug "romanhlavac/ddd-accelerator" -Commit ("a" * 40) -Token "test" | Out-Null
} -Message "The newest failed retry must block the governed gate."

Write-Host "DDDA GitHub check-run aggregation contract: PASS"
