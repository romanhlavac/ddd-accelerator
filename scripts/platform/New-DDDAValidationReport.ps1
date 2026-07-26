[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ValidationId,
    [Parameter(Mandatory = $true)][ValidateSet("PASS", "FAIL")][string]$Status,
    [Parameter(Mandatory = $true)][ValidateSet("pr", "release", "working-tree")][string]$SourceKind,
    [Parameter(Mandatory = $true)][string]$Repository,
    [Parameter(Mandatory = $true)][string]$Commit,
    [int]$Pr,
    [string]$Branch,
    [Parameter(Mandatory = $true)][string]$PackagePath,
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
$packageFull = (Resolve-Path -LiteralPath $PackagePath).Path
$suitesFull = (Resolve-Path -LiteralPath $SuitesJsonPath).Path
$suitesDocument = Get-Content -LiteralPath $suitesFull -Raw -Encoding UTF8 | ConvertFrom-Json
$suites = @($suitesDocument)
if ($suites.Count -eq 0) {
    throw "Validation report vyžaduje alespoň jednu suite."
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

$report = [ordered]@{
    schema_version = 1
    validation_id = $ValidationId
    status = $Status
    started_at = $StartedAt.ToUniversalTime().ToString("o")
    completed_at = $CompletedAt.ToUniversalTime().ToString("o")
    source = $source
    package = [ordered]@{
        path = $packageFull
        sha256 = Get-DDDAPlatformFileHash -Path $packageFull
    }
    workspace = if ([string]::IsNullOrWhiteSpace($Workspace)) { $null } else { [System.IO.Path]::GetFullPath($Workspace) }
    miro_board_id = if ([string]::IsNullOrWhiteSpace($MiroBoardId)) { $null } else { $MiroBoardId }
    suites = $suites
    diagnostics = @($Diagnostics)
}
Write-DDDAPlatformJson -Value $report -Path $jsonPath

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
$markdown.Add("- Package: ``$packageFull``")
$markdown.Add("- Package SHA-256: ``$($report.package.sha256)``")
if (-not [string]::IsNullOrWhiteSpace($Workspace)) { $markdown.Add("- Workspace: ``$Workspace``") }
if (-not [string]::IsNullOrWhiteSpace($MiroBoardId)) { $markdown.Add("- Miro board ID: ``$MiroBoardId``") }
$markdown.Add("")
$markdown.Add("## Suites")
$markdown.Add("")
$markdown.Add("| Suite | Status | Duration (ms) | Details |")
$markdown.Add("|---|---|---:|---|")
foreach ($suite in $suites) {
    $details = [string]$suite.details
    $details = $details.Replace("|", "\|").Replace("`r", " ").Replace("`n", " ")
    $markdown.Add("| $($suite.name) | $($suite.status) | $($suite.duration_ms) | $details |")
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
    package_sha256 = $report.package.sha256
}
if ($Json) {
    $result | ConvertTo-Json -Depth 10
}
else {
    Write-Host "DDDA validation report: $Status"
    Write-Host "JSON: $jsonPath"
    Write-Host "Markdown: $markdownPath"
}
