[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PlatformPath "scripts/platform/DDDAPlatformSupport.ps1")
. (Join-Path $PlatformPath "scripts/platform/DDDAGitHubSupport.ps1")

function Assert-True {
    param([bool]$Condition, [Parameter(Mandatory = $true)][string]$Message)
    if (-not $Condition) { throw $Message }
}
$support = Get-Content -LiteralPath (Join-Path $PlatformPath "scripts/platform/DDDAGitHubSupport.ps1") -Raw -Encoding UTF8
Assert-True -Condition ($support -match 'Evaluate-DDDACheckRuns\.py') -Message "GitHub support nepoužívá shared mandatory-check adapter."
Assert-True -Condition ($support -notmatch 'Get-DDDALatestCheckRunsByName|allowedConclusions') -Message "GitHub support stále vlastní duplicate latest-run nebo conclusion semantics."

Write-Host "DDDA GitHub check-run aggregation contract: PASS"
