[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
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
$parsed = ConvertFrom-DDDAHrdrComment -Comment ([pscustomobject]@{ body = $body })
Assert-True -Condition ([string]$parsed.decision -eq "pending") -Message "Publikovaný HRDR scaffold musí být zpětně parsovatelný."

Write-Host "DDDA HRDR comment contract: PASS"
