[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ValidationId,
    [Parameter(Mandatory = $true)][ValidateSet("PASS", "FAIL")][string]$Status,
    [Parameter(Mandatory = $true)][ValidateSet("pr", "release", "working-tree")][string]$SourceKind,
    [Parameter(Mandatory = $true)][string]$Repository,
    [Parameter(Mandatory = $true)][string]$Commit,
    [int]$Pr,
    [string]$Branch,
    [string]$PackagePath,
    [string]$Workspace,
    [string]$MiroBoardId,
    [Parameter(Mandatory = $true)][string]$SuitesJsonPath,
    [Parameter(Mandatory = $true)][string]$OutputRoot,
    [string[]]$Diagnostics = @(),
    [datetime]$StartedAt = (Get-Date).ToUniversalTime(),
    [datetime]$CompletedAt = (Get-Date).ToUniversalTime(),
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")

if ($Commit -notmatch '^[0-9a-f]{40}$') {
    throw "Validation report vyžaduje plný Git commit SHA."
}

$packageFull = $null
$packageRecord = $null
if (-not [string]::IsNullOrWhiteSpace($PackagePath)) {
    $packageFull = (Resolve-Path -LiteralPath $PackagePath).Path
    $packageRecord = [ordered]@{
        path = $packageFull
        sha256 = Get-DDDAPlatformFileHash -Path $packageFull
    }
}
elseif ($Status -eq "PASS") {
    throw "PASS validation report vyžaduje existující package."
}

$suitesFull = (Resolve-Path -LiteralPath $SuitesJsonPath).Path
$suitesText = Get-Content -LiteralPath $suitesFull -Raw -Encoding UTF8
$suiteList = [System.Collections.Generic.List[object]]::new()
if (-not [string]::IsNullOrWhiteSpace($suitesText)) {
    $parsedSuites = $suitesText | ConvertFrom-Json
    foreach ($suite in @($parsedSuites)) {
        if ($null -ne $suite) {
            $suiteList.Add($suite)
        }
    }
}
$suites = [object[]]$suiteList.ToArray()

if ($Status -eq "PASS" -and $suites.Count -eq 0) {
    throw "PASS validation report vyžaduje alespoň jednu suite."
}

$outputFull = [System.IO.Path]::GetFullPath($OutputRoot)
New-Item -ItemType Directory -Path $outputFull -Force | Out-Null
$jsonPath = Join-Path $outputFull "result.json"
$markdownPath = Join-Path $outputFull "result.md"

$source = [ordered]@{
    kind = $SourceKind
    repository = $Repository
    pr = if ($Pr -gt 0) { $Pr } else { $null }
    branch = if ([string]::IsNullOrWhiteSpace($Branch)) { $null } else { $Branch }
    commit = $Commit
}

$report = [pscustomobject][ordered]@{
    schema_version = 1
    validation_id = $ValidationId
    status = $Status
    started_at = $StartedAt.ToUniversalTime().ToString("o")
    completed_at = $CompletedAt.ToUniversalTime().ToString("o")
    source = $source
    package = $packageRecord
    workspace = if ([string]::IsNullOrWhiteSpace($Workspace)) { $null } else { [System.IO.Path]::GetFullPath($Workspace) }
    miro_board_id = if ([string]::IsNullOrWhiteSpace($MiroBoardId)) { $null } else { $MiroBoardId }
    suites = $suites
    diagnostics = [string[]]@($Diagnostics)
}
Write-DDDAPlatformJson -Value $report -Path $jsonPath

$jsonText = Get-Content -LiteralPath $jsonPath -Raw -Encoding UTF8
if ($suites.Count -eq 0 -and $jsonText -notmatch '"suites"\s*:\s*\[\s*\]') {
    throw "Validation report nezapsal prázdné suites jako JSON pole."
}

$markdown = [System.Collections.Generic.List[string]]::new()
$markdown.Add("# DDDA validation report")
$markdown.Add("")
$markdown.Add("- Status: **$Status**")
$markdown.Add("- Validation ID: ``$ValidationId``")
$markdown.Add("- Source: ``$SourceKind``")
$markdown.Add("- Repository: ``$Repository``")
if ($Pr -gt 0) { $markdown.Add("- PR: ``$Pr``") }
if (-not [string]::IsNullOrWhiteSpace($Branch)) { $markdown.Add("- Branch: ``$Branch``") }
$markdown.Add("- Commit: ``$Commit``")
if ($null -ne $packageRecord) {
    $markdown.Add("- Package: ``$packageFull``")
    $markdown.Add("- Package SHA-256: ``$($packageRecord.sha256)``")
}
else {
    $markdown.Add("- Package: not created")
}
if (-not [string]::IsNullOrWhiteSpace($Workspace)) { $markdown.Add("- Workspace: ``$Workspace``") }
if (-not [string]::IsNullOrWhiteSpace($MiroBoardId)) { $markdown.Add("- Miro board ID: ``$MiroBoardId``") }
$markdown.Add("")
$markdown.Add("## Suites")
$markdown.Add("")
if ($suites.Count -eq 0) {
    $markdown.Add("No suite started before the validation failed.")
}
else {
    $markdown.Add("| Suite | Status | Duration (ms) | Details |")
    $markdown.Add("|---|---|---:|---|")
    foreach ($suite in $suites) {
        $details = [string]$suite.details
        $details = $details.Replace("|", "\|").Replace("`r", " ").Replace("`n", " ")
        $markdown.Add("| $($suite.name) | $($suite.status) | $($suite.duration_ms) | $details |")
    }
}

if (@($Diagnostics).Count -gt 0) {
    $markdown.Add("")
    $markdown.Add("## Diagnostics")
    $markdown.Add("")
    foreach ($diagnostic in $Diagnostics) {
        $markdown.Add("- ``$diagnostic``")
    }
}
Write-DDDAPlatformText -Value (($markdown -join [Environment]::NewLine) + [Environment]::NewLine) -Path $markdownPath

$result = [ordered]@{
    status = $Status
    json = $jsonPath
    markdown = $markdownPath
    package_sha256 = if ($null -eq $packageRecord) { $null } else { $packageRecord.sha256 }
}
if ($Json) {
    $result | ConvertTo-Json -Depth 10
}
else {
    Write-Host "DDDA validation report: $Status"
    Write-Host "JSON: $jsonPath"
    Write-Host "Markdown: $markdownPath"
}
