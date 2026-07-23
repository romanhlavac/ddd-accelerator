[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [ValidateSet("Pull", "Push", "Both")][string]$Direction = "Both",
    [switch]$DryRun,
    [switch]$IncludeLayout,
    [switch]$ConfirmDelete,
    [switch]$RecreateMissing,
    [switch]$PromoteNew
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$platformRoot = [System.IO.Path]::GetFullPath($PlatformPath)
$projectRoot = [System.IO.Path]::GetFullPath($ProjectPath)
$pythonExe = Join-Path $platformRoot ".ddda\runtime\miro-venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) { throw "DDDA Miro runtime není nainstalován. Spusť nejprve .\scripts\Install-DDDAMiroRuntime.ps1." }
$arguments = @("-m", "ddda_miro", "--project", $projectRoot, "--platform", $platformRoot,
    "sync", "--direction", $Direction.ToLowerInvariant())
if ($DryRun) { $arguments += "--dry-run" }
if ($IncludeLayout) { $arguments += "--include-layout" }
if ($ConfirmDelete) { $arguments += "--confirm-delete" }
if ($RecreateMissing) { $arguments += "--recreate-missing" }
if ($PromoteNew) { $arguments += "--promote-new" }
& $pythonExe @arguments
exit $LASTEXITCODE
