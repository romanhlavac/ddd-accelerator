[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$WithMiro,
    [switch]$Full,
    [switch]$ResetToken,
    [switch]$KeepArtifacts,
    [switch]$CleanupOnFailure,
    [switch]$ForceRecreateRuntime,
    [switch]$NonInteractive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {}

. (Join-Path $PSScriptRoot "private/DDDAMiroSupport.ps1")

$platformRoot = (Resolve-Path $PlatformPath).Path
$gitRoot = Invoke-DDDAGit -RepositoryPath $platformRoot -Arguments @("rev-parse", "--show-toplevel")
if ([System.IO.Path]::GetFullPath($gitRoot).TrimEnd('\', '/') -ne [System.IO.Path]::GetFullPath($platformRoot).TrimEnd('\', '/')) {
    throw "PlatformPath není Git root DDDA. Zadaná cesta: $platformRoot; Git root: $gitRoot"
}

Assert-DDDACleanGitRepository -RepositoryPath $platformRoot -Label "Platformní"

Write-Host "=== DDDA inicializace po clone ==="
Write-Host "Platforma: $platformRoot"

Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Test-DDDAInstallation.ps1") -Arguments @(
    "-PlatformPath", $platformRoot
)

$pythonCommand = Resolve-DDDAPythonCommand
$installArguments = @("-PlatformPath", $platformRoot, "-PythonCommand", $pythonCommand)
if ($ForceRecreateRuntime) { $installArguments += "-ForceRecreate" }

Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Install-DDDASteeringRuntime.ps1") -Arguments $installArguments
Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Install-DDDAMiroRuntime.ps1") -Arguments $installArguments

$steeringPython = if (Test-DDDAIsWindows) {
    Join-Path $platformRoot ".ddda/runtime/steering-venv/Scripts/python.exe"
}
else {
    Join-Path $platformRoot ".ddda/runtime/steering-venv/bin/python"
}
$miroPython = if (Test-DDDAIsWindows) {
    Join-Path $platformRoot ".ddda/runtime/miro-venv/Scripts/python.exe"
}
else {
    Join-Path $platformRoot ".ddda/runtime/miro-venv/bin/python"
}

if (-not (Test-Path $steeringPython)) { throw "DDDA steering runtime nebyl vytvořen: $steeringPython" }
if (-not (Test-Path $miroPython)) { throw "DDDA Miro runtime nebyl vytvořen: $miroPython" }

& $steeringPython -m ddda_steering --help *> $null
Assert-DDDALastExitCode -Operation "Ověření DDDA steering CLI"
& $miroPython -m ddda_miro --help *> $null
Assert-DDDALastExitCode -Operation "Ověření DDDA Miro CLI"

Assert-DDDACleanGitRepository -RepositoryPath $platformRoot -Label "Platformní"
Write-Host "Offline inicializace po clone: PASS"

if ($WithMiro) {
    $smokeArguments = @("-PlatformPath", $platformRoot, "-SkipRuntimeInstall")
    if ($Full) { $smokeArguments += "-Full" }
    if ($ResetToken) { $smokeArguments += "-ResetToken" }
    if ($KeepArtifacts) { $smokeArguments += "-KeepArtifacts" }
    if ($CleanupOnFailure) { $smokeArguments += "-CleanupOnFailure" }
    if ($NonInteractive) { $smokeArguments += "-NonInteractive" }
    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Invoke-DDDAMiroSmokeTest.ps1") -Arguments $smokeArguments
}

Write-Host ""
Write-Host "DDDA inicializace po clone: PASS"
Write-Host "Další krok: spusť Initialize-DDDAFirstRun.ps1 pro example nebo Initialize-DDDAProjectFirstRun.ps1 pro vlastní intake."
