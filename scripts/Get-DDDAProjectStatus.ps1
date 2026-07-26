[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [switch]$Json,
    [switch]$Refresh
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "private/DDDASteeringSupport.ps1")

$platformRoot = (Resolve-Path $PlatformPath).Path
$projectRoot = (Resolve-Path $ProjectPath).Path
Assert-DDDAProjectGitRoot -ProjectRoot $projectRoot

if ($Refresh) {
    $result = Invoke-DDDASteeringJson -PlatformRoot $platformRoot -Arguments @(
        "status",
        "--platform-root", $platformRoot,
        "--project-root", $projectRoot
    )
}
else {
    $reportPath = Join-Path $projectRoot "reports/project-status.yaml"
    if (-not (Test-Path -LiteralPath $reportPath)) {
        throw "Status report neexistuje: $reportPath. Spusť příkaz znovu s -Refresh."
    }

    $pythonExe = Get-DDDASteeringPythonExe -PlatformRoot $platformRoot
    $pythonCode = @'
import json
import sys
from pathlib import Path
from ruamel.yaml import YAML

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

path = Path(sys.argv[1])
with path.open("r", encoding="utf-8-sig") as handle:
    document = YAML(typ="safe").load(handle) or {}

report = document.get("status_report")
if not isinstance(report, dict):
    raise SystemExit(f"Status report nemá objekt status_report: {path}")

print(json.dumps(report, ensure_ascii=False))
'@

    $output = & $pythonExe -c $pythonCode $reportPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Načtení DDDA status reportu selhalo:`n$($output | Out-String)"
    }

    $text = ($output | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) {
        throw "Načtení DDDA status reportu nevrátilo výsledek."
    }
    $result = $text | ConvertFrom-Json
}

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
