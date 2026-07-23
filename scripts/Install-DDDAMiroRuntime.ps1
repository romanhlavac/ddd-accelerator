[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$PythonCommand = "python",
    [switch]$ForceRecreate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$platformRoot = [System.IO.Path]::GetFullPath($PlatformPath)
$runtimeRoot = Join-Path $platformRoot "runtime\miro"
$venvRoot = Join-Path $platformRoot ".ddda\runtime\miro-venv"
$pythonExe = Join-Path $venvRoot "Scripts\python.exe"
if (-not (Test-Path (Join-Path $runtimeRoot "pyproject.toml"))) { throw "Miro runtime nebyl nalezen: $runtimeRoot" }
if ($ForceRecreate -and (Test-Path $venvRoot)) { Remove-Item -Recurse -Force $venvRoot }
if (-not (Test-Path $pythonExe)) {
    & $PythonCommand -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) { throw "Vytvoření Python virtual environment selhalo." }
}
& $pythonExe -m pip install --disable-pip-version-check -e $runtimeRoot
if ($LASTEXITCODE -ne 0) { throw "Instalace DDDA Miro runtime selhala." }
Write-Host "DDDA Miro runtime je připraven."
Write-Host "Python: $pythonExe"
Write-Host "Ověření: & `"$pythonExe`" -m ddda_miro --help"
