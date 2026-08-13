[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$WorkspaceRoot,
    [switch]$WithMiro,
    [switch]$Full,
    [switch]$ResetToken,
    [switch]$KeepArtifacts,
    [switch]$CleanupOnFailure,
    [switch]$ForceRecreateRuntime,
    [switch]$NonInteractive,
    [switch]$NoInitialCommit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {
}

. (Join-Path $PSScriptRoot "private/DDDAMiroSupport.ps1")

function Resolve-DDDAFirstRunWorkspaceRoot {
    param(
        [Parameter(Mandatory = $true)][string]$PlatformRoot,
        [string]$RequestedWorkspaceRoot
    )

    if (-not [string]::IsNullOrWhiteSpace($RequestedWorkspaceRoot)) {
        return [System.IO.Path]::GetFullPath($RequestedWorkspaceRoot)
    }

    $platformParent = Split-Path -Parent $PlatformRoot
    if ((Split-Path -Leaf $platformParent) -ieq "platform") {
        return [System.IO.Path]::GetFullPath((Split-Path -Parent $platformParent))
    }

    return [System.IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $PlatformRoot) "DDDA-Workspace"))
}

$platformRoot = (Resolve-Path $PlatformPath).Path
$workspaceFull = Resolve-DDDAFirstRunWorkspaceRoot -PlatformRoot $platformRoot -RequestedWorkspaceRoot $WorkspaceRoot
$projectId = "life-insurance-greenfield"
$projectRoot = Join-Path (Join-Path $workspaceFull "projects") $projectId
$workspaceFile = Join-Path $workspaceFull "workspace.yaml"
$projectAlreadyExisted = Test-Path $projectRoot

if ($WithMiro -and $NoInitialCommit) {
    throw "-NoInitialCommit nelze kombinovat s -WithMiro. Projektový Miro bootstrap vyžaduje čistý projektový Git repozitář."
}

Write-Host "=== DDDA první spuštění ==="
Write-Host "Platforma: $platformRoot"
Write-Host "Workspace: $workspaceFull"
Write-Host "Example:   $projectId"

$afterCloneArguments = @("-PlatformPath", $platformRoot)
if ($WithMiro) { $afterCloneArguments += "-WithMiro" }
if ($Full) { $afterCloneArguments += "-Full" }
if ($ResetToken) { $afterCloneArguments += "-ResetToken" }
if ($KeepArtifacts) { $afterCloneArguments += "-KeepArtifacts" }
if ($CleanupOnFailure) { $afterCloneArguments += "-CleanupOnFailure" }
if ($ForceRecreateRuntime) { $afterCloneArguments += "-ForceRecreateRuntime" }
if ($NonInteractive) { $afterCloneArguments += "-NonInteractive" }

Write-Host ""
Write-Host "=== 1/5 Platforma po clone ==="
Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAAfterClone.ps1") -Arguments $afterCloneArguments

Write-Host ""
Write-Host "=== 2/5 Workspace ==="
if (-not (Test-Path $workspaceFile)) {
    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAWorkspace.ps1") -Arguments @(
        "-WorkspaceRoot", $workspaceFull,
        "-WorkspaceId", "ddda-example-workspace",
        "-WorkspaceName", "DDDA Example Workspace"
    )
}
else {
    Write-Host "Existující workspace bude znovu použit: $workspaceFull"
}

Write-Host ""
Write-Host "=== 3/5 Referenční example projekt ==="
if (-not (Test-Path $projectRoot)) {
    $exampleArguments = @(
        "-WorkspaceRoot", $workspaceFull,
        "-PlatformPath", $platformRoot
    )
    if ($NoInitialCommit) { $exampleArguments += "-NoInitialCommit" }

    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/New-DDDAExampleProject.ps1") -Arguments $exampleArguments
}
else {
    $workspaceText = Get-Content $workspaceFile -Raw -Encoding UTF8
    if ($workspaceText -notmatch "(?m)^\s*-\s+id:\s*$([regex]::Escape($projectId))\s*$") {
        throw "Projektový adresář existuje, ale projekt '$projectId' není registrován ve workspace.yaml: $projectRoot"
    }
    if (-not (Test-Path (Join-Path $projectRoot "artifacts/align/project-charter.yaml"))) {
        throw "Existující projekt není materializovaný referenční example: $projectRoot"
    }
    Write-Host "Existující referenční example projekt bude znovu použit: $projectRoot"
}

Write-Host ""
Write-Host "=== 4/5 Workspace a projektové kontroly ==="
Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Test-DDDAInstallation.ps1") -Arguments @(
    "-PlatformPath", $platformRoot,
    "-WorkspaceRoot", $workspaceFull,
    "-ProjectPath", $projectRoot
)

if ($WithMiro) {
    Write-Host ""
    Write-Host "=== 5/5 Projektový Miro board a online smoke test ==="
    $projectMiroArguments = @(
        "-PlatformPath", $platformRoot,
        "-WorkspaceRoot", $workspaceFull,
        "-ProjectId", $projectId,
        "-CreateBoard"
    )
    if ($projectAlreadyExisted) { $projectMiroArguments += "-Resume" }
    if ($NonInteractive) { $projectMiroArguments += "-NonInteractive" }

    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAProjectMiro.ps1") -Arguments $projectMiroArguments
}
else {
    Write-Host ""
    Write-Host "=== 5/5 Projektový Miro board ==="
    Write-Host "Přeskočeno. Pro online první spuštění použij -WithMiro."
}

Write-Host ""
Write-Host "DDDA první spuštění: PASS"
Write-Host "Workspace: $workspaceFull"
Write-Host "Projekt:   $projectRoot"
Write-Host "Otevření:  cursor `"$(Join-Path $workspaceFull 'DDDA.code-workspace')`""
if ($WithMiro) {
    Write-Host "Miro map:  $(Join-Path $projectRoot 'miro/miro-map.yaml')"
    Write-Host "Sync state: $(Join-Path $projectRoot 'miro/sync-state.yaml')"
    Write-Host "Sync reporty: $(Join-Path $projectRoot 'reports/miro-sync')"
    Write-Host "Miro mapping, sync state a sync reporty zkontroluj a commituj samostatně; skript commit ani push neprovádí."
}
