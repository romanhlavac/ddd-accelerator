[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PlatformPath "scripts/platform/DDDAPlatformSupport.ps1")
. (Join-Path $PlatformPath "scripts/platform/DDDAReleaseGovernanceSupport.ps1")

function Assert-True {
    param([Parameter(Mandatory = $true)][bool]$Condition, [Parameter(Mandatory = $true)][string]$Message)
    if (-not $Condition) { throw $Message }
}

$record = [pscustomobject]@{
    schema_version = 1
    repository = "romanhlavac/ddd-accelerator"
    pr = 103
    source_sha = ("a" * 40)
    candidate_package_sha256 = ("b" * 64)
    version = "0.1.1"
    reviewer = "romanhlavac"
    decision_owner = "romanhlavac"
    decision = "pending"
    decided_at = $null
    scope_issues = @(9, 12, 67, 68, 70, 96, 98)
    findings = @()
    accepted_risks = @()
}

$body = Format-DDDAHrdrComment -Record $record
Assert-True -Condition ($body -match '(?s)```json\s*\{.*?"decision"\s*:\s*"pending".*?\}\s*```') -Message "HRDR scaffold musí obsahovat literal fenced JSON."

function Invoke-DDDAGitHubApi {
    param([string]$Method, [string]$Path, [string]$Token, [object]$Body)
    if ($Method -eq "GET" -and $Path -match '/comments\?') {
        return @([pscustomobject]@{
            id = 42
            user = [pscustomobject]@{ login = "github-actions[bot]"; type = "Bot" }
            body = $body
        })
    }
    throw "Unexpected test API call: $Method $Path"
}

$evidence = Get-DDDAHrdrEvidence `
    -RepositorySlug "romanhlavac/ddd-accelerator" `
    -Pr 103 `
    -Token "test-token"
Assert-True -Condition ([string]$evidence.status -eq "PASS") -Message "Publikovaný HRDR scaffold musí projít shared adapterem."
Assert-True -Condition ([string]$evidence.record.decision -eq "pending") -Message "Shared adapter musí vrátit pending HRDR scaffold."
Assert-True -Condition ([int64]$evidence.comment_id -eq 42) -Message "Shared adapter musí zachovat authoritative comment id."

Write-Host "DDDA HRDR comment contract: PASS"
