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
    $readerScript = Join-Path $platformRoot "runtime/steering/read_status.py"
    if (-not (Test-Path -LiteralPath $readerScript)) {
        throw "Read-only status reader neexistuje: $readerScript"
    }

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = @(& $pythonExe $readerScript $reportPath 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    $text = ($output | ForEach-Object { $_.ToString() } | Out-String).Trim()
    if ($exitCode -ne 0) {
        throw "Načtení DDDA status reportu selhalo. Exit code: $exitCode`n$text"
    }
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
