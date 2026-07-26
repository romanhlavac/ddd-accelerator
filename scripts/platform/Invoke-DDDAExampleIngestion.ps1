[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [Parameter(Mandatory = $true)][string]$WorkspaceRoot,
    [string]$ExamplePath = "examples/minimal",
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")

$platformRoot = [System.IO.Path]::GetFullPath($PlatformPath).TrimEnd('\', '/')
if (-not (Test-Path -LiteralPath $platformRoot -PathType Container)) {
    throw "PlatformPath neexistuje: $platformRoot"
}

$exampleRoot = if ([System.IO.Path]::IsPathRooted($ExamplePath)) {
    [System.IO.Path]::GetFullPath($ExamplePath)
}
else {
    [System.IO.Path]::GetFullPath((Join-Path $platformRoot $ExamplePath))
}
$null = Assert-DDDAPlatformPathWithin -CandidatePath (Join-Path $exampleRoot "manifest.yaml") -AllowedRoot $platformRoot -Label "Example manifest"

$manifestPath = Join-Path $exampleRoot "manifest.yaml"
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Example manifest neexistuje: $manifestPath"
}

$manifestText = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8
try {
    $document = $manifestText | ConvertFrom-Json
}
catch {
    throw "Example manifest musí být JSON-compatible YAML: $manifestPath`n$($_.Exception.Message)"
}

$manifest = $document.manifest
if ($null -eq $manifest -or $manifest.schema_version -ne 1) {
    throw "Example manifest má neplatný nebo nepodporovaný kontrakt."
}

$workspaceFull = [System.IO.Path]::GetFullPath($WorkspaceRoot)
New-Item -ItemType Directory -Path $workspaceFull -Force | Out-Null
$reportRoot = Join-Path $workspaceFull "reports/ingestion"
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null

$items = [System.Collections.Generic.List[object]]::new()
foreach ($file in @($manifest.files)) {
    $source = [System.IO.Path]::GetFullPath((Join-Path $exampleRoot ([string]$file.source)))
    $target = [System.IO.Path]::GetFullPath((Join-Path $workspaceFull ([string]$file.target)))

    $null = Assert-DDDAPlatformPathWithin -CandidatePath $source -AllowedRoot $exampleRoot -Label "Ingestion source"
    $null = Assert-DDDAPlatformPathWithin -CandidatePath $target -AllowedRoot $workspaceFull -Label "Ingestion target"

    $required = $true
    if ($file.PSObject.Properties["required"]) {
        $required = [bool]$file.required
    }

    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        if ($required) {
            throw "Povinný example input neexistuje: $source"
        }
        $items.Add([ordered]@{
            source = [string]$file.source
            target = [string]$file.target
            role = [string]$file.role
            status = "SKIP"
            sha256 = $null
        })
        continue
    }

    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $target -Force
    $sourceHash = Get-DDDAPlatformFileHash -Path $source
    $targetHash = Get-DDDAPlatformFileHash -Path $target
    if ($sourceHash -ne $targetHash) {
        throw "Hash ingestion targetu neodpovídá source: $target"
    }

    $items.Add([ordered]@{
        source = [string]$file.source
        target = [string]$file.target
        role = [string]$file.role
        status = "INGESTED"
        sha256 = $targetHash
    })
}

$intakeSource = [System.IO.Path]::GetFullPath((Join-Path $exampleRoot ([string]$manifest.project_intake)))
$null = Assert-DDDAPlatformPathWithin -CandidatePath $intakeSource -AllowedRoot $exampleRoot -Label "Project intake"
if (-not (Test-Path -LiteralPath $intakeSource -PathType Leaf)) {
    throw "Project intake uvedený v manifestu neexistuje: $intakeSource"
}

$intakeItem = @($manifest.files | Where-Object { [string]$_.source -eq [string]$manifest.project_intake } | Select-Object -First 1)
if ($intakeItem.Count -ne 1) {
    throw "Manifest musí obsahovat právě jeden files záznam pro project_intake."
}
$intakeTarget = [System.IO.Path]::GetFullPath((Join-Path $workspaceFull ([string]$intakeItem[0].target)))

$report = [ordered]@{
    schema_version = 1
    example_id = [string]$manifest.example_id
    manifest = $manifestPath
    workspace = $workspaceFull
    created_at = Get-DDDAPlatformIsoTimestamp
    project_intake = $intakeTarget
    status = "PASS"
    files = @($items)
}
$reportJson = Join-Path $reportRoot "ingestion-report.json"
$reportMarkdown = Join-Path $reportRoot "ingestion-report.md"
Write-DDDAPlatformJson -Value $report -Path $reportJson

$markdown = @(
    "# DDDA example ingestion report",
    "",
    "- Status: **PASS**",
    "- Example: `$($manifest.example_id)`",
    "- Workspace: `$workspaceFull`",
    "- Manifest: `$manifestPath`",
    "- Project intake: `$intakeTarget`",
    "",
    "| Role | Source | Target | Status | SHA-256 |",
    "|---|---|---|---|---|"
)
foreach ($item in $items) {
    $markdown += "| $($item.role) | `$($item.source)` | `$($item.target)` | $($item.status) | `$($item.sha256)` |"
}
Write-DDDAPlatformText -Value (($markdown -join [Environment]::NewLine) + [Environment]::NewLine) -Path $reportMarkdown

$result = [ordered]@{
    status = "PASS"
    example_id = [string]$manifest.example_id
    workspace = $workspaceFull
    project_intake = $intakeTarget
    report_json = $reportJson
    report_markdown = $reportMarkdown
}

if ($Json) {
    $result | ConvertTo-Json -Depth 10
}
else {
    Write-Host "DDDA example ingestion: PASS"
    Write-Host "Project intake: $intakeTarget"
    Write-Host "Report: $reportJson"
}
