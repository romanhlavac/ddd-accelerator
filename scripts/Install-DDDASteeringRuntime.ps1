[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$PythonCommand = "python",
    [switch]$ForceRecreate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$platformRoot = [System.IO.Path]::GetFullPath($PlatformPath)
$runtimeRoot = Join-Path $platformRoot "runtime\steering"
$venvRoot = Join-Path $platformRoot ".ddda\runtime\steering-venv"
$pythonExe = if ($env:OS -eq "Windows_NT" -or $PSVersionTable.PSEdition -eq "Desktop") {
    Join-Path $venvRoot "Scripts\python.exe"
}
else {
    Join-Path $venvRoot "bin/python"
}

if (-not (Test-Path (Join-Path $runtimeRoot "pyproject.toml"))) {
    throw "Steering runtime nebyl nalezen: $runtimeRoot"
}
if ($ForceRecreate -and (Test-Path $venvRoot)) {
    Remove-Item -Recurse -Force $venvRoot
}
if (-not (Test-Path $pythonExe)) {
    & $PythonCommand -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) { throw "Vytvoření steering Python virtual environment selhalo." }
}
& $pythonExe -m pip install --disable-pip-version-check -e $runtimeRoot
if ($LASTEXITCODE -ne 0) { throw "Instalace DDDA steering runtime selhala." }
& $pythonExe -m ddda_steering --help *> $null
if ($LASTEXITCODE -ne 0) { throw "Ověření DDDA steering CLI selhalo." }
Write-Host "DDDA steering runtime je připraven."
Write-Host "Python: $pythonExe"
