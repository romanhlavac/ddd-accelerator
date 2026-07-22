[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [ValidateRange(30, 86400)][int]$IntervalSeconds = 60,
    [int]$MaxCycles,
    [switch]$IncludeLayout
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$platformRoot = [System.IO.Path]::GetFullPath($PlatformPath)
$projectRoot = [System.IO.Path]::GetFullPath($ProjectPath)
$pythonExe = Join-Path $platformRoot ".ddda\runtime\miro-venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) { throw "DDDA Miro runtime není nainstalován. Spusť nejprve .\scripts\Install-DDDAMiroRuntime.ps1." }
$arguments = @("-m", "ddda_miro", "--project", $projectRoot, "--platform", $platformRoot,
    "watch", "--interval-seconds", $IntervalSeconds)
if ($MaxCycles -gt 0) { $arguments += @("--max-cycles", $MaxCycles) }
if ($IncludeLayout) { $arguments += "--include-layout" }
Write-Host "DDDA Miro sync worker běží. Ukončení: Ctrl+C."
& $pythonExe @arguments
exit $LASTEXITCODE
