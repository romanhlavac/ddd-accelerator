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
    [string]$PackageArtifactName,
    [string]$WorkflowRunId,
    [string]$Workspace,
    [string]$MiroBoardId,
    [string]$MiroEvidencePath,
    [string[]]$RedactedRoots = @(),
    [Parameter(Mandatory = $true)][string]$SuitesJsonPath,
    [Parameter(Mandatory = $true)][string]$OutputRoot,
    [string[]]$Diagnostics = @(),
    [datetime]$StartedAt = (Get-Date).ToUniversalTime(),
    [datetime]$CompletedAt = (Get-Date).ToUniversalTime(),
    [switch]$PortablePaths,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAMiroEvidenceSupport.ps1")

if ($Commit -notmatch '^[0-9a-f]{40}$') {
    throw "Validation report vyžaduje plný Git commit SHA."
}

$workspaceFull = if ([string]::IsNullOrWhiteSpace($Workspace)) { $null } else { [System.IO.Path]::GetFullPath($Workspace) }
$packageFull = $null
$packageRecord = $null
if (-not [string]::IsNullOrWhiteSpace($PackagePath)) {
    $packageFull = (Resolve-Path -LiteralPath $PackagePath).Path
    $packageRecord = [ordered]@{
        path = if ($PortablePaths) { Split-Path -Leaf $packageFull } else { $packageFull }
        sha256 = Get-DDDAPlatformFileHash -Path $packageFull
        artifact_name = if ([string]::IsNullOrWhiteSpace($PackageArtifactName)) { $null } else { $PackageArtifactName }
        workflow_run_id = if ([string]::IsNullOrWhiteSpace($WorkflowRunId)) { $null } else { $WorkflowRunId }
    }
}

function ConvertTo-DDDAPortableEvidenceText {
    param([AllowNull()][string]$Value)

    if ($null -eq $Value -or -not $PortablePaths) { return $Value }
    $portable = $Value
    if (-not [string]::IsNullOrWhiteSpace($workspaceFull)) {
        $portable = $portable.Replace($workspaceFull, ("validation/" + $ValidationId))
        $portable = $portable.Replace($workspaceFull.Replace('\', '\\'), ("validation/" + $ValidationId))
        $portable = $portable.Replace($workspaceFull.Replace('\', '/'), ("validation/" + $ValidationId))
    }
    if (-not [string]::IsNullOrWhiteSpace($packageFull)) {
        $portable = $portable.Replace($packageFull, (Split-Path -Leaf $packageFull))
        $portable = $portable.Replace($packageFull.Replace('\', '\\'), (Split-Path -Leaf $packageFull))
        $portable = $portable.Replace($packageFull.Replace('\', '/'), (Split-Path -Leaf $packageFull))
    }
    foreach ($root in @($RedactedRoots)) {
        if (-not [string]::IsNullOrWhiteSpace([string]$root)) {
            $rootFull = [System.IO.Path]::GetFullPath([string]$root)
            $portable = $portable.Replace($rootFull, '[redacted-root]')
            $portable = $portable.Replace($rootFull.Replace('\', '\\'), '[redacted-root]')
            $portable = $portable.Replace($rootFull.Replace('\', '/'), '[redacted-root]')
        }
    }
    return $portable
}
if ([string]::IsNullOrWhiteSpace($PackagePath) -and $Status -eq "PASS") {
    throw "PASS validation report vyžaduje existující package."
}

$suitesFull = (Resolve-Path -LiteralPath $SuitesJsonPath).Path
$suitesText = Get-Content -LiteralPath $suitesFull -Raw -Encoding UTF8
$suiteList = [System.Collections.Generic.List[object]]::new()
if (-not [string]::IsNullOrWhiteSpace($suitesText)) {
    $parsedSuites = $suitesText | ConvertFrom-Json
    foreach ($suite in @($parsedSuites)) {
        if ($null -ne $suite) {
            $suiteList.Add([pscustomobject][ordered]@{
                name = [string]$suite.name
                status = [string]$suite.status
                duration_ms = [int64]$suite.duration_ms
                details = ConvertTo-DDDAPortableEvidenceText -Value ([string]$suite.details)
            })
        }
    }
}
$suites = [object[]]$suiteList.ToArray()

if ($Status -eq "PASS" -and $suites.Count -eq 0) {
    throw "PASS validation report vyžaduje alespoň jednu suite."
}

if (-not [string]::IsNullOrWhiteSpace($MiroEvidencePath)) {
    $miroEvidence = Import-DDDAMiroEvidence -Path $MiroEvidencePath
}
elseif (-not [string]::IsNullOrWhiteSpace($MiroBoardId)) {
    $miroEvidence = New-DDDALegacyMiroEvidence -BoardId $MiroBoardId -Workspace $Workspace
}
else {
    $miroEvidence = New-DDDANotRunMiroEvidence -Workspace $Workspace
}
$miroEvidenceJson = $miroEvidence | ConvertTo-Json -Depth 50 -Compress
$miroEvidence = (ConvertTo-DDDAPortableEvidenceText -Value $miroEvidenceJson) | ConvertFrom-Json
$null = Assert-DDDAMiroEvidenceContract -Evidence $miroEvidence
if ($Status -eq "PASS" -and [string]$miroEvidence.status -eq "FAIL") {
    throw "PASS validation report nesmí obsahovat FAIL Miro evidence."
}

$outputFull = [System.IO.Path]::GetFullPath($OutputRoot)
New-Item -ItemType Directory -Path $outputFull -Force | Out-Null
$jsonPath = Join-Path $outputFull "result.json"
$markdownPath = Join-Path $outputFull "result.md"
$workspaceReference = if ([string]::IsNullOrWhiteSpace($Workspace)) { $null } elseif ($PortablePaths) { "validation/$ValidationId" } else { $workspaceFull }

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
    workspace = $workspaceReference
    miro_board_id = $miroEvidence.board_id
    miro = $miroEvidence
    suites = $suites
    diagnostics = [string[]]@($Diagnostics | ForEach-Object { ConvertTo-DDDAPortableEvidenceText -Value ([string]$_) })
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
    $markdown.Add("- Package: ``$($packageRecord.path)``")
    $markdown.Add("- Package SHA-256: ``$($packageRecord.sha256)``")
    if (-not [string]::IsNullOrWhiteSpace([string]$packageRecord.artifact_name)) {
        $markdown.Add("- Package artifact: ``$($packageRecord.artifact_name)``")
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$packageRecord.workflow_run_id)) {
        $markdown.Add("- Workflow run: ``$($packageRecord.workflow_run_id)``")
    }
}
else {
    $markdown.Add("- Package: not created")
}
if (-not [string]::IsNullOrWhiteSpace($Workspace)) {
    $markdown.Add("- Workspace: ``$workspaceReference``")
}

$markdown.Add("")
$markdown.Add("## Miro evidence")
$markdown.Add("")
$markdown.Add("- Status: **$($miroEvidence.status)**")
if (-not [string]::IsNullOrWhiteSpace([string]$miroEvidence.board_id)) {
    $markdown.Add("- Board ID: ``$($miroEvidence.board_id)``")
    $markdown.Add("- Board URL: $($miroEvidence.board_url)")
}
else {
    $markdown.Add("- Board: not created")
}
if (-not [string]::IsNullOrWhiteSpace([string]$miroEvidence.workspace)) {
    $markdown.Add("- Acceptance workspace: ``$($miroEvidence.workspace)``")
}
$markdown.Add("- Mapping: **$($miroEvidence.mapping.status)**; verified artifacts: $($miroEvidence.mapping.verified_count)")
$markdown.Add("- Sync state: **$($miroEvidence.sync_state.status)**; verified artifacts: $($miroEvidence.sync_state.verified_count)")
$markdown.Add("- Idempotence: **$($miroEvidence.idempotence.status)**; second-run create-board operations: $($miroEvidence.idempotence.second_run_create_board_operations); mutating operations: $($miroEvidence.idempotence.second_run_mutating_operations)")
$markdown.Add("- Cleanup: **$($miroEvidence.cleanup.state)**")
if (-not [string]::IsNullOrWhiteSpace([string]$miroEvidence.cleanup.completed_at)) {
    $markdown.Add("- Cleanup completed at: ``$($miroEvidence.cleanup.completed_at)``")
}
if (@($miroEvidence.managed_artifacts).Count -gt 0) {
    $markdown.Add("- Managed artifacts: ``$(@($miroEvidence.managed_artifacts) -join '`, `')``")
}
if (-not [string]::IsNullOrWhiteSpace([string]$miroEvidence.cleanup.error)) {
    $markdown.Add("- Cleanup error: $($miroEvidence.cleanup.error)")
}

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

if (@($report.diagnostics).Count -gt 0) {
    $markdown.Add("")
    $markdown.Add("## Diagnostics")
    $markdown.Add("")
    foreach ($diagnostic in @($report.diagnostics)) {
        $markdown.Add("- ``$diagnostic``")
    }
}
Write-DDDAPlatformText -Value (($markdown -join [Environment]::NewLine) + [Environment]::NewLine) -Path $markdownPath

$result = [ordered]@{
    status = $Status
    json = $jsonPath
    markdown = $markdownPath
    package_sha256 = if ($null -eq $packageRecord) { $null } else { $packageRecord.sha256 }
    miro_status = [string]$miroEvidence.status
    miro_cleanup_state = [string]$miroEvidence.cleanup.state
}
if ($Json) {
    $result | ConvertTo-Json -Depth 10
}
else {
    Write-Host "DDDA validation report: $Status"
    Write-Host "JSON: $jsonPath"
    Write-Host "Markdown: $markdownPath"
}
