[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$CreateBoard,
    [switch]$DryRun
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$platformRoot = [System.IO.Path]::GetFullPath($PlatformPath)
$projectRoot = [System.IO.Path]::GetFullPath($ProjectPath)
$pythonExe = Join-Path $platformRoot ".ddda\runtime\miro-venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) { throw "DDDA Miro runtime není nainstalován. Spusť nejprve .\scripts\Install-DDDAMiroRuntime.ps1." }
$arguments = @("-m", "ddda_miro", "--project", $projectRoot, "--platform", $platformRoot, "render")
if ($CreateBoard) { $arguments += "--create-board" }
if ($DryRun) { $arguments += "--dry-run" }
& $pythonExe @arguments
exit $LASTEXITCODE
