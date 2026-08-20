[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [Parameter(Mandatory = $true)][string]$Repository,
    [Parameter(Mandatory = $true)][string]$Actor,
    [Parameter(Mandatory = $true)][ValidateRange(1, 2147483647)][int]$Pr,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-f]{40}$')][string]$HeadSha,
    [Parameter(Mandatory = $true)][string]$HeadRepository,
    [Parameter(Mandatory = $true)][string]$CommandText,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$policyPath = Join-Path (Resolve-Path -LiteralPath $PlatformPath).Path "config/platform/development-policy.yaml"
$policy = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$remote = $policy.remote_execution
if ($null -eq $remote -or -not [bool]$remote.enabled) {
    throw "Remote execution is disabled by platform policy."
}
if ([string]$Actor -notin @($remote.allowed_actors | ForEach-Object { [string]$_ })) {
    throw "Actor '$Actor' is not allowed to request remote DDDA execution."
}
if ([bool]$remote.same_repository_only -and $HeadRepository -ne $Repository) {
    throw "Remote execution is allowed only for same-repository pull requests."
}

$miroTeamId = ""
if ($remote.PSObject.Properties.Name -contains "miro_team_id") {
    $miroTeamId = [string]$remote.miro_team_id
}

$normalized = $CommandText.Trim()
$result = [ordered]@{
    status = "PASS"
    repository = $Repository
    actor = $Actor
    pr = $Pr
    head_sha = $HeadSha
    head_repository = $HeadRepository
    action = $null
    remediation_script = $null
    miro_team_id = $miroTeamId
    keep_review_board = $true
    merge_allowed = $false
    promotion_allowed = $false
    release_allowed = $false
}

if ($normalized -in @($remote.allowed_validate_commands | ForEach-Object { [string]$_ })) {
    $result.action = "validate-pr"
}
elseif ($normalized -match '^/ddda remediate\s+(?<path>scripts/remediation/[A-Za-z0-9._/-]+\.ps1)\s+--expected-sha\s+(?<sha>[0-9a-f]{40})$') {
    if (-not [bool]$remote.remediation.enabled) {
        throw "Remote remediation is disabled by platform policy."
    }
    if ([string]$Matches["sha"] -ne $HeadSha) {
        throw "Remediation expected SHA does not match the current PR head."
    }
    $scriptPath = [string]$Matches["path"]
    $prefix = [string]$remote.remediation.allowed_path_prefix
    if (-not $scriptPath.StartsWith($prefix, [System.StringComparison]::Ordinal)) {
        throw "Remediation script is outside the allowed path prefix."
    }
    $fullScriptPath = [System.IO.Path]::GetFullPath((Join-Path (Resolve-Path -LiteralPath $PlatformPath).Path $scriptPath))
    $allowedRoot = [System.IO.Path]::GetFullPath((Join-Path (Resolve-Path -LiteralPath $PlatformPath).Path $prefix))
    if (-not $fullScriptPath.StartsWith($allowedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Remediation script escapes the allowed root."
    }
    # Existence is intentionally not checked on the trusted default-branch checkout.
    # The workflow checks the path after checkout of the authorized exact PR head.
    $result.action = "remediate"
    $result.remediation_script = $scriptPath
}
else {
    throw "Unsupported remote DDDA command."
}

if ($Json) {
    $result | ConvertTo-Json -Depth 20
}
else {
    Write-Host "DDDA remote execution request: PASS"
    Write-Host "Action: $($result.action)"
    Write-Host "PR: $Pr"
    Write-Host "SHA: $HeadSha"
}
