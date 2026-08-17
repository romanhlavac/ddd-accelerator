[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [string]$Gate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "private/DDDASteeringSupport.ps1")

$platformRoot = (Resolve-Path $PlatformPath).Path
$projectRoot = (Resolve-Path $ProjectPath).Path
$result = Invoke-DDDASteeringJson -PlatformRoot $platformRoot -Arguments @(
    "status",
    "--platform-root", $platformRoot,
    "--project-root", $projectRoot
)
$gates = @($result.gates)
if (-not [string]::IsNullOrWhiteSpace($Gate)) {
    $gates = @($gates | Where-Object { $_.gate -eq $Gate })
    if ($gates.Count -eq 0) { throw "Gate '$Gate' nebyla nalezena." }
}
foreach ($item in $gates) {
    Write-Host ("{0} {1}: {2}" -f $item.gate, $item.stage, $item.status)
    foreach ($missing in @($item.missing)) { Write-Host "  CHYBÍ: $missing" }
}
