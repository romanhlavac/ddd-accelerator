[CmdletBinding()]
param(
    [switch]$SkipViews,
    [switch]$DoNotOpenProject,
    [switch]$DoNotPublishReport
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repository = "romanhlavac/ddd-accelerator"
$evidenceIssue = 42
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$initializer = Join-Path $PSScriptRoot "Initialize-DDDAGitHubGovernance.ps1"

if (-not (Test-Path -LiteralPath $initializer -PathType Leaf)) {
    throw "Initializer script was not found: $initializer"
}

Push-Location $repoRoot
try {
    # Use hashtable splatting for PowerShell script parameters. Array splatting
    # passes values positionally and would treat '-OpenProject' as an argument
    # value instead of a named switch.
    $initializerParameters = @{
        Apply = $true
    }
    if (-not $DoNotOpenProject) {
        $initializerParameters["OpenProject"] = $true
    }
    if ($SkipViews) {
        $initializerParameters["SkipViews"] = $true
    }

    & $initializer @initializerParameters
    if (-not $?) {
        throw "GitHub governance initialization failed."
    }

    $report = Get-ChildItem -LiteralPath $repoRoot -Filter "ddda-github-governance-setup-*.md" -File |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1

    if (-not $report) {
        throw "The initializer completed but no setup report was found in $repoRoot."
    }

    if (-not $DoNotPublishReport) {
        & gh issue comment $evidenceIssue -R $repository --body-file $report.FullName
        if ($LASTEXITCODE -ne 0) {
            throw "The setup succeeded, but publishing the report to Issue #$evidenceIssue failed. Report: $($report.FullName)"
        }
        Write-Host "Evidence report published to Issue #$evidenceIssue." -ForegroundColor Green
    }
    else {
        Write-Host "Evidence report retained locally: $($report.FullName)" -ForegroundColor Yellow
    }

    Write-Host "GitHub governance setup completed." -ForegroundColor Green
}
finally {
    Pop-Location
}
