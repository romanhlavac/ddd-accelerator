[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("doctor", "test", "validate-pr", "promote-pr")]
    [string]$Command,

    [ValidateSet("lint", "schema", "unit", "component", "integration", "smoke", "regression", "security", "e2e", "acceptance", "all")]
    [string]$Suite,

    [int]$Pr,
    [string]$Version,
    [string]$PackagePath,
    [switch]$WithMiro,
    [switch]$Full,
    [switch]$CleanupOnFailure,
    [switch]$KeepArtifacts,
    [switch]$KeepReviewBoard,
    [string]$MiroTeamId,
    [switch]$NonInteractive,
    [switch]$ConfirmMerge,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {}

$platformRoot = (Resolve-Path $PSScriptRoot).Path
$hostExe = (Get-Process -Id $PID).Path

function Invoke-DDDACommandScript {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [string[]]$Arguments = @()
    )

    $scriptPath = Join-Path $platformRoot $RelativePath
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "DDDA command implementation neexistuje: $scriptPath"
    }

    $hostArguments = @("-NoProfile")
    if ($env:OS -eq "Windows_NT" -or $PSVersionTable.PSEdition -eq "Desktop") {
        $hostArguments += @("-ExecutionPolicy", "Bypass")
    }
    $hostArguments += @("-File", $scriptPath)
    $hostArguments += $Arguments

    & $hostExe @hostArguments
    if ($LASTEXITCODE -ne 0) {
        throw "DDDA command '$Command' selhal. Exit code: $LASTEXITCODE"
    }
}

switch ($Command) {
    "doctor" {
        $arguments = @("-PlatformPath", $platformRoot)
        Invoke-DDDACommandScript -RelativePath "scripts/Test-DDDAInstallation.ps1" -Arguments $arguments
        Write-Host ""
        Write-Host "DDDA doctor: PASS"
    }
    "test" {
        if ([string]::IsNullOrWhiteSpace($Suite)) {
            throw "Příkaz test vyžaduje -Suite."
        }
        $arguments = @("-PlatformPath", $platformRoot, "-Suite", $Suite)
        if (-not [string]::IsNullOrWhiteSpace($PackagePath)) { $arguments += @("-PackagePath", $PackagePath) }
        if ($WithMiro) { $arguments += "-WithMiro" }
        if ($Full) { $arguments += "-Full" }
        if ($CleanupOnFailure) { $arguments += "-CleanupOnFailure" }
        if ($KeepReviewBoard) { $arguments += "-KeepReviewBoard" }
        if (-not [string]::IsNullOrWhiteSpace($MiroTeamId)) { $arguments += @("-MiroTeamId", $MiroTeamId) }
        if ($NonInteractive) { $arguments += "-NonInteractive" }
        Invoke-DDDACommandScript -RelativePath "scripts/platform/Invoke-DDDAPlatformTest.ps1" -Arguments $arguments
    }
    "validate-pr" {
        if ($Pr -le 0) {
            throw "Příkaz validate-pr vyžaduje kladné -Pr."
        }
        $arguments = @("-PlatformPath", $platformRoot, "-Pr", [string]$Pr)
        if ($WithMiro) { $arguments += "-WithMiro" }
        if ($Full) { $arguments += "-Full" }
        if ($CleanupOnFailure) { $arguments += "-CleanupOnFailure" }
        if ($KeepArtifacts) { $arguments += "-KeepArtifacts" }
        if ($KeepReviewBoard) { $arguments += "-KeepReviewBoard" }
        if (-not [string]::IsNullOrWhiteSpace($MiroTeamId)) { $arguments += @("-MiroTeamId", $MiroTeamId) }
        if ($NonInteractive) { $arguments += "-NonInteractive" }
        Invoke-DDDACommandScript -RelativePath "scripts/platform/Invoke-DDDAValidatePr.ps1" -Arguments $arguments
    }
    "promote-pr" {
        if ($Pr -le 0) {
            throw "Příkaz promote-pr vyžaduje kladné -Pr."
        }
        if ([string]::IsNullOrWhiteSpace($Version)) {
            throw "Příkaz promote-pr vyžaduje -Version."
        }
        $arguments = @("-PlatformPath", $platformRoot, "-Pr", [string]$Pr, "-Version", $Version)
        if ($ConfirmMerge) { $arguments += "-ConfirmMerge" }
        if ($WithMiro) { $arguments += "-WithMiro" }
        if ($Full) { $arguments += "-Full" }
        if ($CleanupOnFailure) { $arguments += "-CleanupOnFailure" }
        if ($KeepArtifacts) { $arguments += "-KeepArtifacts" }
        if ($KeepReviewBoard) { $arguments += "-KeepReviewBoard" }
        if (-not [string]::IsNullOrWhiteSpace($MiroTeamId)) { $arguments += @("-MiroTeamId", $MiroTeamId) }
        if ($NonInteractive) { $arguments += "-NonInteractive" }
        if ($DryRun) { $arguments += "-DryRun" }
        Invoke-DDDACommandScript -RelativePath "scripts/platform/Invoke-DDDAPromotePr.ps1" -Arguments $arguments
    }
}
