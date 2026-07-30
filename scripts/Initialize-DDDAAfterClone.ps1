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
$packageManifestPath = Join-Path $platformRoot "ddda-package.json"
$isPackageDistribution = Test-Path -LiteralPath $packageManifestPath -PathType Leaf
$isGitDistribution = -not $isPackageDistribution -and (Test-Path -LiteralPath (Join-Path $platformRoot ".git"))

if ($isPackageDistribution) {
    $packageManifest = Get-Content -LiteralPath $packageManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($packageManifest.schema_version -ne 1) {
        throw "Nepodporovaná verze DDDA package manifestu."
    }
}
elseif ($isGitDistribution) {
    $gitRoot = Invoke-DDDAGit -RepositoryPath $platformRoot -Arguments @("rev-parse", "--show-toplevel")
    if ([System.IO.Path]::GetFullPath($gitRoot).TrimEnd('\', '/') -ne [System.IO.Path]::GetFullPath($platformRoot).TrimEnd('\', '/')) {
        throw "PlatformPath není Git root DDDA. Zadaná cesta: $platformRoot; Git root: $gitRoot"
    }
    Assert-DDDACleanGitRepository -RepositoryPath $platformRoot -Label "Platformní"
}
else {
    throw "PlatformPath není Git distribuce ani rozbalený DDDA package: $platformRoot"
}

Write-Host "=== DDDA inicializace distribuce ==="
Write-Host "Platforma: $platformRoot"
Write-Host "Typ:       $(if ($isPackageDistribution) { 'package' } else { 'git' })"

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

& $steeringPython -I -m ddda_steering --help *> $null
Assert-DDDALastExitCode -Operation "Ověření DDDA steering CLI"
& $miroPython -I -m ddda_miro --help *> $null
Assert-DDDALastExitCode -Operation "Ověření DDDA Miro CLI"

if ($isGitDistribution) {
    Assert-DDDACleanGitRepository -RepositoryPath $platformRoot -Label "Platformní"
}
Write-Host "Offline inicializace distribuce: PASS"

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
Write-Host "DDDA inicializace distribuce: PASS"
Write-Host "Další krok: spusť Initialize-DDDAFirstRun.ps1 pro example nebo Initialize-DDDAProjectFirstRun.ps1 pro vlastní intake."
