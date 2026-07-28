[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [Parameter(Mandatory = $true)][string]$WorkspaceRoot,
    [Parameter(Mandatory = $true)][string]$IntakeFile,
    [switch]$WithMiro,
    [switch]$Full,
    [switch]$ResetToken,
    [switch]$KeepArtifacts,
    [switch]$CleanupOnFailure,
    [switch]$ForceRecreateRuntime,
    [switch]$NonInteractive,
    [switch]$NoInitialCommit,
    [switch]$Resume
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {}

. (Join-Path $PSScriptRoot "private/DDDASteeringSupport.ps1")

$platformRoot = (Resolve-Path $PlatformPath).Path
$workspaceFull = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$intakeFull = (Resolve-Path $IntakeFile).Path

if ($WithMiro -and $NoInitialCommit) {
    throw "-NoInitialCommit nelze kombinovat s -WithMiro. Projektový Miro bootstrap vyžaduje čistý projektový Git repozitář."
}

$pythonCommand = Resolve-DDDAPythonCommand
$installArgs = @("-PlatformPath", $platformRoot, "-PythonCommand", $pythonCommand)
if ($ForceRecreateRuntime) { $installArgs += "-ForceRecreate" }
Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Install-DDDASteeringRuntime.ps1") -Arguments $installArgs

$summary = Invoke-DDDASteeringJson -PlatformRoot $platformRoot -Arguments @(
    "intake-summary",
    "--platform-root", $platformRoot,
    "--intake", $intakeFull
)
$projectId = [string]$summary.project_id
$projectName = [string]$summary.name
$projectType = [string]$summary.type
$projectTypeAlias = if ($null -eq $summary.type_alias) { $null } else { [string]$summary.type_alias }
$projectRoot = Join-Path (Join-Path $workspaceFull "projects") $projectId
$workspaceFile = Join-Path $workspaceFull "workspace.yaml"
$projectExists = Test-Path $projectRoot

function Get-DDDAFirstRunFileHash {
    param([Parameter(Mandatory = $true)][string]$Path)

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-DDDAFirstRunOptionalOrigin {
    param([Parameter(Mandatory = $true)][string]$RepositoryPath)

    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = @(& git -C $RepositoryPath remote get-url origin 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    if ($exitCode -ne 0) {
        return $null
    }

    return (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
}

$legacyProtectedState = $null

Write-Host "=== DDDA řízený první start projektu ==="
Write-Host "Platforma: $platformRoot"
Write-Host "Workspace: $workspaceFull"
Write-Host "Projekt:   $projectId"
Write-Host "Typ:       $projectType"

if (-not (Test-Path $workspaceFile)) {
    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAWorkspace.ps1") -Arguments @(
        "-WorkspaceRoot", $workspaceFull,
        "-WorkspaceId", "ddda-workspace",
        "-WorkspaceName", "DDDA Workspace"
    )
}

if (-not $projectExists) {
    $createArgs = @(
        "-WorkspaceRoot", $workspaceFull,
        "-ProjectId", $projectId,
        "-Name", $projectName,
        "-Type", $projectType,
        "-NoInitialCommit"
    )
    if (-not [string]::IsNullOrWhiteSpace($projectTypeAlias)) {
        $createArgs += @("-TypeAlias", $projectTypeAlias)
    }
    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/New-DDDAProject.ps1") -Arguments $createArgs
}
elseif (-not $Resume) {
    throw "Projekt již existuje: $projectRoot. Pro bezpečné pokračování použij -Resume."
}

Assert-DDDAProjectGitRoot -ProjectRoot $projectRoot
if ($projectExists -and $Resume) {
    $status = Invoke-DDDAGit -RepositoryPath $projectRoot -Arguments @("status", "--porcelain")
    if (-not [string]::IsNullOrWhiteSpace($status)) {
        $allowed = @($status -split "`r?`n" | Where-Object { $_ -and $_ -notmatch '^.. (project-intake.yaml|project-profile.yaml|lifecycle-tailoring.yaml|artifacts/|decisions/|reports/|\.ddda/|project.yaml|miro/)' })
        if ($allowed.Count -gt 0) {
            throw "Resume odmítnut: projekt obsahuje změny mimo řízené DDDA cesty:`n$($allowed -join "`n")"
        }
    }

    $protectedPaths = @("project.yaml", "ddda.lock.yaml")
    $miroMapPath = Join-Path $projectRoot "miro/miro-map.yaml"
    if (Test-Path -LiteralPath $miroMapPath -PathType Leaf) {
        $protectedPaths += "miro/miro-map.yaml"
    }

    $protectedHashes = @{}
    foreach ($relativePath in $protectedPaths) {
        $fullPath = Join-Path $projectRoot $relativePath
        if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
            throw "Legacy resume vyžaduje preserved file: $relativePath"
        }
        $protectedHashes[$relativePath] = Get-DDDAFirstRunFileHash -Path $fullPath
    }

    $legacyProtectedState = [pscustomobject]@{
        hashes = $protectedHashes
        workspace_hash = Get-DDDAFirstRunFileHash -Path $workspaceFile
        origin = Get-DDDAFirstRunOptionalOrigin -RepositoryPath $projectRoot
    }
}

$bootstrapArguments = @(
    "bootstrap",
    "--platform-root", $platformRoot,
    "--project-root", $projectRoot,
    "--intake", $intakeFull
)
if ($projectExists -and $Resume) {
    $bootstrapArguments += "--preserve-project-manifest"
}
$result = Invoke-DDDASteeringJson -PlatformRoot $platformRoot -Arguments $bootstrapArguments

if ($null -ne $legacyProtectedState) {
    foreach ($relativePath in @($legacyProtectedState.hashes.Keys)) {
        $actualHash = Get-DDDAFirstRunFileHash -Path (Join-Path $projectRoot $relativePath)
        if ($actualHash -ne [string]$legacyProtectedState.hashes[$relativePath]) {
            throw "Legacy resume změnil preserved file '$relativePath'."
        }
    }

    $actualWorkspaceHash = Get-DDDAFirstRunFileHash -Path $workspaceFile
    if ($actualWorkspaceHash -ne [string]$legacyProtectedState.workspace_hash) {
        throw "Legacy resume změnil workspace.yaml."
    }

    $actualOrigin = Get-DDDAFirstRunOptionalOrigin -RepositoryPath $projectRoot
    if ($actualOrigin -ne [string]$legacyProtectedState.origin) {
        throw "Legacy resume změnil repository ownership/origin."
    }
}

if (-not $NoInitialCommit) {
    & git -C $projectRoot add .
    if ($LASTEXITCODE -ne 0) { throw "Git add projektu selhal." }
    $changes = Invoke-DDDAGit -RepositoryPath $projectRoot -Arguments @("status", "--porcelain")
    if (-not [string]::IsNullOrWhiteSpace($changes)) {
        & git -C $projectRoot commit -m "chore: initialize DDDA project steering"
        if ($LASTEXITCODE -ne 0) { throw "Iniciační commit projektu selhal. Ověř git config user.name a user.email." }
    }
}

Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Test-DDDAInstallation.ps1") -Arguments @(
    "-PlatformPath", $platformRoot,
    "-WorkspaceRoot", $workspaceFull,
    "-ProjectPath", $projectRoot
)

if ($WithMiro) {
    $miroArgs = @(
        "-PlatformPath", $platformRoot,
        "-WorkspaceRoot", $workspaceFull,
        "-ProjectId", $projectId,
        "-CreateBoard"
    )
    if ($projectExists -or $Resume) { $miroArgs += "-Resume" }
    if ($ResetToken) { $miroArgs += "-ResetToken" }
    if ($ForceRecreateRuntime) { $miroArgs += "-ForceRecreateRuntime" }
    if ($NonInteractive) { $miroArgs += "-NonInteractive" }
    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAProjectMiro.ps1") -Arguments $miroArgs
}

Write-Host ""
Write-Host "DDDA řízený první start projektu: PASS"
Write-Host "Projekt:       $projectRoot"
Write-Host "Aktuální fáze: $($result.current_stage)"
Write-Host "Další gate:    $($result.next_gate)"
Write-Host "Status:        $(Join-Path $projectRoot 'artifacts/status/current-status.yaml')"
Write-Host "Další kroky:   $(Join-Path $projectRoot 'artifacts/status/next-actions.yaml')"
if ($WithMiro) {
    Write-Host "Miro mapping, sync state a sync report zkontroluj a commituj samostatně; token se do Gitu nezapisuje."
}
