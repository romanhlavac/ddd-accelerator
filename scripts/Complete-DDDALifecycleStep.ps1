[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [Parameter(Mandatory = $true)][ValidateSet("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")][string]$Gate,
    [Parameter(Mandatory = $true)][ValidateSet("passed", "conditional", "rejected")][string]$Outcome,
    [Parameter(Mandatory = $true)][string]$Reviewer,
    [string]$Note,
    [string[]]$Condition = @(),
    [switch]$Commit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "private/DDDASteeringSupport.ps1")

$platformRoot = (Resolve-Path $PlatformPath).Path
$projectRoot = (Resolve-Path $ProjectPath).Path
Assert-DDDAProjectGitRoot -ProjectRoot $projectRoot
$arguments = @(
    "review-gate",
    "--platform-root", $platformRoot,
    "--project-root", $projectRoot,
    "--gate", $Gate,
    "--outcome", $Outcome,
    "--reviewer", $Reviewer
)
if (-not [string]::IsNullOrWhiteSpace($Note)) { $arguments += @("--note", $Note) }
foreach ($value in $Condition) { $arguments += @("--condition", $value) }
$result = Invoke-DDDASteeringJson -PlatformRoot $platformRoot -Arguments $arguments

Write-Host "Gate $Gate: $Outcome"
Write-Host "Aktuální fáze: $($result.current_stage)"
Write-Host "Další gate: $($result.next_gate)"
Write-Host "Před commitem zkontroluj: git -C `"$projectRoot`" diff"

if ($Commit) {
    & git -C $projectRoot diff --check
    if ($LASTEXITCODE -ne 0) { throw "Git diff --check selhal." }
    & git -C $projectRoot add project.yaml decisions/gates artifacts/status reports/project-status.yaml
    if ($LASTEXITCODE -ne 0) { throw "Git add gate změn selhal." }
    & git -C $projectRoot commit -m "docs(gate): record $Gate $Outcome"
    if ($LASTEXITCODE -ne 0) { throw "Gate commit selhal." }
    Write-Host "Gate commit byl vytvořen. Push ani merge nebyl proveden."
}
