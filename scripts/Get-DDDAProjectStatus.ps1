[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "private/DDDASteeringSupport.ps1")

$platformRoot = (Resolve-Path $PlatformPath).Path
$projectRoot = (Resolve-Path $ProjectPath).Path
Assert-DDDAProjectGitRoot -ProjectRoot $projectRoot
$result = Invoke-DDDASteeringJson -PlatformRoot $platformRoot -Arguments @(
    "status",
    "--platform-root", $platformRoot,
    "--project-root", $projectRoot
)
if ($Json) {
    $result | ConvertTo-Json -Depth 20
    return
}
Write-Host "DDDA project status"
Write-Host "Fáze:       $($result.current_stage)"
Write-Host "Další gate: $($result.next_gate)"
Write-Host "Další kroky:"
foreach ($action in @($result.next_actions)) { Write-Host "- $action" }
Write-Host ""
Write-Host "Doporučený prompt:"
Write-Host $result.chat_prompt
