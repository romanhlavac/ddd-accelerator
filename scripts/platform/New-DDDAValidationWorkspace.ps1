[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [Parameter(Mandatory = $true)][string]$WorkspaceRoot,
    [string]$ExamplePath = "examples/minimal",
    [switch]$NoInitialCommit,
    [switch]$NonInteractive,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")

$platformRoot = [System.IO.Path]::GetFullPath($PlatformPath).TrimEnd('\', '/')
if (-not (Test-Path -LiteralPath (Join-Path $platformRoot "ddda-package.json") -PathType Leaf)) {
    throw "Validation workspace musí být generován z rozbaleného DDDA package: $platformRoot"
}

$workspaceFull = [System.IO.Path]::GetFullPath($WorkspaceRoot)
if (Test-Path -LiteralPath $workspaceFull) {
    $existing = @(Get-ChildItem -LiteralPath $workspaceFull -Force -ErrorAction SilentlyContinue)
    if ($existing.Count -gt 0) {
        throw "Validation workspace musí být nový nebo prázdný: $workspaceFull"
    }
}
New-Item -ItemType Directory -Path $workspaceFull -Force | Out-Null

$ingestionScript = Join-Path $platformRoot "scripts/platform/Invoke-DDDAExampleIngestion.ps1"
$ingestionText = & $ingestionScript -PlatformPath $platformRoot -WorkspaceRoot $workspaceFull -ExamplePath $ExamplePath -Json | Out-String
if ([string]::IsNullOrWhiteSpace($ingestionText)) {
    throw "Manifest-driven ingestion nevrátil JSON."
}
$ingestion = $ingestionText.Trim() | ConvertFrom-Json
if ($ingestion.status -ne "PASS") {
    throw "Manifest-driven ingestion nevrátil PASS."
}

$intakeText = Get-Content -LiteralPath $ingestion.project_intake -Raw -Encoding UTF8
if ($intakeText -notmatch '(?m)^\s*project_id:\s*(?<id>[a-z0-9][a-z0-9-]{1,62})\s*$') {
    throw "Z project intake nelze určit project_id: $($ingestion.project_intake)"
}
$projectId = $Matches["id"]
$projectRoot = Join-Path (Join-Path $workspaceFull "projects") $projectId

$oldAuthorName = $env:GIT_AUTHOR_NAME
$oldAuthorEmail = $env:GIT_AUTHOR_EMAIL
$oldCommitterName = $env:GIT_COMMITTER_NAME
$oldCommitterEmail = $env:GIT_COMMITTER_EMAIL
$env:GIT_AUTHOR_NAME = "DDDA Validation"
$env:GIT_AUTHOR_EMAIL = "ddda-validation@example.invalid"
$env:GIT_COMMITTER_NAME = "DDDA Validation"
$env:GIT_COMMITTER_EMAIL = "ddda-validation@example.invalid"

try {
    $arguments = @(
        "-PlatformPath", $platformRoot,
        "-WorkspaceRoot", $workspaceFull,
        "-IntakeFile", [string]$ingestion.project_intake,
        "-NonInteractive"
    )
    if ($NoInitialCommit) {
        $arguments += "-NoInitialCommit"
    }
    Invoke-DDDAPlatformChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAProjectFirstRun.ps1") -Arguments $arguments
}
finally {
    if ($null -eq $oldAuthorName) { Remove-Item Env:\GIT_AUTHOR_NAME -ErrorAction SilentlyContinue } else { $env:GIT_AUTHOR_NAME = $oldAuthorName }
    if ($null -eq $oldAuthorEmail) { Remove-Item Env:\GIT_AUTHOR_EMAIL -ErrorAction SilentlyContinue } else { $env:GIT_AUTHOR_EMAIL = $oldAuthorEmail }
    if ($null -eq $oldCommitterName) { Remove-Item Env:\GIT_COMMITTER_NAME -ErrorAction SilentlyContinue } else { $env:GIT_COMMITTER_NAME = $oldCommitterName }
    if ($null -eq $oldCommitterEmail) { Remove-Item Env:\GIT_COMMITTER_EMAIL -ErrorAction SilentlyContinue } else { $env:GIT_COMMITTER_EMAIL = $oldCommitterEmail }
}

foreach ($required in @(
    "workspace.yaml",
    "DDDA.code-workspace",
    "reports/ingestion/ingestion-report.json",
    "projects/$projectId/project.yaml",
    "projects/$projectId/project-intake.yaml",
    "projects/$projectId/lifecycle-tailoring.yaml",
    "projects/$projectId/artifacts/status/current-status.yaml",
    "projects/$projectId/artifacts/status/next-actions.yaml",
    "projects/$projectId/reports/project-status.yaml"
)) {
    $path = Join-Path $workspaceFull $required
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Validation workspace neobsahuje povinný výstup: $required"
    }
}

$statusText = & (Join-Path $platformRoot "scripts/Get-DDDAProjectStatus.ps1") -PlatformPath $platformRoot -ProjectPath $projectRoot -Json | Out-String
if ([string]::IsNullOrWhiteSpace($statusText)) {
    throw "Read-only status validation nevrátila JSON."
}
$status = $statusText.Trim() | ConvertFrom-Json
if ($status.current_stage -ne "align" -or $status.next_gate -ne "G1") {
    throw "Validation workspace očekával align/G1, získal $($status.current_stage)/$($status.next_gate)."
}

$result = [ordered]@{
    status = "PASS"
    workspace = $workspaceFull
    project_id = $projectId
    project = $projectRoot
    current_stage = [string]$status.current_stage
    next_gate = [string]$status.next_gate
    ingestion_report = [string]$ingestion.report_json
}

if ($Json) {
    $result | ConvertTo-Json -Depth 10
}
else {
    Write-Host "DDDA validation workspace: PASS"
    Write-Host "Workspace: $workspaceFull"
    Write-Host "Project:   $projectRoot"
    Write-Host "Stage:     $($result.current_stage)"
    Write-Host "Next gate: $($result.next_gate)"
}
